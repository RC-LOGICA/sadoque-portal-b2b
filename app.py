import streamlit as st
import psycopg2
import psycopg2.extras
import os
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

# 1. Configuração inicial da página
st.set_page_config(page_title="Portal do Embarcador | SADOQUE TRANSPORTES", page_icon="📦", layout="wide")
load_dotenv()

# ==============================================================================
# REMOÇÃO DO CABEÇALHO E RODAPÉ (Visual Profissional)
# ==============================================================================
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .stApp > header { display: none !important; }
    footer {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==============================================================================
# LIGAÇÃO SEGURA E BUSCA DE DADOS
# ==============================================================================
@st.cache_resource
def iniciar_ligacao():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def validar_login(utilizador, palavra_passe):
    try:
        conn = iniciar_ligacao()
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

@st.cache_data(ttl=60)
def buscar_dados_cargas(cnpj_cliente):
    try:
        conn = iniciar_ligacao()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Adicionei a coluna 'tipo_entrega' e mudei o nome para 'Status' para o nosso gráfico
        cursor.execute("""
            SELECT 
                numero_nf as "NF",
                cliente_consignatario as "Destinatário",
                cidade as "Cidade de Destino",
                qtd_volumes as "Volumes",
                COALESCE(NULLIF(tipo_entrega, ''), 'Em Trânsito') as "Status"
            FROM cargas
            WHERE cnpj_embarcador = %s
            ORDER BY id DESC
        """, (cnpj_cliente,))
        registos = cursor.fetchall()
        if registos:
            return pd.DataFrame([dict(r) for r in registos])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar as notas: {e}")
        return None

@st.cache_data(ttl=30)
def buscar_historico_nf(numero_nf):
    """Busca a linha do tempo completa de uma NF específica."""
    try:
        conn = iniciar_ligacao()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT status, cidade_localizacao, TO_CHAR(data_registro, 'DD/MM/YYYY HH24:MI') as data_hora
            FROM rastreio_cargas
            WHERE numero_nf = %s
            ORDER BY data_registro DESC
        """, (str(numero_nf),))
        
        registos = cursor.fetchall()
        if registos:
            return pd.DataFrame([dict(r) for r in registos])
        return pd.DataFrame()
    except Exception as e:
        return None

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
    # --- CSS MÁGICO PARA O EFEITO DE CARTÃO, LOGO E LIMPEZA VISUAL ---
    estilo_caixa_login = """
        <style>
        /* Caixa flutuante do formulário */
        [data-testid="stForm"] {
            background-color: #1F3A5F !important;
            border: 1px solid #2C5282 !important;
            border-radius: 15px !important;
            padding: 2.5rem !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5) !important;
        }
        
        /* 1. Sombra 3D projetada perfeitamente no formato da sua Logo */
        [data-testid="stImage"] img {
            filter: drop-shadow(0px 10px 15px rgba(0, 0, 0, 0.6)) !important;
        }
        
        /* 2. Esconde definitivamente a mensagem "Press Enter to submit form" */
        div[data-testid="InputInstructions"], 
        div[data-testid="stInputInstructions"] {
            display: none !important;
            visibility: hidden !important;
        }
        </style>
    """
    st.markdown(estilo_caixa_login, unsafe_allow_html=True)
    
    # Empurra tudo um pouco mais para baixo para centrar no ecrã
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Ajuste das colunas principais
    col1, col2, col3 = st.columns([1.2, 1.0, 1.2])
    
    with col2:
        with st.form("form_login"):
            
            # --- LOGOTIPO COM SOMBRA ---
            c1, c_img, c2 = st.columns([1, 1.5, 1])
            with c_img:
                caminho_logo = "assets/logo.png" 
                if os.path.exists(caminho_logo):
                    st.image(caminho_logo)
                else:
                    st.markdown("<h3 style='text-align: center; color: #ffb703;'>📦 SADOQUE</h3>", unsafe_allow_html=True)
            
            st.markdown("<p style='text-align: center; color: #a3b1c6; font-size: 14px; margin-top: 10px; margin-bottom: 20px;'>Bem-vindo ao sistema de rastreio corporativo.</p>", unsafe_allow_html=True)
            
            # --- CAMPOS DE LOGIN LIMPOS ---
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
                        st.rerun()
                    else:
                        st.error("Utilizador ou palavra-passe incorretos.")
                else:
                    st.warning("Por favor, preencha todos os campos.")

# ==============================================================================
# ECRÃ PRINCIPAL (DASHBOARD COMPLETO)
# ==============================================================================
def ecra_dashboard():
    # --- MENU LATERAL ---
    st.sidebar.title(f"🏢 {st.session_state['nome_empresa']}")
    st.sidebar.markdown(f"**CNPJ:** {st.session_state['cnpj_ativo']}")
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Atualizar Dados"):
        buscar_dados_cargas.clear()
        st.rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Terminar Sessão"):
        st.session_state.clear()
        st.rerun()
        
    # =====================================================================
    # ESTILOS CSS DO DASHBOARD (CRIAR CAIXAS/CARDS)
    # =====================================================================
    estilos_dashboard = """
        <style>
        /* Transforma os números soltos em Cartões Elevados (Caixas mais claras) */
        [data-testid="stMetric"] {
            background-color: #1F3A5F !important;
            border-left: 5px solid #2a9d8f !important; 
            border-radius: 8px !important;
            padding: 15px 20px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        }
        
        /* Centraliza verticalmente o cabeçalho */
        [data-testid="column"] {
            align-self: center;
        }
        </style>
    """
    st.markdown(estilos_dashboard, unsafe_allow_html=True)

    # =====================================================================
    # CABEÇALHO CO-BRANDING (SADOQUE + CLIENTE)
    # =====================================================================
    # Colunas simétricas: Sadoque (Esquerda), Espaço (Centro), Cliente (Direita)
    col_sad, col_centro, col_cli = st.columns([1, 2, 1])
    
    with col_sad:
        caminho_logo_sadoque = "assets/logo.png"
        if os.path.exists(caminho_logo_sadoque):
            # Aumentámos a largura para 140 para equilibrar com a logo do cliente
            st.image(caminho_logo_sadoque, width=140) 
        else:
            st.markdown("<h3 style='color: #ffb703;'>📦 SADOQUE</h3>", unsafe_allow_html=True)

    with col_cli:
        nome_cliente_ativo = st.session_state.get('nome_empresa', 'Cliente')
        cnpj_ativo = st.session_state.get('cnpj_ativo', '')
        caminho_logo_cliente = f"assets/{cnpj_ativo}.png"
        
        st.markdown(f"<div style='text-align: right; margin-bottom: 5px; color: #a3b1c6;'>Seja bem-vindo,</div>", unsafe_allow_html=True)
        
        if os.path.exists(caminho_logo_cliente):
            # Mantém a proporção correta para a logo da Esmaltec
            c_vazia, c_img_cli = st.columns([0.5, 1.5])
            with c_img_cli:
                st.image(caminho_logo_cliente, use_container_width=True)
        else:
            st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 18px; color: #ffffff;'>{nome_cliente_ativo}</div>", unsafe_allow_html=True)

    # =====================================================================
    # TÍTULO CENTRALIZADO E LINHA DIVISÓRIA
    # =====================================================================
    st.markdown("<div style='text-align: center; color: #a3b1c6; font-size: 18px; font-weight: bold; margin-top: 20px; margin-bottom: 5px;'>Inteligência Logística e Rastreio (B2B)</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    df_cargas = buscar_dados_cargas(st.session_state['cnpj_ativo'])
    
    if df_cargas is None: st.stop()
    if df_cargas.empty:
        st.info("Ainda não existem notas fiscais registadas para o seu CNPJ no sistema.")
        return

    # --- FILTROS ---
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

    # --- MÉTRICAS ---
    st.markdown("---")
    t_notas = len(df_filtrado)
    t_volumes = int(df_filtrado["Volumes"].fillna(0).sum()) if "Volumes" in df_filtrado.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Notas Exibidas", t_notas)
    c2.metric("Volumes Totais", t_volumes)
    c3.metric("Status Operacional", "Verde 🟢")
    st.markdown("---")
    
    # FUNCIONALIDADE 1: GRÁFICOS (DASHBOARDS)
    if not df_filtrado.empty:
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("**Distribuição por Status**")
            # Gráfico de Rosca (Donut)
            fig_status = px.pie(df_filtrado, names='Status', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig_status, use_container_width=True)
            
        with col_graf2:
            st.markdown("**Volume por Cidade (Top 10)**")
            # Gráfico de Barras
            df_cidades = df_filtrado.groupby('Cidade de Destino')['Volumes'].sum().reset_index()
            df_cidades = df_cidades.sort_values(by='Volumes', ascending=False).head(10)
            fig_cidades = px.bar(df_cidades, x='Cidade de Destino', y='Volumes', color='Volumes', color_continuous_scale='Blues')
            st.plotly_chart(fig_cidades, use_container_width=True)

    # --- TABELA DE RASTREIO ---
    st.subheader("Central de Rastreio")
    if df_filtrado.empty:
        st.warning("Nenhuma carga encontrada.")
    else:
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        
        # FUNCIONALIDADE 2: BOTÃO DE EXPORTAÇÃO (Excel/CSV)
        # Converte a tabela filtrada para CSV para download
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descarregar Dados (CSV / Excel)",
            data=csv,
            file_name=f"relatorio_cargas_{st.session_state['nome_empresa']}.csv",
            mime="text/csv",
        )

    # FUNCIONALIDADE 3: TIMELINE REAL (VISÃO DETALHADA)
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
            
            # Desenha a linha do tempo iterando sobre os resultados do banco de dados
            for index, row in df_historico.iterrows():
                col_time1, col_time2 = st.columns([1, 4])
                
                with col_time1:
                    # O evento mais recente (index 0) fica a verde, os restantes a cinzento
                    if index == 0:
                        st.markdown(f"🟢 **{row['data_hora']}**")
                    else:
                        st.markdown(f"⚪ *{row['data_hora']}*")
                        
                with col_time2:
                    # Trata o valor vazio ou 'nan' para ficar elegante no portal
                    cidade_exibicao = str(row['cidade_localizacao'])
                    if cidade_exibicao.lower() == 'nan' or cidade_exibicao.strip() == '' or cidade_exibicao.lower() == 'none':
                        cidade_exibicao = "Em Trânsito / Base"

                    if index == 0:
                        st.markdown(f"**Status Atual: {row['status']}**")
                        st.markdown(f"📍 *{cidade_exibicao}*")
                    else:
                        st.markdown(f"*{row['status']}*")
                        st.markdown(f"📍 *{cidade_exibicao}*")

# ==============================================================================
# CONTROLO DE FLUXO
# ==============================================================================
if not st.session_state['logado']:
    ecra_login()
else:
    ecra_dashboard()