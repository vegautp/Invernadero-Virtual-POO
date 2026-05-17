import customtkinter as ctk
from interfaz import VentanaInvernadero

if __name__ == "__main__":
    # Configuración inicial del tema
    ctk.set_appearance_mode("dark")  # Modo oscuro por defecto
    ctk.set_default_color_theme("blue")  # Tema de colores principal
    
    root = ctk.CTk()
    app = VentanaInvernadero(root)
    root.mainloop()