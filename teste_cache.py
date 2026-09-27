from gemini_extractor import extrair_pecas_gemini
import time

txt = "1- 185x50 MDF Preto 15mm"
print("Chamada 1...")
t0 = time.time()
r1 = extrair_pecas_gemini(texto=txt)
t1 = time.time()
print(f"Tempo 1: {t1-t0:.2f}s")

print("Chamada 2 (repetida)...")
t2 = time.time()
r2 = extrair_pecas_gemini(texto=txt)
t3 = time.time()
print(f"Tempo 2 (Cache SHA-256): {t3-t2:.5f}s")
assert r1 == r2
print("TESTE DE CACHE SHA-256 APROVADO COM SUCESSO!")
