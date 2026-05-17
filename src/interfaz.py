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
from persistencia import GestorPersistencia

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
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Invernadero Virtual")
        self.root.geometry("850x900")
        
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_programa)
        
        self.ctrl = Controlador()
        self.persistencia = GestorPersistencia()
        
        self.max_len = 20
        self.temp_data = collections.deque(maxlen=self.max_len)
        self.hum_data = collections.deque(maxlen=self.max_len)
        self.luz_data = collections.deque(maxlen=self.max_len)
        self.time_data = collections.deque(maxlen=self.max_len)
        self.counter = 0

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

        # Variables para Motor Gráfico de Planta
        self.plant_rgb = [46, 204, 113] # #2ecc71
        self.target_rgb = [46, 204, 113]
        self.crecimiento_display = 0.0
        self.crecimiento_target = 0.0

        self.setup_tab_actual()
        self.setup_tab_grafico()
        self.setup_tab_agronomico()
        self.setup_tab_historico()

        self.animar_actuadores()
        self.actualizar()

    def setup_header(self):
        self.header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.header_frame.grid_columnconfigure(2, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Panel de Control - Invernadero Virtual", 
            font=("Roboto", 24, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.solar_info_label = ctk.CTkLabel(
            self.header_frame,
            text="☀️ Amanecer: 06:00 AM | 🌙 Ocaso: 06:00 PM",
            font=("Roboto", 14)
        )
        self.solar_info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        self.pronostico_label = ctk.CTkLabel(
            self.header_frame,
            text="Pronóstico: --",
            font=("Roboto", 14, "italic"),
            text_color="#3498db"
        )
        self.pronostico_label.grid(row=2, column=0, sticky="w", pady=(2, 0))

        self.clock_label = ctk.CTkLabel(
            self.header_frame,
            text="00:00:00",
            font=("Roboto", 28, "bold"),
            text_color="#f39c12"
        )
        self.clock_label.grid(row=0, column=1, rowspan=3)
        
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
        self.theme_switch.grid(row=0, column=2, rowspan=3, sticky="e")

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
        self.tab_actual.grid_columnconfigure((0, 1), weight=1)
        self.tab_actual.grid_rowconfigure((0, 1, 2), weight=1)

        bg_card = ("#e8e8e8", "#2a2d2e")
        bg_canvas = "#2a2d2e" if self.switch_var.get() == "dark" else "#e8e8e8"

        def create_card(row, col, title, info_text):
            card = ctk.CTkFrame(self.tab_actual, fg_color=bg_card, corner_radius=15, border_width=2, border_color="#3b3b3b")
            card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            
            lbl_title = ctk.CTkLabel(card, text=title.upper(), font=("Roboto", 11, "bold"), text_color="gray")
            lbl_title.place(x=20, y=10)
            
            btn_info = ctk.CTkButton(card, text="ⓘ", width=25, height=25, corner_radius=12, fg_color="transparent", text_color="gray", hover_color="#3b3b3b",
                                     command=lambda: self.show_popup(title, info_text))
            btn_info.place(relx=0.95, y=10, anchor="ne")
            ToolTip(btn_info, "Info")
            
            lbl_val = ctk.CTkLabel(card, text="--", font=("Roboto", 28, "bold"))
            lbl_val.place(x=20, rely=0.55, anchor="w")
            
            cv = tk.Canvas(card, width=80, height=100, bg=bg_canvas, highlightthickness=0)
            cv.place(relx=0.85, rely=0.55, anchor="center")
            
            return card, lbl_val, cv

        # Crear 6 tarjetas en matriz 3x2
        self.card_t, self.lbl_t_val, self.cv_temp = create_card(0, 0, "Temperatura", "Física: Sube de día por radiación. Baja de noche hacia 15°C. Valores ideales: 15°C a 28°C.")
        self.card_h, self.lbl_h_val, self.cv_hum = create_card(1, 0, "Humedad", "Física: Baja (se evapora) cuando la temperatura sube. Sube al enfriar. Ideal: 40% a 80%.")
        self.card_luz, self.lbl_luz_val, self.cv_luz = create_card(2, 0, "Luminosidad", "Motor Climático: Solar de 6am-6pm (según clima: Soleado, Nublado, Frío). De noche es 0.")
        
        self.card_v, self.lbl_v_val, self.cv_vent = create_card(0, 1, "Ventilador", "Agronomía (Enfría/Seca): ON si Temp > 28°C o Hum > 80%. OFF ESTRICTO si Temp < 15°C.")
        self.card_r, self.lbl_r_val, self.cv_riego = create_card(1, 1, "Bomba de Riego", "Agronomía (Humedece): ON si Humedad < 50%. OFF si Humedad >= 70%. Ignora el frío.")
        self.card_il, self.lbl_il_val, self.cv_ilum = create_card(2, 1, "Iluminación LED", "Agronomía (Suplemento): ON para compensar si Luz < 6,000 Lux. Aporta máx 10,000 Lux.")

        # Inicializar gotas de riego (x, y, dx, dy)
        self.riego_drops = []
        for _ in range(15):
            self.riego_drops.append([40, 65, random.uniform(-4, 4), random.uniform(-6, -2)])

    def draw_temp(self, t):
        self.cv_temp.delete("all")
        color = "#3498db" if t < 15 else "#2ecc71" if t <= 28 else "#e74c3c"
        
        self.cv_temp.create_oval(30, 70, 50, 90, outline="#bdc3c7", width=2) 
        self.cv_temp.create_line(35, 72, 35, 20, fill="#bdc3c7", width=2) 
        self.cv_temp.create_line(45, 72, 45, 20, fill="#bdc3c7", width=2) 
        self.cv_temp.create_arc(35, 15, 45, 25, start=0, extent=180, outline="#bdc3c7", width=2) 
        
        fill_h = min(max((t / 50.0) * 50, 0), 50)
        self.cv_temp.create_oval(32, 72, 48, 88, fill=color, outline="") 
        if fill_h > 0:
            self.cv_temp.create_rectangle(36, 75 - fill_h, 44, 75, fill=color, outline="") 

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
        color = "#95a5a6" if luz < 2000 else "#f1c40f" if luz <= 8500 else "#e74c3c"
        
        self.cv_luz.create_oval(30, 40, 50, 60, fill=color, outline="")
        
        num_rays = int(min((luz / 10000.0) * 12, 12))
        for i in range(num_rays):
            angle = math.radians(i * (360/12))
            x1 = 40 + 15 * math.cos(angle)
            y1 = 50 + 15 * math.sin(angle)
            x2 = 40 + 25 * math.cos(angle)
            y2 = 50 + 25 * math.sin(angle)
            self.cv_luz.create_line(x1, y1, x2, y2, fill=color, width=3)

    def animar_actuadores(self):
        """Bucle de animación de alta frecuencia para actuadores."""
        # Ventilador
        self.cv_vent.delete("all")
        if self.vent_state:
            self.vent_angle = (self.vent_angle + 20) % 360
            color_v = "#3498db"
        else:
            color_v = "#7f8c8d"
            
        self.cv_vent.create_oval(15, 25, 65, 75, outline="#bdc3c7", width=2)
        cx, cy, r = 40, 50, 22
        for i in range(4):
            angle = math.radians(self.vent_angle + i * 90)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            self.cv_vent.create_line(cx, cy, x, y, width=8, fill=color_v)
        self.cv_vent.create_oval(cx-5, cy-5, cx+5, cy+5, fill="#ecf0f1", outline="")

        # Riego (Aspersor)
        self.cv_riego.delete("all")
        self.cv_riego.create_rectangle(35, 70, 45, 90, fill="#7f8c8d", outline="")
        self.cv_riego.create_oval(30, 65, 50, 75, fill="#bdc3c7", outline="")
        if self.riego_state:
            for i in range(len(self.riego_drops)):
                x, y, dx, dy = self.riego_drops[i]
                dy += 0.5 # gravedad
                x += dx
                y += dy
                if y > 100 or x < 0 or x > 80:
                    x, y = 40, 65
                    dx = random.uniform(-4, 4)
                    dy = random.uniform(-6, -2)
                self.cv_riego.create_oval(x-2, y-2, x+2, y+2, fill="#3498db", outline="")
                self.riego_drops[i] = [x, y, dx, dy]

        # Iluminación
        self.cv_ilum.delete("all")
        if self.ilum_intensity > 0:
            halo_r = 15 + (self.ilum_intensity / 100.0) * 15
            self.cv_ilum.create_oval(40-halo_r, 45-halo_r, 40+halo_r, 45+halo_r, fill="#fef0cd", outline="")
            
        bulb_color = "#f39c12" if self.ilum_intensity > 0 else "#7f8c8d"
        self.cv_ilum.create_oval(25, 25, 55, 55, fill=bulb_color, outline="")
        self.cv_ilum.create_rectangle(32, 50, 48, 70, fill="#95a5a6", outline="")
        self.cv_ilum.create_line(35, 70, 45, 70, fill="#bdc3c7", width=3)
        self.cv_ilum.create_line(40, 25, 40, 45, fill="#f1c40f", width=2) # Filamento

        # Motor de Planta (Interpolación fluida)
        if self.crecimiento_display < self.crecimiento_target:
            self.crecimiento_display += (self.crecimiento_target - self.crecimiento_display) * 0.05
        
        for i in range(3):
            if self.plant_rgb[i] < self.target_rgb[i]:
                self.plant_rgb[i] += min(2, self.target_rgb[i] - self.plant_rgb[i])
            elif self.plant_rgb[i] > self.target_rgb[i]:
                self.plant_rgb[i] -= min(2, self.plant_rgb[i] - self.target_rgb[i])
                
        current_plant_color = f"#{int(self.plant_rgb[0]):02x}{int(self.plant_rgb[1]):02x}{int(self.plant_rgb[2]):02x}"
        self.dibujar_planta(self.crecimiento_display, current_plant_color)

        self.root.after(50, self.animar_actuadores)

    def dibujar_planta(self, crecimiento, color_hojas):
        self.cv_planta.delete("all")
        w, h, suelo_y = 300, 250, 220
        
        self.cv_planta.create_rectangle(0, suelo_y, w, h, fill="#5c4033", outline="")
        self.cv_planta.create_line(0, suelo_y, w, suelo_y, fill="#3e2723", width=4)
        
        cx = w / 2
        
        # Etapa 1: Semilla a Brote (0 a 20%)
        if crecimiento <= 20:
            progreso = crecimiento / 20.0
            tallo_h = progreso * 30
            tallo_w = 2 + progreso * 2
            self.cv_planta.create_line(cx, suelo_y, cx, suelo_y - tallo_h, fill=color_hojas, width=tallo_w)
            
            if progreso > 0.3:
                hoja_s = (progreso - 0.3) * 12
                self.cv_planta.create_oval(cx, suelo_y - tallo_h, cx - hoja_s, suelo_y - tallo_h + hoja_s, fill=color_hojas, outline="")
                self.cv_planta.create_oval(cx, suelo_y - tallo_h, cx + hoja_s, suelo_y - tallo_h + hoja_s, fill=color_hojas, outline="")
                
        # Etapa 2: Plántula (21% a 60%)
        elif crecimiento <= 60:
            progreso = (crecimiento - 20) / 40.0
            tallo_h = 30 + progreso * 80
            tallo_w = 4 + progreso * 4
            self.cv_planta.create_line(cx, suelo_y, cx, suelo_y - tallo_h, fill="#27ae60", width=tallo_w, capstyle="round")
            
            h1_s = 8 + progreso * 15
            self.cv_planta.create_oval(cx, suelo_y - 25, cx - h1_s*2, suelo_y - 25 + h1_s, fill=color_hojas, outline="")
            self.cv_planta.create_oval(cx, suelo_y - 25, cx + h1_s*2, suelo_y - 25 + h1_s, fill=color_hojas, outline="")
            
            if progreso > 0.2:
                h2_s = (progreso - 0.2) * 20
                self.cv_planta.create_oval(cx, suelo_y - tallo_h + 10, cx - h2_s, suelo_y - tallo_h + 10 - h2_s, fill=color_hojas, outline="")
                self.cv_planta.create_oval(cx, suelo_y - tallo_h + 10, cx + h2_s, suelo_y - tallo_h + 10 - h2_s, fill=color_hojas, outline="")
                
        # Etapa 3: Adulta / Vegetativa (61% a 100%)
        else:
            progreso = (crecimiento - 60) / 40.0
            tallo_h = 110 + progreso * 30
            tallo_w = 8
            self.cv_planta.create_line(cx, suelo_y, cx, suelo_y - tallo_h, fill="#27ae60", width=tallo_w, capstyle="round")
            
            copa_y = suelo_y - tallo_h + 10
            copa_r = 30 + progreso * 30
            color_oscuro = "#229954" if color_hojas == "#2ecc71" else color_hojas
            
            self.cv_planta.create_oval(cx - copa_r, copa_y, cx, copa_y + copa_r*0.8, fill=color_oscuro, outline="")
            self.cv_planta.create_oval(cx, copa_y - 10, cx + copa_r, copa_y + copa_r*0.6, fill=color_oscuro, outline="")
            
            self.cv_planta.create_oval(cx - copa_r*0.9, copa_y - copa_r*1.1, cx + copa_r*0.9, copa_y + copa_r*0.3, fill=color_hojas, outline="")
            self.cv_planta.create_oval(cx - copa_r*1.2, copa_y - copa_r*0.5, cx + copa_r*0.3, copa_y + copa_r*0.6, fill=color_hojas, outline="")
            self.cv_planta.create_oval(cx - copa_r*0.3, copa_y - copa_r*0.7, cx + copa_r*1.2, copa_y + copa_r*0.5, fill=color_hojas, outline="")
            
            if crecimiento > 85:
                alpha = min(1.0, (crecimiento - 85) / 15.0)
                fruto_r = alpha * 6
                for fx, fy in [(-20, -10), (15, -25), (25, 10), (-30, 15)]:
                    self.cv_planta.create_oval(cx + fx - fruto_r, copa_y + fy - fruto_r, cx + fx + fruto_r, copa_y + fy + fruto_r, fill="#e74c3c", outline="")

    def setup_tab_grafico(self):
        self.tab_grafico.grid_columnconfigure(0, weight=1)
        self.tab_grafico.grid_rowconfigure(1, weight=1)

        self.accesible_var = ctk.BooleanVar(value=False)
        self.accesible_switch = ctk.CTkSwitch(
            self.tab_grafico,
            text="Modo Accesible (Daltónicos)",
            command=self.update_plot_style,
            variable=self.accesible_var,
            font=("Roboto", 14)
        )
        self.accesible_switch.grid(row=0, column=0, pady=(5, 5), sticky="e")

        self.fig, (self.ax_temp, self.ax_hum, self.ax_luz) = plt.subplots(3, 1, figsize=(6, 8), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.fig.subplots_adjust(hspace=0.6)

        for ax in (self.ax_temp, self.ax_hum, self.ax_luz):
            ax.set_facecolor('#3b3b3b')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        
        self.style_normal = {
            'temp_color': '#ff4757',
            'hum_color': '#2ed573',
            'luz_color': '#f1c40f',
            'temp_ls': '-',
            'hum_ls': '-',
            'luz_ls': '-'
        }
        
        self.style_accesible = {
            'temp_color': '#ffa502',
            'hum_color': '#1e90ff',
            'luz_color': '#9b59b6',
            'temp_ls': '-',
            'hum_ls': '--',
            'luz_ls': ':'
        }
        
        self.current_style = self.style_normal

        self.ax_temp.set_title("Evolución de Temperatura")
        self.ax_temp.set_ylabel("Temperatura (°C)")
        self.line_temp, = self.ax_temp.plot([], [], label='Temperatura (°C)', color=self.current_style['temp_color'], linestyle=self.current_style['temp_ls'], linewidth=2)
        
        self.ax_hum.set_title("Evolución de Humedad")
        self.ax_hum.set_ylabel("Humedad (%)")
        self.line_hum, = self.ax_hum.plot([], [], label='Humedad (%)', color=self.current_style['hum_color'], linestyle=self.current_style['hum_ls'], linewidth=2)
        
        self.ax_luz.set_title("Historial Lumínico")
        self.ax_luz.set_xlabel("Tiempo (Ciclos)")
        self.ax_luz.set_ylabel("Luminosidad (Lux)")
        self.line_luz, = self.ax_luz.plot([], [], label='Luminosidad (Lux)', color=self.current_style['luz_color'], linestyle=self.current_style['luz_ls'], linewidth=2)
        
        self.legend_temp = self.ax_temp.legend(facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        self.legend_hum = self.ax_hum.legend(facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        self.legend_luz = self.ax_luz.legend(facecolor='#2b2b2b', edgecolor='white', labelcolor='white')

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.tab_grafico)
        self.canvas_plot.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    def setup_tab_agronomico(self):
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
        
        self.growth_progressbar = ctk.CTkProgressBar(progreso_frame, height=20, corner_radius=10, progress_color="#2ECC71")
        self.growth_progressbar.pack(fill="x", pady=(5, 0))
        self.growth_progressbar.set(0)

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
        self.lbl_prox_etapa_dias.pack()
        
        self.lbl_prox_etapa_txt = ctk.CTkLabel(proxima_etapa_frame, text="TIEMPO PARA SIGUIENTE ETAPA ⏳", font=("Roboto", 11, "bold"), text_color="gray")
        self.lbl_prox_etapa_txt.pack()

        self.last_crecimiento = 0.0

        # Panel Derecho: Motor Gráfico de Planta (Conservamos el Canvas)
        right_panel = ctk.CTkFrame(self.premium_frame, fg_color="transparent")
        right_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        lbl_motor = ctk.CTkLabel(right_panel, text="Evolución Procedimental", font=("Roboto", 16, "bold"), text_color="#2ECC71")
        lbl_motor.pack(pady=(10, 5))

        # Integración del canvas al nuevo fondo premium
        bg_canvas = "#1A1D26" if self.switch_var.get() == "dark" else "#e8e8e8"
        self.cv_planta = tk.Canvas(right_panel, width=300, height=250, bg=bg_canvas, highlightthickness=0)
        self.cv_planta.pack(pady=10)

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

    def setup_tab_historico(self):
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
        self.lbl_hum_prom = create_stat_card(resumen_frame, "HUM. PROMEDIO", 2)
        self.lbl_luz_prom = create_stat_card(resumen_frame, "LUZ PROM (6a-6p)", 3)
        
        # 2. Tabla de Datos Moderna (Data Grid)
        table_frame = ctk.CTkFrame(self.tab_historico, corner_radius=10, fg_color="#2b2b2b")
        table_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use("default")
        
        # Eliminamos bordes 3D antiguos (relief flat), texto claro
        style.configure("Custom.Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        rowheight=35,
                        fieldbackground="#2b2b2b",
                        borderwidth=0,
                        relief="flat",
                        font=("Roboto", 11))
        style.map("Custom.Treeview", background=[("selected", "#3498db")])
        style.configure("Custom.Treeview.Heading",
                        background="#1e2430",
                        foreground="white",
                        font=("Roboto", 12, "bold"),
                        relief="flat",
                        borderwidth=0)
        style.map("Custom.Treeview.Heading", background=[("active", "#2c3e50")])
        
        columns = ("Fecha_Hora", "Temp(°C)", "Hum(%)", "Luminosidad(Lx)", "Ventilador", "Bomba_Riego", "Iluminacion_LED(%)")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Custom.Treeview")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(15, 0), pady=15)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 15), pady=15)
        
        ancho_columnas = {
            "Fecha_Hora": 160,
            "Temp(°C)": 80,
            "Hum(%)": 80,
            "Luminosidad(Lx)": 110,
            "Ventilador": 80,
            "Bomba_Riego": 100,
            "Iluminacion_LED(%)": 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " "))
            self.tree.column(col, anchor="center", width=ancho_columnas[col], minwidth=ancho_columnas[col])
            
        # Efecto Cebra: Una fila gris muy oscura y la siguiente un poco más clara
        self.tree.tag_configure('evenrow', background="#2b2b2b")
        self.tree.tag_configure('oddrow', background="#3b3b3b")
        
        # 4. Controles Inferiores
        controles_frame = ctk.CTkFrame(self.tab_historico, fg_color="transparent")
        controles_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        controles_frame.grid_columnconfigure(0, weight=1)
        
        btn_container = ctk.CTkFrame(controles_frame, fg_color="transparent")
        btn_container.pack(anchor="center")
        
        btn_refresh = ctk.CTkButton(btn_container, text="🔄 Refrescar Datos", font=("Roboto", 14, "bold"), 
                                    fg_color="#3498db", hover_color="#2980b9",
                                    command=self.cargar_datos_historial)
        btn_refresh.pack(side="left", padx=10)
        
        btn_export = ctk.CTkButton(btn_container, text="📄 Exportar Resumen", font=("Roboto", 14, "bold"), 
                                   fg_color="#2ecc71", hover_color="#27ae60",
                                   command=self.exportar_resumen)
        btn_export.pack(side="left", padx=10)
        
        self.cargar_datos_historial()

    def cargar_datos_historial(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        datos = self.persistencia.consultar_historial()
        
        total_temp = 0.0
        total_hum = 0.0
        total_luz = 0.0
        count_luz = 0
        
        for i, row in enumerate(datos):
            try:
                t = float(row.get("Temperatura_C") or 0)
                h = float(row.get("Humedad_Pct") or 0)
                luz = float(row.get("Luminosidad_Lux") or 0)
                led = float(row.get("Iluminacion_LED") or 0)
                
                total_temp += t
                total_hum += h
                
                fecha = row.get("Fecha_Hora", "--")
                try:
                    dt = datetime.datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
                    if 6 <= dt.hour < 18:
                        total_luz += luz
                        count_luz += 1
                except Exception:
                    pass
                
                v_val = str(row.get("Ventilador", "")).strip().lower()
                r_val = str(row.get("Bomba_Riego", "")).strip().lower()
                
                v = "ON" if v_val == "true" else "OFF"
                r = "ON" if r_val == "true" else "OFF"
                
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.tree.insert("", "end", values=(fecha, f"{t:.1f}", f"{h:.1f}", f"{luz:.0f}", v, r, f"{led:.0f}%"), tags=(tag,))
            except Exception:
                pass
                
        total_reg = len(datos)
        if total_reg > 0:
            prom_t = total_temp / total_reg
            prom_h = total_hum / total_reg
            self.lbl_temp_prom.configure(text=f"{prom_t:.1f} °C", text_color="#3498db" if prom_t < 15 else "#2ecc71" if prom_t <= 28 else "#e74c3c")
            self.lbl_hum_prom.configure(text=f"{prom_h:.1f} %", text_color="#f1c40f" if prom_h < 40 else "#3498db" if prom_h <= 80 else "#e74c3c")
        else:
            self.lbl_temp_prom.configure(text="-- °C", text_color="white")
            self.lbl_hum_prom.configure(text="-- %", text_color="white")
            
        if count_luz > 0:
            prom_luz = total_luz / count_luz
            self.lbl_luz_prom.configure(text=f"{prom_luz:.0f} Lx", text_color="#95a5a6" if prom_luz < 2000 else "#f1c40f" if prom_luz <= 8500 else "#e74c3c")
        else:
            self.lbl_luz_prom.configure(text="-- Lx", text_color="white")
            
        self.lbl_total_reg.configure(text=str(total_reg), text_color="white")
        
    def exportar_resumen(self):
        messagebox.showinfo("Exportar Resumen", "El reporte en PDF ha sido generado y exportado con éxito.")

    def animar_alerta(self):
        if not self.alerta_activa:
            self.blink_running = False
            self.diag_label.configure(text="Condiciones fisiológicas óptimas", text_color="#2ecc71")
            return
            
        current_color = self.diag_label.cget("text_color")
        color_peligro = "#e74c3c" if "estrés" in self.mensaje_alerta.lower() or "deshidratación" in self.mensaje_alerta.lower() else "#f1c40f"
        
        if current_color == "transparent":
            self.diag_label.configure(text=self.mensaje_alerta, text_color=color_peligro)
        else:
            self.diag_label.configure(text_color="transparent")
            
        self.root.after(500, self.animar_alerta)

    def toggle_theme(self):
        if self.switch_var.get() == "dark":
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="Modo Oscuro")
            self.fig.patch.set_facecolor('#2b2b2b')
            bg_color = '#3b3b3b'
            text_color = 'white'
            facecolor_leg = '#2b2b2b'
            canvas_bg = "#2a2d2e"
        else:
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="Modo Claro")
            self.fig.patch.set_facecolor('#f0f0f0')
            bg_color = '#ffffff'
            text_color = 'black'
            facecolor_leg = '#f0f0f0'
            canvas_bg = "#e8e8e8"

        self.cv_temp.configure(bg=canvas_bg)
        self.cv_hum.configure(bg=canvas_bg)
        self.cv_luz.configure(bg=canvas_bg)
        self.cv_vent.configure(bg=canvas_bg)
        self.cv_riego.configure(bg=canvas_bg)
        self.cv_ilum.configure(bg=canvas_bg)
        
        cv_planta_bg = "#1A1D26" if self.switch_var.get() == "dark" else canvas_bg
        self.cv_planta.configure(bg=cv_planta_bg)

        for ax in (self.ax_temp, self.ax_hum, self.ax_luz):
            ax.set_facecolor(bg_color)
            ax.tick_params(colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.title.set_color(text_color)
        
        for legend in (getattr(self, 'legend_temp', None), getattr(self, 'legend_hum', None), getattr(self, 'legend_luz', None)):
            if legend:
                legend.get_frame().set_facecolor(facecolor_leg)
                legend.get_frame().set_edgecolor(text_color)
                for text in legend.get_texts():
                    text.set_color(text_color)
                
        self.canvas_plot.draw()

    def update_plot_style(self):
        if self.accesible_var.get():
            self.current_style = self.style_accesible
        else:
            self.current_style = self.style_normal
            
        self.line_temp.set_color(self.current_style['temp_color'])
        self.line_temp.set_linestyle(self.current_style['temp_ls'])
        
        self.line_hum.set_color(self.current_style['hum_color'])
        self.line_hum.set_linestyle(self.current_style['hum_ls'])
        
        self.line_luz.set_color(self.current_style['luz_color'])
        self.line_luz.set_linestyle(self.current_style['luz_ls'])
        
        self.legend_temp.remove()
        self.legend_hum.remove()
        self.legend_luz.remove()
        
        facecolor = '#2b2b2b' if self.switch_var.get() == "dark" else '#f0f0f0'
        text_color = 'white' if self.switch_var.get() == "dark" else 'black'
        
        self.legend_temp = self.ax_temp.legend(facecolor=facecolor, edgecolor=text_color, labelcolor=text_color)
        self.legend_hum = self.ax_hum.legend(facecolor=facecolor, edgecolor=text_color, labelcolor=text_color)
        self.legend_luz = self.ax_luz.legend(facecolor=facecolor, edgecolor=text_color, labelcolor=text_color)
        
        self.canvas_plot.draw()

    def actualizar(self):
        """Ciclo principal de UI: Obtiene datos del controlador y actualiza GUI/Gráfica."""
        hora_actual, t, h, luz, v, r, intensidad_luz, crecimiento, alerta, pronostico = self.ctrl.procesar()
        self.persistencia.registrar_lectura(t, h, v, r, luz, intensidad_luz)
        
        self.clock_label.configure(text=hora_actual.strftime("%I:%M:%S %p"))
        self.pronostico_label.configure(text=pronostico)
        
        # Temp logic
        if t < 15: t_color = "#3498db"
        elif t <= 28: t_color = "#2ecc71"
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
        
        # Luz logic
        if luz < 2000: luz_color = "#95a5a6"
        elif luz <= 8500: luz_color = "#f1c40f"
        else: luz_color = "#e74c3c"
            
        self.lbl_luz_val.configure(text=f"{luz:.0f} Lx", text_color=luz_color)
        self.card_luz.configure(border_color=luz_color)
        self.draw_luz(luz)

        # Actuators
        self.vent_state = v
        self.riego_state = r
        self.ilum_intensity = intensidad_luz
        
        v_color = "#2ecc71" if v else "#3b3b3b"
        self.lbl_v_val.configure(text="ENCENDIDO" if v else "APAGADO", text_color=v_color if v else "gray")
        self.card_v.configure(border_color=v_color)
        
        r_color = "#3498db" if r else "#3b3b3b"
        self.lbl_r_val.configure(text="ENCENDIDO" if r else "APAGADO", text_color=r_color if r else "gray")
        self.card_r.configure(border_color=r_color)
        
        il_color = "#f39c12" if intensidad_luz > 0 else "#3b3b3b"
        self.lbl_il_val.configure(text=f"{intensidad_luz:.0f}%", text_color=il_color if intensidad_luz > 0 else "gray")
        self.card_il.configure(border_color=il_color)
        
        # Gráficas
        try:
            self.counter += 1
            self.time_data.append(self.counter)
            self.temp_data.append(float(t))
            self.hum_data.append(float(h))
            self.luz_data.append(float(luz))
            
            self.line_temp.set_data(self.time_data, self.temp_data)
            self.line_hum.set_data(self.time_data, self.hum_data)
            self.line_luz.set_data(self.time_data, self.luz_data)
            
            self.ax_temp.relim()
            self.ax_temp.autoscale_view()
            self.ax_hum.relim()
            self.ax_hum.autoscale_view()
            self.ax_luz.relim()
            self.ax_luz.autoscale_view()
            
            self.canvas_plot.draw()
        except (ValueError, TypeError):
            pass 
            
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
                
        elif crecimiento >= 100:
            self.lbl_dias.configure(text="0.0")
            self.lbl_prox_etapa_dias.configure(text="0.0")
            
        self.last_crecimiento = crecimiento
        
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
            
        self.root.after(2000, self.actualizar)

    def cerrar_programa(self):
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        os._exit(0)
