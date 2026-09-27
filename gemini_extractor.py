"""
Módulo de Extração Inteligente de Listas de Peças via Gemini 3.8 Flash.
Capaz de ler:
- Fotos de listas manuscritas em papel
- Capturas de tela de conversas do WhatsApp
- Texto livre colado pelo operador
"""

import os
import json
import re
import hashlib
from typing import Optional, Dict, Any
import google.generativeai as genai
from PIL import Image
import io
import time

CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cache_extracao_ia.json"))

def _carregar_cache() -> Dict[str, Any]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _salvar_cache(cache: Dict[str, Any]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar cache: {e}")

def calcular_hash_entrada(texto: Optional[str] = None, imagem_bytes: Optional[bytes] = None) -> str:
    """Calcula o hash SHA-256 único da imagem e/ou texto de entrada."""
    hasher = hashlib.sha256()
    if texto:
        hasher.update(texto.strip().encode("utf-8"))
    if imagem_bytes:
        hasher.update(imagem_bytes)
    return hasher.hexdigest()

def get_api_key() -> str:
    """Busca a chave em variáveis de ambiente ou no local.settings.json"""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    
    # Tenta ler do Segundo Cerebro
    caminho_settings = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Segundo Cerebro", "local.settings.json"))
    if os.path.exists(caminho_settings):
        try:
            with open(caminho_settings, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("Values", {}).get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return ""


SYSTEM_PROMPT = """
Você é o assistente oficial de planejamento de corte da Embu Ferragens (marcenaria profissional no Brasil).
Sua missão é extrair com precisão cirúrgica a lista de peças de madeira (MDF/Compensado) a partir do texto ou da foto fornecida.

REGRAS OBRIGATÓRIAS DE CONVERSÃO E NORMALIZAÇÃO:
1. UNIDADES DE MEDIDA NO BRASIL:
   - Medidas expressas em dezenas/centenas como '185x50', '135x40', '140x20', '65x20' ESTÃO EM CENTÍMETROS (cm).
   - Você DEVE converter TODAS as medidas para MILÍMETROS (mm) multiplicando por 10.
     Exemplo: 185x50 cm -> comprimento: 1850 mm, largura: 500 mm.
     Exemplo: 140x20 cm -> comprimento: 1400 mm, largura: 200 mm.
     Exemplo: 65x20 cm  -> comprimento: 650 mm,  largura: 200 mm.
   - Se os números já estiverem na casa dos milhares (ex: 1850x500 ou 2750x1850), mantenha como mm.
   - Se for ambíguo (ex: '80'), considere cm (800 mm) se estiver no contexto de móveis (portas, laterais, gavetas).

2. QUANTIDADES:
   - Notações como '1- 185x50', '2- 140x20', '2x 65x20', '4 peças de 70x50' indicam a quantidade.
   - O campo 'quantidade' deve ser um número inteiro >= 1.

3. CONVENÇÃO DE DIMENSÕES:
   - Em marcenaria: comprimento (ao longo do veio/maior lado) e largura (travessa/menor lado).
   - Defina comprimento_mm >= largura_mm sempre que possível, a menos que especificado o contrário.

4. FITAS DE BORDA:
   - Se houver menção de fita (ex: '4L' = 4 lados, '1C' = 1 comprimento, '2L' = 2 larguras):
     Preencha os booleanos fita_sup, fita_inf, fita_esq, fita_dir. Caso não haja menção, padrão é false.

5. SEPARAÇÃO DE MATERIAIS:
   - Agrupe por material/espessura (ex: 'MDF Preto 15mm', 'MDF Preto 6mm', 'MDF Branco TX 18mm').
   - Se nenhum material for informado, use 'MDF Padrão 15mm'.

FORMATO DA RESPOSTA:
Responda EXCLUSIVAMENTE com um JSON válido (sem markdown de código ```json e sem texto antes ou depois):
{
  "materiais": [
    {
      "material": "MDF Preto 15mm",
      "pecas": [
        {
          "id": "P1",
          "nome": "Peça 1850x500",
          "comprimento_mm": 1850,
          "largura_mm": 500,
          "quantidade": 1,
          "fita_sup": false,
          "fita_inf": false,
          "fita_esq": false,
          "fita_dir": false
        }
      ]
    }
  ]
}
"""


def extrair_pecas_gemini(texto: Optional[str] = None,
                         imagem_bytes: Optional[bytes] = None,
                         mime_type: str = "image/jpeg",
                         api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Chama o Gemini 3.8 Flash para estruturar a lista de peças a partir de texto ou imagem.
    Utiliza Cache SHA-256 para evitar consumo desnecessário de cota do Gemini.
    """
    # 1. Verifica Cache SHA-256
    hash_entrada = calcular_hash_entrada(texto, imagem_bytes)
    cache = _carregar_cache()
    if hash_entrada in cache:
        print(f"[CACHE HIT SHA-256] Resposta recuperada instantaneamente do cache local ({hash_entrada[:10]}...).")
        return cache[hash_entrada]

    # 2. Se não estiver no cache, chama o Gemini com retry e fallback de modelos
    key = api_key or get_api_key()
    if not key:
        raise ValueError("Chave de API do Gemini não encontrada! Configure a GEMINI_API_KEY.")

    genai.configure(api_key=key)
    modelos_disponiveis = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

    contents = [SYSTEM_PROMPT]
    if texto and texto.strip():
        contents.append(f"Entrada textual do operador/cliente:\n{texto.strip()}")
    if imagem_bytes:
        image = Image.open(io.BytesIO(imagem_bytes))
        contents.append(image)

    raw_text = None
    ultimo_erro = None

    for m_name in modelos_disponiveis:
        for tentativa in range(3):
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(contents)
                raw_text = response.text.strip()
                break
            except Exception as e:
                ultimo_erro = e
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "resourceexhausted" in err_str:
                    time.sleep(2.0 * (tentativa + 1))
                else:
                    break
        if raw_text:
            break

    if not raw_text:
        raise ValueError(f"Não foi possível extrair com a IA após tentativas: {ultimo_erro}")

    # Limpa marcações markdown se presentes
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-zA-Z]*\n", "", raw_text)
        raw_text = re.sub(r"\n```$", "", raw_text)

    try:
        data = json.loads(raw_text)
        # 3. Salva no Cache SHA-256
        cache[hash_entrada] = data
        _salvar_cache(cache)
        print(f"[CACHE MISS] Resposta do Gemini salva com sucesso no cache ({hash_entrada[:10]}...).")
        return data
    except json.JSONDecodeError as err:
        match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            cache[hash_entrada] = data
            _salvar_cache(cache)
            return data
        raise ValueError(f"O Gemini retornou uma resposta fora do formato JSON: {raw_text}") from err


if __name__ == "__main__":
    teste_texto = """
    Me vê este material preto MDF 15 mm
    1- 185x50
    1-185x45
    1-135x40
    1-135x35
    2-140x20
    2-65x20

    E MDF preto 6mm
    1-180x45
    1-130x35
    1-140x65
    """
    resultado = extrair_pecas_gemini(texto=teste_texto)
    print("Sucesso! Materiais extraídos:", len(resultado.get("materiais", [])))
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
