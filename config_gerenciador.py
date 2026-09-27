"""
Gerenciador de Configurações Comerciais da Loja (Embu Ferragens)
Permite ao Admin alterar preços de MDF, corte, fitas, frete, WhatsApp e Pix.
"""

import os
import json
from typing import Dict, Any

ARQUIVO_CONFIG = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_loja.json"))

CONFIG_PADRAO = {
    "admin_senha_hash": "embu2026",
    "exigir_senha_marceneiro": False,
    "senha_marceneiro": "PARCEIRO",
    "whatsapp_loja": "5511999999999",
    "pix_chave": "123vini.dias@gmail.com",
    "pix_titular": "VINICIUS DIAS",
    "pix_cidade": "EMBU DAS ARTES",
    "precos_mdf_chapa": {
        "MDF Preto 15mm": 275.00,
        "MDF Preto 6mm": 165.00,
        "MDF Branco TX 15mm": 210.00,
        "MDF Branco TX 18mm": 245.00,
        "MDF Carvalho Hanover 15mm": 290.00,
        "MDF Freijó 15mm": 295.00,
        "MDF Padrão 15mm": 230.00
    },
    "preco_corte_por_chapa": 35.00,
    "preco_fita_metro": 1.50,
    "frete_motorista_padrao": 50.00
}


def carregar_config() -> Dict[str, Any]:
    """Carrega o arquivo de configuração ou cria o padrão se não existir."""
    if not os.path.exists(ARQUIVO_CONFIG):
        salvar_config(CONFIG_PADRAO)
        return dict(CONFIG_PADRAO)
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Mescla com padrão caso novas chaves tenham sido criadas
            for k, v in CONFIG_PADRAO.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return dict(CONFIG_PADRAO)


def salvar_config(novas_configs: Dict[str, Any]):
    """Salva as configurações atualizadas no disco."""
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(novas_configs, f, indent=2, ensure_ascii=False)
