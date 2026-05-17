import datetime
from entidades import SensorTemperatura, SensorHumedad, SensorLuminosidad, Ventilador, BombaRiego, SistemaIluminacion, Planta

class Controlador:
    def __init__(self, sp_temp=25.0, kp_temp=10.0, sp_hum=60.0, kp_hum=5.0):
        self.temp = SensorTemperatura()
        self.hum = SensorHumedad()
        self.luz = SensorLuminosidad()
        self.vent = Ventilador()
        self.riego = BombaRiego()
        self.iluminacion = SistemaIluminacion()
        self.planta = Planta()
        
        # Parámetros de control proporcional
        self.sp_temp = sp_temp
        self.kp_temp = kp_temp
        self.sp_hum = sp_hum
        self.kp_hum = kp_hum

    def procesar(self):
        hora_actual = datetime.datetime.now()
        
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        luz_natural = self.luz.leer_valor(hora_actual)
        
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

        # Lógica de iluminación
        # Calculamos la intensidad para compensar la falta de luz
        # Asumiendo que las bombillas al 100% dan 4000 Lux
        luz_objetivo = 4000.0
        if luz_natural < luz_objetivo:
            self.iluminacion.alternar(True)
            diferencia = luz_objetivo - luz_natural
            self.iluminacion.intensidad = min(100.0, (diferencia / 4000.0) * 100.0)
            luz_aportada = (self.iluminacion.intensidad / 100.0) * 4000.0
            luz_total = luz_natural + luz_aportada
        else:
            self.iluminacion.alternar(False)
            self.iluminacion.intensidad = 0.0
            luz_total = luz_natural
        
        # Evaluar fisiología de la planta
        alerta = self.planta.evaluar_condiciones(t, h, luz=luz_total)
        
        return hora_actual, t, h, round(luz_total, 2), self.vent.encendido, self.riego.encendido, round(self.iluminacion.intensidad, 2), self.planta.porcentaje_crecimiento, alerta
