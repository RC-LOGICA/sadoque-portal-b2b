import sys
import os
import streamlit as st
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

# 1. Configuração inicial da página (Mantenha o layout="wide" para destrancar os limites padrão)
st.set_page_config(page_title="Portal do Embarcador | SADOQUE TRANSPORTES", page_icon="📦", layout="wide")
load_dotenv()

# ==============================================================================
# DESIGN SYSTEM PROFISSIONAL (Responsivo + Correção de Inputs)
# ==============================================================================
estilo_flutuante = """
    <style>
    /* 1. Oculta barra superior e rodapé padrão do Streamlit */
    [data-testid="stHeader"], footer { display: none !important; }

    /* 2. O FUNDO ABSOLUTO DO NAVEGADOR */
    .stApp {
        background-color: #03060A !important;
    }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: transparent !important;
    }

    /* 3. A JANELA DA APLICAÇÃO (Desktop) */
    .block-container {
        background-color: #162A45 !important;
        max-width: 1250px !important;
        margin: 5vh auto !important;
        padding: 3rem 4rem !important;
        border-radius: 20px !important;
        box-shadow: 0px 25px 90px rgba(0, 0, 0, 1) !important;
        border: 1px solid #2c4970 !important;
    }

    /* 4. CORREÇÃO DAS CAIXAS DE BUSCA (Fundo escuro e borda) */
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        background-color: #0B132B !important; /* Fundo mais escuro para destacar do painel */
        border: 1px solid #2c4970 !important; /* Borda discreta */
        border-radius: 8px !important;
    }
    
    /* Borda verde (cor da sua paleta) quando o cliente clica para digitar */
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
        border-color: #2a9d8f !important;
    }

    /* 5. RESPONSIVIDADE PARA CELULAR (Ecrãs até 768px) */
    @media (max-width: 768px) {
        .block-container {
            margin: 2vh 3vw !important;
            padding: 1.5rem 1rem !important;
            border-radius: 15px !important;
        }
        
        /* CORREÇÃO DAS LOGOS: Força a imagem real a encolher pela metade */
        [data-testid="stImage"] img {
            max-width: 55% !important;
            margin: 0 auto !important;
            display: block !important;
        }
    }
    </style>
"""
st.markdown(estilo_flutuante, unsafe_allow_html=True)

# ==============================================================================
# LIGAÇÃO SEGURA E BUSCA DE DADOS (ALTA PERFORMANCE - SEM TRAVAMENTOS)
# ==============================================================================
@st.cache_resource
def inicializar_pool():
    try:
        ambiente = os.getenv("AMBIENTE", "PROD").strip().upper()
        if ambiente == "DEV":
            db_url = os.getenv("DATABASE_URL_DEV")
            print("🌐 PORTAL WEB: Iniciado em MODO DEV (Homologação)")
        else:
            # CORREÇÃO ESTRUTURAL: Lendo a variável exata do seu .env
            db_url = os.getenv("DATABASE_URL") 
            print("🌐 PORTAL WEB: Iniciado em MODO PROD (Lendo o Supabase Oficial)")
            
        if not db_url:
            st.error("Variável de ambiente de conexão não encontrada!")
            return None
            
        return ThreadedConnectionPool(1, 20, db_url)
    except Exception as e:
        st.error(f"Erro crítico ao conectar com a base de dados: {e}")
        return None
pool_global = inicializar_pool()

def conectar_banco():
    if not pool_global:
        raise Exception("O Banco de Dados não está inicializado.")
    return pool_global.getconn()

def liberar_conexao(conn):
    """Devolve a conexão para a Pool garantindo que a transação é fechada."""
    if conn and pool_global:
        try:
            conn.rollback()  # 🔓 A MÁGICA: Fecha a leitura e liberta a tabela para o Desktop!
        except:
            pass
        pool_global.putconn(conn)

