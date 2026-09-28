"""
Módulo de Telemetria, Auditoria e Registro de Pedidos — Embu Ferragens.
Registra todos os pedidos e simulações com IP, geolocalização e detalhes de corte para o administrador.
Utiliza apenas bibliotecas padrão para máxima confiabilidade e zero dependências externas.
"""

import os
import json
import csv
import io
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "pedidos_log.json"))

# Fuso horário de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))


def capturar_info_cliente() -> Dict[str, str]:
    """
    Captura dados de IP, geolocalização e dispositivo do visitante através dos cabeçalhos do Streamlit/Cloudflare.
    """
    headers = {}
    try:
        import streamlit as st
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = dict(st.context.headers)
    except Exception:
        pass

    # 1. IP Real (Cloudflare Proxy ou X-Forwarded-For)
    ip = (
        headers.get("cf-connecting-ip")
        or headers.get("x-forwarded-for", "").split(",")[0].strip()
        or headers.get("x-real-ip")
        or "127.0.0.1 (Local)"
    )

    # 2. Localização Geográfica (injetada automaticamente pelo Cloudflare)
    cidade = headers.get("cf-ipcity") or headers.get("x-vercel-ip-city") or ""
    estado = headers.get("cf-region") or headers.get("x-vercel-ip-country-region") or ""
    pais = headers.get("cf-ipcountry") or headers.get("x-vercel-ip-country") or "BR"

    if not cidade and (ip.startswith("127.") or ip.startswith("192.168.")):
        cidade = "Embu das Artes (Local/Dev)"
        estado = "SP"
    elif not cidade:
        cidade = "São Paulo / Grande SP"
        estado = "SP"

    # 3. Dispositivo / Navegador
    user_agent = headers.get("user-agent", "")
    ua_lower = user_agent.lower()
    if "iphone" in ua_lower or "ipad" in ua_lower:
        dispositivo = "iPhone / iOS"
    elif "android" in ua_lower:
        dispositivo = "Smartphone Android"
    elif "windows" in ua_lower:
        dispositivo = "Computador (Windows)"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        dispositivo = "Computador (Mac)"
    elif "linux" in ua_lower:
        dispositivo = "Computador (Linux)"
    else:
        dispositivo = "Navegador Web"

    return {
        "ip": ip,
        "cidade": cidade,
        "estado": estado,
        "pais": pais,
        "dispositivo": dispositivo,
        "user_agent": user_agent[:120]
    }


def carregar_logs() -> List[Dict[str, Any]]:
    """Carrega o histórico de pedidos ordenado do mais recente para o mais antigo."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
                if isinstance(logs, list):
                    return sorted(logs, key=lambda x: x.get("timestamp", 0), reverse=True)
        except Exception as e:
            print(f"Erro ao carregar pedidos_log.json: {e}")
            return []
    return []


def registrar_log_pedido(evento: str, dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Registra um evento de corte ou pedido com todas as informações técnicas e de localização.
    """
    agora_br = datetime.now(FUSO_BRASILIA)
    data_formatada = agora_br.strftime("%d/%m/%Y %H:%M:%S")
    timestamp = time.time()
    
    id_unico = f"EMB-{agora_br.strftime('%y%m%d')}-{int(timestamp) % 10000:04d}"

    info_cli = capturar_info_cliente()

    novo_registro = {
        "id": id_unico,
        "data_hora": data_formatada,
        "timestamp": timestamp,
        "evento": evento,
        "cliente": dados.get("cliente", "Marceneiro Não Informado"),
        "material": dados.get("material", "MDF"),
        "chapas": int(dados.get("chapas", 1)),
        "aproveitamento": dados.get("aproveitamento", "0%"),
        "total_pecas": int(dados.get("total_pecas", 0)),
        "metros_fita": float(dados.get("metros_fita", 0.0)),
        "valor_total_rs": float(dados.get("valor_total_rs", 0.0)),
        "logistica": dados.get("logistica", "Balcão"),
        "cidade": info_cli["cidade"],
        "estado": info_cli["estado"],
        "ip": info_cli["ip"],
        "dispositivo": info_cli["dispositivo"],
        "pecas_resumo": dados.get("pecas_resumo", "")
    }

    logs = carregar_logs()
    # Adiciona no início
    logs.insert(0, novo_registro)

    # Mantém os últimos 1.500 registros para controle de tamanho
    logs = logs[:1500]

    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar pedidos_log.json: {e}")

    return novo_registro


def limpar_logs() -> bool:
    """Limpa o arquivo de logs de pedidos."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return True
    except Exception:
        return False


def exportar_logs_csv() -> str:
    """Converte os logs em uma string CSV pronta para download."""
    logs = carregar_logs()
    if not logs:
        return ""
    colunas_ordem = [
        "id", "data_hora", "evento", "cliente", "material", "chapas",
        "aproveitamento", "total_pecas", "metros_fita", "valor_total_rs",
        "logistica", "cidade", "estado", "dispositivo", "ip", "pecas_resumo"
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=colunas_ordem, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    for row in logs:
        writer.writerow(row)
    return output.getvalue()
