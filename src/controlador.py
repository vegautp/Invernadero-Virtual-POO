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
        
        # Parámetros PWM
        self.periodo_pwm = 5
        self.tick_pwm = 0

    def procesar(self):
        ahora = datetime.datetime.now()
        dt_sec = (ahora - self.ultimo_tick).total_seconds()
        self.ultimo_tick = ahora
        self.tiempo_simulado += datetime.timedelta(seconds=dt_sec * self.multiplicador_tiempo)
        
        self.tick_pwm = (self.tick_pwm + 1) % self.periodo_pwm
        
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
        # La inercia térmica depende estrictamente del tiempo simulado transcurrido
        dt_simulado = dt_sec * self.multiplicador_tiempo
        factor_inercia = dt_simulado / 2.0
        t_actual += (t_ext - t_actual) * min(1.0, 0.06 * factor_inercia)
        h_actual += (h_ext - h_actual) * min(1.0, 0.02 * factor_inercia)
        
        # B) Efecto Invernadero (Calor solar atrapado)
        if es_de_dia:
            calor_solar = (luz_natural / 100000.0) * 2.2
            t_actual += calor_solar * factor_inercia
            
        # C) Impacto Activo de Actuadores del ciclo anterior
        if self.vent.encendido:
            # Intercambio pasivo con el exterior acelerado
            t_actual += (t_ext - t_actual) * min(1.0, 0.38 * factor_inercia)
            h_actual += (h_ext - h_actual) * min(1.0, 0.38 * factor_inercia)
            # Extracción mecánica garantizada
            h_actual -= random.uniform(0.5, 1.5) * factor_inercia
            t_actual -= random.uniform(0.1, 0.3) * factor_inercia
            
        if self.riego.encendido:
            # Aspersión directa: incrementa humedad y enfría por evaporación
            h_actual += random.uniform(2.0, 3.0) * factor_inercia
            t_actual -= 0.6 * factor_inercia
            
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
        # Requisito Ideal: 6,000 Lux de día. En la noche, encender con poca luminosidad (ej. 1,000 Lux).
        requisito_ideal_lux = 6000.0 if es_de_dia else 1000.0
        max_aporte_led = 10000.0
        
        esfuerzo_ilum = 0.0
        if luz_natural < requisito_ideal_lux:
            diferencia = requisito_ideal_lux - luz_natural
            esfuerzo_ilum = min(100.0, (diferencia / max_aporte_led) * 100.0)
            
        self.iluminacion.esfuerzo = esfuerzo_ilum
        estado_ilum = self.tick_pwm < (esfuerzo_ilum / 100.0) * self.periodo_pwm
        self.iluminacion.alternar(estado_ilum)
        
        if estado_ilum:
            self.iluminacion.intensidad = 100.0
            luz_aportada = max_aporte_led
            luz_total = luz_natural + luz_aportada
            # Calor residual LED aplicado en el mismo ciclo de decisión (bug fix)
            t_actual += 0.04
            self.temp.valor = max(10.0, min(50.0, t_actual))
        else:
            self.iluminacion.intensidad = 0.0
            luz_total = luz_natural
            
        # 5. Lógica de Actuadores Térmicos e Hídricos
        
        # Sistema Térmico (Calefacción y Ventilador/Extractor) con PWM
        setpoint_temp = 22.0
        limite_inf_temp = 18.0
        limite_sup_temp = 25.0
        
        esfuerzo_calef = 0.0
        esfuerzo_vent = 0.0
        
        if t < limite_inf_temp:
            # Hace frío: Calefacción proporcional para llegar a 22.0°C. Ventilador apagado absoluto.
            error_frio = setpoint_temp - t
            esfuerzo_calef = min(100.0, max(0.0, error_frio * self.kp_temp))
            esfuerzo_vent = 0.0
        elif t > limite_sup_temp:
            # Hace calor: Ventilador/Extractor proporcional para enfriar hacia 22.0°C. Calefacción apagada.
            esfuerzo_calef = 0.0
            error_calor = t - setpoint_temp
            esfuerzo_vent = min(100.0, max(0.0, error_calor * 15.0))
        else:
            # Zona de confort (18 a 25)
            esfuerzo_calef = 0.0
            esfuerzo_vent = 0.0
            
        # Control de humedad de seguridad (evita Botrytis) solo si no hace frío extremo
        if h > 80.0 and t >= limite_inf_temp:
            esfuerzo_vent = min(100.0, esfuerzo_vent + (h - 80.0) * 10.0)
            
        # --- Aplicación PWM Calefacción ---
        self.calefaccion.esfuerzo = esfuerzo_calef
        estado_calef = self.tick_pwm < (esfuerzo_calef / 100.0) * self.periodo_pwm
        
        if estado_calef:
            self.calefaccion.encendido = True
            self.calefaccion.potencia = 100.0
            # Limitamos el choque térmico instantáneo para simular la inercia de la masa de aire
            # y suavizar el pulso PWM a altas velocidades (x50)
            aporte_calor = 1.5 * factor_inercia
            t_actual += aporte_calor
            h_actual -= 0.5 * factor_inercia
        else:
            self.calefaccion.encendido = False
            self.calefaccion.potencia = 0.0

        # --- Aplicación PWM Ventilador/Extractor ---
        self.vent.esfuerzo = esfuerzo_vent
        estado_vent = self.tick_pwm < (esfuerzo_vent / 100.0) * self.periodo_pwm
        self.vent.alternar(estado_vent)
            
        # Bomba de Riego (Humedece) con PWM:
        esfuerzo_riego = 0.0
        if h < 50.0:
            err_h_riego = 50.0 - h
            esfuerzo_riego = min(100.0, 50.0 + err_h_riego * 10.0)
        elif h >= 70.0:
            esfuerzo_riego = 0.0
        else:
            esfuerzo_riego = max(0.0, (70.0 - h) * 2.5)

        self.riego.esfuerzo = esfuerzo_riego
        estado_riego = self.tick_pwm < (esfuerzo_riego / 100.0) * self.periodo_pwm
        self.riego.alternar(estado_riego)
        
        # Evaluar fisiología de la planta
        # La planta percibe el promedio lumínico del pulso PWM, no los destellos instantáneos
        luz_promedio = luz_natural + (10000.0 * (self.iluminacion.esfuerzo / 100.0))
        alerta = self.planta.evaluar_condiciones(t, h, luz=luz_promedio, multiplicador=self.multiplicador_tiempo, es_de_dia=es_de_dia)
        
        # Obtenemos lecturas redondeadas del exterior para la UI
        t_ext = round(self.motor_clima.temp_exterior, 1)
        h_ext = round(self.motor_clima.hum_exterior, 1)
        
        return hora_actual, t, h, round(luz_total, 2), self.vent.encendido, self.riego.encendido, round(self.iluminacion.intensidad, 2), self.calefaccion.encendido, round(self.calefaccion.potencia, 2), self.planta.porcentaje_crecimiento, alerta, pronostico, t_ext, h_ext, self.vent.esfuerzo, self.riego.esfuerzo, self.iluminacion.esfuerzo, self.calefaccion.esfuerzo
