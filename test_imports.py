import sys
import os
sys.path.append('src')
try:
    import entidades
    print("entidades imported")
    import controlador
    print("controlador imported")
    ctrl = controlador.Controlador()
    print("Controlador instantiated")
    import persistencia
    print("persistencia imported")
    import interfaz
    print("interfaz imported")
    import tkinter as tk
    root = tk.Tk()
    app = interfaz.VentanaInvernadero(root)
    print("VentanaInvernadero instantiated")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

