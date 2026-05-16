import datetime
import os

def guardar_log(t, h, v, r):
    # Asegura que la carpeta data exista
    if not os.path.exists('data'):
        os.makedirs('data')
        
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_v = "ON" if v else "OFF"
    estado_r = "ON" if r else "OFF"
    
    linea = f"[{fecha}] T: {t}C | H: {h}% | Vent: {estado_v} | Riego: {estado_r}\n"
    
    with open("data/historial.txt", "a") as f:
        f.write(linea)