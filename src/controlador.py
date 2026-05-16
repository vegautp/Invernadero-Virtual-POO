import datetime
from entidades import SensorTemperatura, SensorHumedad, SensorLuminosidad, Ventilador, BombaRiego, SistemaIluminacion, Planta

class Controlador:
    def __init__(self):
        self.temp = SensorTemperatura()
        self.hum = SensorHumedad()
        self.luz = SensorLuminosidad()
        self.vent = Ventilador()
        self.riego = BombaRiego()
        self.iluminacion = SistemaIluminacion()
        self.planta = Planta()

    def procesar(self):
        hora_actual = datetime.datetime.now()
        
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        luz_natural = self.luz.leer_valor(hora_actual)
        
        # Lógica On/Off
        self.vent.alternar(t > 28.0)
        self.riego.alternar(h < 40.0)
        
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
