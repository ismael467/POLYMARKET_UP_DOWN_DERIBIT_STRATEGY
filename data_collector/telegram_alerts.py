import requests
import csv
import time
import os
import json
from datetime import datetime, date

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
EDGE_MINIMO = float(os.environ.get("EDGE_MINIMO", "0.05"))
APUESTA = 5.0
ARCHIVO_ESTADO = "simulacion.json"

def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    })

def cargar_estado():
    if os.path.exists(ARCHIVO_ESTADO):
        with open(ARCHIVO_ESTADO, "r") as f:
            return json.load(f)
    return {
        "saldo": 100.0,
        "operaciones_hoy": 0,
        "ganadoras_hoy": 0,
        "perdedoras_hoy": 0,
        "pnl_hoy": 0.0,
        "fecha_hoy": str(date.today()),
        "ultima_señal": None,
        "precio_entrada": None,
        "direccion_entrada": None
    }

def guardar_estado(estado):
    with open(ARCHIVO_ESTADO, "w") as f:
        json.dump(estado, f)

def resetear_dia_si_nuevo(estado):
    hoy = str(date.today())
    if estado["fecha_hoy"] != hoy:
        # Enviar resumen del día anterior
        msg = (
            f"📊 <b>RESUMEN DEL DÍA</b>\n"
            f"📅 {estado['fecha_hoy']}\n"
            f"━━━━━━━━━━━━━━\n"
            f"Operaciones: {estado['operaciones_hoy']}\n"
            f"✅ Ganadoras: {estado['ganadoras_hoy']}\n"
            f"❌ Perdedoras: {estado['perdedoras_hoy']}\n"
        )
        if estado['operaciones_hoy'] > 0:
            winrate = estado['ganadoras_hoy'] / estado['operaciones_hoy'] * 100
            msg += f"🎯 Win rate: {winrate:.0f}%\n"
        msg += (
            f"💰 PnL hoy: {estado['pnl_hoy']:+.2f}$\n"
            f"💼 Saldo total: {estado['saldo']:.2f}$"
        )
        enviar_alerta(msg)

        estado["operaciones_hoy"] = 0
        estado["ganadoras_hoy"] = 0
        estado["perdedoras_hoy"] = 0
        estado["pnl_hoy"] = 0.0
        estado["fecha_hoy"] = hoy
    return estado

def resolver_operacion_anterior(estado, precio_actual, direccion_actual):
    if estado["ultima_señal"] is None:
        return estado

    precio_entrada = estado["precio_entrada"]
    direccion = estado["direccion_entrada"]
    hora = datetime.now().strftime("%H:%M")

    if precio_entrada is None:
        return estado

    subio = float(precio_actual) > float(precio_entrada)
    gano = (direccion == "UP" and subio) or (direccion == "DOWN" and not subio)

    if gano:
        ganancia = APUESTA * 0.9  # simula pago ~90 centavos por dólar
        estado["saldo"] += ganancia
        estado["pnl_hoy"] += ganancia
        estado["ganadoras_hoy"] += 1
        resultado = f"✅ GANÓ +{ganancia:.2f}$"
    else:
        estado["saldo"] -= APUESTA
        estado["pnl_hoy"] -= APUESTA
        estado["perdedoras_hoy"] += 1
        resultado = f"❌ PERDIÓ -{APUESTA:.2f}$"

    msg = (
        f"📋 <b>RESULTADO OPERACIÓN</b>\n"
        f"🕐 Hora: {hora}\n"
        f"📊 Dirección: {direccion}\n"
        f"💵 Entrada: ${precio_entrada}\n"
        f"💵 Salida: ${precio_actual}\n"
        f"{resultado}\n"
        f"💼 Saldo: {estado['saldo']:.2f}$"
    )
    enviar_alerta(msg)

    estado["ultima_señal"] = None
    estado["precio_entrada"] = None
    estado["direccion_entrada"] = None
    return estado

def monitorear_probabilidades():
    ultima_fila = None
    estado = cargar_estado()
    print("🚀 Monitor de alertas con simulación iniciado...")

    while True:
        try:
            with open("probabilities.csv", "r") as f:
                filas = list(csv.DictReader(f))
                if not filas:
                    time.sleep(30)
                    continue

                fila = filas[-1]
                if fila == ultima_fila:
                    time.sleep(30)
                    continue

                ultima_fila = fila
                estado = resetear_dia_si_nuevo(estado)

                prob_modelo = float(fila.get("model_prob", 0))
                prob_mercado = float(fila.get("market_price", 0))
                edge = prob_modelo - prob_mercado
                direccion = fila.get("direction", "UP")
                precio_btc = fila.get("btc_price", "0")
                hora = datetime.now().strftime("%H:%M")

                # Resolver operación anterior
                estado = resolver_operacion_anterior(
                    estado, precio_btc, direccion
                )

                if abs(edge) >= EDGE_MINIMO and estado["saldo"] >= APUESTA:
                    estado["operaciones_hoy"] += 1
                    estado["ultima_señal"] = hora
                    estado["precio_entrada"] = precio_btc
                    estado["direccion_entrada"] = direccion

                    emoji = "🟢" if edge > 0 else "🔴"
                    señal = "COMPRAR" if edge > 0 else "VENDER"

                    msg = (
                        f"{emoji} <b>ALERTA POLYMARKET BTC</b>\n"
                        f"🕐 Hora: {hora}\n"
                        f"💰 BTC: ${precio_btc}\n"
                        f"📊 Dirección: {direccion}\n"
                        f"🤖 Prob. Modelo: {prob_modelo:.1%}\n"
                        f"🏪 Precio Mercado: {prob_mercado:.1%}\n"
                        f"⚡ Edge: {edge:+.1%}\n"
                        f"✅ Señal: <b>{señal}</b>\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"💵 Apuesta simulada: {APUESTA:.2f}$\n"
                        f"💼 Saldo actual: {estado['saldo']:.2f}$"
                    )
                    enviar_alerta(msg)
                    guardar_estado(estado)
                    print(f"Alerta enviada: Edge {edge:+.1%}")

        except FileNotFoundError:
            print("Esperando probabilities.csv...")
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(30)

if __name__ == "__main__":
    monitorear_probabilidades()
