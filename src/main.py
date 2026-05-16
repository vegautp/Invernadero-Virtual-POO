import tkinter as tk
from interfaz import VentanaInvernadero

if __name__ == "__main__":
    print("Iniciando sistema... Presione Ctrl+C en la terminal para salir.")
    root = tk.Tk()
    app = VentanaInvernadero(root)
    root.mainloop()