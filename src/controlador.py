from entidades import SensorTemperatura, SensorHumedad, Ventilador, BombaRiego

class Controlador:
    def __init__(self):
        self.sensor_temp = SensorTemperatura()
        self.sensor_hum = SensorHumedad()
        self.ventilador = Ventilador()
        self.riego = BombaRiego()

    def procesar_logica(self):
        t = self.sensor_temp.leer_valor()
        h = self.sensor_hum.leer_valor()
        
        # Lógica On/Off: Si Temp > 28 enciende ventilador. Si Hum < 40 enciende riego.
        self.ventilador.alternar(t > 28.0)
        self.riego.alternar(h < 40.0)
        
        return t, h, self.ventilador.activo, self.riego.activo