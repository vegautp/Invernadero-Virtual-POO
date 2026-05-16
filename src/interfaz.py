import customtkinter as ctk
from controlador import Controlador
from persistencia import guardar_log

class VentanaInvernadero:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Invernadero Virtual")
        self.root.geometry("650x450")
        
        self.ctrl = Controlador()

        # Configuración principal de grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Dashboard del Invernadero", 
            font=("Roboto", 24, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        # Switch de modo Claro/Oscuro
        self.switch_var = ctk.StringVar(value="dark")
        self.theme_switch = ctk.CTkSwitch(
            self.header_frame, 
            text="Modo Oscuro", 
            command=self.toggle_theme,
            variable=self.switch_var, 
            onvalue="dark", 
            offvalue="light",
            font=("Roboto", 14)
        )
        self.theme_switch.grid(row=0, column=1, sticky="e")

        # --- Contenedor Principal (Dashboard) ---
        self.dashboard_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.dashboard_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.dashboard_frame.grid_columnconfigure((0, 1), weight=1)
        self.dashboard_frame.grid_rowconfigure(0, weight=1)

        # 1. Panel de Sensores
        self.sensor_frame = ctk.CTkFrame(self.dashboard_frame, corner_radius=15)
        self.sensor_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        
        self.sensor_title = ctk.CTkLabel(
            self.sensor_frame, 
            text="Sensores", 
            font=("Roboto", 18, "bold")
        )
        self.sensor_title.pack(pady=(20, 15))
        
        self.temp_label = ctk.CTkLabel(self.sensor_frame, text="Temperatura: --", font=("Roboto", 16))
        self.temp_label.pack(pady=15)
        
        self.hum_label = ctk.CTkLabel(self.sensor_frame, text="Humedad: --", font=("Roboto", 16))
        self.hum_label.pack(pady=15)

        # 2. Panel de Actuadores
        self.actuator_frame = ctk.CTkFrame(self.dashboard_frame, corner_radius=15)
        self.actuator_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        
        self.actuator_title = ctk.CTkLabel(
            self.actuator_frame, 
            text="Actuadores", 
            font=("Roboto", 18, "bold")
        )
        self.actuator_title.pack(pady=(20, 15))
        
        self.vent_label = ctk.CTkLabel(self.actuator_frame, text="Ventilador: --", font=("Roboto", 16))
        self.vent_label.pack(pady=15)
        
        self.riego_label = ctk.CTkLabel(self.actuator_frame, text="Bomba Riego: --", font=("Roboto", 16))
        self.riego_label.pack(pady=15)

        # Iniciar ciclo de actualización
        self.actualizar()

    def toggle_theme(self):
        """Alternar entre modo claro y oscuro."""
        if self.switch_var.get() == "dark":
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="Modo Oscuro")
        else:
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="Modo Claro")

    def actualizar(self):
        """Obtiene datos del controlador y actualiza la GUI."""
        # Procesar datos y guardar (sin modificar lógica de negocio)
        t, h, v, r = self.ctrl.procesar()
        guardar_log(t, h, v, r)
        
        # Formatear números si son float/int
        temp_str = f"{t:.1f} °C" if isinstance(t, (int, float)) else f"{t} °C"
        hum_str = f"{h:.1f} %" if isinstance(h, (int, float)) else f"{h} %"
        
        self.temp_label.configure(text=f"Temperatura: {temp_str}")
        self.hum_label.configure(text=f"Humedad: {hum_str}")
        
        # Mapeo visual para actuadores (Verde si encendido, Gris/Rojo si apagado)
        vent_estado = "Encendido" if v else "Apagado"
        vent_color = "#2ecc71" if v else "#e74c3c" # Verde / Rojo
        self.vent_label.configure(text=f"Ventilador: {vent_estado}", text_color=vent_color)
        
        riego_estado = "Encendido" if r else "Apagado"
        riego_color = "#3498db" if r else "#e74c3c" # Azul / Rojo
        self.riego_label.configure(text=f"Bomba Riego: {riego_estado}", text_color=riego_color)
        
        # Refrescar cada 2 segundos manteniendo la lógica original
        self.root.after(2000, self.actualizar)