def validar_login(utilizador, palavra_passe):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT id, cnpj_embarcador, senha_hash, nome_fantasia 
            FROM usuarios_web 
            WHERE login = %s AND ativo = TRUE
        """, (utilizador,))
        user = cursor.fetchone()
        if user and check_password_hash(user['senha_hash'], palavra_passe):
            return user
        return None
    except Exception as e:
        st.error(f"⚠️ Erro ao comunicar com a base de dados: {e}")
        return None
    finally:
        liberar_conexao(conn)

@st.cache_data(ttl=60)
def buscar_dados_cargas(cnpj_cliente):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # MAPEAMENTO FINAL: Coluna 'status_carregamento' inserida na lógica de extração
        cursor.execute("""
            SELECT 
                REGEXP_REPLACE(numero_nf::TEXT, '[^0-9]', '', 'g') as "NF",
                MAX(cliente) as "Destinatário",
                MAX(cidade) || ' / ' || MAX(estado) as "Cidade de Destino",
                MAX(COALESCE(qtd_volumes, 0)) as "Volumes", 
                MAX(COALESCE(NULLIF(data_prev_entrega::TEXT, ''), 'Em cálculo...')) as "Previsão",
                MAX(
                    CASE 
                        WHEN status_carregamento IS NULL THEN 'Na Base'
                        WHEN TRIM(status_carregamento) = '' THEN 'Na Base'
                        WHEN LOWER(TRIM(status_carregamento)) = 'nan' THEN 'Na Base'
                        WHEN status_carregamento ILIKE '%%TR_NSITO%%' THEN 'Em Trânsito'
                        WHEN status_carregamento ILIKE '%%BASE%%' THEN 'Na Base'
                        ELSE UPPER(TRIM(status_carregamento))
                    END
                ) as "Status"
            FROM cargas
            WHERE REGEXP_REPLACE(cnpj_consignatario, '[^0-9]', '', 'g') = REGEXP_REPLACE(%s, '[^0-9]', '', 'g')
            GROUP BY REGEXP_REPLACE(numero_nf::TEXT, '[^0-9]', '', 'g')
            ORDER BY "NF" DESC
        """, (str(cnpj_cliente),))
        
        registos = cursor.fetchall()
        if registos:
            return pd.DataFrame([dict(r) for r in registos])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao buscar cargas: {e}")
        return None
    finally:
        liberar_conexao(conn)

@st.cache_data(ttl=30)
def buscar_historico_nf(numero_nf):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT status, cidade_localizacao, observacao, TO_CHAR(data_registro, 'DD/MM/YYYY HH24:MI') as data_hora
            FROM rastreio_cargas
            WHERE numero_nf = %s
            ORDER BY data_registro DESC
        """, (str(numero_nf),))
        registos = cursor.fetchall()
        if registos:
            return pd.DataFrame([dict(r) for r in registos])
        return pd.DataFrame()
    except Exception:
        return None
    finally:
        liberar_conexao(conn)

# 🚀 FUNÇÃO 1: CORRIGINDO O ALERTA (Removendo conflito de Timezone)
def verificar_alertas_chat(cnpj):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT m.numero_nf 
            FROM mensagens_cargas m
            INNER JOIN cargas c ON m.numero_nf = c.numero_nf
            WHERE c.cnpj_embarcador = %s 
              AND UPPER(m.remetente) != 'CLIENTE'
        """, (str(cnpj),))
        registos = cursor.fetchall()
        if registos:
            return [str(r[0]) for r in registos]
        return []
    except Exception as e:
        return []
    finally:
        liberar_conexao(conn)

# 🚀 FUNÇÃO 2: ORDENAÇÃO CORRETA DAS MENSAGENS (Intercalando o Chat)
def buscar_mensagens(nf, cnpj):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT m.remetente, m.mensagem, 
                   TO_CHAR(m.data_envio AT TIME ZONE 'America/Fortaleza', 'DD/MM HH24:MI') as data_formatada
            FROM mensagens_cargas m
            INNER JOIN cargas c ON m.numero_nf = c.numero_nf
            WHERE m.numero_nf = %s AND c.cnpj_embarcador = %s
            ORDER BY m.data_envio ASC, m.id ASC
        """, (str(nf), str(cnpj)))
        registos = cursor.fetchall()
        if registos:
            return pd.DataFrame([dict(r) for r in registos])
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    finally:
        liberar_conexao(conn)

