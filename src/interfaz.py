"""
interfaz.py — Módulo de Interfaz Gráfica de Usuario (GUI).

Construido con CustomTkinter. Es el responsable exclusivo de la visualización
y la interacción con el usuario. Lee el estado del Controlador y renderiza
indicadores, gráficas (con Matplotlib) y el registro histórico.
Implementa el motor gráfico que no interfiere con la lógica física.
"""

# IMPORTANTE: Requiere instalar matplotlib. Ejecutar: pip install matplotlib
import sys
import os
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import math
import random
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import datetime

from controlador import Controlador
from ui.panel_graficos import PanelMonitoreoGrafico

class ToolTip:
    """Clase para mostrar un texto emergente al pasar el cursor sobre un widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, background="#34495e", foreground="white", relief="solid", borderwidth=1, font=("Roboto", 10))
        label.pack(ipadx=5, ipady=2)

    def leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class VentanaInvernadero:
    """
    Clase principal de la interfaz gráfica del Invernadero Virtual.

    Gestiona la ventana principal, el sistema de pestañas (tabs) y delega la
    lógica de control al objeto Controlador. Contiene loops asíncronos para
    animaciones visuales y actualización de datos en tiempo real.
    """
    def __init__(self, root):
        """
        Inicializa la interfaz gráfica y sus pestañas.

        Args:
            root (ctk.CTk): Ventana raíz de CustomTkinter.
        """
        self.root = root
        self.root.title("Sistema Invernadero Virtual")
        self.root.geometry("850x900")
        
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_programa)
        
        self.ctrl = Controlador()

        
        self.current_data = (0.0, 0.0, 0.0, False, False, 0.0, 0.0)
        self.ultimo_refresco_pesado = datetime.datetime.now()

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)


        self.setup_header()
        
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_actual = self.tabview.add("Monitoreo Actual")
        self.tab_grafico = self.tabview.add("Monitoreo Gráfico")
        self.tab_agronomico = self.tabview.add("Análisis Agronómico")
        self.tab_historico = self.tabview.add("Registro Histórico")
        
        # Variables para animaciones independientes
        self.vent_state = False
        self.vent_angle = 0
        self.riego_state = False
        self.riego_drops = []
        self.ilum_intensity = 0.0
        self.malla_anim_pct = 0.0

        # Variables para Motor Gráfico de Planta
        self.plant_rgb = [46, 204, 113] # #2ecc71
        self.target_rgb = [46, 204, 113]
        self.crecimiento_display = 0.0
        self.crecimiento_target = 0.0

        self.setup_tab_actual()
        self.setup_tab_grafico()
        self.setup_tab_agronomico()
        self.setup_tab_historico()
        self.setup_time_banner()

        self.animar_actuadores()
        self.actualizar()
        self._tick_reloj()  # Loop de reloj independiente, 1 seg


    def setup_header(self):
        self.header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.header_frame.grid_columnconfigure(2, weight=1)
        self.header_frame.grid_columnconfigure(3, weight=0)
        self.header_frame.grid_columnconfigure(4, weight=0)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Panel de Control - Invernadero Virtual", 
            font=("Roboto", 24, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.solar_info_label = ctk.CTkLabel(
            self.header_frame,
            text="☀️ Fotoperiodo Activo: 07:00 AM a 11:59 PM (Descanso: 12:00 AM a 07:00 AM)",
            font=("Roboto", 13)
        )
        self.solar_info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        self.estado_solar_label = ctk.CTkLabel(
            self.header_frame,
            text="Cargando estado solar...",
            font=("Roboto", 15, "bold")
        )
        self.estado_solar_label.grid(row=2, column=0, sticky="w", pady=(2, 0))

        clock_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        clock_container.grid(row=0, column=1, rowspan=3, padx=(20, 20))
        
        self.lbl_dia_virtual = ctk.CTkLabel(
            clock_container,
            text="Día Virtual: 1",
            font=("Roboto", 13, "bold"),
            text_color="#3498db"
        )
        self.lbl_dia_virtual.pack(anchor="center", pady=(0, 2))

        self.clock_label = ctk.CTkLabel(
            clock_container,
            text="00:00:00",
            font=("Roboto", 28, "bold"),
            text_color="#f39c12"
        )
        self.clock_label.pack(anchor="center")
        

        
        self.btn_abrir_banner = ctk.CTkButton(
            self.header_frame,
            text="⏱️ Configurar Hora",
            font=("Roboto", 14, "bold"),
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            command=self.abrir_banner_tiempo,
            width=140
        )
        self.btn_abrir_banner.grid(row=0, column=3, rowspan=3, padx=(10, 10))
        
        self.speed_var = ctk.StringVar(value="x1")
        self.speed_menu = ctk.CTkOptionMenu(
            self.header_frame,
            values=["x1", "x2", "x5", "x10", "x50"],
            variable=self.speed_var,
            command=self.cambiar_velocidad,
            width=80
        )
        self.speed_menu.grid(row=0, column=4, rowspan=3, padx=(10, 0), sticky="e")

    def setup_time_banner(self):
        self.banner_frame = ctk.CTkFrame(self.root, width=280, height=250, corner_radius=15, fg_color="#1e2430", border_width=2, border_color="#3498db")
        self.banner_frame.place(relx=1.3, rely=0.1, anchor="ne")
        self.banner_frame.pack_propagate(False)
        
        top_frame = ctk.CTkFrame(self.banner_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        lbl_title = ctk.CTkLabel(top_frame, text="Controlador de Tiempo", font=("Roboto", 16, "bold"), text_color="white")
        lbl_title.pack(side="left", padx=5)
        
        btn_close = ctk.CTkButton(top_frame, text="✖", width=30, height=30, corner_radius=15, fg_color="#e74c3c", hover_color="#c0392b", font=("Roboto", 14, "bold"), command=self.cerrar_banner_tiempo)
        btn_close.pack(side="right")
        
        inputs_frame = ctk.CTkFrame(self.banner_frame, fg_color="transparent")
        inputs_frame.pack(pady=15)
        
        self.entry_hora = ctk.CTkEntry(inputs_frame, width=60, font=("Roboto", 24, "bold"), justify="center", placeholder_text="HH")
        self.entry_hora.pack(side="left", padx=5)
        
        lbl_dots = ctk.CTkLabel(inputs_frame, text=":", font=("Roboto", 24, "bold"))
        lbl_dots.pack(side="left")
        
        self.entry_minuto = ctk.CTkEntry(inputs_frame, width=60, font=("Roboto", 24, "bold"), justify="center", placeholder_text="MM")
        self.entry_minuto.pack(side="left", padx=5)
        
        self.ampm_var = ctk.StringVar(value="AM")
        self.menu_ampm = ctk.CTkOptionMenu(inputs_frame, values=["AM", "PM"], variable=self.ampm_var, width=70, font=("Roboto", 14, "bold"))
        self.menu_ampm.pack(side="left", padx=5)
        
        btn_frame = ctk.CTkFrame(self.banner_frame, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        btn_aceptar = ctk.CTkButton(btn_frame, text="Aceptar", width=100, fg_color="#2ecc71", hover_color="#27ae60", font=("Roboto", 14, "bold"), command=self.aplicar_hora_manual)
        btn_aceptar.pack(side="left", padx=10)
        
        btn_cancelar = ctk.CTkButton(btn_frame, text="Cancelar", width=100, fg_color="#7f8c8d", hover_color="#95a5a6", font=("Roboto", 14, "bold"), command=self.cerrar_banner_tiempo)
        btn_cancelar.pack(side="right", padx=10)

    def abrir_banner_tiempo(self, current_relx=1.3):
        if current_relx > 0.98:
            current_relx -= 0.04
            self.banner_frame.place(relx=current_relx, rely=0.1, anchor="ne")
            self.root.after(15, self.abrir_banner_tiempo, current_relx)
        else:
            self.banner_frame.place(relx=0.98, rely=0.1, anchor="ne")

    def cerrar_banner_tiempo(self, current_relx=0.98):
        if current_relx < 1.3:
            current_relx += 0.04
            self.banner_frame.place(relx=current_relx, rely=0.1, anchor="ne")
            self.root.after(15, self.cerrar_banner_tiempo, current_relx)
        else:
            self.banner_frame.place(relx=1.3, rely=0.1, anchor="ne")

    def aplicar_hora_manual(self):
        try:
            h = int(self.entry_hora.get())
            m = int(self.entry_minuto.get())
            ampm = self.ampm_var.get()
            
            if not (1 <= h <= 12) or not (0 <= m <= 59):
                raise ValueError
                
            hora_24 = h
            if ampm == "PM" and h != 12:
                hora_24 += 12
            elif ampm == "AM" and h == 12:
                hora_24 = 0
                
            self.ctrl.fijar_hora_manual(hora_24, m)
            self.cerrar_banner_tiempo()
            
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Error", "Por favor ingresa una hora válida (HH: 1-12, MM: 0-59).")

    def cambiar_velocidad(self, choice):
        mult = float(choice.replace("x", ""))
        self.ctrl.multiplicador_tiempo = mult

    def show_popup(self, title, message):
        """Muestra una leyenda técnica explicativa en formato modal."""
        popup = ctk.CTkToplevel(self.root)
        popup.title(title)
        popup.geometry("350x200")
        popup.attributes("-topmost", True)
        popup.focus_set()
        
        lbl_title = ctk.CTkLabel(popup, text=title, font=("Roboto", 18, "bold"))
        lbl_title.pack(pady=(15, 5))
        
        lbl_msg = ctk.CTkLabel(popup, text=message, font=("Roboto", 14), justify="center", wraplength=300)
        lbl_msg.pack(pady=10)
        
        btn = ctk.CTkButton(popup, text="Entendido", command=popup.destroy, width=120)
        btn.pack(pady=10)

    def setup_tab_actual(self):
        """
        Construye la pestaña 'Monitoreo Actual'.

        Crea los paneles de visualización para sensores (termómetro, higrómetro, luxómetro)
        y actuadores (ventilador, riego, malla térmica). Utiliza Canvas de Tkinter
        incrustados en frames de CustomTkinter para renderizar indicadores (gauges)
        estáticos y dinámicos.
        """
        # 1. Contenedor Infinito (Scrollable)
        self.scroll_actual = ctk.CTkScrollableFrame(self.tab_actual, fg_color="transparent")
        self.scroll_actual.pack(fill="both", expand=True, padx=5, pady=5)

        bg_card = "#2a2d2e"
        bg_canvas = "#2a2d2e"

        # --- SECCIÓN 1 (Exterior) ---
        lbl_sec1 = ctk.CTkLabel(self.scroll_actual, text="🌎 ENTORNO EXTERIOR", font=("Arial", 12, "bold"), text_color="gray", anchor="w")
        lbl_sec1.pack(fill="x", padx=25, pady=(15, 0))

        self.weather_container = ctk.CTkFrame(self.scroll_actual, fg_color="transparent")
        self.weather_container.pack(fill="x", padx=15, pady=(5, 5))
        self.weather_container.grid_columnconfigure(0, weight=1)
        self.weather_container.grid_columnconfigure(1, weight=1)

        # Recuadro Izquierdo (Pronóstico - Altura Uniforme)
        self.forecast_frame = ctk.CTkFrame(self.weather_container, fg_color=bg_card, corner_radius=15, border_width=2, border_color="#3498db", height=100)
        self.forecast_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.forecast_frame.grid_propagate(False)
        
        lbl_pronostico_title = ctk.CTkLabel(self.forecast_frame, text="PRONÓSTICO CLIMÁTICO", font=("Arial", 11, "bold"), text_color="#3498db", anchor="w")
        lbl_pronostico_title.pack(fill="x", padx=15, pady=(10, 0))
        
        self.pronostico_label = ctk.CTkLabel(
            self.forecast_frame,
            text="Cargando pronóstico del clima...",
            font=("Roboto", 14, "bold"),
            justify="left",
            anchor="nw",
            text_color=("#2c3e50", "#3498db"),
            wraplength=400
        )
        self.pronostico_label.pack(padx=15, pady=(5, 12), fill="both", expand=True)
        
        # Recuadro Derecho (Sensores Externos - Altura Uniforme)
        self.ext_weather_frame = ctk.CTkFrame(self.weather_container, fg_color=bg_card, corner_radius=15, border_width=2, border_color="#e67e22", height=100)
        self.ext_weather_frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.ext_weather_frame.grid_propagate(False)
        
        lbl_ext_title = ctk.CTkLabel(self.ext_weather_frame, text="SENSORES EXTERIORES", font=("Arial", 11, "bold"), text_color="#e67e22", anchor="center")
        lbl_ext_title.pack(fill="x", padx=15, pady=(10, 0))

        self.lbl_ext_temp = ctk.CTkLabel(
            self.ext_weather_frame,
            text="🌡️ Ext: -- °C | 💧 Hum: -- %",
            font=("Roboto", 14, "bold"),
            text_color="#e67e22",
            anchor="center"
        )
        self.lbl_ext_temp.pack(padx=15, pady=(5, 12), fill="both", expand=True)

        def create_card(parent, row, col, title, info_text):
            card = ctk.CTkFrame(parent, fg_color=bg_card, corner_radius=15, border_width=2, border_color="#3b3b3b", height=140)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)
            
            # Header container
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=(10, 0))
            
            lbl_title = ctk.CTkLabel(header, text=title.upper(), font=("Roboto", 11, "bold"), text_color="gray", anchor="w")
            lbl_title.pack(side="left", padx=(10, 0))
            
            btn_info = ctk.CTkButton(header, text="ⓘ", width=25, height=25, corner_radius=12, fg_color="transparent", text_color="gray", hover_color="#3b3b3b",
                                     command=lambda: self.show_popup(title, info_text))
            btn_info.pack(side="right")
            ToolTip(btn_info, "Info")
            
            # Content container
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            content.grid_columnconfigure(0, weight=1)
            content.grid_columnconfigure(1, weight=0)
            
            lbl_val = ctk.CTkLabel(content, text="--", font=("Roboto", 24, "bold"), anchor="w", justify="left", wraplength=120)
            lbl_val.grid(row=0, column=0, sticky="w", padx=(10, 0))
            
            cv = tk.Canvas(content, width=80, height=80, bg=bg_canvas, highlightthickness=0)
            cv.grid(row=0, column=1, sticky="e", padx=(0, 10))
            
            return card, lbl_val, cv

        # --- SECCIÓN 2 (Interior) ---
        lbl_sec2 = ctk.CTkLabel(self.scroll_actual, text="🌿 SENSORES INTERIORES DEL INVERNADERO", font=("Arial", 12, "bold"), text_color="gray", anchor="w")
        lbl_sec2.pack(fill="x", padx=25, pady=(15, 0))

        self.interior_container = ctk.CTkFrame(self.scroll_actual, fg_color="transparent")
        self.interior_container.pack(fill="x", padx=15, pady=(5, 5))
        self.interior_container.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_t, self.lbl_t_val, self.cv_temp = create_card(self.interior_container, 0, 0, "Temperatura", "Física: Sube de día por radiación. Baja de noche hacia 15°C.\nAzul: < 15°C | Verde: 15°C a 29°C | Rojo: >= 29°C")
        self.card_h, self.lbl_h_val, self.cv_hum = create_card(self.interior_container, 0, 1, "Humedad", "Física: Baja (se evapora) cuando la temperatura sube. Sube con frío.\nAmarillo: < 40% | Azul: 40% a 80% | Rojo: > 80%")
        self.card_luz, self.lbl_luz_val, self.cv_luz = create_card(self.interior_container, 0, 2, "Luminosidad", "Agronomía: Rango de luz útil para la fotosíntesis.\nGris: < 1,000 Lx | Amarillo: 1,001 Lx a 45,000 Lx | Rojo: > 45,000 Lx")
        
        # --- SECCIÓN 3 (Actuadores) ---
        lbl_sec3 = ctk.CTkLabel(self.scroll_actual, text="⚙️ ACTUADORES", font=("Arial", 12, "bold"), text_color="gray", anchor="w")
        lbl_sec3.pack(fill="x", padx=25, pady=(15, 0))

        def create_actuator_card(parent, col, title, info_text):
            """Tarjeta de actuador con icono + gauge circular agrupados y centrados."""
            # ── Variables de diseño ── Modifica SOLO estas para escalar la tarjeta ──
            icon_size       = 80   # ancho y alto del canvas del icono animado (px)
            gauge_size      = 90   # ancho y alto del canvas del gauge circular (px)
            espacio_interno = 16   # padding horizontal entre icono y gauge (px)
            # ────────────────────────────────────────────────────────────────────────

            card_h = 40 + max(icon_size, gauge_size + 22) + 20  # altura dinámica
            card = ctk.CTkFrame(parent, fg_color=bg_card, corner_radius=15,
                                border_width=2, border_color="#3b3b3b", height=card_h)
            card.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)

            # ── Cabecera ─────────────────────────────────────────────────────────
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=(10, 0))
            
            # Botón de info a la derecha
            ctk.CTkButton(header, text="ⓘ", width=25, height=25, corner_radius=12,
                          fg_color="transparent", text_color="gray", hover_color="#3b3b3b",
                          command=lambda: self.show_popup(title, info_text)).pack(side="right")
            
            # Título centrado (con padding izquierdo compensatorio para equilibrar el botón de la derecha)
            ctk.CTkLabel(header, text=title.upper(), font=("Roboto", 10, "bold"),
                         text_color="gray", anchor="center").pack(fill="x", expand=True, padx=(25, 0))

            # ── Contenedor central: icono + gauge como una unidad visual ─────────
            centro = ctk.CTkFrame(card, fg_color="transparent")
            centro.pack(expand=True, pady=(0, 8))   # se centra vertical y horizontalmente, ligeramente desplazado arriba

            # Canvas del icono animado (izquierda)
            cv_icon = tk.Canvas(centro, width=icon_size, height=icon_size,
                                bg=bg_canvas, highlightthickness=0)
            cv_icon.pack(side="left", padx=(0, espacio_interno))

            # Sub-frame derecho: gauge arriba + estado debajo
            derecha = ctk.CTkFrame(centro, fg_color="transparent")
            derecha.pack(side="left")

            cv_gauge = tk.Canvas(derecha, width=gauge_size, height=gauge_size,
                                 bg=bg_canvas, highlightthickness=0)
            cv_gauge.pack()

            lbl_val = ctk.CTkLabel(derecha, text="--", font=("Roboto", 12, "bold"),
                                   anchor="center", wraplength=gauge_size)
            lbl_val.pack(pady=(2, 0))

            return card, lbl_val, cv_icon, cv_gauge

        self.actuadores_container = ctk.CTkFrame(self.scroll_actual, fg_color="transparent")
        self.actuadores_container.pack(fill="x", padx=15, pady=(5, 15))
        # Fila 0: 3 columnas con peso 1 (Ventilador, Aspersores, Iluminación LED)
        self.actuadores_container.grid_columnconfigure((0, 1, 2), weight=1)
        # Fila 1: simulamos 2 tarjetas centradas con relleno lateral
        self.actuadores_container.grid_columnconfigure(3, weight=1)

        self.card_v,     self.lbl_v_val,     self.cv_vent,  self.gauge_v     = create_actuator_card(self.actuadores_container, 0, "Ventilador",     "Termodinámica: Sistema Pad & Fan.\nON normal: 27°C | OFF normal: 24.5°C\nCon Malla Desplegada: ON 33°C | OFF 26°C")
        self.card_r,     self.lbl_r_val,     self.cv_riego, self.gauge_r     = create_actuator_card(self.actuadores_container, 1, "Aspersores",     "Agronomía (Humedece): ON si Humedad < 45%. OFF si Humedad >= 63%.\nTiene seguro de frío para no ahogar la planta.")
        self.card_il,    self.lbl_il_val,    self.cv_ilum,  self.gauge_il    = create_actuator_card(self.actuadores_container, 2, "Iluminación LED", "Agronomía (Suplemento): Compensa sombra solar de forma dinámica con Histéresis según la etapa.\n⚠️ APAGADO de noche para descanso celular.")
        self.card_calef, self.lbl_calef_val, self.cv_calef, self.gauge_calef = create_actuator_card(self.actuadores_container, 3, "Calefacción",    "Control Proporcional PID: Se enciende suavemente si T < 22°C para evitar caídas bruscas en heladas.")

        # ── Tarjeta especial: PANTALLA TÉRMICA (fila 1, sin gauge, 2 columnas centradas) ──
        # Usamos una sub-fila: ponemos la 5ta tarjeta centrada occupando col 1 y 2 de una segunda fila
        def create_thermal_card(parent):
            """Tarjeta de Pantalla Térmica sin gauge circular (estado ON/OFF visual)."""
            card = ctk.CTkFrame(parent, fg_color=bg_card, corner_radius=15,
                                border_width=2, border_color="#3b3b3b", height=180)
            card.grid(row=1, column=0, columnspan=4, padx=120, pady=(0, 10), sticky="ew")
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            card.grid_columnconfigure(2, weight=1)

            # Cabecera
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=(10, 0))
            ctk.CTkButton(header, text="ⓘ", width=25, height=25, corner_radius=12,
                          fg_color="transparent", text_color="gray", hover_color="#3b3b3b",
                          command=lambda: self.show_popup(
                              "PANTALLA TÉRMICA",
                              "FUNCIÓN: Reduce radiación térmica 85% y lumínica 75%.\n"
                              "DESPLIEGUE: Preventivo si Temp > 27°C y Luz > 30,000 Lx.\n"
                              "RETRACCIÓN: Si Temp < 24°C o baja la luz (< 15,000 Lx)."
                          )).pack(side="right")
            ctk.CTkLabel(header, text="PANTALLA TÉRMICA", font=("Roboto", 10, "bold"),
                         text_color="gray", anchor="center").pack(fill="x", expand=True, padx=(25, 0))

            # Contenedor central
            centro = ctk.CTkFrame(card, fg_color="transparent")
            centro.pack(expand=True, pady=(0, 8))

            # Canvas de la silueta de la malla
            cv_malla = tk.Canvas(centro, width=100, height=80,
                                 bg=bg_canvas, highlightthickness=0)
            cv_malla.pack(side="left", padx=(0, 20))

            # Estado a la derecha del canvas
            lbl_malla_val = ctk.CTkLabel(centro, text="PLEGADA", font=("Roboto", 14, "bold"),
                                         text_color="#95a5a6", anchor="center", wraplength=120)
            lbl_malla_val.pack(side="left")

            return card, lbl_malla_val, cv_malla

        self.card_malla, self.lbl_malla_val, self.cv_malla = create_thermal_card(self.actuadores_container)

        self.calef_potencia = 0.0
        self.malla_desplegada_prev = False  # Detectar cambios de estado para la animación de transición

        # Inicializar gotas de riego (x, y, dx, dy)
        self.riego_drops = []
        for _ in range(15):
            self.riego_drops.append([40, 65, random.uniform(-4, 4), random.uniform(-6, -2)])

    # ─────────────────────────────────────────────────────────────────────────
    def draw_gauge(self, cv, pct, color_on):
        """Gauge circular de 280°: track gris + arco de progreso + % centrado."""
        cv.delete("all")
        W = int(cv.cget("width"))
        H = int(cv.cget("height"))
        cx, cy = W // 2, H // 2
        r      = min(cx, cy) - 5   # radio → aprovecha el 90% del canvas
        TRACK  = "#444444"
        START, SPAN = 220, -280

        # Track gris de fondo
        cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                      start=START, extent=SPAN,
                      outline=TRACK, width=11, style="arc")
        # Arco de progreso coloreado
        if pct > 0:
            cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                          start=START, extent=SPAN*(min(pct, 100)/100.0),
                          outline=color_on, width=11, style="arc")
        # Porcentaje centrado — fuente proporcional al tamaño del canvas
        font_size = max(10, W // 6)
        cv.create_text(cx, cy, text=f"{pct:.0f}%",
                       font=("Helvetica", font_size, "bold"),
                       fill=color_on if pct > 0 else TRACK, anchor="center")

    def draw_temp(self, t):
        self.cv_temp.delete("all")
        color = "#3498db" if t < 15 else "#2ecc71" if t < 29 else "#e74c3c"
        
        self.cv_temp.create_oval(25, 52, 45, 72, outline="#bdc3c7", width=2) 
        self.cv_temp.create_line(30, 54, 30, 5, fill="#bdc3c7", width=2) 
        self.cv_temp.create_line(40, 54, 40, 5, fill="#bdc3c7", width=2) 
        self.cv_temp.create_arc(30, 0, 40, 10, start=0, extent=180, outline="#bdc3c7", width=2) 
        
        fill_h = min(max((t / 50.0) * 50, 0), 50)
        self.cv_temp.create_oval(27, 54, 43, 70, fill=color, outline="") 
        if fill_h > 0:
            self.cv_temp.create_rectangle(31, 57 - fill_h, 39, 57, fill=color, outline="") 

    def draw_hum(self, h):
        self.cv_hum.delete("all")
        color = "#f1c40f" if h < 40 else "#3498db" if h <= 80 else "#e74c3c"
        
        self.cv_hum.create_oval(20, 20, 60, 60, outline="#bdc3c7", width=4)
        angle = (h / 100.0) * 360
        self.cv_hum.create_arc(20, 20, 60, 60, start=90, extent=-angle, outline=color, width=4, style="arc")
        
        self.cv_hum.create_oval(32, 40, 48, 56, fill=color, outline="")
        self.cv_hum.create_polygon(32, 48, 48, 48, 40, 30, fill=color, outline="")

    def draw_luz(self, luz):
        self.cv_luz.delete("all")
        # Gris: sin luz útil (<1000), Amarillo: fotosíntesis óptima (1001-45000), Rojo: fotoinhibición (>45000)
        color = "#95a5a6" if luz < 1000 else "#f1c40f" if luz <= 45000 else "#e74c3c"
        
        self.cv_luz.create_oval(20, 30, 40, 50, fill=color, outline="")
        
        num_rays = int(min((luz / 10000.0) * 12, 12))
        for i in range(num_rays):
            angle = math.radians(i * (360/12))
            x1 = 30 + 15 * math.cos(angle)
            y1 = 40 + 15 * math.sin(angle)
            x2 = 30 + 25 * math.cos(angle)
            y2 = 40 + 25 * math.sin(angle)
            self.cv_luz.create_line(x1, y1, x2, y2, fill=color, width=3)

    def animar_actuadores(self):
        """
        Bucle asíncrono secundario para animaciones de la GUI.

        Se encarga exclusivamente de actualizar la rotación del ventilador,
        las gotas de lluvia, la opacidad de la malla térmica y el pulso del LED.
        Al operar en un after() separado con un delay constante (50 ms),
        garantiza que las animaciones sean fluidas sin importar el lag del
        bucle termodinámico principal.
        """
        """Bucle de animación de alta frecuencia para actuadores."""
        # Ventilador
        self.cv_vent.delete("all")
        if self.vent_state:
            self.vent_angle = (self.vent_angle + 20) % 360
            color_v = "#3498db"
        else:
            color_v = "#7f8c8d"
            
        self.cv_vent.create_oval(5, 15, 55, 65, outline="#bdc3c7", width=2)
        cx, cy, r = 30, 40, 22
        for i in range(4):
            angle = math.radians(self.vent_angle + i * 90)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            self.cv_vent.create_line(cx, cy, x, y, width=8, fill=color_v)
        self.cv_vent.create_oval(cx-5, cy-5, cx+5, cy+5, fill="#ecf0f1", outline="")

        # Aspersores
        self.cv_riego.delete("all")
        self.cv_riego.create_rectangle(25, 40, 35, 60, fill="#7f8c8d", outline="")
        self.cv_riego.create_oval(20, 35, 40, 45, fill="#bdc3c7", outline="")
        if self.riego_state:
            for i in range(len(self.riego_drops)):
                x, y, dx, dy = self.riego_drops[i]
                dy += 0.5 # gravedad
                x += dx
                y += dy
                if y > 80 or x < 0 or x > 80:
                    x, y = 30, 35
                    dx = random.uniform(-4, 4)
                    dy = random.uniform(-6, -2)
                self.cv_riego.create_oval(x-2, y-2, x+2, y+2, fill="#3498db", outline="")
                self.riego_drops[i] = [x, y, dx, dy]

        # Iluminación LED
        self.cv_ilum.delete("all")
        if self.ilum_intensity > 0:
            halo_r = 15 + (self.ilum_intensity / 100.0) * 15
            self.cv_ilum.create_oval(30-halo_r, 35-halo_r, 30+halo_r, 35+halo_r, fill="#fef0cd", outline="")
            
        bulb_color = "#f39c12" if self.ilum_intensity > 0 else "#7f8c8d"
        self.cv_ilum.create_oval(15, 15, 45, 45, fill=bulb_color, outline="")
        self.cv_ilum.create_rectangle(22, 40, 38, 60, fill="#95a5a6", outline="")
        self.cv_ilum.create_line(25, 60, 35, 60, fill="#bdc3c7", width=3)
        self.cv_ilum.create_line(30, 15, 30, 35, fill="#f1c40f", width=2) # Filamento

        # Calefacción
        self.cv_calef.delete("all")
        self.cv_calef.create_rectangle(10, 15, 50, 65, outline="#7f8c8d", width=2, fill="")
        
        for i in range(3):
            y_base = 25 + i * 15
            if self.calef_potencia > 0:
                # Interpolamos el color de gris oscuro a rojo brillante incandescente
                r_val = int(127 + (255 - 127) * (self.calef_potencia / 100.0))
                g_val = int(140 - 140 * (self.calef_potencia / 100.0))
                b_val = int(141 - 141 * (self.calef_potencia / 100.0))
                color_resistencia = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
                # Añadir un halo de calor aleatorio
                if random.random() < (self.calef_potencia / 100.0):
                    self.cv_calef.create_line(15, y_base, 45, y_base, fill="#e74c3c", width=6, capstyle="round")
            else:
                color_resistencia = "#7f8c8d"
            
            self.cv_calef.create_line(15, y_base, 45, y_base, fill=color_resistencia, width=4, capstyle="round")

        # Pantalla Térmica (Animación lenta y fluida)
        malla_activa = getattr(self, 'ctrl', None) and self.ctrl.malla_desplegada
        target_malla = 100.0 if malla_activa else 0.0
        
        if self.malla_anim_pct < target_malla:
            self.malla_anim_pct = min(100.0, self.malla_anim_pct + 4.0)
        elif self.malla_anim_pct > target_malla:
            self.malla_anim_pct = max(0.0, self.malla_anim_pct - 4.0)
            
        self.draw_malla(self.malla_anim_pct)

        # Motor de Planta (Interpolación fluida)
        if self.crecimiento_display < self.crecimiento_target:
            self.crecimiento_display += (self.crecimiento_target - self.crecimiento_display) * 0.05
        elif self.crecimiento_display > self.crecimiento_target:
            self.crecimiento_display -= (self.crecimiento_display - self.crecimiento_target) * 0.05
        
        for i in range(3):
            if self.plant_rgb[i] < self.target_rgb[i]:
                self.plant_rgb[i] += min(2, self.target_rgb[i] - self.plant_rgb[i])
            elif self.plant_rgb[i] > self.target_rgb[i]:
                self.plant_rgb[i] -= min(2, self.plant_rgb[i] - self.target_rgb[i])
                
        current_plant_color = f"#{int(self.plant_rgb[0]):02x}{int(self.plant_rgb[1]):02x}{int(self.plant_rgb[2]):02x}"
        self.dibujar_planta(self.crecimiento_display, current_plant_color, getattr(self, 'clima_actual', 'Soleado'))

        self.root.after(50, self.animar_actuadores)

    def draw_malla(self, pct):
        """Dibuja el icono de la Pantalla Térmica: animación vertical fluida según porcentaje (0 a 100)."""
        self.cv_malla.delete("all")
        W, H = 100, 80
        color_lamas = "#f39c12" if pct > 0 else "#7f8c8d"
        color_carril = "#bdc3c7"

        # Rieles laterales
        self.cv_malla.create_rectangle(8, 5, 13, H - 5, fill=color_carril, outline="")
        self.cv_malla.create_rectangle(W - 13, 5, W - 8, H - 5, fill=color_carril, outline="")

        # Tubo superior enrollador
        self.cv_malla.create_rectangle(8, 5, W - 8, 16, fill=color_carril, outline="", width=0)
        self.cv_malla.create_oval(8, 3, 20, 15, fill="#95a5a6", outline="")
        self.cv_malla.create_oval(W - 20, 3, W - 8, 15, fill="#95a5a6", outline="")

        if pct > 0:
            num_lamas = 6
            alto_total_lamas = H - 20
            # Altura actual basada en el porcentaje
            altura_actual = alto_total_lamas * (pct / 100.0)
            alto_lama = alto_total_lamas / num_lamas
            
            for i in range(num_lamas):
                y0 = 16 + i * alto_lama
                y1 = y0 + alto_lama - 2
                
                # Solo dibujar completamente si la lama entra en la altura animada
                if y1 <= 16 + altura_actual:
                    self.cv_malla.create_rectangle(13, y0, W - 13, y1, fill=color_lamas, outline="")
                    self.cv_malla.create_line(13, y1, W - 13, y1, fill="#c0392b", width=1)
                elif y0 < 16 + altura_actual:
                    # Lama parcial cortada (creando la ilusión de que baja suavemente)
                    self.cv_malla.create_rectangle(13, y0, W - 13, 16 + altura_actual, fill=color_lamas, outline="")
                    self.cv_malla.create_line(13, 16 + altura_actual, W - 13, 16 + altura_actual, fill="#c0392b", width=1)

            if pct == 100.0:
                self.cv_malla.create_text(W // 2, H - 6, text="▼ 25%", font=("Helvetica", 7, "bold"), fill="#f39c12")
            else:
                self.cv_malla.create_text(W // 2, H // 2 + 8, text=f"{int(pct)}%", font=("Helvetica", 8), fill="#f39c12")
        else:
            # Solo la pantalla enrollada en el tubo (plegada al 0%)
            self.cv_malla.create_rectangle(13, 5, W - 13, 16, fill="#95a5a6", outline="")
            self.cv_malla.create_text(W // 2, H // 2 + 8, text="PLEGADA", font=("Helvetica", 8), fill="#7f8c8d")

    def dibujar_planta(self, crecimiento, color_hojas, clima_actual="Soleado", plantada=True):
        """
        Motor de renderizado procedimental del cultivo (Canvas Tkinter).

        Dibuja dinámicamente la planta en función de su porcentaje de crecimiento.
        - 0-20%: Semilla y raíz.
        - 21-40%: Tallo emergente.
        - 41-70%: Ramificaciones y hojas escalables.
        - 71-90%: Aparición de flores.
        - 91-100%: Fructificación (tomates rojos).

        Args:
            crecimiento (float): Porcentaje de crecimiento (0 a 100).
            color_hojas (str/list): Color RGB que refleja la salud biológica.
            clima_actual (str): Modifica el entorno visual (sol, lluvia, luna).
            plantada (bool): Si es False, dibuja la maceta vacía.
        """
        self.cv_planta.delete("all")
        w, h, suelo_y = 390, 325, 286
        
        # 1. Dibujar el cielo según el clima y ciclo de luz
        if clima_actual == "Noche":
            self.cv_planta.create_rectangle(0, 0, w, suelo_y, fill="#0b0f19", outline="")
            self.cv_planta.create_oval(52, 52, 55, 55, fill="#ffffff", outline="")
            self.cv_planta.create_oval(182, 26, 185, 29, fill="#ffffff", outline="")
            self.cv_planta.create_oval(325, 91, 328, 94, fill="#ffffff", outline="")
            self.cv_planta.create_oval(286, 26, 338, 78, fill="#f1c40f", outline="")
        elif clima_actual == "Soleado":
            self.cv_planta.create_rectangle(0, 0, w, suelo_y, fill="#5dade2", outline="")
            self.cv_planta.create_oval(286, 26, 351, 91, fill="#f39c12", outline="")
            self.cv_planta.create_line(319, 13, 319, 0, fill="#f39c12", width=3)
            self.cv_planta.create_line(319, 104, 319, 117, fill="#f39c12", width=3)
            self.cv_planta.create_line(273, 59, 260, 59, fill="#f39c12", width=3)
            self.cv_planta.create_oval(286, 26, 351, 91, fill="#f39c12", outline="")
            self.cv_planta.create_line(364, 59, 377, 59, fill="#f39c12", width=3)
        elif clima_actual == "Nublado":
            self.cv_planta.create_rectangle(0, 0, w, suelo_y, fill="#95a5a6", outline="")
            self.cv_planta.create_oval(247, 39, 299, 91, fill="#7f8c8d", outline="")
            self.cv_planta.create_oval(273, 13, 351, 91, fill="#7f8c8d", outline="")
            self.cv_planta.create_oval(325, 39, 377, 91, fill="#7f8c8d", outline="")
        elif clima_actual == "Frío":
            self.cv_planta.create_rectangle(0, 0, w, suelo_y, fill="#aed6f1", outline="")
            self.cv_planta.create_oval(247, 39, 299, 91, fill="#ecf0f1", outline="")
            self.cv_planta.create_oval(273, 26, 351, 91, fill="#ecf0f1", outline="")
            self.cv_planta.create_oval(325, 39, 377, 91, fill="#ecf0f1", outline="")
            self.cv_planta.create_oval(273, 111, 278, 116, fill="#ffffff", outline="")
            self.cv_planta.create_oval(312, 124, 317, 129, fill="#ffffff", outline="")
            self.cv_planta.create_oval(351, 104, 356, 109, fill="#ffffff", outline="")
        else:
            self.cv_planta.create_rectangle(0, 0, w, suelo_y, fill="#34495e", outline="")
            
        # 2. Dibujar el suelo de tierra
        self.cv_planta.create_rectangle(0, suelo_y, w, h, fill="#5c4033", outline="")
        self.cv_planta.create_line(0, suelo_y, w, suelo_y, fill="#3e2723", width=4)
        
        if not plantada:
            return
            
        cx = w / 2
        
        # Etapa 1: Semilla a Brote (0 a 20%)
        if crecimiento <= 20:
            progreso = crecimiento / 20.0
            tallo_h = progreso * 39
            tallo_w = 2 + progreso * 2
            self.cv_planta.create_line(cx, suelo_y, cx, suelo_y - tallo_h, fill=color_hojas, width=tallo_w)
            
            if progreso > 0.3:
                hoja_s = (progreso - 0.3) * 15.6
                self.cv_planta.create_oval(cx, suelo_y - tallo_h, cx - hoja_s, suelo_y - tallo_h + hoja_s, fill=color_hojas, outline="")
                self.cv_planta.create_oval(cx, suelo_y - tallo_h, cx + hoja_s, suelo_y - tallo_h + hoja_s, fill=color_hojas, outline="")
                
        # Etapa 2: Plántula (21% a 60%)
        elif crecimiento <= 60:
            progreso = (crecimiento - 20) / 40.0
            tallo_h = 39 + progreso * 104
            tallo_w = 4 + progreso * 4
            self.cv_planta.create_line(cx, suelo_y, cx, suelo_y - tallo_h, fill="#27ae60", width=tallo_w, capstyle="round")
            
            h1_s = 10.4 + progreso * 19.5
            self.cv_planta.create_oval(cx, suelo_y - 32, cx - h1_s*2, suelo_y - 32 + h1_s, fill=color_hojas, outline="")
            self.cv_planta.create_oval(cx, suelo_y - 32, cx + h1_s*2, suelo_y - 32 + h1_s, fill=color_hojas, outline="")
            
            if progreso > 0.2:
                h2_s = (progreso - 0.2) * 26
                self.cv_planta.create_oval(cx, suelo_y - tallo_h + 13, cx - h2_s, suelo_y - tallo_h + 13 - h2_s, fill=color_hojas, outline="")
                self.cv_planta.create_oval(cx, suelo_y - tallo_h + 13, cx + h2_s, suelo_y - tallo_h + 13 - h2_s, fill=color_hojas, outline="")
                
        # Etapa 3: Adulta / Vegetativa (61% a 100%)
        else:
            progreso = (crecimiento - 60) / 40.0
            tallo_h = 143 + progreso * 39
            tallo_w = 8
            self.cv_planta.create_line(cx, suelo_y, cx, suelo_y - tallo_h, fill="#27ae60", width=tallo_w, capstyle="round")
            
            copa_y = suelo_y - tallo_h + 13
            copa_r = 39 + progreso * 39
            color_oscuro = "#229954" if color_hojas == "#2ecc71" else color_hojas
            
            self.cv_planta.create_oval(cx - copa_r, copa_y, cx, copa_y + copa_r*0.8, fill=color_oscuro, outline="")
            self.cv_planta.create_oval(cx, copa_y - 13, cx + copa_r, copa_y + copa_r*0.6, fill=color_oscuro, outline="")
            
            self.cv_planta.create_oval(cx - copa_r*0.9, copa_y - copa_r*1.1, cx + copa_r*0.9, copa_y + copa_r*0.3, fill=color_hojas, outline="")
            self.cv_planta.create_oval(cx - copa_r*1.2, copa_y - copa_r*0.5, cx + copa_r*0.3, copa_y + copa_r*0.6, fill=color_hojas, outline="")
            self.cv_planta.create_oval(cx - copa_r*0.3, copa_y - copa_r*0.7, cx + copa_r*1.2, copa_y + copa_r*0.5, fill=color_hojas, outline="")
            
            if crecimiento > 85:
                alpha = min(1.0, (crecimiento - 85) / 15.0)
                fruto_r = alpha * 7.8
                for fx, fy in [(-26, -13), (20, -33), (33, 13), (-39, 20)]:
                    self.cv_planta.create_oval(cx + fx - fruto_r, copa_y + fy - fruto_r, cx + fx + fruto_r, copa_y + fy + fruto_r, fill="#e74c3c", outline="")


    def setup_tab_grafico(self):
        """
        Construye la pestaña 'Monitoreo Gráfico'.

        Instancia el módulo PanelMonitoreoGrafico (separado en ui/panel_graficos.py)
        que utiliza Matplotlib incrustado en Tkinter para graficar el historial
        en tiempo real. Le inyecta la función `obtener_datos_actuales` como callback.
        """
        self.tab_grafico.grid_columnconfigure(0, weight=1)
        self.tab_grafico.grid_rowconfigure(1, weight=1)

        # Instanciar el nuevo panel gráfico independiente
        self.panel_grafico = PanelMonitoreoGrafico(
            master=self.tab_grafico,
            obtener_datos_cb=self.obtener_datos_actuales
        )

    def obtener_datos_actuales(self):
        """Devuelve la tupla con el estado actual para que el panel gráfico la procese cada 10s."""
        return self.current_data

    def setup_tab_agronomico(self):
        """
        Construye la pestaña 'Análisis Agronómico'.

        Configura el canvas principal donde se renderiza la planta,
        el panel de estado (barras de progreso de salud y crecimiento) y el
        registro de cosechas históricas. Implementa la lógica del Farming Loop.
        """
        self.tab_agronomico.grid_columnconfigure(0, weight=1)
        self.tab_agronomico.grid_rowconfigure(0, weight=3)
        self.tab_agronomico.grid_rowconfigure(1, weight=1)

        # 1. CONTENEDOR CON RELIEVE (Card Premium)
        self.premium_frame = ctk.CTkFrame(self.tab_agronomico, fg_color="#1A1D26", corner_radius=16, border_width=1, border_color="#2ECC71")
        self.premium_frame.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        self.premium_frame.grid_columnconfigure(0, weight=1)
        self.premium_frame.grid_columnconfigure(1, weight=1)
        
        # Panel Izquierdo: Datos Agronómicos
        left_panel = ctk.CTkFrame(self.premium_frame, fg_color="transparent")
        left_panel.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # FILA 1: LA ETAPA BIOLÓGICA (Look de Medalla/Badge)
        badge_etapa = ctk.CTkFrame(left_panel, fg_color="#2a2d2e", corner_radius=10, border_width=1, border_color="#3b3b3b")
        badge_etapa.pack(anchor="w", pady=(10, 20), ipadx=10, ipady=5)
        
        self.lbl_etapa = ctk.CTkLabel(badge_etapa, text="Semilla 🌱", font=("Roboto", 18, "bold"), text_color="white")
        self.lbl_etapa.pack(side="left", padx=(5, 5))
        
        info_etapas = "0-20%: Semilla 🌱\n21-40%: Brote 🌿\n41-70%: Vegetativo 🌳\n71-90%: Floración 🌸\n91-100%: Fructificación 🍅"
        btn_info_etapa = ctk.CTkButton(badge_etapa, text="ⓘ", width=25, height=25, corner_radius=12, fg_color="transparent", text_color="gray", hover_color="#3b3b3b",
                                     command=lambda: self.show_popup("Etapas de la Planta", info_etapas))
        btn_info_etapa.pack(side="left", padx=(0, 5))
        ToolTip(btn_info_etapa, "Info Etapas")

        # FILA 2: LÍNEA DE TIEMPO / BARRA DE PROGRESO
        progreso_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        progreso_frame.pack(fill="x", pady=20)
        
        self.lbl_pct = ctk.CTkLabel(progreso_frame, text="Progreso: 0.0%", font=("Roboto", 14, "bold"), text_color="#2ECC71")
        self.lbl_pct.pack(anchor="e")
        
        self.growth_progressbar = ctk.CTkProgressBar(progreso_frame, height=18, corner_radius=9, progress_color="#2ECC71")
        self.growth_progressbar.pack(fill="x", pady=(4, 0))
        self.growth_progressbar.set(0)

        # BARRA DE SALUD DE LA PLANTA
        salud_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        salud_header.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(salud_header, text="🟢  Salud de la Planta", font=("Roboto", 13, "bold"), text_color="#1abc9c").pack(side="left")
        self.lbl_salud_pct = ctk.CTkLabel(salud_header, text="100%", font=("Roboto", 13, "bold"), text_color="#1abc9c")
        self.lbl_salud_pct.pack(side="right")

        self.salud_progressbar = ctk.CTkProgressBar(left_panel, height=14, corner_radius=7, progress_color="#1abc9c")
        self.salud_progressbar.pack(fill="x", pady=(3, 0))
        self.salud_progressbar.set(1.0)
        self.salud_planta = 100.0  # Valor interno (0‒100)

        # FILA 3: CONTADOR DE COSECHA (Tipo Widget Digital)
        cosecha_frame = ctk.CTkFrame(left_panel, fg_color="#21252f", corner_radius=12)
        cosecha_frame.pack(fill="x", pady=(10, 10), ipadx=15, ipady=15)
        
        self.lbl_dias = ctk.CTkLabel(cosecha_frame, text="--", font=("Roboto", 36, "bold"), text_color="#F1C40F")
        self.lbl_dias.pack()
        
        lbl_dias_txt = ctk.CTkLabel(cosecha_frame, text="DÍAS ESTIMADOS PARA LA COSECHA 📅", font=("Roboto", 11, "bold"), text_color="gray")
        lbl_dias_txt.pack()

        # FILA 4: PRÓXIMA ETAPA (Tiempo Estimado)
        proxima_etapa_frame = ctk.CTkFrame(left_panel, fg_color="#1e2430", corner_radius=12, border_width=1, border_color="#2c3e50")
        proxima_etapa_frame.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)
        
        self.lbl_prox_etapa_dias = ctk.CTkLabel(proxima_etapa_frame, text="--", font=("Roboto", 24, "bold"), text_color="#3498db")
        self.lbl_prox_etapa_dias.pack(pady=(8, 2))
        
        self.lbl_prox_etapa_txt = ctk.CTkLabel(proxima_etapa_frame, text="TIEMPO PARA SIGUIENTE ETAPA ⏳", font=("Roboto", 11, "bold"), text_color="gray")
        self.lbl_prox_etapa_txt.pack(pady=(0, 8))

        # FILA 5: BOTÓN DEL FARMING LOOP (Plantar / Cosechar)
        self.btn_farming = ctk.CTkButton(
            left_panel, 
            text="PLANTAR", 
            font=("Roboto", 18, "bold"), 
            height=50,
            command=self.on_btn_farming_click
        )
        self.btn_farming.pack(fill="x", pady=(10, 0))

        self.last_crecimiento = 0.0
        self.listo_para_cosechar = False

        # Panel Derecho: Tabview con Visualización e Historial
        right_panel = ctk.CTkFrame(self.premium_frame, fg_color="transparent")
        right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        self.tabview_agro = ctk.CTkTabview(
            right_panel,
            fg_color="#21252f",
            segmented_button_fg_color="#1A1D26",
            segmented_button_selected_color="#2ECC71",
            segmented_button_selected_hover_color="#27ae60",
            segmented_button_unselected_color="#1A1D26",
            segmented_button_unselected_hover_color="#2a2d2e",
            text_color="white",
            corner_radius=12,
        )
        self.tabview_agro.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.tabview_agro.add("🌿  Visualización")
        self.tabview_agro.add("🏆  Historial de Cosechas")

        # ── Tab 1: Canvas procedimental (30% más grande) ──────────────────────
        tab_vis = self.tabview_agro.tab("🌿  Visualización")
        tab_vis.grid_rowconfigure(0, weight=1)
        tab_vis.grid_columnconfigure(0, weight=1)

        canvas_frame = ctk.CTkFrame(tab_vis, fg_color="transparent")
        canvas_frame.grid(row=0, column=0)

        lbl_motor = ctk.CTkLabel(canvas_frame, text="Evolución Procedimental", font=("Roboto", 15, "bold"), text_color="#2ECC71")
        lbl_motor.pack(pady=(8, 4))

        bg_canvas = "#1A1D26"
        self.cv_planta = tk.Canvas(canvas_frame, width=390, height=325, bg=bg_canvas, highlightthickness=0)
        self.cv_planta.pack(pady=5)

        # ── Tab 2: Historial de cosechas ──────────────────────────────────────
        tab_hist = self.tabview_agro.tab("🏆  Historial de Cosechas")
        tab_hist.grid_rowconfigure(1, weight=1)
        tab_hist.grid_columnconfigure(0, weight=1)

        # Encabezados de tabla con botón de limpiar
        header_frame = ctk.CTkFrame(tab_hist, fg_color="#12151e", corner_radius=8)
        header_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        cols_conf = [("Ciclo #", 60), ("Semilla", 80), ("Fecha", 130), ("Salud Final (%)", 110)]
        for col, (text, w) in enumerate(cols_conf):
            header_frame.grid_columnconfigure(col, weight=1, minsize=w)
            ctk.CTkLabel(header_frame, text=text, font=("Roboto", 12, "bold"),
                         text_color="#2ECC71").grid(row=0, column=col, padx=6, pady=6, sticky="w")
        # Columna extra para el botón limpiar
        header_frame.grid_columnconfigure(4, weight=0)
        ctk.CTkButton(
            header_frame, text="🗑️ Limpiar", width=85, height=26,
            font=("Roboto", 11, "bold"), fg_color="#c0392b", hover_color="#922b21",
            corner_radius=6, command=self.limpiar_historial
        ).grid(row=0, column=4, padx=(4, 6), pady=4)

        # Área scrollable para las filas
        self.historial_scroll = ctk.CTkScrollableFrame(
            tab_hist, fg_color="#1A1D26", corner_radius=8
        )
        self.historial_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        for col in range(4):
            self.historial_scroll.grid_columnconfigure(col, weight=1)

        self.cosecha_num = 0  # Contador de ciclos

        self.diag_frame = ctk.CTkFrame(self.tab_agronomico, corner_radius=15, fg_color="#1A1D26", border_width=1, border_color="#3b3b3b")
        self.diag_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        diag_title_frame = ctk.CTkFrame(self.diag_frame, fg_color="transparent")
        diag_title_frame.pack(pady=(15, 10))
        
        self.diag_title = ctk.CTkLabel(diag_title_frame, text="Diagnóstico Científico", font=("Roboto", 18, "bold"), text_color="white")
        self.diag_title.pack(side="left", padx=(0, 5))
        
        info_diag = "Verde: Condiciones óptimas.\nAmarillo: Alerta moderada (estrés hídrico/térmico leve).\nRojo: Alerta crítica (deshidratación severa o golpe de calor)."
        btn_info_diag = ctk.CTkButton(diag_title_frame, text="ⓘ", width=25, height=25, corner_radius=12, fg_color="transparent", text_color="gray", hover_color="#3b3b3b",
                                     command=lambda: self.show_popup("Info de Diagnóstico", info_diag))
        btn_info_diag.pack(side="left")
        ToolTip(btn_info_diag, "Significado de Alertas")
        
        self.diag_label = ctk.CTkLabel(self.diag_frame, text="Condiciones fisiológicas óptimas", font=("Roboto", 16, "bold"), text_color="#2ecc71")
        self.diag_label.pack(pady=(0, 15))
        
        self.alerta_activa = False
        self.mensaje_alerta = ""
        self.blink_running = False

    def on_btn_farming_click(self):
        planta = self.ctrl.planta
        s = getattr(self, 'salud_planta', 100.0)

        if not planta.plantada:
            # PLANTAR: reiniciar todo y arrancar nuevo ciclo
            planta.plantar()
            self.salud_planta = 100.0
            self.listo_para_cosechar = False
        elif planta.porcentaje_crecimiento >= 100.0 and s >= 94.0:
            # COSECHAR: guardar en historial y resetear
            self.registrar_cosecha(s)
            planta.cosechar()
            self.listo_para_cosechar = False

    def registrar_cosecha(self, salud_final: float):
        """Añade una fila al inventario de cosechas."""
        import datetime
        self.cosecha_num += 1
        row = self.cosecha_num
        dia_virt = getattr(self.ctrl, 'dia_virtual', 1)
        hora_sim = self.ctrl.tiempo_simulado.strftime("%I:%M %p")
        fecha = f"Día {dia_virt} - {hora_sim}"
        etapa = self.lbl_etapa.cget("text") if hasattr(self, 'lbl_etapa') else "--"

        bg = "#1e2430" if row % 2 == 0 else "#21252f"
        fila_frame = ctk.CTkFrame(self.historial_scroll, fg_color=bg, corner_radius=6)
        fila_frame.grid(row=row, column=0, columnspan=4, sticky="ew", padx=4, pady=2)
        for col in range(4):
            fila_frame.grid_columnconfigure(col, weight=1)

        valores = [str(row), etapa, fecha, f"{salud_final:.1f}%"]
        colores = ["white", "#2ECC71", "#95a5a6", "#F1C40F"]
        for col, (val, color) in enumerate(zip(valores, colores)):
            ctk.CTkLabel(fila_frame, text=val, font=("Roboto", 12),
                         text_color=color).grid(row=0, column=col, padx=8, pady=5, sticky="w")

    def limpiar_historial(self):
        """Elimina todas las filas del inventario de cosechas y reinicia el contador."""
        for widget in self.historial_scroll.winfo_children():
            widget.destroy()
        self.cosecha_num = 0

    def setup_tab_historico(self):
        """
        Construye la pestaña 'Registro Histórico'.

        Configura la tabla (Treeview) de registros y los paneles de métricas globales.
        Maneja la lógica de paginación e inicializa el auto-refresco asíncrono.
        """
        self.tab_historico.grid_columnconfigure(0, weight=1)
        self.tab_historico.grid_rowconfigure(1, weight=1)
        
        # 1. Panel de Resumen (Tarjetas Superiores)
        resumen_frame = ctk.CTkFrame(self.tab_historico, fg_color="transparent")
        resumen_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        resumen_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        def create_stat_card(parent, title, col):
            card = ctk.CTkFrame(parent, fg_color="#3b3b3b", corner_radius=10)
            card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
            lbl_title = ctk.CTkLabel(card, text=title, font=("Roboto", 12, "bold"), text_color="gray")
            lbl_title.pack(pady=(10, 0))
            lbl_val = ctk.CTkLabel(card, text="--", font=("Roboto", 28, "bold"), text_color="white")
            lbl_val.pack(pady=(5, 10))
            return lbl_val

        self.lbl_total_reg = create_stat_card(resumen_frame, "TOTAL REGISTROS", 0)
        self.lbl_temp_prom = create_stat_card(resumen_frame, "TEMP. PROMEDIO", 1)
        self.lbl_hum_prom  = create_stat_card(resumen_frame, "HUM. PROMEDIO", 2)
        self.lbl_luz_prom  = create_stat_card(resumen_frame, "LUZ PROM", 3)
        
        # 2. Tabla con scroll vertical Y horizontal
        table_outer = ctk.CTkFrame(self.tab_historico, corner_radius=10, fg_color="#2b2b2b")
        table_outer.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        table_outer.grid_columnconfigure(0, weight=1)
        table_outer.grid_rowconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Treeview",
                        background="#2b2b2b", foreground="white",
                        rowheight=35, fieldbackground="#2b2b2b",
                        borderwidth=0, relief="flat", font=("Roboto", 11))
        style.map("Custom.Treeview", background=[("selected", "#3498db")])
        style.configure("Custom.Treeview.Heading",
                        background="#1e2430", foreground="white",
                        font=("Roboto", 12, "bold"), relief="flat", borderwidth=0)
        style.map("Custom.Treeview.Heading", background=[("active", "#2c3e50")])
        
        # ── Columnas actualizadas ─────────────────────────────────────────────
        columns = (
            "N°", "Fecha_Hora", "Temp(°C)", "Hum(%)", "Luminosidad(Lx)",
            "Ventilador", "Aspersores", "Iluminacion_LED(%)",
            "Calefaccion(%)", "Pant. Termica"
        )
        self.tree = ttk.Treeview(
            table_outer, columns=columns, show="headings", style="Custom.Treeview"
        )
        
        # Scrollbar vertical
        v_scroll = ttk.Scrollbar(table_outer, orient="vertical",   command=self.tree.yview)
        # Scrollbar horizontal
        h_scroll = ttk.Scrollbar(table_outer, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(15, 0), pady=(15, 0))
        v_scroll.grid(row=0, column=1, sticky="ns",  padx=(0, 15), pady=(15, 0))
        h_scroll.grid(row=1, column=0, sticky="ew",  padx=(15, 0), pady=(0, 10))
        
        ancho_columnas = {
            "N°":                   40,
            "Fecha_Hora":          160,
            "Temp(°C)":             80,
            "Hum(%))":              80,
            "Luminosidad(Lx)":     110,
            "Ventilador":           85,
            "Aspersores":           90,
            "Iluminacion_LED(%)":  120,
            "Calefaccion(%)": 110,
            "Pant. Termica":       110,
        }
        nombres_visibles = {
            "N°":                  "#",
            "Fecha_Hora":          "Fecha / Hora",
            "Temp(°C)":            "Temp (°C)",
            "Hum(%))":             "Hum (%)",
            "Luminosidad(Lx)":     "Luz (Lx)",
            "Ventilador":          "Ventilador",
            "Aspersores":          "Aspersores",
            "Iluminacion_LED(%)": "Ilum. LED (%)",
            "Calefaccion(%)": "Calef. (%)",
            "Pant. Termica":       "Pant. Térmica",
        }
        for col in columns:
            ancho = ancho_columnas.get(col, 100)
            self.tree.heading(col, text=nombres_visibles.get(col, col))
            self.tree.column(col, anchor="center", width=ancho, minwidth=ancho)
            
        self.tree.tag_configure('evenrow', background="#2b2b2b")
        self.tree.tag_configure('oddrow',  background="#3b3b3b")
        
        # 3. Controles Inferiores y Paginación
        self.pagina_actual = 1
        self.total_paginas = 1
        
        controles_frame = ctk.CTkFrame(self.tab_historico, fg_color="transparent")
        controles_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        btn_container = ctk.CTkFrame(controles_frame, fg_color="transparent")
        btn_container.pack(anchor="center")
        
        self.btn_anterior = ctk.CTkButton(
            btn_container, text="◀ Anterior", width=100, font=("Roboto", 14, "bold"),
            command=self.pagina_anterior
        )
        self.btn_anterior.pack(side="left", padx=5)
        
        self.lbl_paginacion = ctk.CTkLabel(
            btn_container, text="Página 1 de 1", font=("Roboto", 14, "bold")
        )
        self.lbl_paginacion.pack(side="left", padx=10)
        
        self.btn_siguiente = ctk.CTkButton(
            btn_container, text="Siguiente ▶", width=100, font=("Roboto", 14, "bold"),
            command=self.pagina_siguiente
        )
        self.btn_siguiente.pack(side="left", padx=5)
        
        # Separador visual
        ctk.CTkLabel(btn_container, text="│", font=("Roboto", 18), text_color="#555").pack(side="left", padx=8)
        
        self.entry_pagina = ctk.CTkEntry(btn_container, width=50, justify="center", placeholder_text="Pág")
        self.entry_pagina.pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            btn_container, text="Ir", width=40, font=("Roboto", 14, "bold"),
            fg_color="#8e44ad", hover_color="#9b59b6",
            command=self.ir_a_pagina
        ).pack(side="left", padx=5)
        



        ctk.CTkButton(
            btn_container, text="🗑️ Limpiar Datos", font=("Roboto", 14, "bold"),
            fg_color="#c0392b", hover_color="#e74c3c",
            command=self.limpiar_datos_historial
        ).pack(side="left", padx=5)
        
        self.refrescar_datos_historial()
        self._auto_refrescar_historial()  # Iniciar loop de auto-refresco

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.cargar_datos_historial(self.pagina_actual - 1)
            
    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas:
            self.cargar_datos_historial(self.pagina_actual + 1)
            
    def ir_a_pagina(self):
        try:
            pag = int(self.entry_pagina.get())
            if 1 <= pag <= self.total_paginas:
                self.cargar_datos_historial(pag)
            else:
                messagebox.showerror("Error", f"La página debe estar entre 1 y {self.total_paginas}.")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número de página válido.")
            

    def _calcular_promedios_globales(self):
        # Lee TODO el historial y calcula el promedio
        historial_completo = self.ctrl.persistencia.consultar_historial()
        total_reg = len(historial_completo)
        
        if total_reg == 0:
            self.lbl_temp_prom.configure(text="-- °C", text_color="white")
            self.lbl_hum_prom.configure(text="-- %", text_color="white")
            self.lbl_luz_prom.configure(text="-- Lx", text_color="white")
            self.lbl_total_reg.configure(text="0", text_color="white")
            return

        total_temp = 0.0
        total_hum = 0.0
        total_luz = 0.0
        count_luz = 0

        for row in historial_completo:
            try:
                t   = float(row.get("Temperatura_C") or 0)
                h   = float(row.get("Humedad_Pct") or 0)
                luz = float(row.get("Luminosidad_Lux") or 0)
                
                total_temp += t
                total_hum  += h
                
                # Extraer hora de strings tipo "Día Virtual 1 - 14:30:00" o "2026-05-19 14:30:00"
                fecha = row.get("Fecha_Hora", "")
                try:
                    if "Día Virtual" in fecha:
                        # Formato nuevo: "Día Virtual X - HH:MM:SS"
                        time_part = fecha.split("-")[-1].strip()
                        dt_hour = int(time_part.split(":")[0])
                    else:
                        # Formato viejo
                        dt = datetime.datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
                        dt_hour = dt.hour
                        
                    if 6 <= dt_hour < 18:
                        total_luz += luz
                        count_luz += 1
                except Exception:
                    pass
            except Exception:
                continue

        prom_t = total_temp / total_reg
        prom_h = total_hum / total_reg
        self.lbl_temp_prom.configure(text=f"{prom_t:.1f} °C", text_color="#3498db" if prom_t < 15 else "#2ecc71" if prom_t < 29 else "#e74c3c")
        self.lbl_hum_prom.configure(text=f"{prom_h:.1f} %", text_color="#f1c40f" if prom_h < 40 else "#3498db" if prom_h <= 80 else "#e74c3c")
        
        if count_luz > 0:
            prom_luz = total_luz / count_luz
            self.lbl_luz_prom.configure(text=f"{prom_luz:.0f} Lx", text_color="#95a5a6" if prom_luz < 1000 else "#f1c40f" if prom_luz <= 45000 else "#e74c3c")
        else:
            self.lbl_luz_prom.configure(text="-- Lx", text_color="white")
            
        self.lbl_total_reg.configure(text=str(total_reg), text_color="white")

    def refrescar_datos_historial(self):
        """Actualiza promedios globales y recarga la página 1."""
        self._calcular_promedios_globales()
        self.cargar_datos_historial(1)

    def _auto_refrescar_historial(self):
        """Refresca silenciosamente el historial en la página actual cada 5 segundos."""
        self._calcular_promedios_globales()
        self.cargar_datos_historial(self.pagina_actual)
        self.root.after(5000, self._auto_refrescar_historial)

    def limpiar_datos_historial(self):
        """Borra todos los registros del CSV con un diálogo NO bloqueante."""
        dialogo = ctk.CTkToplevel(self.root)
        dialogo.title("Confirmar")
        dialogo.geometry("380x160")
        dialogo.attributes("-topmost", True)
        dialogo.resizable(False, False)
        dialogo.grab_set()  # Modal sin bloquear el hilo del reloj

        ctk.CTkLabel(
            dialogo,
            text="¿Borrar TODOS los datos del historial?",
            font=("Roboto", 15, "bold")
        ).pack(pady=(22, 4))
        ctk.CTkLabel(
            dialogo,
            text="Esta acción no se puede deshacer.",
            font=("Roboto", 12),
            text_color="#e74c3c"
        ).pack(pady=(0, 16))

        btn_frame = ctk.CTkFrame(dialogo, fg_color="transparent")
        btn_frame.pack()

        def confirmar():
            dialogo.destroy()
            import csv
            with self.ctrl.persistencia.ruta.open(mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Fecha_Hora", "Temperatura_C", "Humedad_Pct", "Ventilador",
                                  "Aspersores", "Luminosidad_Lux", "Iluminacion_LED",
                                  "Calefaccion_Pct", "Malla_Desplegada"])
            self.refrescar_datos_historial()

        ctk.CTkButton(
            btn_frame, text="Sí, borrar", width=120,
            fg_color="#c0392b", hover_color="#e74c3c",
            font=("Roboto", 13, "bold"), command=confirmar
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_frame, text="Cancelar", width=120,
            fg_color="#555", hover_color="#777",
            font=("Roboto", 13, "bold"), command=dialogo.destroy
        ).pack(side="left", padx=10)

    def cargar_datos_historial(self, pagina):
        existing_items = self.tree.get_children()

            
        datos, total_pag, total_reg = self.ctrl.obtener_historial_paginado(pagina, limite=50)
        self.pagina_actual = pagina
        self.total_paginas = max(1, total_pag)
        
        self.lbl_paginacion.configure(text=f"Página {self.pagina_actual} de {self.total_paginas}")
        self.entry_pagina.delete(0, 'end')
        
        self.btn_anterior.configure(state="normal" if self.pagina_actual > 1 else "disabled")
        self.btn_siguiente.configure(state="normal" if self.pagina_actual < self.total_paginas else "disabled")
        
        for i, row in enumerate(datos):
            try:
                fecha = row.get("Fecha_Hora", "--")
                t   = float(row.get("Temperatura_C") or 0)
                h   = float(row.get("Humedad_Pct") or 0)
                luz = float(row.get("Luminosidad_Lux") or 0)
                led = float(row.get("Iluminacion_LED") or 0)
                
                v_val = str(row.get("Ventilador", "")).strip()
                # Compatibilidad: columna puede llamarse Aspersores o Bomba_Riego (datos viejos)
                r_raw = row.get("Aspersores") or row.get("Bomba_Riego", "")
                r_val = str(r_raw).strip()

                calef_raw = row.get("Calefaccion_Pct", "")
                malla_raw = row.get("Malla_Desplegada", "")

                def _to_pct(raw_str):
                    """Convierte True/False o número a cadena de porcentaje."""
                    s = raw_str.lower()
                    if s == "true":  return "100%"
                    if s == "false": return "0%"
                    try:
                        return f"{float(raw_str):.0f}%"
                    except (ValueError, TypeError):
                        return "--"

                v_disp    = _to_pct(v_val)
                r_disp    = _to_pct(r_val)
                calef_disp = _to_pct(calef_raw) if calef_raw not in ("", None) else "--"
                malla_disp = "🟢 Sí" if malla_raw.lower() == "true" else "🔴 No"
                
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                values = (i + 1, fecha, f"{t:.1f}", f"{h:.1f}", f"{luz:.0f}", v_disp, r_disp, f"{led:.0f}%", calef_disp, malla_disp)
                
                if i < len(existing_items):
                    self.tree.item(existing_items[i], values=values, tags=(tag,))
                else:
                    self.tree.insert("", "end", values=values, tags=(tag,))
            except Exception:
                pass
                
        # Eliminar cualquier fila sobrante si la nueva página tiene menos de 50 registros
        for i in range(len(datos), len(existing_items)):
            self.tree.delete(existing_items[i])
                


    def animar_alerta(self):
        if not self.alerta_activa:
            self.blink_running = False
            self.diag_label.configure(text="Condiciones fisiológicas óptimas", text_color="#2ecc71")
            return
            
        current_text = self.diag_label.cget("text")
        color_peligro = "#e74c3c" if "estrés" in self.mensaje_alerta.lower() or "deshidratación" in self.mensaje_alerta.lower() else "#f1c40f"
        
        if current_text == " ":
            self.diag_label.configure(text=self.mensaje_alerta, text_color=color_peligro)
        else:
            self.diag_label.configure(text=" ")
            
        self.root.after(500, self.animar_alerta)



    def _tick_reloj(self):
        """
        Bucle asíncrono terciario: Reloj Virtual.

        Mantiene sincronizada la hora mostrada en el Header con la hora
        simulada del controlador. Se ajusta dinámicamente según el multiplicador
        de velocidad para evitar saltos bruscos en el UI.
        """
        """Loop independiente del reloj: se actualiza exactamente cada 1 segundo."""
        hora_actual = self.ctrl.tiempo_simulado
        self.clock_label.configure(text=hora_actual.strftime("%I:%M:%S %p"))
        if hasattr(self, 'lbl_dia_virtual'):
            self.lbl_dia_virtual.configure(text=f"Día Virtual: {self.ctrl.dia_virtual}")
        delay_reloj = int(1000 / max(1.0, self.ctrl.multiplicador_tiempo))
        self.root.after(max(20, delay_reloj), self._tick_reloj)

    def actualizar(self):
        """
        Ciclo principal de la Interfaz Gráfica (GUI).

        Este método es el corazón asíncrono visual. Se ejecuta periódicamente
        (con frecuencia dinámica según el multiplicador de tiempo) y realiza:
        1. Llamada a self.ctrl.procesar() para avanzar la simulación física.
        2. Extracción de variables de estado (temperatura, humedad, actuadores, etc).
        3. Actualización de colores y textos (Widgets CTk) según umbrales agronómicos.
        4. Actualización condicional del registro histórico cada 5 segundos reales.
        5. Lógica condicional de la salud biológica de la planta (Farming Loop).

        La separación de este método respecto a la física del controlador
        garantiza que la GUI no bloquee los cálculos termodinámicos.
        """
        resultado = self.ctrl.procesar()
        hora_actual, t, h, luz, v, r, intensidad_luz, calef_on, calef_pot, crecimiento, alerta, pronostico, t_ext, h_ext, esfuerzo_v, esfuerzo_r, esfuerzo_il, esfuerzo_c, estado_fotoperiodo = resultado
        self.estado_fotoperiodo = estado_fotoperiodo
        
        # Extraer el clima actual del pronóstico para la animación gráfica
        self.clima_actual = "Soleado"
        if "🌙" in pronostico or "Noche" in pronostico:
            self.clima_actual = "Noche"
        elif "☀️" in pronostico or "Soleado" in pronostico:
            self.clima_actual = "Soleado"
        elif "☁️" in pronostico or "Nublado" in pronostico:
            self.clima_actual = "Nublado"
        elif "❄️" in pronostico or "Frío" in pronostico:
            self.clima_actual = "Frío"
            
        ahora_real = datetime.datetime.now()
        hacer_refresco_pesado = (ahora_real - self.ultimo_refresco_pesado).total_seconds() >= 5.0
        
        if hacer_refresco_pesado:
            self.ultimo_refresco_pesado = ahora_real
            self.ctrl.registrar_lectura(
                self.ctrl.dia_virtual,
                hora_actual,          # fecha/hora SIMULADA
                t, h,
                esfuerzo_v,           # % ventilador
                esfuerzo_r,           # % aspersores
                luz, intensidad_luz,
                calef_pct=calef_pot,
                malla=self.ctrl.malla_desplegada
            )
        
        # Nota: el reloj se actualiza en _tick_reloj() cada 1 segundo, no aquí
        self.pronostico_label.configure(text=pronostico)
        self.lbl_ext_temp.configure(text=f"🌡️ Ext: {t_ext:.1f} °C | 💧 Hum: {h_ext:.1f} %")
        
        # Estado Solar Dinámico: muestra el clima real con emoji y temperatura exterior
        hora = hora_actual.hour
        clima_actual = self.ctrl.motor_clima.estado_actual

        iconos_clima = {
            "Soleado":    ("☀️", "#f39c12"),
            "Nublado":    ("☁️", "#95a5a6"),
            "Día Opaco":  ("🌫️", "#7f8c8d"),
            "Lluvia":     ("🌧️", "#2980b9"),
            "Tormenta":   ("⛈️", "#8e44ad"),
            "Frío":       ("❄️", "#3498db"),
            "Despejado":  ("🌙", "#2c3e50"),
        }
        emoji, color_solar = iconos_clima.get(clima_actual, ("🌡️", "#bdc3c7"))

        if 6 <= hora < 18:
            periodo = "Mañana" if hora < 12 else "Tarde"
            estado_solar = f"{emoji} {clima_actual} · {periodo} · {t_ext:.1f}°C ext."
        else:
            estado_solar = f"{emoji} {clima_actual} · Noche · {t_ext:.1f}°C ext."
            
        self.estado_solar_label.configure(text=estado_solar, text_color=color_solar)
        
        # Temp logic
        if t < 15: t_color = "#3498db"
        elif t < 29: t_color = "#2ecc71"
        else: t_color = "#e74c3c"
            
        self.lbl_t_val.configure(text=f"{t:.1f} °C", text_color=t_color)
        self.card_t.configure(border_color=t_color)
        self.draw_temp(t)
        
        # Hum logic
        if h < 40: h_color = "#f1c40f"
        elif h <= 80: h_color = "#3498db"
        else: h_color = "#e74c3c"
            
        self.lbl_h_val.configure(text=f"{h:.1f} %", text_color=h_color)
        self.card_h.configure(border_color=h_color)
        self.draw_hum(h)
        
        # Luz logic — Umbrales agronómicos correctos:
        # Gris: sin luz útil (<1000 Lx) | Amarillo: fotosíntesis óptima (1001-45000 Lx) | Rojo: fotoinhibición (>45000 Lx)
        if luz < 1000: luz_color = "#95a5a6"
        elif luz <= 45000: luz_color = "#f1c40f"
        else: luz_color = "#e74c3c"
            
        self.lbl_luz_val.configure(text=f"{luz:.0f} Lx", text_color=luz_color)
        self.card_luz.configure(border_color=luz_color)
        self.draw_luz(luz)

        # Actuadores
        self.vent_state      = v
        self.riego_state     = r
        self.ilum_intensity  = intensidad_luz

        # ── Ventilador ───────────────────────────────────────────────────────
        v_color = "#2ecc71" if v else "#95a5a6"
        self.lbl_v_val.configure(text="ON" if v else "OFF",
                                 text_color=v_color)
        self.card_v.configure(border_color=v_color)
        self.draw_gauge(self.gauge_v, esfuerzo_v if v else 0, v_color)

        # ── Aspersores ───────────────────────────────────────────────────────
        r_color = "#3498db" if r else "#95a5a6"
        self.lbl_r_val.configure(text="ON" if r else "OFF",
                                 text_color=r_color)
        self.card_r.configure(border_color=r_color)
        self.draw_gauge(self.gauge_r, esfuerzo_r if r else 0, r_color)

        # ── Iluminación LED ──────────────────────────────────────────────────
        if estado_fotoperiodo:
            il_color = "#9b59b6"
            il_text  = "Descanso"
            il_pct   = 0
        elif intensidad_luz > 0:
            il_color = "#f39c12"
            il_text  = "ON"
            il_pct   = esfuerzo_il
        else:
            il_color = "#95a5a6"
            il_text  = "OFF"
            il_pct   = 0
        self.lbl_il_val.configure(text=il_text, text_color=il_color)
        self.card_il.configure(border_color=il_color)
        self.draw_gauge(self.gauge_il, il_pct, il_color)

        # ── Calefacción ──────────────────────────────────────────────────────
        self.calef_potencia = calef_pot
        c_color = "#e74c3c" if calef_on else "#95a5a6"
        self.lbl_calef_val.configure(text="ON" if calef_on else "OFF",
                                     text_color=c_color)
        self.card_calef.configure(border_color=c_color)
        self.draw_gauge(self.gauge_calef, esfuerzo_c if calef_on else 0, c_color)

        # ── Pantalla Térmica (Malla de Sombreo) ──────────────────────────────
        malla_on = self.ctrl.malla_desplegada
        if malla_on != self.malla_desplegada_prev:
            # Estado en transición: mostrar texto animado por 1.5 segundos
            trans_text = "DESPLEGANDO..." if malla_on else "RETRAYENDO..."
            trans_color = "#f39c12" if malla_on else "#bdc3c7"
            self.lbl_malla_val.configure(text=trans_text, text_color=trans_color)
            self.malla_desplegada_prev = malla_on
            self.root.after(1500, lambda m=malla_on: self.lbl_malla_val.configure(
                text="DESPLEGADA" if m else "PLEGADA",
                text_color="#2ecc71" if m else "#95a5a6"
            ))
        malla_border = "#f39c12" if malla_on else "#3b3b3b"
        self.card_malla.configure(border_color=malla_border)


        # Actualizamos la tupla de datos actuales para el PanelMonitoreoGrafico independiente
        self.current_data = (t, h, luz, v, r, esfuerzo_il, esfuerzo_c,
                             self.ctrl.motor_clima.temp_exterior,
                             self.ctrl.motor_clima.hum_exterior)
            
        # Agronómico Premium
        self.crecimiento_target = crecimiento
        self.growth_progressbar.set(min(1.0, crecimiento / 100.0))
        self.lbl_pct.configure(text=f"Progreso: {crecimiento:.1f}%")
        
        if crecimiento <= 20: etapa = "Semilla 🌱"
        elif crecimiento <= 40: etapa = "Brote 🌿"
        elif crecimiento <= 70: etapa = "Vegetativo 🌳"
        elif crecimiento <= 90: etapa = "Floración 🌸"
        else: etapa = "Fructificación 🍅"

        self.lbl_etapa.configure(text=etapa)

        # ── Barra de Salud de la Planta ──────────────────────────────────────
        # Regla: la salud solo se puede degradar cuando el cultivo ya maduró (100%).
        # Durante el crecimiento se recupera libremente pero no se penaliza.
        if hasattr(self, 'salud_planta') and self.ctrl.planta.plantada:
            if crecimiento >= 100.0 and alerta:
                self.salud_planta = max(0.0, self.salud_planta - 0.15)
            else:
                self.salud_planta = min(100.0, self.salud_planta + 0.08)
        elif not self.ctrl.planta.plantada:
            self.salud_planta = 100.0  # Resetear al retirar planta

        if hasattr(self, 'salud_progressbar'):
            s = self.salud_planta
            self.salud_progressbar.set(s / 100.0)
            self.lbl_salud_pct.configure(text=f"{s:.0f}%")
            if s >= 70:
                color = "#1abc9c"
                icono = "🟢"
            elif s >= 40:
                color = "#f39c12"
                icono = "🟡"
            else:
                color = "#e74c3c"
                icono = "🔴"
            self.salud_progressbar.configure(progress_color=color)
            self.lbl_salud_pct.configure(text_color=color)
        
        # Matemáticas de tiempo estimado para la cosecha y próxima etapa
        if not hasattr(self, 'last_crecimiento'):
            self.last_crecimiento = 0.0
            
        delta_crec = crecimiento - self.last_crecimiento
        if delta_crec > 0 and crecimiento < 100:
            tasa_segundo = delta_crec / 2.0 
            
            # Cosecha total
            porcentaje_restante = 100.0 - crecimiento
            segundos_restantes = porcentaje_restante / tasa_segundo
            dias_restantes = segundos_restantes / 24.0 # 24 seg = 1 día simulado
            self.lbl_dias.configure(text=f"{dias_restantes:.1f}")
            
            # Próxima etapa
            target_prox = 100
            if crecimiento <= 20: target_prox = 21
            elif crecimiento <= 40: target_prox = 41
            elif crecimiento <= 70: target_prox = 71
            elif crecimiento <= 90: target_prox = 91
            
            if target_prox < 100:
                pct_faltante_prox = target_prox - crecimiento
                seg_prox = pct_faltante_prox / tasa_segundo
                dias_prox = seg_prox / 24.0
                self.lbl_prox_etapa_dias.configure(text=f"{dias_prox:.1f} Días")
                self.lbl_prox_etapa_txt.configure(text="TIEMPO PARA SIGUIENTE ETAPA ⏳")
            else:
                self.lbl_prox_etapa_dias.configure(text="--")
                self.lbl_prox_etapa_txt.configure(text="ÚLTIMA ETAPA ALCANZADA")
                
        elif delta_crec < 0:
            self.lbl_dias.configure(text="ESTRÉS")
            self.lbl_prox_etapa_dias.configure(text="PAUSADO")
            self.lbl_prox_etapa_txt.configure(text="PLANTA EN RETROCESO ⚠️")
            
        elif delta_crec == 0 and crecimiento < 100:
            self.lbl_dias.configure(text="PAUSADO")
            self.lbl_prox_etapa_dias.configure(text="--")
            self.lbl_prox_etapa_txt.configure(text="CRECIMIENTO ESTANCADO ⚠️")
            
        elif crecimiento >= 100:
            self.lbl_dias.configure(text="0.0")
            self.lbl_prox_etapa_dias.configure(text="0.0")
            self.lbl_prox_etapa_txt.configure(text="LISTA PARA COSECHA ✅")
            
        self.last_crecimiento = crecimiento

        # ── Farming Loop: Lógica unificada del botón ─────────────────────────
        planta = self.ctrl.planta
        s = getattr(self, 'salud_planta', 100.0)

        if not planta.plantada:
            self.btn_farming.configure(
                state="normal", text="🌱  PLANTAR",
                fg_color=["#1F6AA5", "#3B8ED0"], text_color="white"
            )
            self.listo_para_cosechar = False
        elif crecimiento >= 100.0:
            self.listo_para_cosechar = True
            if s >= 94.0:
                self.btn_farming.configure(
                    state="normal", text="🏆  COSECHAR",
                    fg_color="#f1c40f", text_color="#1a1a1a"
                )
            else:
                self.btn_farming.configure(
                    state="disabled", text="⚠️  Recuperando...",
                    fg_color="#c0392b", text_color="white"
                )
        else:
            self.listo_para_cosechar = False
            self.btn_dots_count = getattr(self, 'btn_dots_count', 0) + 1
            dots = "." * ((self.btn_dots_count % 3) + 1)
            self.btn_farming.configure(
                state="disabled", text=f"🌿  Creciendo{dots}",
                fg_color="#34495e", text_color="white"
            )
        
        if alerta:
            self.alerta_activa = True
            self.mensaje_alerta = alerta
            
            if "estrés" in alerta.lower() or "deshidratación" in alerta.lower():
                self.target_rgb = [230, 126, 34] # #e67e22 (Amarillento/Naranja)
            else:
                self.target_rgb = [241, 196, 15] # #f1c40f (Amarillo pálido)
                
            if not self.blink_running:
                self.blink_running = True
                self.animar_alerta()
        else:
            self.alerta_activa = False
            self.target_rgb = [46, 204, 113] # #2ecc71 (Verde sano)
            
        delay = int(1000 / max(1.0, self.ctrl.multiplicador_tiempo))
        self.root.after(max(20, delay), self.actualizar)

    def cerrar_programa(self):
        """
        Maneja el evento de cierre de ventana (WM_DELETE_WINDOW).

        Asegura que todos los procesos en segundo plano, incluyendo los motores
        de Matplotlib (plt) y los bucles asíncronos de Tkinter, sean destruidos
        limpiamente antes de invocar sys.exit(). Esto previene procesos zombis
        y bloqueos en la terminal.
        """
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)
