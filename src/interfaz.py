import customtkinter as ctk
import random
from controlador import Controlador
from persistencia import guardar_log

# Nuevas herramientas para dibujar la gráfica
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VentanaInvernadero:
    def __init__(self, root):
        self.root = root
        self.ctrl = Controlador()
        self.root.title("Dashboard Invernadero - Modo Oscuro")
        # Hacemos la ventana más alta para que quepa la gráfica
        self.root.geometry("600x600") 
        
        # --- DATOS EN TEXTO ---
        self.label_datos = ctk.CTkLabel(root, text="Iniciando...", font=("Arial", 14))
        self.label_datos.pack(pady=10)
        
        self.label_luz = ctk.CTkLabel(
            root, text="Luz: Cargando... lx", font=("Arial", 28, "bold"), text_color="#FFD700"
        )
        self.label_luz.pack(pady=10)

        # --- NUEVO: CONFIGURACIÓN DE LA GRÁFICA ---
        # Creamos la figura de la gráfica y le damos un fondo oscuro (#242424)
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#242424')
        self.ax.set_facecolor('#242424')
        
        # Pintamos los bordes y textos de la gráfica de blanco para que se vean
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('white')

        self.ax.set_title("Historial de Luminosidad", color="white")
        
        # Listas para guardar el tiempo y la luz
        self.x_data = []
        self.y_data = []
        self.tiempo = 0

        # Creamos la línea de la gráfica en color amarillo
        self.line, = self.ax.plot([], [], color="#FFD700", marker='o') 
        
        # "Pegamos" la gráfica de matplotlib en nuestra ventana de customtkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(pady=10)

        self.actualizar()

    def actualizar(self):
        t, h, v, r = self.ctrl.procesar()
        guardar_log(t, h, v, r)
        self.label_datos.configure(text=f"Temp: {t}°C | Hum: {h}%\nVentilador: {v}\nRiego: {r}")
        
        luz_simulada = round(random.uniform(800, 950), 1)
        self.label_luz.configure(text=f"Luz: {luz_simulada} lx")
        
        # --- NUEVO: ACTUALIZAMOS LOS PUNTOS DE LA GRÁFICA ---
        self.tiempo += 2 # Sumamos 2 segundos en el eje X
        self.x_data.append(self.tiempo)
        self.y_data.append(luz_simulada)
        
        # Borramos los datos viejos para que la gráfica no se haga infinita (mostramos los últimos 10)
        if len(self.x_data) > 10:
            self.x_data.pop(0)
            self.y_data.pop(0)

        # Le pasamos los nuevos datos a la línea y redibujamos
        self.line.set_xdata(self.x_data)
        self.line.set_ydata(self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
        
        self.root.after(2000, self.actualizar)