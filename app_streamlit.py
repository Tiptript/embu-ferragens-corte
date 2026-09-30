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
from log_gerenciador import registrar_log_pedido, carregar_logs, limpar_logs, exportar_logs_csv

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
    /* Ocultar elementos padrão do Streamlit para parecer site profissional (GitHub, Menu, Deploy, Rodapé) */
    #MainMenu {visibility: hidden !important; display: none !important;}
    header {visibility: hidden !important; display: none !important;}
    [data-testid="stHeader"] {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    .stDeployButton {display: none !important;}

    /* ========================================================= */
    /* LARGURA TOTAL NO DESKTOP (FULL-WIDTH 100% SEM ESPAÇOS VAZIOS) */
    /* ========================================================= */
    html, body, [data-testid="stAppViewContainer"], .main, section.main, .stApp {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden !important;
    }

    /* Remove limites fixos de max-width (1140px/1200px) e garante preenchimento de 20px */
    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    div[data-testid="stMain"],
    .main .block-container {
        width: 100% !important;
        max-width: 100% !important;
        padding-top: 0.8rem !important;
        padding-bottom: 2rem !important;
        padding-left: 20px !important;
        padding-right: 20px !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        box-sizing: border-box !important;
    }

    /* Expande contêineres e blocos verticais */
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stHorizontalBlock"] {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* Dataframe e editores de tabela ocupam toda a largura */
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {
        width: 100% !important;
        max-width: 100% !important;
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
    st.session_state.material_selecionado = "MDF Branco TX 15mm"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if "marceneiro_autenticado" not in st.session_state:
    st.session_state.marceneiro_autenticado = not config_loja.get("exigir_senha_marceneiro", False)

if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0

if "ultima_extracao" not in st.session_state:
    st.session_state.ultima_extracao = None

if "mapa_liberado" not in st.session_state:
    st.session_state.mapa_liberado = False



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

    kerf_padrao = float(config_loja.get("kerf_padrao", 4.0))
    refilo_padrao = int(config_loja.get("refilo_padrao", 10))

    kerf = st.number_input("Espessura da Serra (Kerf mm)", min_value=1.0, max_value=8.0, value=kerf_padrao, step=0.5, help="Lâmina de 4.0mm da seccionadora Tecmatic FIT 2.9")
    refilo = st.number_input("Refilo de Borda (mm por lado)", min_value=0, max_value=50, value=refilo_padrao, step=5, help="10mm por lado para esquadro e limpeza das bordas")
    permite_rotacao = st.checkbox("Permitir Rotação de Peças", value=True, help="Ativo para MDF Branco TX (sem veio direcional), maximizando o aproveitamento da chapa.")
    retalho_minimo = st.number_input("Retalho Mínimo Útil (mm)", value=125, step=25)

    st.markdown("""
    <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; margin-top: 10px; font-size: 0.8rem; color: #94a3b8;">
        ⚙️ <b>Oficina Calibrada:</b><br>
        • Seccionadora: <b>Tecmatic FIT 2.9</b><br>
        • Serra: <b>4.0 mm</b> | Refilo: <b>10 mm</b><br>
        • 1º Corte: <b>Longitudinal (2,75m)</b>
    </div>
    """, unsafe_allow_html=True)


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

        tab_adm_precos, tab_adm_loja, tab_adm_seguranca, tab_adm_logs, tab_adm_quest = st.tabs([
            "💰 Preços de MDF e Serviços",
            "📱 WhatsApp, Pix & Proteção",
            "🔐 Senhas e Acesso",
            "📊 Histórico & Logs de Pedidos",
            "📋 Ficha Técnica (Funcionário)"
        ])

        with tab_adm_precos:
            st.markdown("#### 🪵 Tabela Oficial de Preços do MDF (R$ por chapa)")
            st.caption("Esta é a tabela oficial da loja. Os marceneiros e clientes no modo público NÃO conseguem alterar estes valores.")
            precos_mdf = config_loja.get("precos_mdf_chapa", {})
            df_precos_mdf = pd.DataFrame([
                {"Material / Espessura": k, "Preço Chapa (R$)": float(v)} for k, v in precos_mdf.items()
            ])
            edited_precos_df = st.data_editor(df_precos_mdf, num_rows="dynamic", use_container_width=True)

            st.markdown("#### 🪚 Serviços de Corte, Fita de Borda e Frete")
            col_modo1, col_modo2 = st.columns([1, 1])
            with col_modo1:
                modo_corte_sel = st.radio(
                    "Modalidade de Cobrança do Corte:",
                    [
                        "R$ por Corte na Serra (Passada de Lâmina) — Modelo Real da Oficina",
                        "R$ Fixo por Chapa de MDF Cortada"
                    ],
                    index=0 if config_loja.get("modo_cobranca_corte", "por_corte") == "por_corte" else 1
                )
            with col_modo2:
                if "por Corte" in modo_corte_sel:
                    preco_corte_val = st.number_input(
                        "Preço por Corte na Seccionadora (R$ / passada de serra)",
                        value=float(config_loja.get("preco_por_corte", 4.00)),
                        step=0.50,
                        help="Cobrança exata por passada da serra Tecmatic FIT 2.9 (informado pelo funcionário da loja)."
                    )
                else:
                    preco_corte_val = st.number_input(
                        "Taxa Fixa de Corte por Chapa (R$ / chapa)",
                        value=float(config_loja.get("preco_corte_por_chapa", 35.00)),
                        step=5.00
                    )

            col_serv2, col_serv3 = st.columns(2)
            with col_serv2:
                preco_fita = st.number_input(
                    "Preço da Fita de Borda 0.40mm Aplicada (R$ por metro)",
                    value=float(config_loja.get("preco_fita_metro", 4.00)),
                    step=0.50,
                    help="Valor de R$ 4,00/m linear aplicado na coladeira de borda da loja."
                )
            with col_serv3:
                preco_frete = st.number_input(
                    "Taxa de Frete Padrão do Motorista (R$ - Embu e Região)",
                    value=float(config_loja.get("frete_motorista_padrao", 30.00)),
                    step=5.00,
                    help="Valor de R$ 30,00 informado pelo funcionário para fretes locais."
                )

            if st.button("💾 Salvar Alterações de Preços", type="primary"):
                novos_precos = {row["Material / Espessura"]: float(row["Preço Chapa (R$)"]) for _, row in edited_precos_df.iterrows()}
                config_loja["precos_mdf_chapa"] = novos_precos
                config_loja["modo_cobranca_corte"] = "por_corte" if "por Corte" in modo_corte_sel else "por_chapa"
                if "por Corte" in modo_corte_sel:
                    config_loja["preco_por_corte"] = preco_corte_val
                else:
                    config_loja["preco_corte_por_chapa"] = preco_corte_val
                config_loja["preco_fita_metro"] = preco_fita
                config_loja["frete_motorista_padrao"] = preco_frete
                salvar_config(config_loja)
                st.success("Tabela de preços e parâmetros de serviço atualizados com sucesso!")

        with tab_adm_loja:
            st.markdown("#### 📱 Configurações de Recebimento e Atendimento")
            col_zap, col_pix = st.columns(2)
            with col_zap:
                zap_input = st.text_input("WhatsApp da Loja (com DDI e DDD, ex: 5511999999999):", value=config_loja.get("whatsapp_loja", "5511952811775"))
            with col_pix:
                pix_chave_input = st.text_input("Chave Pix Oficial da Loja:", value=config_loja.get("pix_chave", "123vini.dias@gmail.com"))

            col_pix_nome, col_pix_cid = st.columns(2)
            with col_pix_nome:
                pix_nome_input = st.text_input("Nome do Titular da Conta Pix (até 25 letras):", value=config_loja.get("pix_titular", "VINICIUS DIAS"))
            with col_pix_cid:
                pix_cid_input = st.text_input("Cidade da Conta Pix:", value=config_loja.get("pix_cidade", "EMBU DAS ARTES"))

            st.markdown("---")
            st.markdown("#### 🛡️ Proteção do Motor de Corte")
            proteger_motor_cfg = st.checkbox(
                "🔒 Bloquear Mapa Detalhado e Roteiro da Serra antes do envio ao WhatsApp",
                value=config_loja.get("proteger_motor_antes_whatsapp", True),
                help="Quando ativado, o visitante vê as métricas de aproveitamento e chapas, mas a imagem detalhada e a ordem dos cortes só são liberadas após clicar para enviar o pedido no WhatsApp da Embu Ferragens."
            )

            if st.button("💾 Salvar Dados Comerciais & Proteção"):
                config_loja["whatsapp_loja"] = zap_input.replace("+", "").replace("-", "").replace(" ", "")
                config_loja["pix_chave"] = pix_chave_input.strip()
                config_loja["pix_titular"] = pix_nome_input.strip()
                config_loja["pix_cidade"] = pix_cid_input.strip()
                config_loja["proteger_motor_antes_whatsapp"] = proteger_motor_cfg
                salvar_config(config_loja)
                st.success("Configurações comerciais e de proteção salvas com sucesso!")

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

        with tab_adm_logs:
            st.markdown("#### 📊 Histórico de Pedidos e Telemetria de Visitantes")
            st.caption("Acompanhe todos os orçamentos, simulações e pedidos realizados, com data, horário, material, valor e localização aproximada.")

            todos_logs = carregar_logs()

            if not todos_logs:
                st.info("Nenhum pedido ou simulação registrado ainda. Conforme os clientes utilizarem o otimizador, os registros aparecerão aqui em tempo real!")
            else:
                total_pedidos = len(todos_logs)
                faturamento_simulado = sum(float(l.get("valor_total_rs", 0.0)) for l in todos_logs)
                total_chapas = sum(int(l.get("chapas", 0)) for l in todos_logs)
                pedidos_zap = sum(1 for l in todos_logs if "WhatsApp" in str(l.get("evento", "")))

                kpi_log1, kpi_log2, kpi_log3, kpi_log4 = st.columns(4)
                kpi_log1.metric("Simulações / Pedidos", total_pedidos)
                kpi_log2.metric("Enviados no WhatsApp", pedidos_zap)
                kpi_log3.metric("Faturamento Potencial", f"R$ {faturamento_simulado:,.2f}")
                kpi_log4.metric("Chapas Demandadas", f"{total_chapas} un")

                st.markdown("---")

                col_down, col_clear = st.columns([3, 1])
                with col_down:
                    csv_data = exportar_logs_csv()
                    st.download_button(
                        label="📥 Baixar Relatório Completo em CSV (Excel)",
                        data=csv_data,
                        file_name=f"pedidos_embu_ferragens_{int(time.time())}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                with col_clear:
                    if st.button("🗑️ Limpar Histórico de Logs"):
                        limpar_logs()
                        st.success("Histórico limpo!")
                        st.rerun()

                df_logs = pd.DataFrame(todos_logs)
                colunas_exibir = ["id", "data_hora", "evento", "cliente", "material", "chapas", "aproveitamento", "valor_total_rs", "cidade", "dispositivo", "ip"]
                cols_final = [c for c in colunas_exibir if c in df_logs.columns]
                st.dataframe(df_logs[cols_final], use_container_width=True, hide_index=True)

        with tab_adm_quest:
            st.markdown("#### 📋 Questionário de Calibração Técnica da Loja")
            st.caption("Copie este questionário e envie no WhatsApp do funcionário da loja para calibrar estoque, preços reais e serra seccionadora.")

            texto_quest = (
                "📋 QUESTIONÁRIO TÉCNICO PARA O FUNCIONÁRIO — EMBU FERRAGENS\n\n"
                "1. CHAPAS DE MDF E ESTOQUE\n"
                "• Dimensões das chapas mais usadas: 2750 x 1850 mm ou 2750 x 1830 mm?\n"
                "• Preços de venda ao marceneiro dos MDFs em estoque:\n"
                "  - Branco TX 15mm: R$ _____\n"
                "  - Branco TX 18mm: R$ _____\n"
                "  - Branco TX 6mm (fundo): R$ _____\n"
                "  - Preto TX 15mm / 6mm: R$ _____\n"
                "  - Madeirados (Freijó, Carvalho, Nogal): R$ _____\n"
                "  - Compensados (se vender): R$ _____\n\n"
                "2. CONFIGURAÇÕES DA SECCIONADORA\n"
                "• Marca e modelo da máquina: ____________________\n"
                "• Espessura da lâmina da serra principal (Kerf): 3.2mm, 4.0mm ou 4.2mm?\n"
                "• Refilo de esquadro nas bordas da chapa: 0mm, 5mm ou 10mm por lado?\n"
                "• Sentido do 1º corte da serra: Longitudinal (no comprimento de 2,75m) ou Transversal (na largura)?\n"
                "• Retalho mínimo que a loja guarda ou devolve para o cliente: _____ x _____ mm\n\n"
                "3. SERVIÇOS E FITA DE BORDA\n"
                "• Preço do corte na seccionadora: R$ _____ por chapa cortada\n"
                "• Preço da colagem/filetagem de fita de borda: R$ _____ por metro linear\n"
                "• Espessuras de fita disponíveis: Fita fina 0.45mm ou Grossa 1.0mm / 2.0mm?\n\n"
                "4. FRETE E ENTREGAS\n"
                "• Valor do frete padrão em Embu das Artes: R$ _____\n"
                "• Valor para cidades vizinhas (Taboão, Itapecerica, Cotia): R$ _____\n\n"
                "5. CASOS REAIS PARA COMPARAR APROVEITAMENTO\n"
                "• Por favor, envie a lista de 2 ou 3 pedidos de corte reais feitos recentemente para rodarmos no novo motor e compararmos com o software atual!"
            )
            st.text_area("Texto formatado para envio no WhatsApp:", value=texto_quest, height=380)

    st.stop()


# =========================================================================
# MODO CLIENTE: VISÃO DO MARCENEIRO (ORÇAMENTO, CORTE, PIX, WHATSAPP)
# =========================================================================
st.markdown("""
<div class="store-topbar">
    <div class="store-brand">
        <span class="store-icon">🪵</span>
        <div>
            <div class="store-title">Embu Ferragens e Madeiras</div>
            <div class="store-sub">Corte na Seccionadora • Rua Augusto de Almeida Batista, 1942 - Embu das Artes</div>
        </div>
    </div>
    <div class="store-badge">Loja Física Aberta</div>
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


tab_pedido, tab_visualizacao, tab_sequencia, tab_checkout, tab_sobre = st.tabs([
    "📋 1. Peças",
    "📐 2. Mapa do Corte",
    "🪚 3. Roteiro Serra",
    "💳 4. Fechar Pedido",
    "🏬 5. A Loja Física"
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
                        time_limit=6.0,
                        orientacao="horizontal"
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
                            time_limit=3.0 if K_tentativa < k_alvo_max else 6.0,
                            orientacao="horizontal"
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
                    st.session_state.mapa_liberado = False

                    # Telemetria: Registra a simulação de corte para o administrador
                    try:
                        mat_nome_log = st.session_state.material_selecionado
                        preco_unit_ch_log = float(config_loja.get("precos_mdf_chapa", {}).get(mat_nome_log, 238.0))
                        modo_corte_log = config_loja.get("modo_cobranca_corte", "por_corte")
                        if modo_corte_log == "por_corte":
                            cortes_cont = sum(len(sequencia_cortes(ch.get("faixas", []), W, H, kerf_int, int(round(refilo)), int(round(refilo)))) for ch in resultado_chapas)
                            v_corte_log = cortes_cont * float(config_loja.get("preco_por_corte", 4.0))
                        else:
                            v_corte_log = float(config_loja.get("preco_corte_por_chapa", 35.0)) * len(resultado_chapas)
                        taxa_fita_log = float(config_loja.get("preco_fita_metro", 4.0))
                        v_tot_log = (preco_unit_ch_log * len(resultado_chapas)) + v_corte_log + (taxa_fita_log * fita_metros_total)
                        area_nom_tot = len(resultado_chapas) * chapa_w * chapa_h
                        aprov_pct_num = (sum(sum(p['w'] * p['h'] for p in ch['pecas']) for ch in resultado_chapas) / area_nom_tot * 100) if area_nom_tot > 0 else 0.0

                        registrar_log_pedido("Simulação de Corte", {
                            "cliente": "Marceneiro (Simulação)",
                            "material": mat_nome_log,
                            "chapas": len(resultado_chapas),
                            "aproveitamento": f"{aprov_pct_num:.1f}%",
                            "total_pecas": len(pieces_list),
                            "metros_fita": fita_metros_total,
                            "valor_total_rs": v_tot_log,
                            "logistica": "Balcão / Simulação",
                            "pecas_resumo": f"{len(edited_df)} modelos ({len(pieces_list)} peças totais)"
                        })
                    except Exception as e_log:
                        print(f"Erro ao registrar telemetria: {e_log}")

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

        bloqueado_motor = config_loja.get("proteger_motor_antes_whatsapp", True) and not st.session_state.get("mapa_liberado", False) and not st.session_state.get("is_admin", False)

        if bloqueado_motor:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #3b82f6; border-radius: 12px; padding: 26px; text-align: center; margin: 20px 0;">
                <div style="font-size: 2.8rem; margin-bottom: 8px;">🔒</div>
                <h3 style="color: #38bdf8; margin: 0 0 10px 0; font-size: 1.35rem;">Desenho Técnico e Mapa de Corte Protegidos</h3>
                <p style="color: #cbd5e1; font-size: 0.96rem; max-width: 640px; margin: 0 auto 16px auto; line-height: 1.6;">
                    O cálculo das suas peças foi realizado com alta precisão (aproveitamento exibido nos cards acima).<br>
                    Para proteger o algoritmo e a tecnologia da <b>Embu Ferragens</b>, o desenho gráfico das chapas e os botões de download são liberados após o fechamento do pedido.
                </p>
                <div style="background: #0f172a; border-radius: 8px; padding: 12px 16px; display: inline-block; color: #94a3b8; font-size: 0.9rem;">
                    💡 Acesse a <b>Aba 4 (💳 Fechar Pedido)</b> para confirmar o envio no WhatsApp oficial da loja e desbloquear seus mapas imediatamente!
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
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
        bloqueado_motor = config_loja.get("proteger_motor_antes_whatsapp", True) and not st.session_state.get("mapa_liberado", False) and not st.session_state.get("is_admin", False)
        if bloqueado_motor:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #3b82f6; border-radius: 12px; padding: 26px; text-align: center; margin: 20px 0;">
                <div style="font-size: 2.8rem; margin-bottom: 8px;">🪚</div>
                <h3 style="color: #38bdf8; margin: 0 0 10px 0; font-size: 1.35rem;">Roteiro da Seccionadora Protegido</h3>
                <p style="color: #cbd5e1; font-size: 0.96rem; max-width: 640px; margin: 0 auto 16px auto; line-height: 1.6;">
                    A sequência técnica de cortes de 2 estágios (tiras longitudinais e destopos) para o operador da máquina é liberada após a confirmação do pedido no WhatsApp oficial.
                </p>
                <div style="background: #0f172a; border-radius: 8px; padding: 12px 16px; display: inline-block; color: #94a3b8; font-size: 0.9rem;">
                    💡 Acesse a <b>Aba 4 (💳 Fechar Pedido)</b> para enviar seu pedido e desbloquear a sequência completa de cortes.
                </div>
            </div>
            """, unsafe_allow_html=True)
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
            preco_chapa = float(config_loja.get("precos_mdf_chapa", {}).get(mat_escolhido, 238.0))
            chapa_area = (chapa_w * chapa_h) / 1_000_000
            chapas_est = max(1, int(math.ceil(area_m2 / (chapa_area * 0.85))))
            if config_loja.get("modo_cobranca_corte", "por_corte") == "por_corte":
                est_corte = chapas_est * 8 * float(config_loja.get("preco_por_corte", 4.0))
            else:
                est_corte = chapas_est * float(config_loja.get("preco_corte_por_chapa", 35.0))

            st.write(f"• **Material Selecionado:** {mat_escolhido}")
            st.write(f"• **Total de Peças:** {total_pcs} peças ({area_m2:.2f} m² de corte)")
            st.write(f"• **Estimativa de Chapas:** ~{chapas_est} chapa(s) de MDF")
            st.write(f"• **Valor Estimado:** ~R$ {(chapas_est * preco_chapa + est_corte):.2f}")

        st.info("💡 Vá na **Aba 1 (📋 Pedido & Peças)** e clique em **🚀 OTIMIZAR CORTE & GERAR ORÇAMENTO** para liberar o QR Code Pix e o botão oficial do WhatsApp.")
    else:
        st.markdown("### 💳 Orçamento & Fechamento de Pedido")
        st.caption("Pague no Pix sem taxas e envie o pedido diretamente para a serra da Embu Ferragens:")

        # Pré-calcula a sequência de corte para precificar por passada de lâmina ou por chapa
        cortes_todas_chapas = []
        for ch_idx, ch in enumerate(res["chapas"]):
            cortes_ch = sequencia_cortes(ch.get("faixas", []), res["W"], res["H"], res["kerf"], res["refilo"], res["refilo"])
            cortes_todas_chapas.append((ch_idx + 1, ch, cortes_ch))
        total_cortes_serra = sum(len(c[2]) for c in cortes_todas_chapas)

        # 1. Cálculos de Valores
        mat_nome = res["material"]
        preco_unit_chapa = float(config_loja.get("precos_mdf_chapa", {}).get(mat_nome, 238.0))
        qtd_chapas = len(res["chapas"])
        valor_mdf_total = preco_unit_chapa * qtd_chapas

        modo_corte = config_loja.get("modo_cobranca_corte", "por_corte")
        if modo_corte == "por_corte":
            preco_corte_unit = float(config_loja.get("preco_por_corte", 4.0))
            valor_corte_total = total_cortes_serra * preco_corte_unit
            label_corte_resumo = f"🪚 Corte Tecmatic FIT 2.9 ({total_cortes_serra} cortes a R$ {preco_corte_unit:.2f}):"
            texto_corte_zap = f"• Serviço de Corte ({total_cortes_serra} cortes na Tecmatic x R$ {preco_corte_unit:.2f}): R$ {valor_corte_total:.2f}"
        else:
            taxa_corte_unit = float(config_loja.get("preco_corte_por_chapa", 35.0))
            valor_corte_total = taxa_corte_unit * qtd_chapas
            label_corte_resumo = f"🪚 Corte Seccionadora ({qtd_chapas} chapa(s) a R$ {taxa_corte_unit:.2f}):"
            texto_corte_zap = f"• Serviço de Corte ({qtd_chapas} chapa(s)): R$ {valor_corte_total:.2f}"

        taxa_fita_metro = float(config_loja.get("preco_fita_metro", 4.00))
        fita_metros = res["fita_metros"]
        valor_fita_total = taxa_fita_metro * fita_metros
        frete_padrao = float(config_loja.get("frete_motorista_padrao", 30.0))

        col_orc1, col_orc2 = st.columns([1, 1])

        with col_orc1:
            st.markdown("#### 📦 Dados de Entrega / Retirada")
            nome_marceneiro = st.text_input("Seu Nome / Nome da sua Marcenaria:", placeholder="Ex: Marcenaria Silva")
            opcao_logistica = st.radio(
                "Como deseja receber seu MDF cortado?",
                [
                    "🏪 Retirar no Balcão da Loja (Embu das Artes - R$ 0,00)",
                    f"🚚 Entrega pelo Motorista da Loja (+ R$ {frete_padrao:.2f} - Embu e Região)"
                ]
            )

            endereco_entrega = ""
            valor_frete = 0.0

            if "Entrega pelo Motorista" in opcao_logistica:
                valor_frete = frete_padrao
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
<span>{label_corte_resumo}</span>
<b>R$ {valor_corte_total:.2f}</b>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.95rem;">
<span>📏 Fita 0.40mm ({fita_metros:.1f} m a R$ {taxa_fita_metro:.2f}/m):</span>
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
        bloqueado_motor = config_loja.get("proteger_motor_antes_whatsapp", True) and not st.session_state.get("mapa_liberado", False) and not st.session_state.get("is_admin", False)

        st.markdown("---")
        if bloqueado_motor:
            st.markdown("### 🖼️ 2. Mapas de Corte e Desenhos Técnicos")
            st.markdown("""
            <div style="background: #1e293b; border: 1px solid #3b82f6; border-radius: 10px; padding: 18px; margin: 12px 0;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <span style="font-size: 2.2rem;">🔒</span>
                    <div>
                        <h4 style="color: #38bdf8; margin: 0 0 4px 0;">Imagens em Alta Resolução Protegidas</h4>
                        <p style="color: #cbd5e1; font-size: 0.92rem; margin: 0; line-height: 1.5;">
                            Os desenhos técnicos milimétricos e os botões de download de cada chapa serão desbloqueados automaticamente assim que você confirmar o envio para o WhatsApp da Loja abaixo.
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 🖼️ 2. Imagem do Plano de Corte para a Oficina")
            st.caption("Esta imagem traz o desenho oficial da chapa com medidas, sobras e sequência guilhotinada para o operador da serra:")

            col_imgs = st.columns(len(res["chapas"])) if len(res["chapas"]) <= 3 else [st.container()]
            for ch_idx, ch, cortes_ch in cortes_todas_chapas:
                png_bytes = gerar_imagem_plano_chapa(
                    ch, res["chapa_w"], res["chapa_h"],
                    refilo=res["refilo"],
                    kerf=res["kerf"],
                    chapa_idx=ch_idx,
                    total_chapas=len(res["chapas"]),
                    material_nome=res["material"],
                    sequencia_cortes_list=cortes_ch
                )
                alvo_col = col_imgs[ch_idx - 1] if len(res["chapas"]) <= 3 else st
                with alvo_col:
                    st.image(png_bytes, caption=f"Chapa #{ch_idx} ({res['chapa_w']}x{res['chapa_h']} mm)", use_container_width=True)
                    st.download_button(
                        label=f"📥 BAIXAR IMAGEM DO PLANO (Chapa #{ch_idx})",
                        data=png_bytes,
                        file_name=f"plano_corte_chapa_{ch_idx}.png",
                        mime="image/png",
                        type="primary",
                        key=f"dl_chapa_{ch_idx}"
                    )

        # ----------------------------------------------------
        # 3. SEÇÃO DE ENVIO NO WHATSAPP COM TEXTO COMPLETO
        # ----------------------------------------------------
        st.markdown("---")
        st.markdown("### 📲 3. Enviar Pedido no WhatsApp da Loja")

        whatsapp_loja_raw = str(config_loja.get("whatsapp_loja", "5511952811775")).replace("+", "").replace("-", "").replace(" ", "").strip()
        if not whatsapp_loja_raw:
            whatsapp_loja_raw = "5511952811775"
        if not whatsapp_loja_raw.startswith("55"):
            whatsapp_loja_raw = "55" + whatsapp_loja_raw

        st.markdown(f"""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 12px 18px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="color: #94a3b8; font-size: 0.85rem;">Canal Oficial de Atendimento & Produção:</span>
                <div style="color: #38bdf8; font-weight: 700; font-size: 1.05rem;">📱 WhatsApp da Embu Ferragens: +55 (11) 95281-1775</div>
            </div>
            <span style="background: #14532d; color: #4ade80; border: 1px solid #22c55e; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">🔒 Destino Oficial Travado</span>
        </div>
        """, unsafe_allow_html=True)

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
        for ch_idx, ch, cortes_ch in cortes_todas_chapas:
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
            f"🪚 *ORDEM DE CORTE (SECCIONADORA TECMATIC FIT 2.9):*\n{texto_cortes}\n\n"
            f"💰 *VALORES:*\n"
            f"• MDF ({qtd_chapas}x {mat_nome}): R$ {valor_mdf_total:.2f}\n"
            f"{texto_corte_zap}\n"
            f"• Fita de Borda 0.40mm ({fita_metros:.1f} m): R$ {valor_fita_total:.2f}\n"
            f"• Frete: R$ {valor_frete:.2f}\n"
            f"*TOTAL A PAGAR: R$ {valor_final_pedido:.2f}*\n\n"
            f"{status_comp_zap}\n\n"
            f"🖼️ *IMAGEM DO PLANO:* Segue em anexo a imagem do mapa do corte para a serra!"
        )

        link_zap = f"https://wa.me/{whatsapp_loja_raw}?text={urllib.parse.quote(msg_zap)}"

        if bloqueado_motor:
            st.markdown("""
            <div style="background: #14532d; border: 1px solid #22c55e; border-radius: 8px; padding: 14px 18px; margin: 12px 0;">
                <span style="color: #bbf7d0; font-size: 0.95rem; line-height: 1.6;">
                    💡 <b>Como finalizar o pedido em 2 etapas:</b><br>
                    1. Clique no botão azul <b>📲 1. Confirmar Pedido & Liberar Mapas</b> abaixo.<br>
                    2. Em seguida, clique no botão verde <b>📲 ABRIR CONVERSA NO WHATSAPP DA LOJA</b> para despachar seu pedido e anexar o comprovante Pix!
                </span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📲 1. Confirmar Pedido & Liberar Mapas de Corte", type="primary", use_container_width=True):
                st.session_state.mapa_liberado = True
                registrar_log_pedido("Disparo WhatsApp", {
                    "cliente": marceneiro_nome_txt,
                    "material": mat_nome,
                    "chapas": qtd_chapas,
                    "aproveitamento": f"{res.get('aproveitamento_global', 0.0):.1f}%",
                    "total_pecas": res["total_pecas"],
                    "metros_fita": fita_metros,
                    "valor_total_rs": valor_final_pedido,
                    "logistica": logistica_txt,
                    "pecas_resumo": f"{len(edited_df)} modelos ({res['total_pecas']} peças) | Pix: {pix_pago_check}"
                })
                st.success("🎉 Pedido confirmado e mapas liberados com sucesso!")
                st.rerun()
        else:
            st.markdown("""
            <div style="background: #14532d; border: 1px solid #22c55e; border-radius: 8px; padding: 14px 18px; margin: 12px 0;">
                <span style="color: #bbf7d0; font-size: 0.95rem; line-height: 1.6;">
                    💡 <b>Como enviar o pedido no WhatsApp:</b><br>
                    1. Baixe as imagens do corte logo acima (ou na <b>Aba 2</b>) para anexar na conversa.<br>
                    2. Clique no botão verde abaixo para <b>abrir o WhatsApp oficial da Embu Ferragens</b> com toda a lista de peças e ordem de serra já preenchida.<br>
                    3. Na conversa que se abrir, anexe o comprovante Pix e as imagens do plano!
                </span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <a href="{link_zap}" target="_blank" class="btn-whatsapp">
                📲 ENVIAR PEDIDO NO WHATSAPP DA LOJA
            </a>
            """, unsafe_allow_html=True)


# ==========================================
# ABA 5: A LOJA FÍSICA & ATENDIMENTO
# ==========================================
with tab_sobre:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 22px; margin-bottom: 20px;">
        <h2 style="color: #38bdf8; margin: 0 0 6px 0; font-size: 1.55rem; display: flex; align-items: center; gap: 10px;">
            🏬 Embu Ferragens e Madeiras
        </h2>
        <p style="color: #94a3b8; font-size: 0.98rem; margin: 0; line-height: 1.6;">
            A sua parceira completa em marcenaria: corte computadorizado de MDF na seccionadora, colagem de fita de borda e balcão completo de ferragens em Embu das Artes e região.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_loja1, col_loja2 = st.columns([1, 1], gap="large")

    with col_loja1:
        st.markdown("#### 📍 Onde Estamos & Como Chegar")
        st.markdown("""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-bottom: 16px;">
            <p style="color: #f8fafc; font-size: 1.05rem; font-weight: 700; margin: 0 0 6px 0;">
                🏢 Loja Física & Galpão de Corte
            </p>
            <p style="color: #cbd5e1; font-size: 0.95rem; line-height: 1.6; margin: 0 0 14px 0;">
                <b>Endereço:</b> Rua Augusto de Almeida Batista, 1942<br>
                <b>Bairro:</b> Jardim Vazame<br>
                <b>Cidade:</b> Embu das Artes - SP<br>
                <b>CEP:</b> 06826-060
            </p>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <a href="https://www.google.com/maps/search/?api=1&query=Rua+Augusto+de+Almeida+Batista+1942+Embu+das+Artes+SP" target="_blank" style="background: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 8px; font-weight: 700; font-size: 0.88rem; display: inline-flex; align-items: center; gap: 6px;">
                    🗺️ Abrir no Google Maps
                </a>
                <a href="https://waze.com/ul?q=Rua+Augusto+de+Almeida+Batista+1942+Embu+das+Artes" target="_blank" style="background: #0284c7; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 8px; font-weight: 700; font-size: 0.88rem; display: inline-flex; align-items: center; gap: 6px;">
                    🚗 Navegar pelo Waze
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🕒 Horário de Funcionamento")
        st.markdown("""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-bottom: 16px;">
            <table style="width: 100%; color: #cbd5e1; font-size: 0.92rem; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; font-weight: 600;">Segunda a Sexta-feira:</td>
                    <td style="padding: 8px 0; color: #4ade80; text-align: right; font-weight: 700;">08:00 às 17:30</td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 8px 0; font-weight: 600;">Sábado:</td>
                    <td style="padding: 8px 0; color: #4ade80; text-align: right; font-weight: 700;">08:00 às 12:00</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: 600;">Domingo e Feriados:</td>
                    <td style="padding: 8px 0; color: #f87171; text-align: right; font-weight: 700;">Fechado</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📞 Fale Direto Conosco")
        st.markdown("""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px;">
            <p style="color: #cbd5e1; font-size: 0.92rem; margin: 0 0 12px 0;">
                Dúvidas de medidas, consulta de padrões especiais ou suporte no pedido:
            </p>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <a href="https://wa.me/5511952811775?text=Ol%C3%A1%21+Gostaria+de+um+or%C3%A7amento+de+chapas+e+cortes+da+Embu+Ferragens." target="_blank" style="background: #16a34a; color: white; text-decoration: none; padding: 10px 16px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; display: inline-flex; align-items: center; gap: 6px;">
                    📲 WhatsApp: (11) 95281-1775
                </a>
                <a href="tel:11978057030" style="background: #334155; color: white; text-decoration: none; padding: 10px 16px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; display: inline-flex; align-items: center; gap: 6px;">
                    📞 Fixo: (11) 97805-7030
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_loja2:
        st.markdown("#### 🪚 Serviços Especializados")
        st.markdown("""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-bottom: 16px;">
            <div style="margin-bottom: 14px;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 0.98rem; margin-bottom: 3px;">
                    ✂️ Corte Industrial na Seccionadora Tecmatic FIT 2.9
                </div>
                <div style="color: #94a3b8; font-size: 0.86rem; line-height: 1.5;">
                    Cortes perfeitos no esquadro exato com lâmina industrial de 4.0mm e riscador, sem lascas no revestimento e tiras ao longo dos 2,75m.
                </div>
            </div>
            <div style="margin-bottom: 14px;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 0.98rem; margin-bottom: 3px;">
                    📏 Filetagem & Colagem de Fita de Borda 0.40mm
                </div>
                <div style="color: #94a3b8; font-size: 0.86rem; line-height: 1.5;">
                    Colagem térmica profissional Hot-Melt com fita de 0.40mm Branco TX, garantindo proteção contra umidade e acabamento refinado.
                </div>
            </div>
            <div style="margin-bottom: 14px;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 0.98rem; margin-bottom: 3px;">
                    🪵 Estoque de MDF Branco TX (6mm, 15mm e 18mm)
                </div>
                <div style="color: #94a3b8; font-size: 0.86rem; line-height: 1.5;">
                    Chapas padrão Brasil de 2750 x 1850 mm em estoque pronta-entrega (15mm e 18mm para estruturas e portas; 6mm para fundos).
                </div>
            </div>
            <div>
                <div style="color: #38bdf8; font-weight: 700; font-size: 0.98rem; margin-bottom: 3px;">
                    🔩 Balcão Completo de Ferragens
                </div>
                <div style="color: #94a3b8; font-size: 0.86rem; line-height: 1.5;">
                    Dobradiças com amortecedor slow-motion, corrediças telescópicas e invisíveis, puxadores perfil de alumínio, parafusos, colas de contato e aramados.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🚚 Região de Atendimento & Entrega")
        st.markdown("""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 18px;">
            <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5; margin: 0 0 10px 0;">
                Atendemos marceneiros, hobbistas e clientes finais em toda a região:
            </p>
            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px;">
                <span style="background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 10px; border-radius: 16px; font-size: 0.78rem; font-weight: 600;">Embu das Artes</span>
                <span style="background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 10px; border-radius: 16px; font-size: 0.78rem; font-weight: 600;">Taboão da Serra</span>
                <span style="background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 10px; border-radius: 16px; font-size: 0.78rem; font-weight: 600;">Itapecerica da Serra</span>
                <span style="background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 10px; border-radius: 16px; font-size: 0.78rem; font-weight: 600;">Cotia</span>
                <span style="background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 10px; border-radius: 16px; font-size: 0.78rem; font-weight: 600;">Zona Sul / Grande SP</span>
            </div>
            <p style="color: #94a3b8; font-size: 0.84rem; line-height: 1.5; margin: 0;">
                🚗 <b>Retirada na loja:</b> Carregamento facilitado para carretinhas, pick-ups e furgões.<br>
                📦 <b>Entrega na obra/marcenaria:</b> Frete sob consulta com motorista parceiro.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# RODAPÉ: INFORMAÇÕES DA LOJA & CRÉDITOS
# ==========================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #94a3b8; font-size: 0.82rem; padding: 1.2rem 0; line-height: 1.7;">
        🏬 <b>Embu Ferragens e Madeiras</b> — Rua Augusto de Almeida Batista, 1942, Jd. Vazame, Embu das Artes - SP<br>
        📞 WhatsApp: (11) 95281-1775 &nbsp;|&nbsp; Fixo: (11) 97805-7030 &nbsp;|&nbsp; 🕒 Seg a Sex: 08:00 às 17:30 • Sáb: 08:00 às 12:00<br>
        <span style="font-size: 0.75rem; color: #64748b;">Sistema de Otimização de Corte Computadorizado para Seccionadora</span>
    </div>
    """,
    unsafe_allow_html=True
)

