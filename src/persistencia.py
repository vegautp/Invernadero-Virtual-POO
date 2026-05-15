import datetime

def guardar_log(t, h, v, r):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{fecha} | Temp: {t}°C | Hum: {h}% | Vent: {v} | Riego: {r}\n"
    with open("data/historial.txt", "a") as f:
        f.write(linea)
