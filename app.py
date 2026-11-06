import sys
import os
import streamlit as st
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import pandas as pd
import plotly.express as px
import datetime
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
import base64

# 1. Configuração inicial da página
st.set_page_config(page_title="Portal do Embarcador | SADOQUE TRANSPORTES", page_icon="📦", layout="wide")
load_dotenv()

# ==============================================================================
# DESIGN SYSTEM PREMIUM (Ergonômico, Elegante e Moderno)
# ==============================================================================
estilo_flutuante = """
    <style>
    /* 0. BLOQUEIO AGRESSIVO DOS SELOS DA CLOUD E MENUS */
    [data-testid="stHeader"], footer, #MainMenu { display: none !important; }
    [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
    
    /* Esconde botões padrões conhecidos */
    .stDeployButton, [data-testid="stDeployButton"] { display: none !important; }
    .viewerBadge_container, .viewerBadge_link, div[class^="viewerBadge"] { display: none !important; }
    
    /* "Tiro de canhão": Esconde QUALQUER elemento injetado que fique fixo no canto inferior direito */
    div[style*="position: fixed"][style*="bottom:"][style*="right:"] { 
        display: none !important; 
        visibility: hidden !important; 
        opacity: 0 !important; 
        pointer-events: none !important; 
    }

    /* 1. FUNDO GERAL DO PORTAL (Azul Claríssimo e Elegante) */
    .stApp { background-color: #EBF3F9 !important; }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }

    /* 2. TIPOGRAFIA CORPORATIVA (Contraste suave em Azul Escuro) */
    [data-testid="stMarkdownContainer"] *,
    [data-testid="stWidgetLabel"] p {
        color: #1A2E4C !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    .block-container {
        max-width: 1250px !important;
        padding-top: 2.5rem !important;
        padding-bottom: 2.5rem !important;
    }

    /* 3. CAIXAS DE ENTRADA */
    .stTextInput div[data-baseweb="base-input"],
    .stSelectbox div[data-baseweb="select"] > div,
    .stDateInput div[data-baseweb="base-input"],
    .stTextArea div[data-baseweb="base-input"] {
        background-color: #0B132B !important; 
        border: 1px solid rgba(11, 19, 43, 0.1) !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* 4. TEXTO BRANCO NAS CAIXAS */
    .stTextInput input,
    .stDateInput input,
    .stTextArea textarea {
        background-color: transparent !important;
        border: none !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
    }
    .stSelectbox div[data-baseweb="select"] * { color: #ffffff !important; }

    .stSelectbox svg, .stDateInput svg { fill: #ffffff !important; color: #ffffff !important; }
    
    /* 5. BOTÕES DE AÇÃO PREMIUM */
    .stButton > button, 
    .stFormSubmitButton > button,
    [data-testid="stDownloadButton"] button {
        background-color: #0B132B !important; 
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        box-shadow: 0 4px 6px rgba(11, 19, 43, 0.15) !important; 
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton > button *, 
    .stFormSubmitButton > button *,
    [data-testid="stDownloadButton"] button * { color: #ffffff !important; font-weight: 500 !important; }

    /* 6. INTERAÇÃO MODERNA (Foco e Hover) */
    .stTextInput div[data-baseweb="base-input"]:focus-within,
    .stSelectbox div[data-baseweb="select"] > div:focus-within,
    .stDateInput div[data-baseweb="base-input"]:focus-within,
    .stTextArea div[data-baseweb="base-input"]:focus-within {
        border: 1px solid #2A9D8F !important;
        box-shadow: 0 0 0 3px rgba(42, 157, 143, 0.15) !important; 
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    [data-testid="stDownloadButton"] button:hover {
        border: 1px solid #2A9D8F !important;
        background-color: #0F1A3A !important;
        transform: translateY(-1px) !important; 
        box-shadow: 0 6px 12px rgba(42, 157, 143, 0.2) !important;
    }
    .stButton > button:hover *,
    .stFormSubmitButton > button:hover *,
    [data-testid="stDownloadButton"] button:hover * { color: #2A9D8F !important; }

    /* 7. CARTÕES DE MÉTRICAS */
    [data-testid="stMetric"] {
        background-color: #0B132B !important;
        padding: 1.25rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(11, 19, 43, 0.12) !important; 
    }
    [data-testid="stMetric"] * { color: #ffffff !important; }

    /* 8. DIVISORES DISCRETOS */
    hr {
        border-bottom: 1px solid rgba(26, 46, 76, 0.08) !important;
        border-top: none !important;
        margin: 2.5em 0 !important;
    }

    /* ============================================================================== */
    /* 9. ALINHAMENTO RESPONSIVO E CORREÇÕES (TELEMÓVEL E PC) */
    /* ============================================================================== */
    
    [data-testid="stForm"] [data-testid="stImage"] {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.5rem !important; /* Mantém o sistema bem encostado acima */
            padding-bottom: 1rem !important;
        }
        [data-testid="stForm"] {
            padding: 1.5rem !important;
        }
    }
    </style>
"""
st.markdown(estilo_flutuante, unsafe_allow_html=True)

