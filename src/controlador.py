"""
controlador.py — Cerebro del Invernadero Virtual POO.

Lee los sensores, aplica la lógica de control (P-PWM e histéresis) y
actualiza los actuadores cada ciclo. También gestiona el reloj virtual
y delega la persistencia de datos a GestorPersistencia.
"""

import datetime
import random
import math
from entidades import SensorTemperatura, SensorHumedad, SensorLuminosidad, Ventilador, BombaRiego, SistemaIluminacion, Planta, MotorClimatico, Calefaccion
from persistencia import GestorPersistencia

class Controlador:
    """
    Controlador principal del invernadero.

    Integra sensores, actuadores, motor climático, modelo de planta y
    persistencia en un único ciclo de control llamado por la interfaz
    mediante self.procesar() cada vez que el timer de la GUI dispara.
    """

    def __init__(self, sp_temp=25.0, kp_temp=10.0, sp_hum=60.0, kp_hum=5.0):
        """
        Inicializa todos los subsistemas del invernadero.

        Args:
            sp_temp  (float): Setpoint de temperatura (°C). Default 25.0.
            kp_temp  (float): Ganancia proporcional temperatura. Default 10.0.
            sp_hum   (float): Setpoint de humedad (%). Default 60.0.
            kp_hum   (float): Ganancia proporcional humedad. Default 5.0.
        """
        self.temp = SensorTemperatura()
        self.hum = SensorHumedad()
        self.luz = SensorLuminosidad()
        self.vent = Ventilador()
        self.riego = BombaRiego()
        self.iluminacion = SistemaIluminacion()
        self.planta = Planta()
        self.motor_clima = MotorClimatico()
        self.calefaccion = Calefaccion()
        self.malla_desplegada = False  # Estado de la polisombra/pantalla térmica
        self.deshumidificando = False  # Bandera de estado para histéresis de humedad (tiempo muerto)
        self.enfriando = False         # Bandera de estado para histéresis térmica (tiempo muerto)
        self.iluminando = False        # Bandera de estado para histéresis lumínica
        self.persistencia = GestorPersistencia()
        
        # Parámetros de control proporcional
        self.sp_temp = sp_temp
        self.kp_temp = kp_temp
        self.sp_hum = sp_hum
        self.kp_hum = kp_hum
        
        # Variables para manejo del tiempo acelerado
        self.tiempo_simulado = datetime.datetime.now()
        self.ultimo_tick = datetime.datetime.now()
        self.multiplicador_tiempo = 1.0
        self.tiempo_manual = False
        self.salto_temporal = False
        self.dia_virtual = 1
        
    def registrar_lectura(self, dia_virtual, fecha_sim, t, h, v_pct, r_pct, luz, intensidad_luz, calef_pct=0, malla=False):
        """
        Delega la escritura de una fila al GestorPersistencia.

        Se llama desde la interfaz cada 5 segundos reales para no saturar el CSV.
        """
        self.persistencia.registrar_lectura(dia_virtual, fecha_sim, t, h, v_pct, r_pct, luz, intensidad_luz, calef_pct, malla)
        
    def obtener_historial_paginado(self, pagina, limite=50):
        """
        Retorna una página del historial CSV.

        Returns:
            tuple: (lista_registros, total_paginas, total_registros)
        """
        return self.persistencia.obtener_historial_paginado(pagina, limite)
        
    def fijar_hora_manual(self, hora, minuto=0):
        """
        Salta el reloj virtual a una hora específica del día.

        Si la hora destino es menor que la actual, se asume que avanzamos
        al día siguiente (el tiempo es irreversible). Resetea ultimo_tick
        para evitar que el siguiente dt_sec sea gigantesco.

        Args:
            hora   (int | str): Hora destino (0–23).
            minuto (int):       Minuto destino. Default 0.
        """
        # Si saltamos a una hora "anterior" a la actual, asumimos que avanzamos al día siguiente
        hora_int = int(hora)
        if hora_int < self.tiempo_simulado.hour:
            self.dia_virtual += 1
            self.tiempo_simulado += datetime.timedelta(days=1)
            
        # Al saltar en el tiempo, reemplazamos la hora de forma instantánea sin bucles
        self.tiempo_simulado = self.tiempo_simulado.replace(hour=hora_int, minute=int(minuto), second=0)
        # CRÍTICO: Resetear ultimo_tick de inmediato. 
        # Esto previene que el dt_sec de la próxima llamada a procesar() 
        # sea gigantesco e intente compensar todo el tiempo "perdido" congelando el programa.
        self.ultimo_tick = datetime.datetime.now()
        self.tiempo_manual = False
        self.salto_temporal = True
        
    def activar_tiempo_automatico(self):
        """
        Reactiva el avance automático del reloj virtual y reinicia los
        contadores del ciclo PWM.
        """
        self.tiempo_manual = False
        self.ultimo_tick = datetime.datetime.now()
        
        # Parámetros PWM
        self.periodo_pwm = 5
        self.tick_pwm = 0

    def procesar(self):
        """
        Ciclo principal de control. Se ejecuta en cada tick del timer de la GUI.

        Pasos:
            1. Calcula dt_sec (tiempo real transcurrido, máx. 0.5 s).
            2. Avanza el reloj virtual según el multiplicador de tiempo.
            3. Actualiza el motor climático exterior.
            4. Calcula luz natural (curva solar) y artificial (LED).
            5. Aplica control proporcional a calefacción y ventilador.
            6. Aplica histéresis (tiempos muertos) a riego y deshumidificación.
            7. Aplica rampa suave (soft-start) a todos los actuadores.
            8. Integra los deltas termodinámicos sobre los sensores.

        Returns:
            tuple: (hora_actual, t, h, luz, v_on, r_on, il_int, calef_on,
                    calef_pot, crecimiento, alerta, pronostico, t_ext, h_ext,
                    esf_v, esf_r, esf_il, esf_c, estado_fotoperiodo)
        """
        ahora = datetime.datetime.now()
        # Limitar dt_sec a 0.5 s para evitar explosiones termodinámicas por lag
        dt_sec = min(0.5, (ahora - self.ultimo_tick).total_seconds())
        self.ultimo_tick = ahora
        
        if not getattr(self, 'tiempo_manual', False):
            dia_previo = self.tiempo_simulado.day
            # Avanzar el reloj virtual: dt_sec real × multiplicador de velocidad
            self.tiempo_simulado += datetime.timedelta(seconds=dt_sec * self.multiplicador_tiempo)
            # Detectar cambio de día para incrementar el contador de Días Virtuales
            if self.tiempo_simulado.day != dia_previo:
                self.dia_virtual += 1
            
        hora_actual = self.tiempo_simulado
        
        # 1. Actualizar clima exterior y obtener pronóstico (Omitir inercia si hay salto)
        salto = getattr(self, 'salto_temporal', False)
        self.motor_clima.actualizar_clima(hora_actual, salto_temporal=salto)
        
        # 2. Ciclo Día/Noche y Luz Natural Base
        es_de_dia = 6 <= hora_actual.hour < 18
        estado_fotoperiodo = 0 <= hora_actual.hour < 7 # Descanso de 00:00 a 07:00
        
        if es_de_dia:
            # Curva Solar ligada matemáticamente a la curva de temperatura exterior
            hora_f = hora_actual.hour + (hora_actual.minute / 60.0)
            if 6.0 <= hora_f < 12.0:
                frac = (hora_f - 6.0) / 6.0
                factor_diario = -1.0 + math.sin(frac * math.pi / 2) * 2.0
            elif 12.0 <= hora_f <= 15.0:
                frac = (hora_f - 12.0) / 3.0
                factor_diario = 1.0 - (0.1 * frac)
            elif 15.0 < hora_f <= 18.0:
                frac = (hora_f - 15.0) / 3.0
                factor_diario = -1.0 + 1.9 * math.cos(frac * math.pi / 2)
            else:
                factor_diario = -1.0
                
            # factor_diario va de -1.0 a 1.0. Convertimos a porcentaje de 0.0 a 1.0
            factor_solar = max(0.0, (factor_diario + 1.0) / 2.0)
            
            # Hacemos que la luz sea más sensible y caiga un poco antes que el calor residual
            factor_solar = factor_solar ** 1.5
            
            lux_por_clima = {
                "Soleado":    60000.0,
                "Nublado":    22000.0,
                "Día Opaco":  8000.0,
                "Lluvia":     4500.0,
                "Tormenta":   2000.0,
                "Frío":       6000.0,
                "Despejado":  60000.0,  # Noche despejada: luz solar=0 porque es_de_dia es False
            }
            max_lux = lux_por_clima.get(self.motor_clima.estado_actual, 10000.0)
                
            luz_natural = (factor_solar * max_lux) + random.uniform(-500, 500)
            luz_natural = max(0.0, luz_natural)
        else:
            # Durante la noche la luz no es 0 total, simulamos la luz de la luna o resplandor ambiente (~25 Lx a 40 Lx)
            luz_natural = 25.0 + random.uniform(0.0, 15.0)
            
        # 3. Lógica de Control Proporcional (Potencia Objetivo o Esfuerzo)
        t_actual = self.temp.valor
        h_actual = self.hum.valor
        
        t_ext_actual = self.motor_clima.temp_exterior
        
        # --- Malla de Sombreo (Polisombra 50% Automática) ---
        # Lógica de histéresis amplia para evitar oscilaciones
        if not self.malla_desplegada:
            # Desplegar si la temperatura interior es alta, hay mucha luz solar Y la temperatura exterior justifica no solo ventilar
            if t_actual > 27.0 and luz_natural > 35000.0 and t_ext_actual > 25.0:
                self.malla_desplegada = True
        else:
            # Recoger si la temperatura interior está controlada, bajó la luz o afuera refrescó lo suficiente
            if t_actual < 25.0 or luz_natural < 20000.0 or t_ext_actual <= 24.0:
                self.malla_desplegada = False
                
        # Impacto físico INMEDIATO de la malla en la luz:
        if self.malla_desplegada:
            luz_natural *= 0.25  # Transmitancia del 25% (Malla aluminizada al 75%)
            
        # Al reducirse luz_natural, el 'calor_solar' bajará, pero además aplicaremos
        # un corte térmico directo más abajo para detener el efecto invernadero.
        
        # --- Iluminación LED (Suplemento Lumínico con Histéresis) ---
        crecimiento = self.planta.porcentaje_crecimiento
        
        # Definimos los umbrales de histéresis para cada etapa
        if crecimiento <= 20: # Etapa Semilla / Brote
            lux_encendido = 13000.0
            lux_apagado = 15000.0
            requisito_ideal_lux = 10000.0
        elif crecimiento <= 70: # Etapa Vegetativa
            lux_encendido = 27000.0
            lux_apagado = 29000.0
            requisito_ideal_lux = 25000.0
        else: # Etapa Floración / Fructificación
            lux_encendido = 47000.0
            lux_apagado = 50000.0
            requisito_ideal_lux = 45000.0
            
        max_aporte_led = 45000.0
        
        if estado_fotoperiodo:
            self.iluminando = False
            self.iluminacion.esfuerzo = 0.0
        else:
            # Lógica de "Tiempo Muerto" (Histéresis)
            if not self.iluminando:
                if luz_natural < lux_encendido:
                    self.iluminando = True
            else:
                if luz_natural > lux_apagado:
                    self.iluminando = False
                    
            if self.iluminando:
                if luz_natural < requisito_ideal_lux:
                    diferencia = requisito_ideal_lux - luz_natural
                    esfuerzo = (diferencia / max_aporte_led) * 100.0
                    self.iluminacion.esfuerzo = max(10.0, min(100.0, esfuerzo))
                else:
                    # Mantenimiento mínimo mientras está en la zona de tiempo muerto (entre encendido y apagado)
                    self.iluminacion.esfuerzo = 10.0
            else:
                self.iluminacion.esfuerzo = 0.0
            
        # --- Temperatura: Calefacción y Ventilador ---
        setpoint_calefaccion = 22.0
        
        t_ext = self.motor_clima.temp_exterior
        
        # Setpoint dinámico de ventilación
        # Se armoniza con la temperatura exterior para evitar ventilación excesiva si afuera ya hace buen clima
        if self.motor_clima.estado_actual in ["Frío", "Tormenta", "Lluvia"] or t_ext < 16.0:
            setpoint_vent = 30.0
        else:
            # Si afuera hace 25°C, permitimos que el invernadero esté unos grados por encima 
            # del clima exterior antes de encender ventiladores a toda marcha.
            setpoint_vent = max(28.0, t_ext + 4.0)
        
        # Calefacción (Estabilidad y Estado Estacionario)
        if t_actual < setpoint_calefaccion:
            error_frio = setpoint_calefaccion - t_actual
            # Si el error es grande, pide mucha potencia. Al acercarse a 0, se estabiliza en ~15%
            self.calefaccion.esfuerzo = min(100.0, 15.0 + (error_frio * 25.0))
        elif t_actual < setpoint_calefaccion + 1.0:
            # Banda de transición suave para que no caiga a 0 bruscamente
            error_exceso = t_actual - setpoint_calefaccion
            self.calefaccion.esfuerzo = max(0.0, 15.0 - (error_exceso * 15.0))
        else:
            self.calefaccion.esfuerzo = 0.0
            
        # Ventilador (Setpoints fijos solicitados con amplio tiempo muerto)
        if getattr(self, 'malla_desplegada', False):
            setpoint_encendido = 28.0
            setpoint_apagado = 25.0
        else:
            # Sin malla: enciende a 28°C y apaga hasta los 24°C (histéresis de 4°C)
            setpoint_encendido = 28.0
            setpoint_apagado = 24.0
        
        if not self.enfriando:
            if t_actual > setpoint_encendido:
                self.enfriando = True
        else:
            if t_actual < setpoint_apagado:
                self.enfriando = False
                
        if self.enfriando:
            error_calor = t_actual - setpoint_apagado
            # Mantener un mínimo de 15% de esfuerzo asegura que el ventilador no se pare antes de llegar al apagado
            self.vent.esfuerzo = max(15.0, min(100.0, error_calor * 25.0))
        else:
            self.vent.esfuerzo = 0.0
            
        # Corrección de humedad por ventilador (Histéresis / Tiempo Muerto para evitar oscilaciones locas)
        # 1. Lógica de activación/desactivación del estado de deshumidificación
        if not self.deshumidificando:
            # Encender solo si superamos un umbral crítico (73%) Y afuera está frío para asegurar secado psicrométrico
            if h_actual > 73.0 and t_ext < (t_actual - 2.0):
                self.deshumidificando = True
        else:
            # Apagar solo cuando logremos bajar a un nivel óptimo y seguro (65%) o si afuera dejó de hacer frío
            if h_actual < 65.0 or t_ext >= (t_actual - 2.0):
                self.deshumidificando = False
                
        # 2. Aplicación del esfuerzo si la deshumidificación está activa
        if self.deshumidificando:
            # Esfuerzo proporcional a cuánto excedemos el rango óptimo del 65%
            esfuerzo_ext_hum = (h_actual - 65.0) * 10.0
            self.vent.esfuerzo = max(self.vent.esfuerzo, min(100.0, esfuerzo_ext_hum))
            
        # --- Bomba de Riego ---
        # Histéresis estricta irrompible (ON a < 45%, OFF a >= 63%)
        if h_actual < 45.0:
            self.riego.esfuerzo = 100.0
        elif h_actual >= 63.0:
            self.riego.esfuerzo = 0.0
        # Si está entre 45% y 63%, se mantiene el esfuerzo del ciclo anterior.

        # 4. Inercia Mecánica Estricta (Soft-Start / Spin-Down)
        # ── Rampa suave (Soft-Start / Spin-Down) ────────────────────────────────
        # Evita que los actuadores salten bruscamente entre 0% y 100%.
        # Cada ciclo, la potencia real solo puede cambiar ±5% respecto al ciclo anterior.
        # Esto protege los motores de picos de corriente y hace la simulación más realista.
        def ramp_up(potencia_actual, potencia_objetivo, max_delta):
            if getattr(self, 'salto_temporal', False):
                return potencia_objetivo
            if potencia_actual < potencia_objetivo:
                return min(potencia_objetivo, potencia_actual + max_delta)
            elif potencia_actual > potencia_objetivo:
                return max(potencia_objetivo, potencia_actual - max_delta)
            return potencia_actual
            
        max_delta_por_ciclo = 5.0  # Los motores suben/bajan máximo 5% por ciclo
        
        # La luz LED no tiene inercia mecánica, se enciende y apaga de forma instantánea
        self.iluminacion.intensidad = self.iluminacion.esfuerzo
        self.iluminacion.encendido = self.iluminacion.intensidad > 0
        
        self.calefaccion.potencia = ramp_up(self.calefaccion.potencia, self.calefaccion.esfuerzo, max_delta_por_ciclo)
        self.calefaccion.encendido = self.calefaccion.potencia > 0
        
        self.vent.potencia = ramp_up(self.vent.potencia, self.vent.esfuerzo, max_delta_por_ciclo)
        self.vent.encendido = self.vent.potencia > 0
        
        # La bomba de riego tiene un apagado más rápido para que la animación termine en 2-3 segs
        max_delta_riego = 20.0 if self.riego.esfuerzo < self.riego.potencia else max_delta_por_ciclo
        self.riego.potencia = ramp_up(self.riego.potencia, self.riego.esfuerzo, max_delta_riego)
        self.riego.encendido = self.riego.potencia > 0
        
        if getattr(self, 'salto_temporal', False):
            # Forzamos un equilibrio físico instantáneo para que el usuario no tenga que esperar
            # a que el invernadero se caliente o enfríe tras un "viaje en el tiempo" drástico.
            t_ext_actual = self.motor_clima.temp_exterior
            h_ext_actual = self.motor_clima.hum_exterior
            if es_de_dia and luz_natural > 20000.0:
                self.temp.valor = t_ext_actual + 3.0  # Calor solar simulado instantáneo
                self.hum.valor = max(30.0, h_ext_actual - 5.0)
            else:
                self.temp.valor = t_ext_actual + 1.0  # Ligeramente más cálido por aislamiento
                self.hum.valor = h_ext_actual
                
            self.salto_temporal = False

        # 5. Inercia Física Termodinámica (Deltas acumulativos)
        # ── Inercia física termodinámica ─────────────────────────────────────────
        # factor_inercia escala todos los deltas al tiempo simulado transcurrido.
        # Así, a mayor velocidad de simulación, el efecto térmico es proporcional.
        dt_simulado = dt_sec * self.multiplicador_tiempo
        factor_inercia = max(0.1, dt_simulado / 2.0)
        
        delta_temp = 0.0
        delta_hum = 0.0
        
        t_ext = self.motor_clima.temp_exterior
        h_ext = self.motor_clima.hum_exterior
        
        # A. Inercia pasiva (Fugas térmicas del invernadero hacia el exterior)
        # Aumentamos la disipación térmica (de 0.032 a 0.08) para que el invernadero
        # mantenga su temperatura mucho más ligada a la exterior (menor brecha / delta).
        delta_temp += (t_ext - t_actual) * 0.08 * factor_inercia
        # Infiltración pasiva de humedad: muy reducida en días calurosos (invernadero bien sellado).
        # En días fríos/lluviosos hay algo más de filtración natural.
        if t_ext > 28.0:
            factor_infiltracion_hum = 0.001  # Prácticamente sellado en calor extremo
        else:
            factor_infiltracion_hum = 0.005  # Sellado normal en días frescos
        delta_hum += (h_ext - h_actual) * factor_infiltracion_hum * factor_inercia
        
        if not es_de_dia:
            frio_noche = 0.6 * factor_inercia
            delta_temp -= frio_noche
            
        # B. Calor Solar (Efecto Invernadero)
        if es_de_dia:
            # Las nubes bloquean la radiación infrarroja (calor) mucho más que la luz visible.
            # Este multiplicador asegura que en días nublados el invernadero no se caliente como un horno.
            atenuacion_ir = {
                "Soleado":    1.0,
                "Nublado":    0.3,
                "Día Opaco":  0.15,
                "Lluvia":     0.05,
                "Tormenta":   0.02,
                "Frío":       0.2,
                "Despejado":  1.0,
            }
            factor_ir = atenuacion_ir.get(self.motor_clima.estado_actual, 1.0)
            
            # El multiplicador original de 4.5 provocaba un aumento antinatural a 33°C a las 10 a.m.
            # Se ha bajado a 0.8, generando un delta máximo térmico realista de ~15 a 20°C sobre la temp ambiente.
            calor_solar = (luz_natural / 60000.0) * 0.8 * factor_ir
            
            # Corte de Energía Térmica por la Malla de Sombreo
            if self.malla_desplegada:
                calor_solar *= 0.15  # Corta drásticamente el calor radiante (85% de bloqueo térmico)
                
            delta_temp += calor_solar * factor_inercia
            
        # C. Impacto Realista de los Actuadores
        # LED (Calor residual)
        luz_aportada = max_aporte_led * (self.iluminacion.intensidad / 100.0)
        calor_led = (self.iluminacion.intensidad / 100.0) * 0.05 * factor_inercia
        delta_temp += calor_led
        
        # Calefacción (Calor primario potente)
        # Capacidad de calefacción incrementada a 3.5 para contrarrestar heladas exteriores extremas holgadamente.
        pot_c = self.calefaccion.potencia / 100.0
        delta_temp += pot_c * 3.5 * factor_inercia
        delta_hum -= pot_c * 0.5 * factor_inercia
        
        # Ventilador (Extracción e intercambio de aire con Panel Evaporativo 'Pad & Fan')
        if self.vent.potencia > 0:
            pot_v = self.vent.potencia / 100.0
            
            # --- Enfriamiento Suave e Inteligente ---
            # Si el invernadero ya está fresco (ej. en un día lluvioso donde el ventilador prende por humedad),
            # apagamos el "poder extra" de enfriamiento para no congelarlo y chocar con la calefacción.
            poder_enfriamiento = 0.5 
            if t_actual > 25.0:
                poder_enfriamiento = 2.0  # Enfriamiento estándar suave
                if getattr(self, 'malla_desplegada', False):
                    poder_enfriamiento = 2.8  # Un poco más fuerte si hay malla, para sostener 25-27°C sin caídas bruscas
                    
            if t_actual > 23.0:
                delta_temp -= poder_enfriamiento * pot_v * factor_inercia
            
            # Intercambio de aire térmico
            # El panel evaporativo solo "enfría" el aire entrante si afuera hace mucho calor.
            temp_aire_entrante = t_ext
            if t_ext > 26.0 and t_actual > 25.0:
                temp_aire_entrante = 26.0 + (t_ext - 26.0) * 0.4  # Si afuera hace 40, entra a ~31°C
                
            delta_temp += (temp_aire_entrante - t_actual) * 0.3 * pot_v * factor_inercia
            
            # --- Extracción de Humedad (Modo Inteligente) ---
            # El ventilador NO debe secar el invernadero en días calurosos.
            # En un invernadero real, al abrir ventilación en días de 40°C y baja humedad exterior,
            # el buen aislamiento evita que la humedad interior escape fácilmente.
            if self.deshumidificando:
                # MODO DESHUMIDIFICACIÓN ACTIVA: el ventilador seca con fuerza
                # (Solo se activa si hay exceso real de humedad Y afuera está más frío)
                poder_secado = max(1.0, min(3.0, (t_actual - t_ext) / 5.0))
                delta_hum -= 2.5 * pot_v * poder_secado * factor_inercia
            elif t_ext < t_actual - 5.0:
                # Hay una gran diferencia térmica: algo de desecación pasiva ocurre (efecto natural)
                delta_hum -= 0.5 * pot_v * factor_inercia
            else:
                # Días calurosos: el ventilador extrae calor pero también introduce aire exterior.
                # Para evitar que la humedad se desplome de golpe, usamos un coeficiente sumamente bajo (0.006).
                # Aseguramos que el ventilador NUNCA inyecte humedad (si afuera está más húmedo, no hace nada).
                cambio_hum = (h_ext - h_actual) * 0.006 * pot_v * factor_inercia
                if cambio_hum < 0:
                    delta_hum += cambio_hum
            
        # Bomba de Riego (Inercia Hídrica: suma constante y firme)
        if self.riego.potencia > 0:
            pot_r = self.riego.potencia / 100.0
            delta_hum += 8.0 * pot_r * factor_inercia  # Subida contundente para escalar holgadamente hasta 63%
            delta_temp -= 0.5 * pot_r * factor_inercia # Enfriamiento evaporativo
            
        # D. Relación higrotérmica natural cruzada (con transpiración vegetal)
        # Cuando el aire se calienta, la humedad relativa tiende a bajar, pero las plantas transpiran
        # vapor de agua compensando la pérdida y ayudando a mantener la humedad en días calurosos.
        if delta_temp > 0:
            delta_hum -= (delta_temp * 0.25)  # Atenuado de 1.0 a 0.25 para simular transpiración
        else:
            delta_hum -= (delta_temp * 0.4)   # Al bajar la temp, la humedad relativa sube
            
        # Aplicación suave de inercia
        t_actual += delta_temp
        h_actual += delta_hum
        
        self.temp.valor = max(10.0, min(50.0, t_actual))
        self.hum.valor  = max(0.0,  min(100.0, h_actual))
        
        # 6. Luz Total Percibida y Retornos de Estado
        luz_total_percibida = luz_natural + luz_aportada
        self.luz.valor = luz_total_percibida
        
        t = self.temp.leer_valor()
        h = self.hum.leer_valor()
        
        pronostico = self.motor_clima.generar_pronostico(hora_actual)
        alerta = self.planta.evaluar_condiciones(t, h, luz=luz_total_percibida, multiplicador=self.multiplicador_tiempo, es_de_dia=es_de_dia, estado_fotoperiodo=estado_fotoperiodo)
        
        t_ext = round(self.motor_clima.temp_exterior, 1)
        h_ext = round(self.motor_clima.hum_exterior, 1)
        
        return hora_actual, t, h, round(luz_total_percibida, 2), self.vent.encendido, self.riego.encendido, round(self.iluminacion.intensidad, 2), self.calefaccion.encendido, round(self.calefaccion.potencia, 2), self.planta.porcentaje_crecimiento, alerta, pronostico, t_ext, h_ext, self.vent.esfuerzo, self.riego.esfuerzo, self.iluminacion.esfuerzo, self.calefaccion.esfuerzo, estado_fotoperiodo
        h_ext = round(self.motor_clima.hum_exterior, 1)
        
        return hora_actual, t, h, round(luz_total_percibida, 2), self.vent.encendido, self.riego.encendido, round(self.iluminacion.intensidad, 2), self.calefaccion.encendido, round(self.calefaccion.potencia, 2), self.planta.porcentaje_crecimiento, alerta, pronostico, t_ext, h_ext, self.vent.esfuerzo, self.riego.esfuerzo, self.iluminacion.esfuerzo, self.calefaccion.esfuerzo, estado_fotoperiodo
