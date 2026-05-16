import tkinter as tk
from controlador import Controlador
from persistencia import guardar_log

class VentanaInvernadero:
    def __init__(self, root):
        self.ctrl = Controlador()
        self.root = root
        self.root.title("SISTEMA INVERNADERO VIRTUAL - UTP")
        self.root.geometry("400x300")
        
        self.label_titulo = tk.Label(root, text="Monitoreo en Tiempo Real", font=("Arial", 16, "bold"))
        self.label_titulo.pack(pady=10)

        self.label_datos = tk.Label(root, text="Cargando datos...", font=("Consolas", 12), justify="left")
        self.label_datos.pack(pady=20)

        self.actualizar_ciclo()

    def actualizar_ciclo(self):
        t, h, v, r = self.ctrl.procesar_logica()
        guardar_log(t, h, v, r)
        
        texto = (f"TEMPERATURA: {t} °C\n"
                 f"HUMEDAD:     {h} %\n"
                 f"----------------------\n"
                 f"VENTILADOR:  {'[ENCENDIDO]' if v else '[APAGADO]'}\n"
                 f"SIST. RIEGO: {'[ENCENDIDO]' if r else '[APAGADO]'}")
        
        self.label_datos.config(text=texto)
        # Se actualiza cada 2 segundos
        self.root.after(2000, self.actualizar_ciclo)