import random

class Sensor:
    """Clase base para los sensores del invernadero."""
    def __init__(self, nombre, unidad, valor_inicial):
        self.nombre = nombre
        self.unidad = unidad
        self.valor = valor_inicial

    def leer_valor(self):
        # Simulamos una pequeña fluctuación natural del ambiente
        fluctuacion = random.uniform(-0.5, 0.5)
        self.valor += fluctuacion
        return round(self.valor, 2)

class Actuador:
    """Clase base para los actuadores (Ventilador, Riego, etc.)."""
    def __init__(self, nombre):
        self.nombre = nombre
        self.encendido = False
        self.potencia = 0.0

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

    def evaluar_condiciones(self, temp, hum, luz=None):
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
        elif luz is not None and luz < 2000:
            alerta = "Luz insuficiente: Riesgo de etiolación"
        elif luz is not None and luz > 8500:
            alerta = "Radiación crítica: Estrés lumínico"

        # Simulación de crecimiento
        if not alerta:
            if 22.0 <= temp <= 26.0 and (luz is None or 4000 <= luz <= 7000):
                self.porcentaje_crecimiento += 0.05 # Crecimiento óptimo (lento y realista)
            else:
                self.porcentaje_crecimiento += 0.01 # Crecimiento subóptimo (lento y realista)
                
        # Limitar el crecimiento al 100%
        if self.porcentaje_crecimiento > 100.0:
            self.porcentaje_crecimiento = 100.0
            
        return alerta

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

    def leer_valor(self, hora_actual):
        """
        Simula la luz solar basándose en la hora actual del reloj.
        Amanecer a las 06:00 y Ocaso a las 18:00 (06:00 PM).
        """
        if 6 <= hora_actual.hour < 18:
            # Día: Simular luz solar natural (ej. 4000 a 8000 Lux)
            self.valor = random.uniform(4000, 8000)
        else:
            # Noche
            self.valor = 0.0
            
        # Añadir pequeña fluctuación aleatoria simulando nubes, etc.
        fluctuacion = random.uniform(-50, 50)
        self.valor += fluctuacion
        
        # Evitar Lux negativo
        if self.valor < 0:
            self.valor = 0.0
            
        return round(self.valor, 2)

class BombaRiego(Actuador):
    def __init__(self): super().__init__("Bomba de Riego")

class SistemaIluminacion(Actuador):
    def __init__(self):
        super().__init__("Sistema de Iluminación")
        self.intensidad = 0.0  # de 0 a 100%
