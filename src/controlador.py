from entidades import SensorTemperatura, SensorHumedad, Ventilador, BombaRiego

class Controlador:
    def __init__(self):
        self.temp = SensorTemperatura()
        self.hum = SensorHumedad()
        self.vent = Ventilador()
        self.riego = BombaRiego()

    def procesar(self):
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        
        # Lógica On/Off
        self.vent.alternar(t > 28.0)
        self.riego.alternar(h < 40.0)
        
        return t, h, self.vent.activo, self.riego.activo

