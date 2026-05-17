import random
import math

class Sensor:
    """Clase base para los sensores del invernadero."""
    def __init__(self, nombre, unidad, valor_inicial):
        self.nombre = nombre
        self.unidad = unidad
        self.valor = valor_inicial

    def leer_valor(self):
        # Simulamos una pequeña fluctuación natural del ambiente.
        # BUG CORREGIDO: la fluctuación se suma a una copia local, NO al valor base.
        # Antes, cada llamada a leer_valor() desplazaba self.valor permanentemente,
        # causando una deriva (drift) ilimitada de los sensores con el tiempo.
        fluctuacion = random.uniform(-0.5, 0.5)
        return round(self.valor + fluctuacion, 2)

class Actuador:
    """Clase base para los actuadores (Ventilador, Riego, etc.)."""
    def __init__(self, nombre):
        self.nombre = nombre
        self.encendido = False
        self.potencia = 0.0
        self.esfuerzo = 0.0

    def alternar(self, estado: bool):
        self.encendido = estado
        self.potencia = 100.0 if estado else 0.0

    def ajustar_potencia(self, valor: float):
        # Limitamos la potencia entre 0 y 100
        self.potencia = max(0.0, min(100.0, float(valor)))
        self.encendido = self.potencia > 0

    def __str__(self):
        estado_str = "Encendido" if self.encendido else "Apagado"
        return f"{self.nombre}: {estado_str} ({self.potencia:.1f}%)"

class Planta:
    """Clase para simular el crecimiento y estado de estrés fisiológico de la planta."""
    def __init__(self):
        self.porcentaje_crecimiento = 0.0

    def evaluar_condiciones(self, temp, hum, luz=None, multiplicador=1.0, es_de_dia=True):
        """
        Evalúa las condiciones ambientales y actualiza el crecimiento basándose en
        principios de fisiología vegetal:
        - Temperatura alta (>30°C): Cierre estomático, detiene la fotosíntesis,
          riesgo de deshidratación y estrés térmico.
        - Humedad alta (>80%): Baja tasa de transpiración, condensación foliar,
          favorece aparición de patógenos fúngicos (ej. Botrytis).
        - Humedad baja (<40%): Aumenta el déficit de presión de vapor, 
          causando pérdida excesiva de agua y estrés hídrico.
        - Temperatura óptima (22-26°C): Tasa fotosintética máxima, crecimiento activo.
        - Luz óptima (4000-7000 Lux combinando natural y artificial): Crecimiento normal.
        - Luz baja (< 2000 Lux): Advertencia "Luz insuficiente: Riesgo de etiolación".
        - Luz excesiva (> 8500 Lux): Advertencia "Radiación crítica: Estrés lumínico".
        """
        alerta = ""
        
        # Validaciones de estrés (prioridad biológica)
        if temp > 30.0:
            alerta = "Peligro de deshidratación y estrés térmico"
        elif hum > 80.0:
            alerta = "Riesgo de proliferación de patógenos fúngicos (ej. Botrytis)"
        elif hum < 40.0:
            alerta = "Transpiración excesiva, estrés hídrico inminente"
        elif luz is not None and luz < 2000 and es_de_dia:
            alerta = "Luz insuficiente: Riesgo de etiolación"
        elif luz is not None and luz > 18500:
            alerta = "Radiación crítica: Estrés lumínico"

        # Simulación de crecimiento
        # BUG CORREGIDO: antes, el estrés no tenía efecto sobre el crecimiento acumulado.
        # Ahora, condiciones de estrés activo frenan y revierten levemente el crecimiento,
        # modelando el consumo de reservas energéticas de la planta bajo estrés fisiológico.
        if alerta:
            self.porcentaje_crecimiento -= 0.02 * multiplicador  # Regresión leve por estrés
        else:
            if 18.0 <= temp <= 25.0 and (luz is None or 4000 <= luz <= 7000):
                self.porcentaje_crecimiento += 0.05 * multiplicador # Crecimiento óptimo
            else:
                self.porcentaje_crecimiento += 0.01 * multiplicador # Crecimiento subóptimo
                
        # Límites biológicos del ciclo de vida
        self.porcentaje_crecimiento = max(0.0, min(100.0, self.porcentaje_crecimiento))
            
        return alerta