# ==============================================================================
# LIGAÇÃO SEGURA E BUSCA DE DADOS
# ==============================================================================
@st.cache_resource
def inicializar_pool():
    try:
        ambiente = os.getenv("AMBIENTE", "PROD").strip().upper()
        if ambiente == "DEV":
            db_url = os.getenv("DATABASE_URL_DEV")
            print("🌐 PORTAL WEB: Iniciado em MODO DEV (Homologação)")
        else:
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
    if conn and pool_global:
        try:
            conn.rollback()
        except:
            pass
        pool_global.putconn(conn)

def validar_login(utilizador, palavra_passe):
    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT id, cnpj_embarcador, senha_hash, nome_fantasia, perfil_acesso 
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
        
        cursor.execute("""
            SELECT 
                REGEXP_REPLACE(c.numero_nf::TEXT, '[^0-9]', '', 'g') as "NF",
                MAX(c.cliente) as "Destinatário",
                MAX(c.cidade) || ' / ' || MAX(c.estado) as "Cidade de Destino",
                MAX(COALESCE(c.qtd_volumes, 0)) as "Volumes", 
                MAX(COALESCE(NULLIF(c.data_prev_entrega::TEXT, ''), 'Em cálculo...')) as "Previsão",
                MAX(
                    CASE 
                        WHEN c.status_carregamento IS NULL THEN 'Na Base'
                        WHEN TRIM(c.status_carregamento) = '' THEN 'Na Base'
                        WHEN LOWER(TRIM(c.status_carregamento)) = 'nan' THEN 'Na Base'
                        WHEN c.status_carregamento ILIKE '%%TR_NSITO%%' THEN 'Em Trânsito'
                        WHEN c.status_carregamento ILIKE '%%BASE%%' THEN 'Na Base'
                        ELSE UPPER(TRIM(c.status_carregamento))
                    END
                ) as "Status",
                COALESCE(MAX(rf.data_finalizado), '-') as "Data Finalizado"
            FROM cargas c
            LEFT JOIN (
                SELECT numero_nf, TO_CHAR(MAX(data_hora), 'DD/MM/YYYY') as data_finalizado
                FROM rastreio_cargas
                WHERE UPPER(TRIM(status)) = 'FINALIZADO'
                GROUP BY numero_nf
            ) rf ON rf.numero_nf = REGEXP_REPLACE(c.numero_nf::TEXT, '[^0-9]', '', 'g')
            WHERE REGEXP_REPLACE(c.cnpj_consignatario, '[^0-9]', '', 'g') = REGEXP_REPLACE(%s, '[^0-9]', '', 'g')
            GROUP BY REGEXP_REPLACE(c.numero_nf::TEXT, '[^0-9]', '', 'g')
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
# CHAT MANUAL
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
        btn_enviar_msg = st.form_submit_button("📤 Enviar Mensagem", use_container_width=True)
        
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
if 'perfil_acesso' not in st.session_state: st.session_state['perfil_acesso'] = 'COMPLETO'

# Inicializa as variáveis de filtro vazias na sessão caso não existam
if 'filtro_texto' not in st.session_state: st.session_state['filtro_texto'] = ""
if 'filtro_cidade' not in st.session_state: st.session_state['filtro_cidade'] = "Todas"
if 'filtro_dt_ini' not in st.session_state: st.session_state['filtro_dt_ini'] = None
if 'filtro_dt_fim' not in st.session_state: st.session_state['filtro_dt_fim'] = None

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
        [data-testid="stForm"] p, 
        [data-testid="stForm"] div[data-testid="stWidgetLabel"] p,
        [data-testid="stForm"] span { color: #ffffff !important; }
        
        [data-testid="stForm"] div[data-baseweb="base-input"] {
            background-color: #0B132B !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 4px !important;
        }
        [data-testid="stForm"] input {
            background-color: transparent !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ffffff !important;             
            box-shadow: none !important;
        }
        [data-testid="stForm"] div[data-baseweb="base-input"]:focus-within { border-color: #2a9d8f !important; }
        div[data-testid="InputInstructions"], div[data-testid="stInputInstructions"] {
            display: none !important; visibility: hidden !important;
        }
        </style>
    """
    st.markdown(estilo_caixa_login, unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("form_login"):
            # CORREÇÃO: Renderiza a imagem via HTML para garantir alinhamento perfeito (margin: 0 auto)
            caminho_logo = "assets/logo.png" 
            if os.path.exists(caminho_logo):
                with open(caminho_logo, "rb") as f:
                    b64_sad = base64.b64encode(f.read()).decode()
                st.markdown(f'<div style="width: 100%; text-align: center;"><img src="data:image/png;base64,{b64_sad}" style="max-width: 140px; margin: 0 auto; display: block; filter: drop-shadow(0px 10px 15px rgba(0, 0, 0, 0.6));"></div>', unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='text-align: center; color: #ffb703;'>📦 SADOQUE</h3>", unsafe_allow_html=True)
            
            st.markdown("<p style='text-align: center; color: #e2e8f0; font-size: 14px; margin-top: 10px; margin-bottom: 20px;'>Bem-vindo ao sistema de rastreio corporativo.</p>", unsafe_allow_html=True)
            
            username = st.text_input("Utilizador")
            password = st.text_input("Palavra-passe", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True) 
            btn_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_entrar:
                if username and password:
                    dados_cliente = validar_login(username.lower().strip(), password.strip())
                    if dados_cliente:
                        st.session_state['logado'] = True
                        st.session_state['cnpj_ativo'] = dados_cliente['cnpj_embarcador']
                        st.session_state['nome_empresa'] = dados_cliente['nome_fantasia']
                        st.session_state['perfil_acesso'] = dados_cliente.get('perfil_acesso', 'COMPLETO')
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
        </style>
    """
    st.markdown(estilos_dashboard, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # CABEÇALHO FLEXBOX: Cola as logos nas bordas extremas (PC e Telemóvel)
    # ---------------------------------------------------------
    caminho_logo_sadoque = "assets/logo.png"
    nome_cliente_ativo = st.session_state.get('nome_empresa', 'Cliente')
    cnpj_ativo = st.session_state.get('cnpj_ativo', '')
    caminho_logo_cliente = f"assets/{cnpj_ativo}.png"

    b64_sad = ""
    if os.path.exists(caminho_logo_sadoque):
        with open(caminho_logo_sadoque, "rb") as f:
            b64_sad = base64.b64encode(f.read()).decode()

    b64_cli = ""
    if os.path.exists(caminho_logo_cliente):
        with open(caminho_logo_cliente, "rb") as f:
            b64_cli = base64.b64encode(f.read()).decode()

    # Define o tamanho máximo das imagens para que ajustem na tela do telemóvel
    img_sad_html = f'<img src="data:image/png;base64,{b64_sad}" style="max-width: 100px; width: 100%; height: auto;">' if b64_sad else "<h3 style='color: #1A2E4C; margin:0;'>📦 SADOQUE</h3>"
    img_cli_html = f'<img src="data:image/png;base64,{b64_cli}" style="max-width: 150px; width: 100%; height: auto; object-fit: contain;">' if b64_cli else f"<div style='font-weight: bold; font-size: 18px; color: #1A2E4C;'>{nome_cliente_ativo}</div>"

    html_header = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 20px;">
        <div style="display: flex; justify-content: flex-start; align-items: center; width: 48%;">
            {img_sad_html}
        </div>
        <div style="display: flex; flex-direction: column; justify-content: flex-end; align-items: flex-end; width: 48%; text-align: right;">
            <span style='color: #a3b1c6; font-size: 13px; margin-bottom: 2px;'>Seja bem-vindo,</span>
            {img_cli_html}
        </div>
    </div>
    """
    st.markdown(html_header, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; color: #a3b1c6; font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 5px;'>Inteligência Logística e Rastreio (B2B)</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.session_state.get('perfil_acesso', 'COMPLETO') == 'COMPLETO':
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
    
    col_filtro1, col_filtro2, col_filtro3, col_filtro4 = st.columns(4)
    with col_filtro1:
        pesquisa_texto = st.text_input("Procurar por NF ou Destinatário:", key="filtro_texto")
        
    with col_filtro2:
        lista_cidades = ["Todas"] + sorted(df_cargas["Cidade de Destino"].dropna().unique().tolist())
        cidade_selecionada = st.selectbox("Filtrar por Cidade:", lista_cidades, key="filtro_cidade")
        
    with col_filtro3:
        data_inicial = st.date_input("Data Inicial (Previsão):", format="DD/MM/YYYY", key="filtro_dt_ini")
        
    with col_filtro4:
        data_final = st.date_input("Data Final (Previsão):", format="DD/MM/YYYY", key="filtro_dt_fim")
        
    df_filtrado = df_cargas.copy()
    
    # Processa os filtros
    if pesquisa_texto:
        f_nf = df_filtrado["NF"].astype(str).str.contains(pesquisa_texto, case=False, na=False)
        f_dest = df_filtrado["Destinatário"].astype(str).str.contains(pesquisa_texto, case=False, na=False)
        df_filtrado = df_filtrado[f_nf | f_dest]
        
    if cidade_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Cidade de Destino"] == cidade_selecionada]

    if data_inicial and data_final:
        inicio_pd = pd.to_datetime(data_inicial)
        fim_pd = pd.to_datetime(data_final)
        datas_validas = pd.to_datetime(df_filtrado['Previsão'], errors='coerce')
        mascara_data = ((datas_validas >= inicio_pd) & (datas_validas <= fim_pd)) | (df_filtrado['Previsão'] == 'Em cálculo...')
        df_filtrado = df_filtrado[mascara_data]

    st.markdown("<br>", unsafe_allow_html=True)
    
    def limpar_filtros():
        st.session_state['filtro_texto'] = ""
        st.session_state['filtro_cidade'] = "Todas"
        st.session_state['filtro_dt_ini'] = None
        st.session_state['filtro_dt_fim'] = None

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 2])
    with col_btn1:
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            buscar_dados_cargas.clear()
            st.rerun()
    with col_btn2:
        st.button("🧹 Limpar Filtros", use_container_width=True, on_click=limpar_filtros)
    with col_btn3:
        if st.button("🚪 Terminar Sessão", use_container_width=True):
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
            st.plotly_chart(fig_status, use_container_width=True)
        with col_graf2:
            st.markdown("**Volume por Cidade (Top 10)**")
            df_cidades = df_filtrado.groupby('Cidade de Destino')['Volumes'].sum().reset_index()
            df_cidades = df_cidades.sort_values(by='Volumes', ascending=False).head(10)
            fig_cidades = px.bar(df_cidades, x='Cidade de Destino', y='Volumes', color='Volumes', color_continuous_scale='Blues')
            st.plotly_chart(fig_cidades, use_container_width=True)

    st.subheader("Central de Rastreio")
    if df_filtrado.empty:
        st.warning("Nenhuma carga encontrada para os filtros selecionados.")
    else:
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
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
                        st.markdown(f"📝 *Obs: {obs}*")

            if st.session_state.get('perfil_acesso', 'COMPLETO') == 'COMPLETO':
                exibir_chat(nf_selecionada, st.session_state['cnpj_ativo'], st.session_state['nome_empresa'])

# ==============================================================================
# CONTROLO DE FLUXO
# ==============================================================================
if not st.session_state['logado']:
    ecra_login()
else:
    ecra_dashboard()
