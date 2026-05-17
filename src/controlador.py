from entidades import SensorTemperatura, SensorHumedad, Ventilador, BombaRiego

class Controlador:
    def __init__(self, sp_temp=25.0, kp_temp=10.0, sp_hum=60.0, kp_hum=5.0):
        self.temp = SensorTemperatura()
        self.hum = SensorHumedad()
        self.vent = Ventilador()
        self.riego = BombaRiego()
        
        # Parámetros de control proporcional
        self.sp_temp = sp_temp
        self.kp_temp = kp_temp
        self.sp_hum = sp_hum
        self.kp_hum = kp_hum

    def procesar(self):
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        
        # Ventilador: Si Temp <= 25°C -> 0%, Si Temp >= 35°C -> 100%. Entre 25 y 35, proporcional.
        if t <= 25.0:
            potencia_vent = 0.0
        elif t >= 35.0:
            potencia_vent = 100.0
        else:
            potencia_vent = (t - 25.0) * 10.0  # Proporcional de 0 a 100 en un rango de 10°C
        
        self.vent.ajustar_potencia(potencia_vent)
        
        # Bomba: Si Hum >= 60% -> 0%, Si Hum <= 30% -> 100%. Entre 30 y 60, proporcional.
        if h >= 60.0:
            potencia_riego = 0.0
        elif h <= 30.0:
            potencia_riego = 100.0
        else:
            potencia_riego = (60.0 - h) * (100.0 / 30.0)  # Proporcional de 0 a 100 en un rango de 30%
            
        self.riego.ajustar_potencia(potencia_riego)
        
        return t, h, self.vent.potencia, self.riego.potencia

