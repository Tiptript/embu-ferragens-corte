"""
Embu Ferragens — Otimizador de Corte Guilhotinado Profissional
Interface Comercial Unificada em Streamlit:
- Painel Admin para Gestão de Preços (MDF, Corte, Fita, Frete, Pix e WhatsApp)
- Visão do Marceneiro: Foto/Texto com Gemini 3.8 Flash + Motor CP-SAT de Alta Precisão
- Checkout Pix Oficial do Banco Central (Zero Taxas) + Disparo Direto para WhatsApp da Loja
"""

import os
import math
import urllib.parse
import pandas as pd
import streamlit as st
import time

# Módulos locais
from solver2stage import solve_2stage, estimar_chapas_rapido
from geometria import retangulos_maximais, selecionar_sem_sobreposicao, sequencia_cortes, validar_chapa
from gemini_extractor import extrair_pecas_gemini, get_api_key
from config_gerenciador import carregar_config, salvar_config
from pix_generator import gerar_pix_brcode, gerar_qrcode_pix_base64
from gerador_imagem_corte import gerar_imagem_plano_chapa

# Configuração da Página
st.set_page_config(
    page_title="Embu Ferragens - Otimizador de Corte",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Carrega configurações comerciais da loja
config_loja = carregar_config()

# Estilização CSS Moderna & Responsiva (Mobile First & PWA-Like)
st.markdown("""
<style>
    /* Reset de espaçamento superior do Streamlit */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Topbar Comercial */
    .store-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px 18px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .store-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .store-icon {
        font-size: 2rem;
    }
    .store-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1.2;
    }
    .store-sub {
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .store-badge {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.4);
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Tabs em Formato Pills / Chips com Rolagem Suave */
    div[data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: transparent !important;
        border-bottom: 1px solid #334155 !important;
        padding-bottom: 6px !important;
        margin-bottom: 1rem !important;
    }
    button[data-testid="stTab"] {
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border: 1px solid #334155 !important;
        background-color: #1e293b !important;
        color: #cbd5e1 !important;
        transition: all 0.2s ease !important;
    }
    button[data-testid="stTab"][aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4) !important;
    }

    /* Grid Responsivo para KPIs (4 colunas no PC, 2x2 no Celular) */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin: 10px 0 16px 0;
    }
    .metric-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 14px 16px;
        border: 1px solid #334155;
        text-align: center;
    }
    .metric-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #f8fafc;
        margin-top: 4px;
    }
    .metric-value.highlight {
        color: #4ade80;
    }

    /* Botão WhatsApp Gigante com Feedback Tátil */
    .btn-whatsapp {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        text-align: center;
        display: block;
        text-decoration: none;
        font-size: 1.1rem;
        margin-top: 14px;
        box-shadow: 0 4px 16px rgba(37, 211, 102, 0.4);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .btn-whatsapp:active {
        transform: scale(0.98);
    }
    .btn-whatsapp:hover {
        color: white !important;
        box-shadow: 0 6px 20px rgba(37, 211, 102, 0.6);
    }

    /* Card de Resumo de Fatura / Recibo */
    .invoice-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }

    /* ========================================================= */
    /* REGRAS ESPECÍFICAS PARA SMARTPHONES (Telas até 768px)     */
    /* ========================================================= */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.6rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
        .store-topbar {
            padding: 10px 12px !important;
            margin-bottom: 0.75rem !important;
        }
        .store-title {
            font-size: 1.15rem !important;
        }
        .store-sub {
            font-size: 0.75rem !important;
        }
        .store-badge {
            display: none; /* Oculta badge secundário no mobile para dar espaço */
        }
        
        /* Previne o auto-zoom incômodo do iPhone Safari */
        input, select, textarea, .stSelectbox, .stNumberInput input {
            font-size: 16px !important;
        }

        /* Grade 2x2 para indicadores no celular (ocupa apenas ~110px de altura!) */
        .kpi-grid {
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 8px !important;
        }
        .metric-card {
            padding: 10px 8px !important;
        }
        .metric-value {
            font-size: 1.35rem !important;
        }
        .metric-label {
            font-size: 0.7rem !important;
        }

        /* Abas compactas no celular */
        div[data-baseweb="tab-list"] {
            gap: 4px !important;
            overflow-x: auto !important;
            white-space: nowrap !important;
            padding-bottom: 4px !important;
        }
        button[data-testid="stTab"] {
            padding: 7px 10px !important;
            font-size: 0.82rem !important;
            min-height: 38px !important;
        }

        /* Botões com altura de toque confortável */
        .stButton button {
            min-height: 48px !important;
            font-size: 16px !important;
            width: 100% !important;
        }
        .btn-whatsapp {
            font-size: 1rem !important;
            padding: 14px 12px !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# Estado da Sessão
if "pecas_df" not in st.session_state:
    st.session_state.pecas_df = pd.DataFrame([
        {"id": "P1", "nome": "Lateral 185x50", "comprimento_mm": 1850, "largura_mm": 500, "quantidade": 1, "fita": "Sem fita"},
        {"id": "P2", "nome": "Lateral 185x45", "comprimento_mm": 1850, "largura_mm": 450, "quantidade": 1, "fita": "Sem fita"},
        {"id": "P3", "nome": "Base 135x40", "comprimento_mm": 1350, "largura_mm": 400, "quantidade": 1, "fita": "Sem fita"},
        {"id": "P4", "nome": "Prateleira 135x35", "comprimento_mm": 1350, "largura_mm": 350, "quantidade": 1, "fita": "Sem fita"},
        {"id": "P5", "nome": "Frente Gaveta 140x20", "comprimento_mm": 1400, "largura_mm": 200, "quantidade": 2, "fita": "Sem fita"},
        {"id": "P6", "nome": "Lat Gaveta 65x20", "comprimento_mm": 650, "largura_mm": 200, "quantidade": 2, "fita": "Sem fita"},
    ])

if "resultado_corte" not in st.session_state:
    st.session_state.resultado_corte = None

if "material_selecionado" not in st.session_state:
    st.session_state.material_selecionado = "MDF Preto 15mm"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "marceneiro_autenticado" not in st.session_state:
    st.session_state.marceneiro_autenticado = not config_loja.get("exigir_senha_marceneiro", False)

if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0

if "ultima_extracao" not in st.session_state:
    st.session_state.ultima_extracao = None



# ==========================================
# BARRA LATERAL: Controle de Modo & Máquina
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/saw.png", width=65)
    st.markdown("### 🪵 Embu Ferragens")
    st.caption("Central de Corte & Pedidos de MDF")

    modo = st.radio("Selecione o Acesso:", ["👤 Marceneiro / Cliente", "🔒 Painel da Loja (Admin)"])

    st.markdown("---")
    st.markdown("#### ⚙️ Configurações da Chapa")

    preset_chapa = st.selectbox(
        "Dimensão Nominal da Chapa",
        [
            "MDF Padrão Brasil (2750 x 1850 mm)",
            "MDF Arauco / Duratex (2750 x 1830 mm)",
            "Compensado Naval (2200 x 1600 mm)",
            "Customizado..."
        ]
    )

    if preset_chapa == "MDF Padrão Brasil (2750 x 1850 mm)":
        chapa_w, chapa_h = 2750, 1850
    elif preset_chapa == "MDF Arauco / Duratex (2750 x 1830 mm)":
        chapa_w, chapa_h = 2750, 1830
    elif preset_chapa == "Compensado Naval (2200 x 1600 mm)":
        chapa_w, chapa_h = 2200, 1600
    else:
        col_w, col_h = st.columns(2)
        chapa_w = col_w.number_input("Comprimento (mm)", value=2750, step=50)
        chapa_h = col_h.number_input("Largura (mm)", value=1850, step=50)

    kerf = st.number_input("Espessura da Serra (Kerf mm)", min_value=1.0, max_value=8.0, value=4.0, step=0.5)
    refilo = st.number_input("Refilo de Borda (mm por lado)", min_value=0, max_value=50, value=0, step=5)
    permite_rotacao = st.checkbox("Permitir Rotação de Peças", value=False, help="Mantenha desmarcado para respeitar o veio da madeira.")
    retalho_minimo = st.number_input("Retalho Mínimo Útil (mm)", value=125, step=25)


# =========================================================================
# MODO ADMIN: PAINEL DA LOJA (GESTÃO DE PREÇOS, PIX, WHATSAPP E SENHAS)
# =========================================================================
if modo == "🔒 Painel da Loja (Admin)":
    st.markdown('<div class="main-header">🔒 Painel Administrativo — Embu Ferragens</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Gestão de Preços de Venda, Taxas de Corte, Chave Pix e WhatsApp Comercial</div>', unsafe_allow_html=True)

    if not st.session_state.is_admin:
        col_pass1, col_pass2 = st.columns([1, 2])
        with col_pass1:
            senha_digitada = st.text_input("Senha Master do Administrador:", type="password")
            if st.button("Entrar no Painel", type="primary"):
                if senha_digitada == config_loja.get("admin_senha_hash", "embu2026"):
                    st.session_state.is_admin = True
                    st.success("Acesso liberado!")
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
        st.stop()
    else:
        if st.button("🚪 Sair do Painel Admin"):
            st.session_state.is_admin = False
            st.rerun()

        tab_adm_precos, tab_adm_loja, tab_adm_seguranca = st.tabs([
            "💰 Preços de MDF e Serviços",
            "📱 WhatsApp & Chave Pix",
            "🔐 Senhas e Acesso"
        ])

        with tab_adm_precos:
            st.markdown("#### 🪵 Tabela de Preços do MDF (R$ por chapa)")
            precos_mdf = config_loja.get("precos_mdf_chapa", {})
            df_precos_mdf = pd.DataFrame([
                {"Material / Espessura": k, "Preço Chapa (R$)": float(v)} for k, v in precos_mdf.items()
            ])
            edited_precos_df = st.data_editor(df_precos_mdf, num_rows="dynamic", use_container_width=True)

            col_serv1, col_serv2, col_serv3 = st.columns(3)
            with col_serv1:
                preco_corte = st.number_input(
                    "Taxa de Corte na Seccionadora (R$ por chapa)",
                    value=float(config_loja.get("preco_corte_por_chapa", 35.0)),
                    step=5.0
                )
            with col_serv2:
                preco_fita = st.number_input(
                    "Preço da Fita de Borda Aplicada (R$ por metro)",
                    value=float(config_loja.get("preco_fita_metro", 1.50)),
                    step=0.25
                )
            with col_serv3:
                preco_frete = st.number_input(
                    "Taxa de Frete Padrão do Motorista (R$)",
                    value=float(config_loja.get("frete_motorista_padrao", 50.0)),
                    step=10.0
                )

            if st.button("💾 Salvar Alterações de Preços", type="primary"):
                novos_precos = {row["Material / Espessura"]: float(row["Preço Chapa (R$)"]) for _, row in edited_precos_df.iterrows()}
                config_loja["precos_mdf_chapa"] = novos_precos
                config_loja["preco_corte_por_chapa"] = preco_corte
                config_loja["preco_fita_metro"] = preco_fita
                config_loja["frete_motorista_padrao"] = preco_frete
                salvar_config(config_loja)
                st.success("Tabela de preços atualizada com sucesso!")

        with tab_adm_loja:
            st.markdown("#### 📱 Configurações de Recebimento e Atendimento")
            col_zap, col_pix = st.columns(2)
            with col_zap:
                zap_input = st.text_input("WhatsApp da Loja (com DDI e DDD, ex: 5511999999999):", value=config_loja.get("whatsapp_loja", "5511999999999"))
            with col_pix:
                pix_chave_input = st.text_input("Chave Pix Oficial da Loja:", value=config_loja.get("pix_chave", "contato@embuferragens.com.br"))

            col_pix_nome, col_pix_cid = st.columns(2)
            with col_pix_nome:
                pix_nome_input = st.text_input("Nome do Titular da Conta Pix (até 25 letras):", value=config_loja.get("pix_titular", "EMBU FERRAGENS"))
            with col_pix_cid:
                pix_cid_input = st.text_input("Cidade da Conta Pix:", value=config_loja.get("pix_cidade", "EMBU DAS ARTES"))

            if st.button("💾 Salvar Dados Comerciais"):
                config_loja["whatsapp_loja"] = zap_input.replace("+", "").replace("-", "").replace(" ", "")
                config_loja["pix_chave"] = pix_chave_input.strip()
                config_loja["pix_titular"] = pix_nome_input.strip()
                config_loja["pix_cidade"] = pix_cid_input.strip()
                salvar_config(config_loja)
                st.success("Dados de WhatsApp e Pix salvos com sucesso!")

        with tab_adm_seguranca:
            st.markdown("#### 🔐 Controle de Acesso de Marceneiros")
            exigir_senha = st.checkbox("Exigir Senha de Parceiro para Marceneiros Usarem o App", value=config_loja.get("exigir_senha_marceneiro", False))
            senha_marceneiro = st.text_input("Senha dos Marceneiros / Parceiros:", value=config_loja.get("senha_marceneiro", "PARCEIRO"))
            nova_senha_admin = st.text_input("Alterar Senha Master do Admin:", value=config_loja.get("admin_senha_hash", "embu2026"), type="password")

            if st.button("💾 Salvar Configurações de Acesso"):
                config_loja["exigir_senha_marceneiro"] = exigir_senha
                config_loja["senha_marceneiro"] = senha_marceneiro
                config_loja["admin_senha_hash"] = nova_senha_admin
                salvar_config(config_loja)
                st.success("Configurações de segurança atualizadas!")

    st.stop()


# =========================================================================
# MODO CLIENTE: VISÃO DO MARCENEIRO (ORÇAMENTO, CORTE, PIX, WHATSAPP)
# =========================================================================
st.markdown("""
<div class="store-topbar">
    <div class="store-brand">
        <span class="store-icon">🪵</span>
        <div>
            <div class="store-title">Embu Ferragens</div>
            <div class="store-sub">Corte Profissional na Seccionadora • Embu das Artes/SP</div>
        </div>
    </div>
    <div class="store-badge">Loja Aberta</div>
</div>
""", unsafe_allow_html=True)

# Trava de Senha de Parceiro se estiver ativa
if config_loja.get("exigir_senha_marceneiro") and not st.session_state.marceneiro_autenticado:
    col_lock1, col_lock2 = st.columns([1, 2])
    with col_lock1:
        st.info("🔒 Este aplicativo é exclusivo para marceneiros e parceiros da Embu Ferragens.")
        senha_parceiro_digitada = st.text_input("Digite a Senha de Parceiro:", type="password")
        if st.button("Liberar Acesso", type="primary"):
            if senha_parceiro_digitada.strip().upper() == config_loja.get("senha_marceneiro", "PARCEIRO").strip().upper():
                st.session_state.marceneiro_autenticado = True
                st.success("Acesso liberado! Bem-vindo parceiro.")
                st.rerun()
            else:
                st.error("Senha de parceiro incorreta. Solicite sua senha pelo WhatsApp da loja.")
    st.stop()


tab_pedido, tab_visualizacao, tab_sequencia, tab_checkout = st.tabs([
    "📋 1. Peças",
    "📐 2. Mapa do Corte",
    "🪚 3. Roteiro Serra",
    "💳 4. Fechar Pedido"
])


from assistente_movel_foto import analisar_foto_movel, explodir_movel_parametrico

# ==========================================
# ABA 1: ENTRADA DO PEDIDO
# ==========================================
with tab_pedido:
    col_input1, col_input2 = st.columns([1, 1])

    with col_input1:
        st.markdown("#### 📸 Envio de Medidas ou Projeto")
        metodo = st.radio(
            "Como deseja informar as peças?",
            [
                "💬 Colar Mensagem de Texto",
                "📷 Foto de Rascunho / Lista Escrita",
                "🛋️ Projetar Móvel por Foto (Assistente IA)"
            ],
            horizontal=True
        )

        txt_msg = ""
        foto_bytes = None

        if metodo == "💬 Colar Mensagem de Texto":
            txt_msg = st.text_area(
                "Cole o texto com as medidas:",
                height=140,
                placeholder="Exemplo:\nMe vê este material preto MDF 15 mm\n1- 185x50\n1-185x45\n1-135x40\n1-135x35\n2-140x20\n2-65x20"
            )
            if st.button("✨ Ler Medidas com Inteligência Artificial", type="secondary", use_container_width=True):
                if not txt_msg:
                    st.warning("Cole o texto antes de extrair.")
                else:
                    with st.spinner("A IA está identificando as peças e convertendo para milímetros..."):
                        try:
                            extracao = extrair_pecas_gemini(texto=txt_msg)
                            materiais = extracao.get("materiais", [])
                            if materiais:
                                st.session_state.material_selecionado = materiais[0].get("material", "MDF Preto 15mm")
                                novas_pecas = []
                                for idx, m in enumerate(materiais):
                                    for p in m.get("pecas", []):
                                        novas_pecas.append({
                                            "id": p.get("id", f"P{len(novas_pecas)+1}"),
                                            "nome": p.get("nome", f"Peça {p.get('comprimento_mm')}x{p.get('largura_mm')}"),
                                            "comprimento_mm": int(p.get("comprimento_mm", 0)),
                                            "largura_mm": int(p.get("largura_mm", 0)),
                                            "quantidade": int(p.get("quantidade", 1)),
                                            "fita": "Sem fita"
                                        })
                                st.session_state.editor_version += 1
                                st.session_state.pecas_df = pd.DataFrame(novas_pecas)
                                st.session_state.ultima_extracao = {
                                    "origem": "Mensagem de Texto",
                                    "pecas": novas_pecas,
                                    "material": st.session_state.material_selecionado
                                }
                                st.success(f"✅ {len(novas_pecas)} peças extraídas com sucesso!")
                                st.rerun()
                        except Exception as ex:
                            st.error(f"Erro na leitura: {ex}")

        elif metodo == "📷 Foto de Rascunho / Lista Escrita":
            up_file = st.file_uploader("Tire foto do caderno ou print do celular:", type=["jpg", "jpeg", "png", "webp"], key="up_lista")
            if up_file:
                foto_bytes = up_file.read()
                st.image(up_file, caption="Rascunho Enviado", use_container_width=True)

            if st.button("✨ Ler Foto com Inteligência Artificial", type="secondary", use_container_width=True):
                if not foto_bytes:
                    st.warning("Envie uma foto antes de extrair.")
                else:
                    with st.spinner("A IA está analisando a foto e buscando as medidas..."):
                        try:
                            extracao = extrair_pecas_gemini(imagem_bytes=foto_bytes)
                            materiais = extracao.get("materiais", [])
                            if materiais:
                                st.session_state.material_selecionado = materiais[0].get("material", "MDF Preto 15mm")
                                novas_pecas = []
                                for idx, m in enumerate(materiais):
                                    for p in m.get("pecas", []):
                                        novas_pecas.append({
                                            "id": p.get("id", f"P{len(novas_pecas)+1}"),
                                            "nome": p.get("nome", f"Peça {p.get('comprimento_mm')}x{p.get('largura_mm')}"),
                                            "comprimento_mm": int(p.get("comprimento_mm", 0)),
                                            "largura_mm": int(p.get("largura_mm", 0)),
                                            "quantidade": int(p.get("quantidade", 1)),
                                            "fita": "Sem fita"
                                        })
                                st.session_state.editor_version += 1
                                st.session_state.pecas_df = pd.DataFrame(novas_pecas)
                                st.session_state.ultima_extracao = {
                                    "origem": "Foto de Caderno / Rascunho",
                                    "pecas": novas_pecas,
                                    "material": st.session_state.material_selecionado
                                }
                                st.success(f"✅ {len(novas_pecas)} peças extraídas com sucesso!")
                                st.rerun()
                        except Exception as ex:
                            st.error(f"Erro na leitura: {ex}")

        else: # 🛋️ Projetar Móvel por Foto (Assistente IA)
            st.info("💡 Envie a foto de qualquer móvel (armário, balcão, guarda-roupa). A IA analisará a estrutura e fará perguntas para calcular as peças exatas.")
            up_movel = st.file_uploader("Envie a foto do móvel que deseja fabricar:", type=["jpg", "jpeg", "png", "webp"], key="up_movel")

            if up_movel:
                movel_bytes = up_movel.read()
                st.image(up_movel, caption="Móvel de Referência", use_container_width=True)

                if "diagnostico_movel" not in st.session_state or st.session_state.get("hash_movel_atual") != up_movel.name:
                    if st.button("🔍 Analisar Estrutura do Móvel com IA", type="secondary"):
                        with st.spinner("O Gemini 3.8 Flash está analisando a anatomia do móvel..."):
                            diag = analisar_foto_movel(movel_bytes)
                            st.session_state.diagnostico_movel = diag
                            st.session_state.hash_movel_atual = up_movel.name
                            st.rerun()

                if "diagnostico_movel" in st.session_state:
                    diag = st.session_state.diagnostico_movel
                    st.success(f"🛋️ **Móvel Identificado:** {diag.get('tipo_movel', 'Móvel Personalizado')}")
                    st.write(f"*{diag.get('descricao_visual', '')}*")

                    st.markdown("##### ❓ Responda aos detalhes de medidas:")
                    perguntas = diag.get("perguntas_ao_marceneiro", [])
                    for p in perguntas:
                        st.caption(f"• {p}")

                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        w_movel = st.number_input("Largura Total da Parede (mm):", value=1200, step=50)
                    with col_m2:
                        h_movel = st.number_input("Altura Total Desejada (mm):", value=800, step=50)
                    with col_m3:
                        d_movel = st.number_input("Profundidade (mm):", value=550, step=50)

                    col_m4, col_m5, col_m6 = st.columns(3)
                    with col_m4:
                        esp_mdf = st.selectbox("Espessura do MDF:", [15, 18], index=0)
                    with col_m5:
                        qtd_portas = st.number_input("Qtd de Portas:", value=int(diag.get("portas_detectadas", 2)), min_value=0, max_value=8)
                    with col_m6:
                        qtd_gavetas = st.number_input("Qtd de Gavetas:", value=int(diag.get("gavetas_detectadas", 0)), min_value=0, max_value=12)

                    col_m7, col_m8 = st.columns(2)
                    with col_m7:
                        qtd_prat = st.number_input("Prateleiras Internas:", value=int(diag.get("prateleiras_detectadas", 1)), min_value=0, max_value=10)
                    with col_m8:
                        tem_rod = st.checkbox("Móvel com Rodapé no Chão", value=bool(diag.get("tem_rodape", False)))
                        alt_rod = st.number_input("Altura do Rodapé (mm):", value=100 if tem_rod else 0, min_value=0, max_value=200, step=10) if tem_rod else 0

                    if st.button("📐 Calcular e Explodir Peças do Móvel", type="primary", use_container_width=True):
                        pecas_calculadas = explodir_movel_parametrico(
                            largura_total_mm=int(w_movel),
                            altura_total_mm=int(h_movel),
                            profundidade_total_mm=int(d_movel),
                            espessura_mdf_mm=int(esp_mdf),
                            qtd_portas=int(qtd_portas),
                            qtd_gavetas=int(qtd_gavetas),
                            qtd_prateleiras=int(qtd_prat),
                            altura_rodape_mm=int(alt_rod),
                            tem_fundo=True
                        )
                        st.session_state.editor_version += 1
                        st.session_state.pecas_df = pd.DataFrame(pecas_calculadas)
                        st.session_state.ultima_extracao = {
                            "origem": f"Móvel Paramétrico ({diag.get('tipo_movel', 'Personalizado')})",
                            "pecas": pecas_calculadas,
                            "material": st.session_state.material_selecionado
                        }
                        st.success(f"🎉 {len(pecas_calculadas)} peças geradas com folgas reais de marcenaria! Veja na tabela ao lado.")
                        st.rerun()

        # Exibe card de prévia da última extração (para QUALQUER método)
        if st.session_state.get("ultima_extracao"):
            uext = st.session_state["ultima_extracao"]
            st.markdown("---")
            st.markdown(f"#### 📋 Prévia das Peças Lidas ({uext.get('origem', '')})")
            df_prev = pd.DataFrame(uext.get("pecas", []))
            if not df_prev.empty and "nome" in df_prev.columns:
                st.dataframe(df_prev[["nome", "comprimento_mm", "largura_mm", "quantidade"]], use_container_width=True, hide_index=True)
            st.success(f"✅ Todas as {len(df_prev)} peças acima já foram carregadas na tabela ao lado. Você pode alterar qualquer medida antes de cortar!")

    with col_input2:
        st.markdown("#### ✏️ Conferência & Edição da Lista de Peças")
        materiais_disponiveis = list(config_loja.get("precos_mdf_chapa", {}).keys())
        mat_default_idx = materiais_disponiveis.index(st.session_state.material_selecionado) if st.session_state.material_selecionado in materiais_disponiveis else 0

        st.session_state.material_selecionado = st.selectbox(
            "Selecione o MDF deste pedido:",
            materiais_disponiveis,
            index=mat_default_idx
        )

        # Formulário Ergonômico de Adição Rápida para Celular (Touch-Friendly)
        with st.expander("➕ Adicionar Peça Manualmente (Toque Rápido)", expanded=False):
            qa_nome = st.text_input("Nome da Peça (ex: Lateral, Porta, Base):", value="", placeholder="Ex: Lateral Esquerda", key="qa_nome")
            col_qa1, col_qa2 = st.columns(2)
            with col_qa1:
                qa_comp = st.number_input("Comprimento (mm):", value=1000, step=50, min_value=10, max_value=3000, key="qa_comp")
                qa_larg = st.number_input("Largura (mm):", value=400, step=50, min_value=10, max_value=3000, key="qa_larg")
            with col_qa2:
                qa_qtd = st.number_input("Quantidade:", value=1, min_value=1, max_value=50, key="qa_qtd")
                qa_fita = st.selectbox("Fita de Borda:", ["Sem fita", "1 Comprimento", "2 Comprimentos", "4 Lados"], key="qa_fita")
            
            if st.button("➕ Adicionar à Lista de Peças", type="secondary", use_container_width=True):
                novo_id = f"P{len(st.session_state.pecas_df) + 1}"
                nome_final = qa_nome.strip() or f"Peça {int(qa_comp)}x{int(qa_larg)}"
                nova_peca = pd.DataFrame([{
                    "id": novo_id,
                    "nome": nome_final,
                    "comprimento_mm": int(qa_comp),
                    "largura_mm": int(qa_larg),
                    "quantidade": int(qa_qtd),
                    "fita": qa_fita
                }])
                st.session_state.pecas_df = pd.concat([st.session_state.pecas_df, nova_peca], ignore_index=True)
                st.session_state.editor_version += 1
                st.success(f"Peça '{nome_final}' adicionada!")
                st.rerun()

        st.caption("Você também pode alterar valores diretamente nas células da tabela abaixo:")

        edited_df = st.data_editor(
            st.session_state.pecas_df,
            key=f"editor_pecas_{st.session_state.editor_version}",
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "id": st.column_config.TextColumn("ID", width="small", required=True),
                "nome": st.column_config.TextColumn("Peça / Rótulo", width="medium", required=True),
                "comprimento_mm": st.column_config.NumberColumn("Comprimento (mm)", min_value=10, max_value=3000, required=True),
                "largura_mm": st.column_config.NumberColumn("Largura (mm)", min_value=10, max_value=3000, required=True),
                "quantidade": st.column_config.NumberColumn("Qtd", min_value=1, max_value=100, default=1, required=True),
                "fita": st.column_config.SelectboxColumn("Fita de Borda", options=["Sem fita", "1 Comprimento", "2 Comprimentos", "4 Lados"], default="Sem fita")
            },
            height=320
        )
        st.session_state.pecas_df = edited_df

    st.markdown("---")
    col_btn_calc, col_info_calc = st.columns([1, 2])
    with col_btn_calc:
        btn_calcular = st.button("🚀 OTIMIZAR CORTE & GERAR ORÇAMENTO", type="primary", use_container_width=True)

    with col_info_calc:
        total_pecas_count = int(edited_df["quantidade"].sum()) if not edited_df.empty else 0
        area_total_pecas = sum(r["comprimento_mm"] * r["largura_mm"] * r["quantidade"] for _, r in edited_df.iterrows()) / 1_000_000 if not edited_df.empty else 0
        st.markdown(f"**Total de Unidades:** {total_pecas_count} peças | **Área líquida:** {area_total_pecas:.2f} m² de MDF")


# ==========================================
# CÁLCULO DO CORTE NO MOTOR CP-SAT
# ==========================================
if btn_calcular:
    if edited_df.empty or total_pecas_count == 0:
        st.error("A lista de peças não pode estar vazia.")
    else:
        with st.spinner("Otimizando corte na seccionadora com CP-SAT..."):
            t0 = time.time()
            W = int(round(chapa_w - 2 * refilo))
            H = int(round(chapa_h - 2 * refilo))
            kerf_int = int(round(kerf))

            pieces_list = []
            fita_metros_total = 0.0

            for _, row in edited_df.iterrows():
                try:
                    w_p = int(round(float(row["comprimento_mm"])))
                    h_p = int(round(float(row["largura_mm"])))
                    q_p = int(round(float(row["quantidade"])))
                except (ValueError, TypeError):
                    continue
                if w_p <= 0 or h_p <= 0 or q_p <= 0:
                    continue

                pid = str(row["id"])
                fita_op = str(row.get("fita", "Sem fita"))

                # Calcula metragem de fita
                if fita_op == "1 Comprimento":
                    fita_metros_total += (w_p / 1000.0) * q_p
                elif fita_op == "2 Comprimentos":
                    fita_metros_total += (2 * w_p / 1000.0) * q_p
                elif fita_op == "4 Lados":
                    fita_metros_total += (2 * (w_p + h_p) / 1000.0) * q_p

                for i in range(q_p):
                    inst_id = f"{pid}__{i+1}" if q_p > 1 else pid
                    pieces_list.append((w_p, h_p, inst_id))

            if not pieces_list:
                st.error("Nenhuma peça válida encontrada na tabela para corte.")
            else:
                area_p = sum(w * h for w, h, _ in pieces_list)
                k_min = max(1, int(math.ceil(area_p / (W * H))))
                k_heur = estimar_chapas_rapido(pieces_list, W, H, kerf_int, allow_rotation=permite_rotacao)
                k_alvo_max = max(k_min, k_heur)

                resultado_chapas = None
                status_final = "INFEASIBLE"

                # Se a heurística e o limite inferior batem, resolve direto em ~90ms
                if k_min == k_alvo_max:
                    st_calc, ch_calc = solve_2stage(
                        pieces_list, W, H, kerf_int,
                        K=k_min,
                        allow_rotation=permite_rotacao,
                        time_limit=6.0
                    )
                    if ch_calc:
                        resultado_chapas = ch_calc
                        status_final = st_calc
                else:
                    for K_tentativa in range(k_min, k_alvo_max + 1):
                        st_calc, ch_calc = solve_2stage(
                            pieces_list, W, H, kerf_int,
                            K=K_tentativa,
                            allow_rotation=permite_rotacao,
                            time_limit=3.0 if K_tentativa < k_alvo_max else 6.0
                        )
                        if ch_calc:
                            resultado_chapas = ch_calc
                            status_final = st_calc
                            break

                dt_ms = int((time.time() - t0) * 1000)

                if resultado_chapas:
                    st.session_state.resultado_corte = {
                        "chapas": resultado_chapas,
                        "status": status_final,
                        "tempo_ms": dt_ms,
                        "W": W,
                        "H": H,
                        "chapa_w": int(round(chapa_w)),
                        "chapa_h": int(round(chapa_h)),
                        "refilo": int(round(refilo)),
                        "kerf": kerf_int,
                        "total_pecas": len(pieces_list),
                        "fita_metros": fita_metros_total,
                        "material": st.session_state.material_selecionado
                    }
                    st.success(f"🎉 Plano otimizado em {dt_ms} ms! {len(resultado_chapas)} chapa(s) de {st.session_state.material_selecionado}.")
                else:
                    st.error("Não foi possível gerar um plano válido com essas dimensões. Verifique se as peças cabem dentro da chapa.")

if st.session_state.resultado_corte:
    res_atual = st.session_state.resultado_corte
    chapas_atual = res_atual["chapas"]
    area_nom = len(chapas_atual) * res_atual["chapa_w"] * res_atual["chapa_h"]
    area_pc = sum(sum(p["w"] * p["h"] for p in ch["pecas"]) for ch in chapas_atual)
    aprov_atual = (area_pc / area_nom) * 100.0 if area_nom > 0 else 0

    st.markdown(f"""
    <div style="background: #064e3b; border: 1px solid #10b981; border-radius: 8px; padding: 14px 18px; margin: 12px 0;">
        <h4 style="color: #6ee7b7; margin: 0 0 6px 0;">✅ Corte Otimizado com Sucesso!</h4>
        <span style="color: #ecfdf5; font-size: 0.95rem;">
            Necessário: <b>{len(chapas_atual)} chapa(s)</b> de {res_atual['material']} | 
            Aproveitamento: <b>{aprov_atual:.1f}%</b> | 
            Tempo de cálculo: <b>{res_atual['tempo_ms']} ms</b>
        </span>
        <div style="margin-top: 8px; color: #a7f3d0; font-size: 0.9rem;">
            👉 Veja o mapa desenhado na <b>Aba 2 (📐 Mapa do Corte)</b> ou acesse a <b>Aba 4 (💳 Orçamento, Pix & WhatsApp)</b> para pagar e enviar o pedido!
        </div>
    </div>
    """, unsafe_allow_html=True)



# ==========================================
# ABA 2: MAPA VISUAL DO CORTE
# ==========================================
with tab_visualizacao:
    res = st.session_state.resultado_corte
    if not res:
        st.info("💡 Vá na Aba 1 e clique em **🚀 OTIMIZAR CORTE & GERAR ORÇAMENTO**.")
    else:
        chapas = res["chapas"]
        W = res["W"]
        H = res["H"]
        refilo = res["refilo"]

        area_nominal_total = len(chapas) * res["chapa_w"] * res["chapa_h"]
        area_pecas_total = sum(sum(p["w"] * p["h"] for p in ch["pecas"]) for ch in chapas)
        aprov_global = (area_pecas_total / area_nominal_total) * 100.0

        html_kpi = f"""<div class="kpi-grid">
<div class="metric-card">
<div class="metric-label">Chapas Necessárias</div>
<div class="metric-value highlight">{len(chapas)} chapa(s)</div>
</div>
<div class="metric-card">
<div class="metric-label">Aproveitamento</div>
<div class="metric-value highlight">{aprov_global:.1f}%</div>
</div>
<div class="metric-card">
<div class="metric-label">Total de Peças</div>
<div class="metric-value">{res['total_pecas']} un</div>
</div>
<div class="metric-card">
<div class="metric-label">Fita de Borda</div>
<div class="metric-value">{res['fita_metros']:.1f} m</div>
</div>
</div>"""
        st.markdown(html_kpi, unsafe_allow_html=True)

        cores = ["#38bdf8", "#fbbf24", "#34d399", "#f472b6", "#a78bfa", "#f87171", "#fb923c", "#2dd4bf"]

        for ch_idx, ch in enumerate(chapas):
            locais = [{'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h']} for p in ch['pecas']]
            maximais = retangulos_maximais(locais, W, H)
            visiveis = selecionar_sem_sobreposicao(maximais, retalho_minimo)
            area_ch = sum(p['w'] * p['h'] for p in ch['pecas'])
            aprov_ch = (area_ch / (res["chapa_w"] * res["chapa_h"])) * 100.0
            maior_ret = max(visiveis, key=lambda r: r['w'] * r['h']) if visiveis else None

            st.markdown(f"### 📦 Chapa #{ch_idx + 1} — {res['material']} ({res['chapa_w']} x {res['chapa_h']} mm)")
            if maior_ret:
                st.caption(f"Aproveitamento: **{aprov_ch:.1f}%** | Maior Sobra Limpa: **{maior_ret['w']} x {maior_ret['h']} mm** ({maior_ret['w']*maior_ret['h']/1_000_000:.3f} m²)")

            cortes_tab2 = sequencia_cortes(ch.get("faixas", []), res["W"], res["H"], res["kerf"], res["refilo"], res["refilo"])
            png_ch_tab2 = gerar_imagem_plano_chapa(
                ch, res["chapa_w"], res["chapa_h"],
                refilo=res["refilo"],
                kerf=res["kerf"],
                chapa_idx=ch_idx + 1,
                total_chapas=len(chapas),
                material_nome=res["material"],
                sequencia_cortes_list=cortes_tab2
            )
            st.image(png_ch_tab2, caption=f"Mapa Oficial do Corte — Chapa #{ch_idx + 1} ({res['material']})", use_container_width=True)
            st.download_button(
                label=f"📥 Baixar Imagem Oficial do Plano (Chapa #{ch_idx + 1})",
                data=png_ch_tab2,
                file_name=f"plano_corte_chapa_{ch_idx + 1}.png",
                mime="image/png",
                key=f"dl_tab2_{ch_idx + 1}"
            )
            st.markdown("<br>", unsafe_allow_html=True)



# ==========================================
# ABA 3: ROTEIRO DA SECCIONADORA
# ==========================================
with tab_sequencia:
    res = st.session_state.resultado_corte
    if not res:
        st.info("💡 Calcule o plano de corte na Aba 1 para gerar a sequência da máquina.")
    else:
        st.markdown("### 🪚 Sequência de Cortes de 2 Estágios (Para a Serra)")
        for ch_idx, ch in enumerate(res["chapas"]):
            st.markdown(f"#### 🏷️ Chapa #{ch_idx + 1}")
            faixas = ch.get("faixas", [])
            cortes = sequencia_cortes(faixas, res["W"], res["H"], res["kerf"], res["refilo"], res["refilo"])

            c1 = [c for c in cortes if c.get("estagio") == 1]
            c2 = [c for c in cortes if c.get("estagio") == 2]

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("**Fase 1: Tiras de Ponta a Ponta**")
                for c in c1:
                    if c["y1"] == c["y2"]:
                        st.write(f"• Passo {c['ordem']}: Cortar horizontal em **Y = {c['y1']} mm**")
                    else:
                        st.write(f"• Passo {c['ordem']}: Cortar vertical em **X = {c['x1']} mm**")
            with col_f2:
                st.markdown("**Fase 2: Destopo nas Tiras**")
                for c in c2:
                    if c["x1"] == c["x2"]:
                        st.write(f"• Passo {c['ordem']}: Destopar em **X = {c['x1']} mm** (faixa Y={c['y1']} a {c['y2']})")
                    else:
                        st.write(f"• Passo {c['ordem']}: Destopar em **Y = {c['y1']} mm** (faixa X={c['x1']} a {c['x2']})")


# =========================================================================
# ABA 4: CHECKOUT COMERCIAL, PIX GRÁTIS & DISPARO NO WHATSAPP DA LOJA
# =========================================================================
with tab_checkout:
    res = st.session_state.resultado_corte
    if not res:
        st.markdown("### 💳 Estimativa de Orçamento (Pré-Cálculo)")
        st.caption("Esta é uma estimativa preliminar. Clique em 'Otimizar Corte' na Aba 1 para calcular a quantidade exata de chapas e gerar o Pix oficial.")

        pecas_atuais = st.session_state.pecas_df
        if not pecas_atuais.empty:
            total_pcs = int(pecas_atuais["quantidade"].sum())
            area_m2 = sum(float(r["comprimento_mm"]) * float(r["largura_mm"]) * float(r["quantidade"]) for _, r in pecas_atuais.iterrows()) / 1_000_000
            mat_escolhido = st.session_state.material_selecionado
            preco_chapa = float(config_loja.get("precos_mdf_chapa", {}).get(mat_escolhido, 250.0))
            chapa_area = (chapa_w * chapa_h) / 1_000_000
            chapas_est = max(1, int(math.ceil(area_m2 / (chapa_area * 0.85))))

            st.write(f"• **Material Selecionado:** {mat_escolhido}")
            st.write(f"• **Total de Peças:** {total_pcs} peças ({area_m2:.2f} m² de corte)")
            st.write(f"• **Estimativa de Chapas:** ~{chapas_est} chapa(s) de MDF")
            st.write(f"• **Valor Estimado:** ~R$ {(chapas_est * preco_chapa + chapas_est * float(config_loja.get('preco_corte_por_chapa', 35.0))):.2f}")

        st.info("💡 Vá na **Aba 1 (📋 Pedido & Peças)** e clique em **🚀 OTIMIZAR CORTE & GERAR ORÇAMENTO** para liberar o QR Code Pix e o botão oficial do WhatsApp.")
    else:
        st.markdown("### 💳 Orçamento & Fechamento de Pedido")
        st.caption("Pague no Pix sem taxas e envie o pedido diretamente para a serra da Embu Ferragens:")

        # 1. Cálculos de Valores
        mat_nome = res["material"]
        preco_unit_chapa = float(config_loja.get("precos_mdf_chapa", {}).get(mat_nome, 250.0))
        qtd_chapas = len(res["chapas"])
        valor_mdf_total = preco_unit_chapa * qtd_chapas

        taxa_corte_unit = float(config_loja.get("preco_corte_por_chapa", 35.0))
        valor_corte_total = taxa_corte_unit * qtd_chapas

        taxa_fita_metro = float(config_loja.get("preco_fita_metro", 1.50))
        fita_metros = res["fita_metros"]
        valor_fita_total = taxa_fita_metro * fita_metros

        col_orc1, col_orc2 = st.columns([1, 1])

        with col_orc1:
            st.markdown("#### 📦 Dados de Entrega / Retirada")
            nome_marceneiro = st.text_input("Seu Nome / Nome da sua Marcenaria:", placeholder="Ex: Marcenaria Silva")
            opcao_logistica = st.radio(
                "Como deseja receber seu MDF cortado?",
                [
                    "🏪 Retirar no Balcão da Loja (Embu das Artes - R$ 0,00)",
                    f"🚚 Entrega pelo Motorista da Loja (+ R$ {config_loja.get('frete_motorista_padrao', 50.0):.2f})"
                ]
            )

            endereco_entrega = ""
            valor_frete = 0.0

            if "Entrega pelo Motorista" in opcao_logistica:
                valor_frete = float(config_loja.get("frete_motorista_padrao", 50.0))
                endereco_entrega = st.text_area("Endereço completo da obra ou marcenaria:", placeholder="Rua, número, bairro e cidade...")

            valor_final_pedido = valor_mdf_total + valor_corte_total + valor_fita_total + valor_frete

            frete_linha = f"""<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.95rem;">
<span>🚚 Frete Motorista:</span><b>R$ {valor_frete:.2f}</b>
</div>""" if valor_frete > 0 else ""

            html_resumo = f"""<div class="invoice-card">
<div style="font-weight:700; color:#38bdf8; margin-bottom:8px; font-size:1.05rem;">🧾 Resumo do Pedido</div>
<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.95rem;">
<span>🪵 MDF ({qtd_chapas}x {mat_nome}):</span>
<b>R$ {valor_mdf_total:.2f}</b>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.95rem;">
<span>🪚 Corte Seccionadora ({qtd_chapas} chapa):</span>
<b>R$ {valor_corte_total:.2f}</b>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.95rem;">
<span>📏 Fita de Borda ({fita_metros:.1f} m):</span>
<b>R$ {valor_fita_total:.2f}</b>
</div>
{frete_linha}
<hr style="border-color:#334155; margin:10px 0;">
<div style="display:flex; justify-content:space-between; font-size:1.25rem; font-weight:800; color:#4ade80;">
<span>TOTAL:</span>
<span>R$ {valor_final_pedido:.2f}</span>
</div>
</div>"""
            st.markdown(html_resumo, unsafe_allow_html=True)

        with col_orc2:
            st.markdown("#### 💳 1. Pagamento no Pix (Sem Taxas)")
            st.caption(f"Titular: **{config_loja.get('pix_titular', 'VINICIUS DIAS')}** • Embu das Artes")

            chave_pix_loja = config_loja.get("pix_chave", "123vini.dias@gmail.com")
            titular_loja = config_loja.get("pix_titular", "VINICIUS DIAS")
            cidade_loja = config_loja.get("pix_cidade", "EMBU DAS ARTES")

            # Gera BR Code Pix Oficial
            codigo_pix = gerar_pix_brcode(
                chave_pix=chave_pix_loja,
                nome_recebedor=titular_loja,
                cidade=cidade_loja,
                valor=valor_final_pedido,
                txid=f"CORTE{int(time.time()) % 100000}"
            )
            b64_qr = gerar_qrcode_pix_base64(codigo_pix)

            st.markdown("**📋 Pix Copia e Cola (Toque para copiar no celular):**")
            st.code(codigo_pix, language="text")
            st.markdown(f"**Chave Pix Oficial:** `{chave_pix_loja}`")

            with st.expander("📱 Preferir ler o QR Code com outro celular?", expanded=False):
                st.markdown(f'<div style="text-align:center; padding:8px;"><img src="data:image/png;base64,{b64_qr}" style="width: 190px; border-radius: 8px; border: 2px solid #334155;"></div>', unsafe_allow_html=True)

            # Anexo do Comprovante Pix
            st.markdown("##### 📎 Comprovante de Pagamento Pix")
            up_comp_pix = st.file_uploader(
                "Anexe o print do comprovante Pix (opcional):",
                type=["jpg", "jpeg", "png", "pdf"],
                key="up_comp_pix"
            )
            pix_pago_check = st.checkbox(
                "✅ Já realizei o Pix (informar comprovante anexado no WhatsApp)",
                value=bool(up_comp_pix)
            )

        # ----------------------------------------------------
        # 2. SEÇÃO DE IMAGENS DO PLANO DE CORTE PARA WHATSAPP
        # ----------------------------------------------------
        st.markdown("---")
        st.markdown("### 🖼️ 2. Imagem do Plano de Corte para a Oficina")
        st.caption("Esta imagem traz o desenho oficial da chapa com medidas, sobras e sequência guilhotinada para o operador da serra:")

        col_imgs = st.columns(len(res["chapas"])) if len(res["chapas"]) <= 3 else [st.container()]
        chapas_pngs = []

        for ch_idx, ch in enumerate(res["chapas"]):
            cortes_ch = sequencia_cortes(ch.get("faixas", []), res["W"], res["H"], res["kerf"], res["refilo"], res["refilo"])
            png_bytes = gerar_imagem_plano_chapa(
                ch, res["chapa_w"], res["chapa_h"],
                refilo=res["refilo"],
                kerf=res["kerf"],
                chapa_idx=ch_idx + 1,
                total_chapas=len(res["chapas"]),
                material_nome=res["material"],
                sequencia_cortes_list=cortes_ch
            )
            chapas_pngs.append((ch_idx + 1, png_bytes, cortes_ch))

            alvo_col = col_imgs[ch_idx] if len(res["chapas"]) <= 3 else st
            with alvo_col:
                st.image(png_bytes, caption=f"Chapa #{ch_idx + 1} ({res['chapa_w']}x{res['chapa_h']} mm)", use_container_width=True)
                st.download_button(
                    label=f"📥 BAIXAR IMAGEM DO PLANO (Chapa #{ch_idx + 1})",
                    data=png_bytes,
                    file_name=f"plano_corte_chapa_{ch_idx + 1}.png",
                    mime="image/png",
                    type="primary",
                    key=f"dl_chapa_{ch_idx + 1}"
                )

        # ----------------------------------------------------
        # 3. SEÇÃO DE ENVIO NO WHATSAPP COM TEXTO COMPLETO
        # ----------------------------------------------------
        st.markdown("---")
        st.markdown("### 📲 3. Enviar Pedido no WhatsApp da Loja")
        
        col_zap_cfg1, col_zap_cfg2 = st.columns([1, 1])
        with col_zap_cfg1:
            whatsapp_destino = st.text_input(
                "Número de WhatsApp de Destino (com DDD):",
                value=config_loja.get("whatsapp_loja", "5511952811775"),
                help="Você pode alterar este número para enviar para um atendente ou vendedor específico da loja."
            )

        logistica_txt = "Retirada no Balcão da Loja" if "Retirar" in opcao_logistica else f"Entrega pelo Motorista: {endereco_entrega}"
        marceneiro_nome_txt = nome_marceneiro.strip() or "Marceneiro Parceiro"

        # 1. Medidas de todas as peças
        linhas_pecas = []
        for _, r in edited_df.iterrows():
            fita_str = f" [{r['fita']}]" if r.get("fita") and r["fita"] != "Sem fita" else ""
            linhas_pecas.append(f"• {r['nome']}: {r['comprimento_mm']} x {r['largura_mm']} mm ({r['quantidade']}x){fita_str}")
        texto_pecas = "\n".join(linhas_pecas)

        # 2. Ordem exata dos cortes para a seccionadora
        linhas_cortes = []
        for ch_idx, png_bytes, cortes_ch in chapas_pngs:
            linhas_cortes.append(f"\n*CHAPA #{ch_idx} ({res['chapa_w']}x{res['chapa_h']} mm):*")
            c1 = [c for c in cortes_ch if c.get("estagio") == 1]
            c2 = [c for c in cortes_ch if c.get("estagio") == 2]
            linhas_cortes.append("_[Estágio 1: Cortes de Tiras de Ponta a Ponta]_")
            for c in c1:
                if c["y1"] == c["y2"]:
                    linhas_cortes.append(f"  Passo {c['ordem']}: Corte horizontal em Y = {c['y1']} mm")
                else:
                    linhas_cortes.append(f"  Passo {c['ordem']}: Corte vertical em X = {c['x1']} mm")
            linhas_cortes.append("_[Estágio 2: Destopo nas Tiras]_")
            for c in c2:
                if c["x1"] == c["x2"]:
                    linhas_cortes.append(f"  Passo {c['ordem']}: Destopo em X = {c['x1']} mm")
                else:
                    linhas_cortes.append(f"  Passo {c['ordem']}: Destopo em Y = {c['y1']} mm")
        texto_cortes = "\n".join(linhas_cortes)

        status_comp_zap = "✅ *COMPROVANTE PIX:* Pago via Pix e anexado nesta conversa!" if pix_pago_check else "⏳ *PAGAMENTO NO PIX:* Copiado no app / Realizando pagamento..."

        msg_zap = (
            f"🪚 *NOVO PEDIDO DE CORTE — EMBU FERRAGENS*\n\n"
            f"👤 *Cliente / Marcenaria:* {marceneiro_nome_txt}\n"
            f"🪵 *Material:* {mat_nome} ({qtd_chapas} chapa(s))\n"
            f"🧩 *Total de Peças:* {res['total_pecas']} peças cortadas\n"
            f"🚚 *Logística:* {logistica_txt}\n\n"
            f"📐 *MEDIDAS DAS PEÇAS:*\n{texto_pecas}\n\n"
            f"🪚 *ORDEM DE CORTE (SECCIONADORA):*\n{texto_cortes}\n\n"
            f"💰 *VALORES:*\n"
            f"• MDF ({qtd_chapas}x): R$ {valor_mdf_total:.2f}\n"
            f"• Serviço de Corte: R$ {valor_corte_total:.2f}\n"
            f"• Fita de Borda: R$ {valor_fita_total:.2f}\n"
            f"• Frete: R$ {valor_frete:.2f}\n"
            f"*TOTAL A PAGAR: R$ {valor_final_pedido:.2f}*\n\n"
            f"{status_comp_zap}\n\n"
            f"🖼️ *IMAGEM DO PLANO:* Segue em anexo a imagem do mapa do corte para a serra!"
        )

        # Formata número para link wa.me
        numero_limpo = "".join(filter(str.isdigit, str(whatsapp_destino)))
        if numero_limpo and not numero_limpo.startswith("55"):
            numero_limpo = "55" + numero_limpo
        if not numero_limpo:
            numero_limpo = "5511952811775"

        link_zap = f"https://wa.me/{numero_limpo}?text={urllib.parse.quote(msg_zap)}"

        st.markdown("""
        <div style="background: #14532d; border: 1px solid #22c55e; border-radius: 8px; padding: 14px 18px; margin: 12px 0;">
            <span style="color: #bbf7d0; font-size: 0.95rem; line-height: 1.6;">
                💡 <b>Como finalizar o pedido em 3 passos:</b><br>
                1. Clique no botão azul <b>📥 BAIXAR IMAGEM DO PLANO</b> logo acima para salvar o desenho do corte.<br>
                2. Clique no botão verde abaixo para <b>abrir o WhatsApp da Loja</b> com todo o pedido e ordem de cortes já digitados.<br>
                3. Na conversa que se abrir, <b>anexe a imagem do plano de corte</b> e o <b>print do comprovante do Pix</b>!
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <a href="{link_zap}" target="_blank" class="btn-whatsapp">
            📲 ENVIAR PEDIDO NO WHATSAPP DA LOJA
        </a>
        """, unsafe_allow_html=True)

# ==========================================
# RODAPÉ: CRÉDITOS DE ENGENHARIA & IA
# ==========================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #94a3b8; font-size: 0.82rem; padding: 1.2rem 0; line-height: 1.6;">
        🪚 <b>Embu Ferragens</b> — Sistema de Otimização & Canal Digital de Vendas de MDF<br>
        🛠️ <b>Antigravity</b> (Arquiteto & Engenheiro de Execução) &nbsp;|&nbsp;
        🔍 <b>Claude Fable</b> (Revisor Técnico) &nbsp;|&nbsp;
        🎯 <b>Gemini</b> (Prompter & Visão Multimodal)
    </div>
    """,
    unsafe_allow_html=True
)

