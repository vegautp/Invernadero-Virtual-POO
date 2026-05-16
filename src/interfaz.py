import tkinter as tk 
from controlador import Controlador 
from persistencia import guardar_log 

class VentanaInvernadero: 
    def __init__(self, root): 
        self.root = root
        self.ctrl = Controlador() 
        root.title("Sistema Invernadero Virtual") 
        self.label = tk.Label(root, text="Iniciando...", font=("Arial", 14)) 
        self.label.pack(pady=20) 
        self.actualizar() 

    def actualizar(self): 
        t, h, v, r = self.ctrl.procesar() 
        guardar_log(t, h, v, r) 
        self.label.config(text=f"Temp: {t}°C | Hum: {h}%\nVentilador: {v}\nRiego: {r}") 
        self.root.after(2000, self.actualizar) # Refrescar cada 2 segundos 
