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
        
        # Lógica Proporcional (P)
        # Ventilador: enfría, por lo que actúa si Temp > SetPoint
        error_temp = t - self.sp_temp
        potencia_vent = self.kp_temp * error_temp if error_temp > 0 else 0.0
        self.vent.ajustar_potencia(potencia_vent)
        
        # Bomba: humedece, por lo que actúa si Hum < SetPoint
        error_hum = self.sp_hum - h
        potencia_riego = self.kp_hum * error_hum if error_hum > 0 else 0.0
        self.riego.ajustar_potencia(potencia_riego)
        
        return t, h, self.vent.potencia, self.riego.potencia

