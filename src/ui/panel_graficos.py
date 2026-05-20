import tkinter as tk
from typing import Callable, Tuple, Deque
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections

# ─────────────────────────────────────────────────────────────────────────────
#  Constantes de diseño (Dark Mode)
# ─────────────────────────────────────────────────────────────────────────────
FIG_BG  = '#2b2b2b'
AX_BG   = '#3b3b3b'
TEXT_C  = 'white'
COLORS = {
    'temp':    '#ff4757',
    'hum':     '#2ed573',
    'luz':     '#f1c40f',
    'vent':    '#3498db',
    'riego':   '#9b59b6',
    'ilum':    '#f39c12',
    'calef':   '#e67e22',
    'temp_ext':'#e74c3c',
    'hum_ext': '#1abc9c',
}

COLORBLIND_COLORS = {
    'temp':    '#D55E00',
    'hum':     '#56B4E9',
    'luz':     '#F0E442',
    'vent':    '#0072B2',
    'riego':   '#CC79A7',
    'ilum':    '#E69F00',
    'calef':   '#009E73',
    'temp_ext':'#D55E00',
    'hum_ext': '#56B4E9',
}


def _estilizar_ax(ax, title: str, ylabel: str, es_ultimo: bool = False, xlabel: str = "") -> None:
    """Aplica el tema oscuro a un eje matplotlib."""
    ax.set_title(title, color=TEXT_C, fontsize=11, fontweight='bold', pad=10)
    ax.set_ylabel(ylabel, color=TEXT_C, fontsize=10)
    ax.set_facecolor(AX_BG)
    ax.tick_params(colors=TEXT_C)
    ax.xaxis.label.set_color(TEXT_C)
    ax.yaxis.label.set_color(TEXT_C)
    for spine in ax.spines.values():
        spine.set_edgecolor('#555555')
    if es_ultimo:
        lbl = xlabel if xlabel else "Tiempo (min)"
        ax.set_xlabel(lbl, color=TEXT_C, fontsize=10)


def _leyenda(ax) -> None:
    ax.legend(facecolor=FIG_BG, edgecolor=TEXT_C, labelcolor=TEXT_C, loc="upper left")


