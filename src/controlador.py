import datetime
import random
from entidades import SensorTemperatura, SensorHumedad, SensorLuminosidad, Ventilador, BombaRiego, SistemaIluminacion, Planta, MotorClimatico, Calefaccion

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
        self.calefaccion = Calefaccion()
        
        # Parámetros de control proporcional
        self.sp_temp = sp_temp
        self.kp_temp = kp_temp
        self.sp_hum = sp_hum
        self.kp_hum = kp_hum
        
        # Variables para manejo del tiempo acelerado
        self.tiempo_simulado = datetime.datetime.now()
        self.ultimo_tick = datetime.datetime.now()
        self.multiplicador_tiempo = 1.0

    def procesar(self):
        ahora = datetime.datetime.now()
        dt_sec = (ahora - self.ultimo_tick).total_seconds()
        self.ultimo_tick = ahora
        self.tiempo_simulado += datetime.timedelta(seconds=dt_sec * self.multiplicador_tiempo)
        
        hora_actual = self.tiempo_simulado
        
        # 1. Actualizar clima exterior y obtener pronóstico
        self.motor_clima.actualizar_clima(hora_actual)
        
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
        
        # 3. Termodinámica Avanzada y Lazo Cerrado de Actuadores
        t_actual = self.temp.valor
        h_actual = self.hum.valor
        
        t_ext = self.motor_clima.temp_exterior
        h_ext = self.motor_clima.hum_exterior
        
        # A) Conducción Térmica Pasiva: El invernadero tiende lentamente al clima exterior
        # Limitamos el impacto del multiplicador en la conducción para evitar inestabilidad térmica
        t_actual += (t_ext - t_actual) * min(1.0, 0.06 * self.multiplicador_tiempo)
        h_actual += (h_ext - h_actual) * min(1.0, 0.02 * self.multiplicador_tiempo)
        
        # B) Efecto Invernadero (Calor solar atrapado)
        if es_de_dia:
            calor_solar = (luz_natural / 100000.0) * 2.2
            t_actual += calor_solar * self.multiplicador_tiempo
            
        # C) Impacto Activo de Actuadores del ciclo anterior
        if self.vent.encendido:
            # Intercambio pasivo con el exterior
            t_actual += (t_ext - t_actual) * 0.38
            h_actual += (h_ext - h_actual) * 0.38
            # Extracción mecánica garantizada: el ventilador siempre seca y enfría,
            # independientemente del clima exterior (efecto físico del motor).
            h_actual -= random.uniform(0.5, 1.5)
            t_actual -= random.uniform(0.1, 0.3)
            
        if self.riego.encendido:
            # Aspersión directa: siempre incrementa la humedad activamente
            h_actual += random.uniform(2.0, 3.0)
            t_actual -= 0.6  # Enfriamiento por evaporación
            
        # BUG CORREGIDO: el efecto térmico del LED se calculaba ANTES de decidir
        # si el LED estaba encendido en este ciclo (bloque 4), siempre usando el
        # estado del ciclo anterior. El calor del LED ahora se aplica en el bloque 4,
        # junto con la decisión de encendido, garantizando coherencia en el mismo ciclo.
            
        # D) Relación higrotérmica natural: si la temperatura sube, la humedad relativa baja
        delta_t = t_actual - self.temp.valor
        if delta_t > 0:
            h_actual -= (delta_t * 1.5)
        else:
            h_actual += 0.05
            
        self.temp.valor = max(10.0, min(50.0, t_actual))
        self.hum.valor  = max(0.0,  min(100.0, h_actual))
        
        # Obtenemos las lecturas finales que añaden la fluctuación simulada natural del sensor
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        
        # El pronóstico cumple la especificación de negocio (Paso C1) sin interferir con la GUI
        pronostico = self.motor_clima.generar_pronostico(hora_actual)
        
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
            # Calor residual LED aplicado en el mismo ciclo de decisión (bug fix)
            t_actual += 0.04 * (self.iluminacion.intensidad / 100.0)
            self.temp.valor = max(10.0, min(50.0, t_actual))
        else:
            self.iluminacion.alternar(False)
            self.iluminacion.intensidad = 0.0
            luz_total = luz_natural
            
        # 5. Lógica de Actuadores Térmicos e Hídricos
        
        # Sistema de Calefacción con Control Proporcional
        setpoint_calefaccion = 18.0
        if t < setpoint_calefaccion:
            error = setpoint_calefaccion - t
            # kp_temp define qué tan rápido responde (potencia por cada grado de error)
            potencia_calculada = error * self.kp_temp
            self.calefaccion.potencia = min(100.0, max(0.0, potencia_calculada))
            self.calefaccion.encendido = True
            
            # Impacto térmico de la calefacción proporcional al tiempo
            aporte_calor = (self.calefaccion.potencia / 100.0) * 1.5 * self.multiplicador_tiempo
            t_actual += aporte_calor
            # La calefacción reduce la humedad al calentar el aire
            h_actual -= (self.calefaccion.potencia / 100.0) * 0.5 * self.multiplicador_tiempo
            
            # Recalculamos con el nuevo calor inyectado
            self.temp.valor = max(10.0, min(50.0, t_actual))
            self.hum.valor  = max(0.0,  min(100.0, h_actual))
            t = self.temp.leer_valor()
            h = self.hum.leer_valor()
        else:
            self.calefaccion.encendido = False
            self.calefaccion.potencia = 0.0

        # Ventilador (Enfría y seca): 
        # ON si T > 28°C o H > 80%. OFF ESTRICTO si T < 15°C para conservar calor,
        # a menos que la humedad sea crítica (> 80.0%) para prevenir patógenos fúngicos (Botrytis).
        if t < 15.0 and h <= 80.0:
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
        alerta = self.planta.evaluar_condiciones(t, h, luz=luz_total, multiplicador=self.multiplicador_tiempo)
        
        # Obtenemos lecturas redondeadas del exterior para la UI
        t_ext = round(self.motor_clima.temp_exterior, 1)
        h_ext = round(self.motor_clima.hum_exterior, 1)
        
        return hora_actual, t, h, round(luz_total, 2), self.vent.encendido, self.riego.encendido, round(self.iluminacion.intensidad, 2), self.calefaccion.encendido, round(self.calefaccion.potencia, 2), self.planta.porcentaje_crecimiento, alerta, pronostico, t_ext, h_ext
