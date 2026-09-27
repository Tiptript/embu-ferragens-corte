"""
Assistente Paramétrico de Projetos de Móveis por Foto (Embu Ferragens)
Permite ao marceneiro enviar a foto de qualquer armário/móvel (do Pinterest ou do cliente),
a IA identifica os componentes e o motor paramétrico calcula a lista de corte exata com folgas reais.
"""

import json
import re
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from PIL import Image
import io
from gemini_extractor import get_api_key, calcular_hash_entrada, _carregar_cache, _salvar_cache


PROMPT_DIAGNOSTICO_MOVEL = """
Você é um projetista sênior de móveis planejados e marcenaria no Brasil.
Analise a fotografia deste móvel e identifique a estrutura construtiva dele.

Responda EXCLUSIVAMENTE em formato JSON puro:
{
  "tipo_movel": "Balcão / Armário Inferior / Guarda-Roupa / Cômoda / Nicho",
  "descricao_visual": "Descrição curta em português do móvel identificado",
  "portas_detectadas": 2,
  "tipo_porta": "giro",
  "gavetas_detectadas": 0,
  "prateleiras_detectadas": 1,
  "tem_rodape": false,
  "altura_rodape_sugerida_mm": 0,
  "perguntas_ao_marceneiro": [
    "Qual a largura total do vão na parede?",
    "Prefere com rodapé no chão (10cm) ou suspenso na parede?",
    "Quantas prateleiras internas deseja?"
  ]
}
"""


def analisar_foto_movel(imagem_bytes: bytes, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Analisa a foto de um móvel pronto e devolve os componentes detectados e perguntas.
    Utiliza Cache SHA-256 para evitar consumo redundante.
    """
    hash_img = "movel_" + calcular_hash_entrada(imagem_bytes=imagem_bytes)
    cache = _carregar_cache()
    if hash_img in cache:
        return cache[hash_img]

    key = api_key or get_api_key()
    if not key:
        raise ValueError("Chave de API do Gemini não configurada.")

    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-3.8-flash")

    image = Image.open(io.BytesIO(imagem_bytes))
    response = model.generate_content([PROMPT_DIAGNOSTICO_MOVEL, image])
    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-zA-Z]*\n", "", raw_text)
        raw_text = re.sub(r"\n```$", "", raw_text)

    try:
        data = json.loads(raw_text)
    except Exception:
        match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            data = {
                "tipo_movel": "Armário Personalizado",
                "descricao_visual": "Móvel identificado por foto",
                "portas_detectadas": 2,
                "tipo_porta": "giro",
                "gavetas_detectadas": 0,
                "prateleiras_detectadas": 1,
                "tem_rodape": False,
                "altura_rodape_sugerida_mm": 0,
                "perguntas_ao_marceneiro": ["Informe as medidas externas de largura, altura e profundidade."]
            }

    cache[hash_img] = data
    _salvar_cache(cache)
    return data


def explodir_movel_parametrico(
    largura_total_mm: int,
    altura_total_mm: int,
    profundidade_total_mm: int,
    espessura_mdf_mm: int = 15,
    qtd_portas: int = 2,
    qtd_gavetas: int = 0,
    qtd_prateleiras: int = 1,
    altura_rodape_mm: int = 0,
    tem_fundo: bool = True
) -> List[Dict[str, Any]]:
    """
    Calcula as peças exatas do móvel aplicando as regras de engenharia de marcenaria brasileira:
    - Desconto de espessuras de laterais na base e tampo
    - Folga de 26mm para corrediças telescópicas de gavetas
    - Folga central de 3-4mm entre portas de giro
    - Recuo de 20mm nas prateleiras internas
    """
    W = largura_total_mm
    H = altura_total_mm
    D = profundidade_total_mm
    E = espessura_mdf_mm
    R = altura_rodape_mm

    pecas = []

    # 1. Laterais (2x)
    pecas.append({
        "id": "LAT",
        "nome": "Lateral do Móvel",
        "comprimento_mm": H,
        "largura_mm": D,
        "quantidade": 2,
        "fita": "1 Comprimento"
    })

    # 2. Base e Tampo (2x) - Encaixados entre as laterais
    w_vao_interno = W - 2 * E
    h_vao_interno = H - (2 * E) - R

    pecas.append({
        "id": "BASE_TAMPO",
        "nome": "Base e Tampo",
        "comprimento_mm": w_vao_interno,
        "largura_mm": D,
        "quantidade": 2,
        "fita": "1 Comprimento"
    })

    # 3. Rodapé (se houver)
    if R > 0:
        pecas.append({
            "id": "RODAPE_FRONTAL",
            "nome": "Rodapé Frontal",
            "comprimento_mm": w_vao_interno,
            "largura_mm": R,
            "quantidade": 2,
            "fita": "Sem fita"
        })

    # 4. Prateleiras Internas
    if qtd_prateleiras > 0:
        pecas.append({
            "id": "PRAT",
            "nome": "Prateleira Interna",
            "comprimento_mm": w_vao_interno - 2, # 2mm de folga
            "largura_mm": D - 20,                # 20mm de recuo da porta
            "quantidade": qtd_prateleiras,
            "fita": "1 Comprimento"
        })

    # 5. Portas de Giro
    if qtd_portas > 0:
        h_porta = H - R - 4 # 4mm de folga vertical
        w_porta = int((W - 4) / qtd_portas) - 2 # folga de 2mm entre portas
        pecas.append({
            "id": "PORTA",
            "nome": f"Porta de Giro ({qtd_portas}x)",
            "comprimento_mm": max(h_porta, w_porta),
            "largura_mm": min(h_porta, w_porta),
            "quantidade": qtd_portas,
            "fita": "4 Lados"
        })

    # 6. Gavetas (se houver)
    if qtd_gavetas > 0:
        # Altura média da frente da gaveta
        h_frente = int((h_vao_interno / 2) / qtd_gavetas) - 4
        comp_lat_gaveta = max(250, D - 50) # corrediça padrão 350, 400, 450, 500
        comp_contra_frente = w_vao_interno - (2 * E) - 26 # 26mm = folga do par de corrediça telescópica

        # Frente de gaveta
        pecas.append({
            "id": "FRENTE_GAV",
            "nome": "Frente de Gaveta",
            "comprimento_mm": w_vao_interno - 4,
            "largura_mm": h_frente,
            "quantidade": qtd_gavetas,
            "fita": "4 Lados"
        })

        # Laterais de gaveta (2 por gaveta)
        pecas.append({
            "id": "LAT_GAV",
            "nome": "Lateral de Gaveta",
            "comprimento_mm": comp_lat_gaveta,
            "largura_mm": max(100, h_frente - 40),
            "quantidade": qtd_gavetas * 2,
            "fita": "1 Comprimento"
        })

        # Contra-frente e Traseira de gaveta (2 por gaveta)
        pecas.append({
            "id": "CONTRA_GAV",
            "nome": "Contra-Frente / Traseira Gaveta",
            "comprimento_mm": max(100, comp_contra_frente),
            "largura_mm": max(100, h_frente - 40),
            "quantidade": qtd_gavetas * 2,
            "fita": "Sem fita"
        })

    # 7. Fundo do Armário (em MDF 6mm)
    if tem_fundo:
        pecas.append({
            "id": "FUNDO_6MM",
            "nome": "Fundo Traseiro (MDF 6mm)",
            "comprimento_mm": W - 4,
            "largura_mm": H - R - 4,
            "quantidade": 1,
            "fita": "Sem fita"
        })

    return pecas
