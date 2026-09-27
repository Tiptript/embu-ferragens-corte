"""
Gerador de Pix Estático Oficial (Padrão Banco Central do Brasil / BR Code EMVCo)
100% Gratuito, sem intermediários, sem taxas bancárias.
O valor cai diretamente na conta da loja.
"""

import io
import base64
import qrcode

def _crc16_ccitt(payload: str) -> str:
    """Calcula o CRC16-CCITT (polinômio 0x1021) conforme norma do Bacen."""
    crc = 0xFFFF
    for char in payload.encode('utf-8'):
        crc ^= (char << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def gerar_pix_brcode(chave_pix: str,
                     nome_recebedor: str,
                     cidade: str,
                     valor: float,
                     txid: str = "CORTEEMBU") -> str:
    """
    Gera a string 'Pix Copia e Cola' oficial.
    """
    # Limpa e formata dados
    chave = chave_pix.strip()
    nome = nome_recebedor.strip().upper()[:25]
    cid = cidade.strip().upper()[:15]
    val_str = f"{valor:.2f}"
    tx = (txid.strip().upper()[:25]) or "CORTE"

    # Montagem TLV (Tag-Length-Value)
    def tlv(tag: str, val: str) -> str:
        return f"{tag}{len(val):02d}{val}"

    # Merchant Account Information (Tag 26)
    gui = tlv("00", "br.gov.bcb.pix")
    key = tlv("01", chave)
    tag26 = tlv("26", gui + key)

    payload_sem_crc = (
        tlv("00", "01") +                       # Payload Format Indicator
        tlv("01", "12") +                       # Point of Initiation (12 = dinâmico/reutilizável)
        tag26 +                                 # Merchant Account Info
        tlv("52", "0000") +                     # Merchant Category Code
        tlv("53", "986") +                      # Currency BRL (986)
        tlv("54", val_str) +                    # Transaction Amount
        tlv("58", "BR") +                       # Country Code
        tlv("59", nome) +                       # Merchant Name
        tlv("60", cid) +                        # Merchant City
        tlv("62", tlv("05", tx)) +              # Additional Data (TXID)
        "6304"                                  # CRC16 Placeholder
    )

    crc = _crc16_ccitt(payload_sem_crc)
    return payload_sem_crc + crc


def gerar_qrcode_pix_base64(payload_pix: str) -> str:
    """Gera o QR Code em imagem PNG Base64 para exibição direta no Streamlit."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload_pix)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


if __name__ == "__main__":
    # Teste rápido
    pix = gerar_pix_brcode(
        chave_pix="11999999999",
        nome_recebedor="EMBU FERRAGENS",
        cidade="EMBU DAS ARTES",
        valor=420.50,
        txid="PEDIDO01"
    )
    print("Código Pix Copia e Cola gerado:")
    print(pix)
    b64 = gerar_qrcode_pix_base64(pix)
    print(f"Base64 gerado com sucesso ({len(b64)} chars)!")