class MotorClimatico:
    """Motor encargado de generar un estado del clima y su pronóstico."""
    def __init__(self):
        self.climas = ["Soleado", "Nublado", "Frío"]
        self.estado_actual = random.choice(self.climas)
        self.clima_siguiente_dia = random.choice(self.climas)
        self.temp_exterior = 25.0
        self.hum_exterior = 60.0
    
    def actualizar_clima(self, hora_actual):
        # 5% de probabilidad de cambio de clima en cada ciclo
        if random.random() < 0.05:
            self.estado_actual = random.choice(self.climas)
            self.clima_siguiente_dia = random.choice(self.climas)
        self.actualizar_clima_exterior(hora_actual)
            
    def actualizar_clima_exterior(self, hora_actual):
        hora = hora_actual.hour
        
        # 1. Determinar valores de clima de fondo
        if self.estado_actual == "Soleado":
            temp_base = 33.0
            hum_base = 35.0
        elif self.estado_actual == "Nublado":
            temp_base = 22.0
            hum_base = 65.0
        else: # Frío
            temp_base = 10.0
            hum_base = 80.0
            
        # 2. Ciclo Diario de Temperatura (el pico de calor exterior es a las 14:00 (2:00 PM))
        oscilacion_temp = 7.0 if self.estado_actual == "Soleado" else 4.0
        # math.cos((hora - 14) * 2 * math.pi / 24) oscila de 1.0 (a las 14:00) a -1.0 (a las 02:00)
        factor_diario = math.cos((hora - 14) * 2 * math.pi / 24)
        
        self.temp_exterior = temp_base + factor_diario * oscilacion_temp + random.uniform(-0.5, 0.5)
        # La humedad exterior oscila en sentido inverso a la temperatura (relación higrotérmica natural)
        self.hum_exterior = hum_base - factor_diario * (oscilacion_temp * 1.5) + random.uniform(-1.0, 1.0)
        
        # Límites reales de física exterior
        self.temp_exterior = max(-5.0, min(48.0, self.temp_exterior))
        self.hum_exterior = max(10.0, min(100.0, self.hum_exterior))

    def generar_pronostico(self, hora_actual):
        # Determinamos el periodo del día
        hora = hora_actual.hour
        
        # Etiqueta del clima actual con emojis representativos
        iconos = {
            "Soleado": "☀️ Soleado",
            "Nublado": "☁️ Nublado",
            "Frío": "❄️ Frío"
        }
        icono_actual = iconos.get(self.estado_actual, "🌡️")
        
        # Pronóstico dinámico profesional
        if 6 <= hora < 12:
            # Mañana (06:00 AM - 11:59 AM)
            if self.estado_actual == "Soleado":
                detalle = "Mañana despejada. Radiación solar intensa con incremento térmico rápido."
            elif self.estado_actual == "Nublado":
                detalle = "Mañana cubierta. Radiación natural atenuada por nubes densas."
            else:  # Frío
                detalle = "Mañana gélida. Baja radiación natural con viento helado del exterior."
            
            pronostico = f"📅 Clima de Hoy ({icono_actual}): {detalle}"
            
        elif 12 <= hora < 18:
            # Mediodía / Tarde (12:00 PM - 05:59 PM) - Sol Cenital
            if self.estado_actual == "Soleado":
                detalle = "Sol Cenital. Máxima radiación fotosintética activa y alta carga térmica exterior."
            elif self.estado_actual == "Nublado":
                detalle = "Tarde templada. Sol cenital bloqueado por nubes, aporte lumínico moderado."
            else:  # Frío
                detalle = "Tarde fría. Radiación reducida con mínima absorción de calor ambiental."
                
            pronostico = f"📅 Clima de Hoy ({icono_actual}): {detalle}"
            
        else:
            # Noche (06:00 PM - 05:59 AM) - Pronóstico para el día siguiente
            icono_siguiente = iconos.get(self.clima_siguiente_dia, "🌡️")
            
            # Estimación de temperatura nocturna mínima
            if self.clima_siguiente_dia == "Soleado":
                est_noche = "Noche despejada y fresca, estimación mínima estable de 15.0°C."
            elif self.clima_siguiente_dia == "Nublado":
                est_noche = "Noche templada y húmeda, estimación mínima de 16.5°C."
            else:  # Frío
                est_noche = "Noche gélida, estimación mínima por debajo de 12.0°C."
                
            pronostico = (
                f"🌙 {est_noche}\n"
                f"🔮 Pronóstico Mañana ({icono_siguiente}): Se prevé transición a día {self.clima_siguiente_dia.lower()}."
            )
            
        return pronostico

# Clases específicas que hereden de las bases
class SensorTemperatura(Sensor):
    def __init__(self, valor_inicial=25.0):
        super().__init__("Temperatura", "°C", valor_inicial)

class SensorHumedad(Sensor):
    def __init__(self, valor_inicial=60.0):
        super().__init__("Humedad", "%", valor_inicial)

class Ventilador(Actuador):
    def __init__(self):
        super().__init__("Ventilador")

class SensorLuminosidad(Sensor):
    def __init__(self, valor_inicial=0.0):
        super().__init__("Luminosidad", "Lux", valor_inicial)

    def leer_valor(self):
        """
        BUG CORREGIDO: El método original requería 'hora_actual' como argumento,
        pero el Controlador llama a leer_valor() sin argumentos (interfaz heredada
        de la clase base Sensor). Esto causaba un TypeError silencioso.
        El Controlador ya gestiona la lógica Día/Noche directamente en self.luz.valor,
        así que aquí sólo añadimos la fluctuación de sensor sin mutar self.valor.
        """
        fluctuacion = random.uniform(-50, 50)
        return round(max(0.0, self.valor + fluctuacion), 2)

class BombaRiego(Actuador):
    def __init__(self): super().__init__("Bomba de Riego")

class SistemaIluminacion(Actuador):
    def __init__(self):
        super().__init__("Sistema de Iluminación")
        self.intensidad = 0.0  # de 0 a 100%
class Calefaccion:
    def __init__(self):
        self.encendido = False
        self.potencia = 0.0  # Irá de 0.0 a 100.0 (Proporcional)
        self.esfuerzo = 0.0

    def alternar(self, estado):
        self.encendido = estado