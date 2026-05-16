import customtkinter as ctk
from interfaz import VentanaInvernadero

if __name__ == "__main__":
    # Cambiamos tk.Tk() por ctk.CTk() para activar el modo oscuro
    root = ctk.CTk() 
    app = VentanaInvernadero(root)
    root.mainloop()