# ─────────────────────────────────────────────────────────────────────────────
#  Clase principal
# ─────────────────────────────────────────────────────────────────────────────
class PanelMonitoreoGrafico:
    """
    Panel de monitoreo gráfico con tres secciones seleccionables:
      • Sensores Interiores  (Temperatura, Humedad, Luminosidad)
      • Entorno Exterior     (Temperatura exterior, Humedad exterior)
      • Actuadores           (Ventilador, Riego, Iluminación, Calefacción)

    El callback `obtener_datos_cb` debe devolver una tupla de 9 elementos:
        (temp, hum, luz, vent_on, riego_on, ilum_pct, calef_pct, temp_ext, hum_ext)
    """

    SECCIONES = ["Sensores Interiores", "Entorno Exterior", "Actuadores"]

    def __init__(self, master: ctk.CTkFrame, obtener_datos_cb: Callable[[], Tuple]):
        self.master = master
        self.obtener_datos_cb = obtener_datos_cb

        self.colorblind_mode = False

        # ── Buffers de datos (60 × 7 s = 7 min de historial) ───────────────
        self.INTERVALO_S = 7  # segundos por ciclo
        N = 60
        self.time_data  = collections.deque(maxlen=N)
        self.temp_data  = collections.deque(maxlen=N)
        self.hum_data   = collections.deque(maxlen=N)
        self.luz_data   = collections.deque(maxlen=N)
        self.vent_data  = collections.deque(maxlen=N)
        self.riego_data = collections.deque(maxlen=N)
        self.ilum_data  = collections.deque(maxlen=N)
        self.calef_data = collections.deque(maxlen=N)
        self.temp_ext_data = collections.deque(maxlen=N)
        self.hum_ext_data  = collections.deque(maxlen=N)
        self.elapsed_s = 0  # segundos transcurridos totales

        # ── Cabecera con selector ─────────────────────────────────────────────
        header = ctk.CTkFrame(master, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text="📊  Monitor Gráfico",
            font=("Roboto", 16, "bold"),
            text_color="white"
        ).pack(side="left", padx=(0, 20))

        self.combo = ctk.CTkComboBox(
            header,
            values=self.SECCIONES,
            width=220,
            font=("Roboto", 13),
            dropdown_font=("Roboto", 13),
            fg_color="#1A1D26",
            border_color="#3498db",
            button_color="#3498db",
            button_hover_color="#2980b9",
            command=self._on_seccion_cambio
        )
        self.combo.set(self.SECCIONES[0])
        self.combo.pack(side="left")

        self.switch_daltonismo = ctk.CTkSwitch(
            header,
            text="Modo Daltonismo",
            font=("Roboto", 12),
            command=self._toggle_daltonismo,
            onvalue=True,
            offvalue=False
        )
        self.switch_daltonismo.pack(side="right", padx=(20, 0))

        # ── Tres frames scrollables (uno por sección) ─────────────────────────
        opts = dict(fg_color="transparent", corner_radius=10)
        self.frame_interior  = ctk.CTkScrollableFrame(master, **opts)
        self.frame_exterior  = ctk.CTkScrollableFrame(master, **opts)
        self.frame_actuadores = ctk.CTkScrollableFrame(master, **opts)

        # ── Figuras matplotlib (Inicialización diferida) ──────────────────────
        self._graficas_listas = False
        
        # Mostrar mensaje de carga temporalmente (opcional pero ayuda a la UX)
        self.lbl_cargando = ctk.CTkLabel(master, text="Cargando motor gráfico, por favor espere...", font=("Roboto", 14))
        self.lbl_cargando.pack(expand=True)
        
        # Diferir la construcción para que la ventana principal cargue al instante
        self.master.after(50, self._inicializar_graficas_diferidas)

    def _inicializar_graficas_diferidas(self):
        self.lbl_cargando.pack_forget()
        
        self._construir_grafica_interior()
        self._construir_grafica_exterior()
        self._construir_grafica_actuadores()

        # Mostrar la primera sección por defecto
        self._mostrar_frame(self.frame_interior)
        self._graficas_listas = True

        # Arrancar ciclo: primer dato inmediato, luego cada 7 s
        self.actualizar_graficas()

    def _toggle_daltonismo(self):
        self.colorblind_mode = self.switch_daltonismo.get()
        self._dibujar_graficas_interior()
        self._dibujar_graficas_exterior()
        self._dibujar_graficas_actuadores()

    def _get_color(self, key):
        return COLORBLIND_COLORS[key] if self.colorblind_mode else COLORS[key]

    # ── Construcción de figuras ───────────────────────────────────────────────

    def _construir_grafica_interior(self):
        self.fig_int, axs_int = plt.subplots(3, 1, figsize=(7, 10), dpi=100)
        self.fig_int.patch.set_facecolor(FIG_BG)
        self.ax_temp, self.ax_hum, self.ax_luz = axs_int

        _estilizar_ax(self.ax_temp, "Temperatura Interior (°C)", "°C")
        _estilizar_ax(self.ax_hum,  "Humedad Relativa Interior (%)", "%")
        _estilizar_ax(self.ax_luz,  "Luminosidad (Lux)", "Lux", es_ultimo=True)
        self.fig_int.subplots_adjust(hspace=0.55)

        self.canvas_int = FigureCanvasTkAgg(self.fig_int, master=self.frame_interior)
        self.canvas_int.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas_int.draw()

    def _construir_grafica_exterior(self):
        self.fig_ext, axs_ext = plt.subplots(2, 1, figsize=(7, 7), dpi=100)
        self.fig_ext.patch.set_facecolor(FIG_BG)
        self.ax_temp_ext, self.ax_hum_ext = axs_ext

        _estilizar_ax(self.ax_temp_ext, "Temperatura Exterior (°C)", "°C")
        _estilizar_ax(self.ax_hum_ext,  "Humedad Exterior (%)", "%", es_ultimo=True)
        self.fig_ext.subplots_adjust(hspace=0.55)

        self.canvas_ext = FigureCanvasTkAgg(self.fig_ext, master=self.frame_exterior)
        self.canvas_ext.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas_ext.draw()

    def _construir_grafica_actuadores(self):
        self.fig_act, axs_act = plt.subplots(4, 1, figsize=(7, 14), dpi=100)
        self.fig_act.patch.set_facecolor(FIG_BG)
        self.ax_vent, self.ax_riego, self.ax_ilum, self.ax_calef = axs_act

        self.ax_vent.set_ylim(-0.2, 1.2)
        self.ax_riego.set_ylim(-0.2, 1.2)
        self.ax_ilum.set_ylim(-5, 105)
        self.ax_calef.set_ylim(-5, 105)
        _estilizar_ax(self.ax_vent,  "Ventilador (On/Off)", "ON/OFF")
        _estilizar_ax(self.ax_riego, "Aspersores de Riego (On/Off)", "ON/OFF")
        _estilizar_ax(self.ax_ilum,  "Iluminación LED (%)", "%")
        _estilizar_ax(self.ax_calef, "Calefacción (%)", "%", es_ultimo=True)
        self.fig_act.subplots_adjust(hspace=0.6)

        self.canvas_act = FigureCanvasTkAgg(self.fig_act, master=self.frame_actuadores)
        self.canvas_act.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas_act.draw()

    # ── Navegación entre secciones ────────────────────────────────────────────

    def _mostrar_frame(self, frame_visible: ctk.CTkScrollableFrame):
        for f in (self.frame_interior, self.frame_exterior, self.frame_actuadores):
            f.pack_forget()
        frame_visible.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _on_seccion_cambio(self, seleccion: str):
        mapa = {
            self.SECCIONES[0]: self.frame_interior,
            self.SECCIONES[1]: self.frame_exterior,
            self.SECCIONES[2]: self.frame_actuadores,
        }
        self._mostrar_frame(mapa.get(seleccion, self.frame_interior))

    # ── Ciclo de actualización ────────────────────────────────────────────────

    def actualizar_graficas(self) -> None:
        try:
            datos = self.obtener_datos_cb()
            if datos and len(datos) >= 9:
                temp, hum, luz, vent, riego, ilum_pct, calef_pct, temp_ext, hum_ext = datos[:9]

                self.elapsed_s += self.INTERVALO_S
                t_min = self.elapsed_s / 60.0
                self.time_data.append(round(t_min, 2))
                self.temp_data.append(float(temp))
                self.hum_data.append(float(hum))
                self.luz_data.append(float(luz))
                self.vent_data.append(100.0 if vent else 0.0)   # 0 = Apagado, 100 = Encendido (%)
                self.riego_data.append(100.0 if riego else 0.0)
                self.ilum_data.append(float(ilum_pct))
                self.calef_data.append(float(calef_pct))
                self.temp_ext_data.append(float(temp_ext))
                self.hum_ext_data.append(float(hum_ext))

                self._dibujar_graficas_interior()
                self._dibujar_graficas_exterior()
                self._dibujar_graficas_actuadores()

        except Exception as e:
            print(f"[PanelGrafico] Error en actualización: {e}")

        # Próximo ciclo en 7 s
        self.master.after(7000, self.actualizar_graficas)

    def _dibujar_graficas_interior(self):
        td = list(self.time_data)
        if not td: return
        self.ax_temp.clear()
        self.ax_hum.clear()
        self.ax_luz.clear()

        c_temp = self._get_color('temp')
        c_hum = self._get_color('hum')
        c_luz = self._get_color('luz')

        self.ax_temp.plot(td, list(self.temp_data), color=c_temp, label='Temperatura', linewidth=1.8)
        self.ax_hum.plot(td, list(self.hum_data),  color=c_hum,  label='Humedad',      linewidth=1.8)
        self.ax_luz.plot(td, list(self.luz_data),  color=c_luz,  label='Luminosidad',  linewidth=1.8)

        self.ax_temp.fill_between(td, list(self.temp_data), alpha=0.12, color=c_temp)
        self.ax_hum.fill_between(td, list(self.hum_data), alpha=0.12, color=c_hum)
        self.ax_luz.fill_between(td, list(self.luz_data), alpha=0.12, color=c_luz)

        _estilizar_ax(self.ax_temp, "Temperatura Interior (°C)", "°C")
        _estilizar_ax(self.ax_hum,  "Humedad Relativa Interior (%)", "%")
        _estilizar_ax(self.ax_luz,  "Luminosidad (Lux)", "Lux", es_ultimo=True)
        for ax in (self.ax_temp, self.ax_hum, self.ax_luz):
            _leyenda(ax)

        self.fig_int.subplots_adjust(hspace=0.55)
        self.canvas_int.draw()

    def _dibujar_graficas_exterior(self):
        td = list(self.time_data)
        if not td: return
        self.ax_temp_ext.clear()
        self.ax_hum_ext.clear()

        c_t_ext = self._get_color('temp_ext')
        c_h_ext = self._get_color('hum_ext')

        self.ax_temp_ext.plot(td, list(self.temp_ext_data), color=c_t_ext, label='Temp. Exterior', linewidth=1.8)
        self.ax_hum_ext.plot(td, list(self.hum_ext_data),  color=c_h_ext,  label='Hum. Exterior',  linewidth=1.8)

        self.ax_temp_ext.fill_between(td, list(self.temp_ext_data), alpha=0.12, color=c_t_ext)
        self.ax_hum_ext.fill_between(td, list(self.hum_ext_data), alpha=0.12, color=c_h_ext)

        _estilizar_ax(self.ax_temp_ext, "Temperatura Exterior (°C)", "°C")
        _estilizar_ax(self.ax_hum_ext,  "Humedad Exterior (%)", "%", es_ultimo=True)
        for ax in (self.ax_temp_ext, self.ax_hum_ext):
            _leyenda(ax)

        self.fig_ext.subplots_adjust(hspace=0.55)
        self.canvas_ext.draw()

    def _dibujar_graficas_actuadores(self):
        td = list(self.time_data)
        if not td: return
        self.ax_vent.clear()
        self.ax_riego.clear()
        self.ax_ilum.clear()
        self.ax_calef.clear()

        c_v = self._get_color('vent')
        c_r = self._get_color('riego')
        c_i = self._get_color('ilum')
        c_c = self._get_color('calef')

        self.ax_vent.step(td,  list(self.vent_data),  color=c_v,  label='Ventilador',  linewidth=1.8, where='post')
        self.ax_riego.step(td, list(self.riego_data), color=c_r, label='Aspersores',  linewidth=1.8, where='post')
        self.ax_ilum.plot(td,  list(self.ilum_data),  color=c_i,  label='Iluminación LED', linewidth=1.8)
        self.ax_calef.plot(td, list(self.calef_data), color=c_c, label='Calefacción',  linewidth=1.8)

        self.ax_ilum.fill_between(td, list(self.ilum_data), alpha=0.12, color=c_i)
        self.ax_calef.fill_between(td, list(self.calef_data), alpha=0.12, color=c_c)

        # Todos los actuadores en eje Y con escala 0-100%
        for ax in (self.ax_vent, self.ax_riego, self.ax_ilum, self.ax_calef):
            ax.set_ylim(-5, 105)
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda v, _: f"{int(v)}%")
            )

        _estilizar_ax(self.ax_vent,  "Ventilador", "%")
        _estilizar_ax(self.ax_riego, "Aspersores de Riego", "%")
        _estilizar_ax(self.ax_ilum,  "Iluminación LED", "%")
        _estilizar_ax(self.ax_calef, "Calefacción", "%", es_ultimo=True)
        for ax in (self.ax_vent, self.ax_riego, self.ax_ilum, self.ax_calef):
            _leyenda(ax)

        self.fig_act.subplots_adjust(hspace=0.6)
        self.canvas_act.draw()
