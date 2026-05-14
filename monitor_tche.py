import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

# =========================
# TELEGRAM (CORREGIDO DE FORMA DEFINITIVA)
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

mensaje_telegram = ""

# =========================
# DESCARGAR PAGINA
# =========================
url = "https://lista.tcheloco.com.py/?show_all=1"
headers = {"User-Agent": "Mozilla/5.0"}

print("Descargando catálogo...")
response = requests.get(url, headers=headers)
print("STATUS:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")
productos = []
filas = soup.find_all("tr")

for fila in filas:
    columnas = fila.find_all("td")
    textos = [c.get_text(strip=True) for c in columnas]

    if len(textos) >= 5 and "U$" in textos[-1]:
        try:
            precio = textos[-1]
            marca = textos[-2]
            categoria = textos[-3]
            nombre = textos[-4]
            codigo = nombre

            # =========================
            # FILTROS
            # =========================
            marcas_permitidas = ["JBL", "PIONEER", "ECOPOWER"]
            categorias_permitidas = [
                "AUTOMOTIVO",
                "MULTIMEDIAS",
                "RADIO CAR USB",
                "ALTO FALANTES",
                "TOCA CD",
                "DVD AUTOMOTIVO",
            ]

            marca_upper = marca.upper()
            categoria_upper = categoria.upper()

            marca_ok = any(m in marca_upper for m in marcas_permitidas)
            categoria_ok = any(c in categoria_upper for c in categorias_permitidas)

            if not (marca_ok and categoria_ok):
                continue

            productos.append(
                {
                    "codigo": str(codigo),
                    "nombre": str(nombre),
                    "categoria": str(categoria),
                    "marca": str(marca),
                    "precio": str(precio),
                }
            )
        except Exception as e:
            print("Error leyendo fila:", e)

# =========================
# DATAFRAME NUEVO
# =========================
df_nuevo = pd.DataFrame(productos)
print(f"\nProductos encontrados: {len(df_nuevo)}")

archivo_anterior = "productos_tche_anterior.csv"

# =========================
# COMPARAR
# =========================
if os.path.exists(archivo_anterior):
    try:
        df_anterior = pd.read_csv(archivo_anterior, dtype=str)
        anteriores = dict(zip(df_anterior["codigo"], df_anterior["precio"]))
        actuales = dict(zip(df_nuevo["codigo"], df_nuevo["precio"]))

        cambios = 0
        for codigo, precio_nuevo in actuales.items():
            if codigo in anteriores:
                precio_viejo = anteriores[codigo]
                if precio_viejo != precio_nuevo:
                    fila_actual = df_nuevo[df_nuevo["codigo"] == codigo]
                    if not fila_actual.empty:
                        fila = fila_actual.iloc[0]
                        texto = (
                            f"🔄 CAMBIO\n"
                            f"{fila['marca']} - {fila['nombre']}\n"
                            f"{precio_viejo} → {precio_nuevo}\n\n"
                        )
                        print(texto)
                        mensaje_telegram += texto
                        cambios += 1

        nuevos = 0
        for codigo in actuales:
            if codigo not in anteriores:
                fila_actual = df_nuevo[df_nuevo["codigo"] == codigo]
                if not fila_actual.empty:
                    fila = fila_actual.iloc[0]
                    texto = (
                        f"🆕 NUEVO\n"
                        f"{fila['marca']} - {fila['nombre']}\n"
                        f"{fila['precio']}\n\n"
                    )
                    print(texto)
                    mensaje_telegram += texto
                    nuevos += 1

        eliminados = 0
        for codigo in anteriores:
            if codigo not in actuales:
                fila_vieja = df_anterior[df_anterior["codigo"] == codigo]
                if not fila_vieja.empty:
                    fila = fila_vieja.iloc[0]
                    texto = f"❌ ELIMINADO\n" f"{fila['marca']} - {fila['nombre']}\n\n"
                    print(texto)
                    mensaje_telegram += texto
                    eliminados += 1

        print(f"\nCambios: {cambios}")
        print(f"Nuevos: {nuevos}")
        print(f"Eliminados: {eliminados}")

    except Exception as e:
        print("Error comparando:")
        print(e)
else:
    print("\nNo existe archivo anterior todavía.")

# =========================
# GUARDAR CSV
# =========================
df_nuevo.to_csv(archivo_anterior, index=False)
print("\nCSV actualizado correctamente")

# =========================
# ENVIAR TELEGRAM (CON SEGMENTACIÓN DE TEXTO)
# =========================
if mensaje_telegram.strip():
    if not TOKEN or not CHAT_ID:
        print("Error: TOKEN o CHAT_ID no configurados en el entorno.")
    else:
        url_telegram = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        # Imprime de forma segura las credenciales cargadas
        print(f"DEBUG: Token cargado (longitud): {len(TOKEN) if TOKEN else 0}")
        print(f"DEBUG: Chat ID cargado: {CHAT_ID}")

        # Divide el mensaje si supera los 4000 caracteres para evitar bloqueos de la API
        MAX_LENGTH = 4000
        partes = [
            mensaje_telegram[i : i + MAX_LENGTH]
            for i in range(0, len(mensaje_telegram), MAX_LENGTH)
        ]

        for num_parte, parte in enumerate(partes, 1):
            response_tg = requests.post(
                url_telegram, data={"chat_id": CHAT_ID, "text": parte}
            )
            if response_tg.status_code == 200:
                print(f"Parte {num_parte} de Telegram enviada")
            else:
                print(
                    f"Fallo al enviar parte {num_parte}: {response_tg.status_code} - {response_tg.text}"
                )
else:
    print("Sin cambios para Telegram")
