import tkinter as tk
from typing import Callable, Tuple, Deque
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections

class PanelMonitoreoGrafico:
    """
    Panel modular para el monitoreo gráfico de sensores y actuadores.
    Utiliza un ciclo de actualización independiente cada 10 segundos.
    """
    def __init__(self, master: ctk.CTkFrame, obtener_datos_cb: Callable[[], Tuple]):
        self.master = master
        self.obtener_datos_cb = obtener_datos_cb
        
        # Buffers de datos (Max 60 elementos, 60 * 10s = 10 minutos de historial local)
        self.max_len = 60
        self.time_data: Deque[int] = collections.deque(maxlen=self.max_len)
        self.temp_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.hum_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.luz_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.vent_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.riego_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.ilum_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.calef_data: Deque[float] = collections.deque(maxlen=self.max_len)
        self.counter = 0

        # Contenedor Scrollable
        self.scroll_frame = ctk.CTkScrollableFrame(self.master, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configuración de colores
        self.style_normal = {
            'temp_color': '#ff4757', 'hum_color': '#2ed573', 'luz_color': '#f1c40f',
            'vent_color': '#3498db', 'riego_color': '#9b59b6', 'ilum_color': '#f39c12', 'calef_color': '#e67e22'
        }

        # Configuración de la figura principal
        self.fig, self.axs = plt.subplots(7, 1, figsize=(7, 22), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.fig.tight_layout(pad=3.0)

        (self.ax_temp, self.ax_hum, self.ax_luz, self.ax_vent, self.ax_riego, self.ax_ilum, self.ax_calef) = self.axs

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.scroll_frame)
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        self.configurar_ejes()

        # Iniciar ciclo de actualización a 10 segundos
        self.actualizar_graficas()

    def configurar_ejes(self) -> None:
        """
        Aplica o re-aplica los títulos descriptivos, labels y colores a los ejes.
        Debe llamarse DESPUÉS de hacer ax.clear() y ax.plot() para no perder el formato.
        """
        fig_bg = '#2b2b2b'
        ax_bg = '#3b3b3b'
        text_color = 'white'

        self.fig.patch.set_facecolor(fig_bg)
        
        # Títulos descriptivos claros para cada subgráfica
        titles_y = [
            (self.ax_temp, "Sensor de Temperatura Interior (°C)", "°C"), 
            (self.ax_hum, "Humedad Relativa (%)", "%"), 
            (self.ax_luz, "Sensor de Luminosidad (Lux)", "Lux"), 
            (self.ax_vent, "Estado del Ventilador (On/Off)", "ON/OFF"), 
            (self.ax_riego, "Estado de Aspersores de Riego (On/Off)", "ON/OFF"), 
            (self.ax_ilum, "Nivel de Iluminación LED (%)", "%"), 
            (self.ax_calef, "Potencia de Calefacción (%)", "%")
        ]

        for ax, title, ylabel in titles_y:
            # Reaplicamos títulos y estilos para Dark Mode
            ax.set_title(title, color=text_color, fontsize=11, fontweight='bold', pad=10)
            ax.set_ylabel(ylabel, color=text_color, fontsize=10)
            ax.set_facecolor(ax_bg)
            ax.tick_params(colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            
            # Solo la última gráfica (la de abajo) necesita la etiqueta del eje X
            if ax == self.ax_calef:
                ax.set_xlabel("Tiempo (Ciclos de 10s)", color=text_color, fontsize=10)

        # Re-aplicamos los límites fijos del Eje Y para las gráficas booleanas o porcentuales
        self.ax_vent.set_ylim(-0.2, 1.2)
        self.ax_riego.set_ylim(-0.2, 1.2)
        self.ax_ilum.set_ylim(-5, 105)
        self.ax_calef.set_ylim(-5, 105)
        
        # Mantenemos el espaciado para evitar superposiciones
        self.fig.subplots_adjust(hspace=0.6)

    def actualizar_graficas(self) -> None:
        """
        Ciclo independiente que consulta los datos y actualiza las gráficas
        estrictamente cada 10 segundos, limpiando y redibujando correctamente.
        """
        try:
            # 1. Obtener los últimos datos
            datos = self.obtener_datos_cb()
            if datos:
                temp, hum, luz, vent, riego, ilum_pct, calef_pct = datos
                
                # collections.deque automáticamente elimina el dato más viejo si superamos el maxlen
                self.counter += 1
                self.time_data.append(self.counter)
                self.temp_data.append(float(temp))
                self.hum_data.append(float(hum))
                self.luz_data.append(float(luz))
                self.vent_data.append(1.0 if vent else 0.0)
                self.riego_data.append(1.0 if riego else 0.0)
                self.ilum_data.append(float(ilum_pct))
                self.calef_data.append(float(calef_pct))

                # 2. CRUCIAL: Limpiar todas las gráficas para evitar superposición
                for ax in self.axs:
                    ax.clear()

                # 3. Volver a graficar la colección de datos actualizados
                self.ax_temp.plot(self.time_data, self.temp_data, label='Temperatura', color=self.style_normal['temp_color'])
                self.ax_hum.plot(self.time_data, self.hum_data, label='Humedad', color=self.style_normal['hum_color'])
                self.ax_luz.plot(self.time_data, self.luz_data, label='Luminosidad', color=self.style_normal['luz_color'])
                self.ax_vent.plot(self.time_data, self.vent_data, label='Ventilador', color=self.style_normal['vent_color'])
                self.ax_riego.plot(self.time_data, self.riego_data, label='Aspersores', color=self.style_normal['riego_color'])
                self.ax_ilum.plot(self.time_data, self.ilum_data, label='Iluminación', color=self.style_normal['ilum_color'])
                self.ax_calef.plot(self.time_data, self.calef_data, label='Calefacción', color=self.style_normal['calef_color'])

                # 4. CRUCIAL: Reconstruir los ejes, títulos y fondo oscuro que ax.clear() acaba de borrar
                self.configurar_ejes()

                # 5. Volver a mostrar las leyendas
                face_bg = '#2b2b2b'
                text_c = 'white'
                for ax in self.axs:
                    ax.legend(facecolor=face_bg, edgecolor=text_c, labelcolor=text_c, loc="upper left")

                # 6. Renderizar los cambios finales al usuario
                self.canvas_plot.draw()
                
        except Exception as e:
            print(f"Error en bucle de actualización gráfica: {e}")

        # Programar la próxima actualización (Bucle infinito de 10s)
        self.master.after(10000, self.actualizar_graficas)