def salvar_mensagem(nf, cnpj, remetente, texto):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mensagens_cargas (numero_nf, cnpj_embarcador, remetente, mensagem, lida_sadoque)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (str(nf), str(cnpj), remetente, texto))
        conn.commit()
        return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"Erro ao enviar mensagem: {e}")
        return False
    finally:
        liberar_conexao(conn)

# ==============================================================================
# CHAT MANUAL (FIM DOS TRAVAMENTOS DE BANCO DE DADOS)
# ==============================================================================
def exibir_chat(nf_selecionada, cnpj_ativo, nome_empresa):
    st.markdown("---")
    
    col_titulo, col_btn = st.columns([3, 1])
    with col_titulo:
        st.subheader("💬 Canal de Atendimento (Chat)")
    with col_btn:
        if st.button("🔄 Atualizar Mensagens", use_container_width=True):
            st.rerun()
            
    df_mensagens = buscar_mensagens(nf_selecionada, cnpj_ativo)
    
    if not df_mensagens.empty:
        for _, msg_row in df_mensagens.iterrows():
            if msg_row['remetente'] == 'Cliente':
                st.markdown(f"""
                    <div style='background-color:#162A45; padding:10px 15px; border-radius:10px; margin-bottom:10px; margin-left: 20%; text-align:right; border-right: 4px solid #2a9d8f; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                        <span style='font-size:12px; color:#a3b1c6;'>{nome_empresa} • {msg_row['data_formatada']}</span><br>
                        <span style='color:#ffffff; font-size:16px;'>{msg_row['mensagem']}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style='background-color:#1F3A5F; padding:10px 15px; border-radius:10px; margin-bottom:10px; margin-right: 20%; text-align:left; border-left: 4px solid #ffb703; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                        <span style='font-size:12px; color:#a3b1c6;'>Sadoque Transportes • {msg_row['data_formatada']}</span><br>
                        <span style='color:#ffffff; font-size:16px;'>{msg_row['mensagem']}</span>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Nenhuma mensagem registada para esta carga. Caso tenha dúvidas, escreva abaixo.")

    with st.form(f"form_chat_{nf_selecionada}", clear_on_submit=True):
        nova_msg = st.text_area("Digite a sua dúvida ou mensagem:", height=100, placeholder="Ex: Há previsão de chegada para hoje à tarde?")
        btn_enviar_msg = st.form_submit_button("📤 Enviar Mensagem", width="stretch")
        
        if btn_enviar_msg:
            if nova_msg.strip():
                sucesso = salvar_mensagem(nf_selecionada, cnpj_ativo, 'Cliente', nova_msg.strip())
                if sucesso:
                    st.success("Mensagem enviada com sucesso! A Sadoque irá responder brevemente.")
                    st.rerun()
            else:
                st.warning("A mensagem não pode estar vazia.")

# ==============================================================================
# GESTÃO DE SESSÃO
# ==============================================================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'cnpj_ativo' not in st.session_state: st.session_state['cnpj_ativo'] = None
if 'nome_empresa' not in st.session_state: st.session_state['nome_empresa'] = None

# ==============================================================================
# ECRÃ DE LOGIN
# ==============================================================================
def ecra_login():
    estilo_caixa_login = """
        <style>
        [data-testid="stForm"] {
            background-color: #1F3A5F !important;
            border: 1px solid #2C5282 !important;
            border-radius: 15px !important;
            padding: 2.5rem !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5) !important;
        }
        [data-testid="stImage"] img {
            filter: drop-shadow(0px 10px 15px rgba(0, 0, 0, 0.6)) !important;
        }
        div[data-testid="InputInstructions"], div[data-testid="stInputInstructions"] {
            display: none !important; visibility: hidden !important;
        }
        </style>
    """
    st.markdown(estilo_caixa_login, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1.0, 1.2])
    with col2:
        with st.form("form_login"):
            c1, c_img, c2 = st.columns([1, 1.5, 1])
            with c_img:
                caminho_logo = "assets/logo.png" 
                if os.path.exists(caminho_logo):
                    st.image(caminho_logo)
                else:
                    st.markdown("<h3 style='text-align: center; color: #ffb703;'>📦 SADOQUE</h3>", unsafe_allow_html=True)
            
            st.markdown("<p style='text-align: center; color: #a3b1c6; font-size: 14px; margin-top: 10px; margin-bottom: 20px;'>Bem-vindo ao sistema de rastreio corporativo.</p>", unsafe_allow_html=True)
            username = st.text_input("Utilizador")
            password = st.text_input("Palavra-passe", type="password")
            st.markdown("<br>", unsafe_allow_html=True) 
            btn_entrar = st.form_submit_button("Entrar no Sistema", width="stretch")
            if btn_entrar:
                if username and password:
                    dados_cliente = validar_login(username.lower().strip(), password.strip())
                    if dados_cliente:
                        st.session_state['logado'] = True
                        st.session_state['cnpj_ativo'] = dados_cliente['cnpj_embarcador']
                        st.session_state['nome_empresa'] = dados_cliente['nome_fantasia']
                        st.rerun()
                    else:
                        st.error("Utilizador ou palavra-passe incorretos.")
                else:
                    st.warning("Por favor, preencha todos os campos.")

# ==============================================================================
# ECRÃ PRINCIPAL (DASHBOARD)
# ==============================================================================
def ecra_dashboard():
    estilos_dashboard = """
        <style>
        [data-testid="stMetric"] {
            background-color: #1F3A5F !important; border-left: 5px solid #2a9d8f !important; 
            border-radius: 8px !important; padding: 15px 20px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        }
        [data-testid="column"] { align-self: center; }
        </style>
    """
    st.markdown(estilos_dashboard, unsafe_allow_html=True)

    col_sad, col_centro, col_cli = st.columns([1, 2, 1])
    with col_sad:
        caminho_logo_sadoque = "assets/logo.png"
        if os.path.exists(caminho_logo_sadoque):
            st.image(caminho_logo_sadoque, width=140) 
        else:
            st.markdown("<h3 style='color: #ffb703;'>📦 SADOQUE</h3>", unsafe_allow_html=True)

    with col_cli:
        nome_cliente_ativo = st.session_state.get('nome_empresa', 'Cliente')
        cnpj_ativo = st.session_state.get('cnpj_ativo', '')
        caminho_logo_cliente = f"assets/{cnpj_ativo}.png"
        st.markdown(f"<div style='text-align: right; margin-bottom: 5px; color: #a3b1c6;'>Seja bem-vindo,</div>", unsafe_allow_html=True)
        if os.path.exists(caminho_logo_cliente):
            c_vazia, c_img_cli = st.columns([0.5, 1.5])
            with c_img_cli:
                st.image(caminho_logo_cliente, width="stretch")
        else:
            st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 18px; color: #ffffff;'>{nome_cliente_ativo}</div>", unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; color: #a3b1c6; font-size: 18px; font-weight: bold; margin-top: 20px; margin-bottom: 5px;'>Inteligência Logística e Rastreio (B2B)</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 🚨 ALERTA VISUAL INTELIGENTE DE MENSAGENS AQUI 🚨
    nfs_com_resposta = verificar_alertas_chat(st.session_state['cnpj_ativo'])
    if nfs_com_resposta:
        nfs_str = ", ".join(nfs_com_resposta)
        st.warning(f"🔔 **NOVA MENSAGEM DO SUPORTE:** A Sadoque respondeu recentemente no chat das Notas Fiscais: **{nfs_str}**. Desça até o detalhe do rastreio para ler e responder.", icon="🚨")
    
    df_cargas = buscar_dados_cargas(st.session_state['cnpj_ativo'])
    
    if df_cargas is None: return
    if df_cargas.empty:
        st.info("Ainda não existem notas fiscais registadas para o seu CNPJ no sistema.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Terminar Sessão"):
            st.session_state.clear()
            st.rerun()
        return

    st.markdown("### 🔍 Filtros")
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        pesquisa_texto = st.text_input("Procurar por Número da NF ou Destinatário:", "")
    with col_filtro2:
        lista_cidades = ["Todas"] + sorted(df_cargas["Cidade de Destino"].dropna().unique().tolist())
        cidade_selecionada = st.selectbox("Filtrar por Cidade de Destino:", lista_cidades)
        
    df_filtrado = df_cargas.copy()
    if pesquisa_texto:
        f_nf = df_filtrado["NF"].astype(str).str.contains(pesquisa_texto, case=False, na=False)
        f_dest = df_filtrado["Destinatário"].astype(str).str.contains(pesquisa_texto, case=False, na=False)
        df_filtrado = df_filtrado[f_nf | f_dest]
    if cidade_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Cidade de Destino"] == cidade_selecionada]

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
    with col_btn1:
        if st.button("🔄 Atualizar Dados", width="stretch"):
            buscar_dados_cargas.clear()
            st.rerun()
    with col_btn2:
        if st.button("🚪 Terminar Sessão", width="stretch"):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    t_notas = len(df_filtrado)
    t_volumes = int(df_filtrado["Volumes"].fillna(0).sum()) if "Volumes" in df_filtrado.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Notas Exibidas", t_notas)
    c2.metric("Volumes Totais", t_volumes)
    c3.metric("Status Operacional", "Verde 🟢")
    st.markdown("---")
    
    if not df_filtrado.empty:
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("**Distribuição por Status**")
            fig_status = px.pie(df_filtrado, names='Status', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_status, width="stretch")
        with col_graf2:
            st.markdown("**Volume por Cidade (Top 10)**")
            df_cidades = df_filtrado.groupby('Cidade de Destino')['Volumes'].sum().reset_index()
            df_cidades = df_cidades.sort_values(by='Volumes', ascending=False).head(10)
            fig_cidades = px.bar(df_cidades, x='Cidade de Destino', y='Volumes', color='Volumes', color_continuous_scale='Blues')
            st.plotly_chart(fig_cidades, width="stretch")

    st.subheader("Central de Rastreio")
    if df_filtrado.empty:
        st.warning("Nenhuma carga encontrada.")
    else:
        st.dataframe(df_filtrado, width="stretch", hide_index=True)
        csv = df_filtrado.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            label="🗂️ Descarregar Dados (CSV / Excel)", data=csv,
            file_name="relatorio_rastreio_sadoque.csv", mime="text/csv",
        )

    st.markdown("---")
    st.subheader("🔎 Detalhes do Rastreio (Linha do Tempo)")
    
    lista_nfs = ["Selecione uma NF..."] + df_filtrado["NF"].astype(str).tolist()
    nf_selecionada = st.selectbox("Escolha uma Nota Fiscal para ver o histórico detalhado:", lista_nfs)
    
    if nf_selecionada != "Selecione uma NF...":
        df_historico = buscar_historico_nf(nf_selecionada)
        if df_historico is None or df_historico.empty:
            st.warning(f"Ainda não existem registos de movimento para a NF {nf_selecionada}.")
        else:
            st.success(f"**Histórico Oficial da NF: {nf_selecionada}**")
            for index, row in df_historico.iterrows():
                col_time1, col_time2 = st.columns([1, 4])
                
                with col_time1:
                    if index == 0:
                        st.markdown(f"🟢 **{row['data_hora']}**")
                    else:
                        st.markdown(f"⚪ *{row['data_hora']}*")
                        
                with col_time2:
                    cidade_exibicao = str(row['cidade_localizacao'])
                    if cidade_exibicao.lower() in ['nan', 'none', 'nulo', '']:
                        cidade_exibicao = "Em Trânsito / Base"

                    obs = str(row.get('observacao', ''))
                    
                    if index == 0:
                        st.markdown(f"**Status Atual: {row['status']}**")
                        st.markdown(f"📍 *{cidade_exibicao}*")
                    else:
                        st.markdown(f"*{row['status']}*")
                        st.markdown(f"📍 *{cidade_exibicao}*")
                    
                    if obs.lower() not in ['nan', 'none', 'nulo', '']:
                        st.caption(f"📝 *Obs: {obs}*")

            # ==============================================================================
            # CHAMA O CHAT MANUAL
            # ==============================================================================
            exibir_chat(nf_selecionada, st.session_state['cnpj_ativo'], st.session_state['nome_empresa'])

# ==============================================================================
# CONTROLO DE FLUXO
# ==============================================================================
if not st.session_state['logado']:
    ecra_login()
else:
    ecra_dashboard()
