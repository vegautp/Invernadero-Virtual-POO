"""
main.py — Punto de entrada del Invernadero Virtual POO.

Este módulo inicializa el tema visual de la aplicación mediante CustomTkinter
y arranca el bucle principal de la interfaz gráfica (GUI). Su única
responsabilidad es configurar el entorno y delegar el control a la clase
VentanaInvernadero, siguiendo el Principio de Responsabilidad Única (SRP).

Autores:
    Dorance Agudelo Rodríguez
    Yulian Alexis Ricardo Serna
    Juan Gabriel Vega Ospina

Institución:
    Universidad Tecnológica de Pereira
    Facultad de Ingenierías — Ingeniería Eléctrica
"""

import customtkinter as ctk
from interfaz import VentanaInvernadero

if __name__ == "__main__":
    # Activar el modo oscuro global para todos los widgets de CustomTkinter.
    ctk.set_appearance_mode("dark")

    # Definir la paleta de colores base ("blue" es el tema por defecto de CTk).
    ctk.set_default_color_theme("blue")

    # Crear la ventana raíz de CustomTkinter (equivalente a tk.Tk() en Tkinter estándar).
    root = ctk.CTk()

    # Instanciar el controlador principal de la interfaz, que a su vez
    # inicializa el Controlador físico, los sensores y todos los módulos.
    app = VentanaInvernadero(root)

    # Iniciar el bucle de eventos de la GUI. Este método bloquea el hilo principal
    # hasta que el usuario cierra la ventana, momento en el que se ejecuta cerrar_programa().
    root.mainloop()