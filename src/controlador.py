import datetime
import random
from entidades import SensorTemperatura, SensorHumedad, SensorLuminosidad, Ventilador, BombaRiego, SistemaIluminacion, Planta, MotorClimatico

class Controlador:
    def __init__(self, sp_temp=25.0, kp_temp=10.0, sp_hum=60.0, kp_hum=5.0):
        self.temp = SensorTemperatura()
        self.hum = SensorHumedad()
        self.luz = SensorLuminosidad()
        self.vent = Ventilador()
        self.riego = BombaRiego()
        self.iluminacion = SistemaIluminacion()
        self.planta = Planta()
        self.motor_clima = MotorClimatico()
        
        # Parámetros de control proporcional
        self.sp_temp = sp_temp
        self.kp_temp = kp_temp
        self.sp_hum = sp_hum
        self.kp_hum = kp_hum

    def procesar(self):
        hora_actual = datetime.datetime.now()
        
        # 1. Actualizar clima y obtener pronóstico
        self.motor_clima.actualizar_clima()
        
        # 2. Ciclo Día/Noche y Luz Natural
        es_de_dia = 6 <= hora_actual.hour < 18
        if es_de_dia:
            if self.motor_clima.estado_actual == "Soleado":
                luz_natural = random.uniform(10000, 15000)
            elif self.motor_clima.estado_actual == "Nublado":
                luz_natural = random.uniform(1000, 4000)
            else: # Frío
                luz_natural = random.uniform(500, 2000)
        else:
            luz_natural = 0.0
            
        self.luz.valor = luz_natural
        
        # 3. Termodinámica Básica
        t_actual = self.temp.valor
        h_actual = self.hum.valor
        
        # Fórmula: Si hay luz, la energía radiante incrementa la temperatura.
        if es_de_dia:
            incremento_t = (luz_natural / 100000.0)
            t_actual += incremento_t
        else:
            # Fórmula: De noche, la temperatura desciende de forma natural hacia los 15°C
            descenso_t = (t_actual - 15.0) * 0.01
            t_actual -= descenso_t
            
        # Fórmula: Si la temperatura sube, la humedad tiende a bajar (evaporación)
        delta_t = t_actual - self.temp.valor
        if delta_t > 0:
            h_actual -= (delta_t * 2.0)
        else:
            h_actual += 0.05
            
        self.temp.valor = max(10.0, min(50.0, t_actual))
        self.hum.valor = max(10.0, min(100.0, h_actual))
        
        # Obtenemos las lecturas finales que añaden la fluctuación simulada natural del sensor
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        
        # El pronóstico cumple la especificación de negocio (Paso C1) sin interferir con la GUI
        pronostico = self.motor_clima.generar_pronostico(t)
        
        # 4. Lógica de Iluminación LED (Actuador Suplementario)
        # Requisito Ideal: 6,000 Lux. Aporte máximo LED: 10,000 Lux al 100%.
        requisito_ideal_lux = 6000.0
        max_aporte_led = 10000.0
        
        if luz_natural < requisito_ideal_lux:
            self.iluminacion.alternar(True)
            diferencia = requisito_ideal_lux - luz_natural
            # Calcula el % exacto para compensar el déficit (sin pasarse del 100%)
            porcentaje_necesario = (diferencia / max_aporte_led) * 100.0
            self.iluminacion.intensidad = min(100.0, porcentaje_necesario)
            luz_aportada = (self.iluminacion.intensidad / 100.0) * max_aporte_led
            luz_total = luz_natural + luz_aportada
        else:
            self.iluminacion.alternar(False)
            self.iluminacion.intensidad = 0.0
            luz_total = luz_natural
            
        # 5. Lógica de Actuadores Térmicos e Hídricos
        # Ventilador (Enfría y seca): 
        # ON si T > 28°C o H > 80%. OFF ESTRICTO si T < 15°C para conservar calor.
        if t < 15.0:
            self.vent.alternar(False)
        elif t > 28.0 or h > 80.0:
            self.vent.alternar(True)
        else:
            self.vent.alternar(False) # Apagado en rango ideal
            
        # Bomba de Riego (Humedece):
        # ON si H < 50%. OFF si H >= 70%. NUNCA encender como respuesta al frío.
        if h < 50.0:
            self.riego.alternar(True)
        elif h >= 70.0:
            self.riego.alternar(False)
        # Entre 50% y 70%, mantiene el estado previo (histéresis)
        
        # Evaluar fisiología de la planta
        alerta = self.planta.evaluar_condiciones(t, h, luz=luz_total)
        
        return hora_actual, t, h, round(luz_total, 2), self.vent.encendido, self.riego.encendido, round(self.iluminacion.intensidad, 2), self.planta.porcentaje_crecimiento, alerta, pronostico
