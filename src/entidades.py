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

    def alternar(self, estado: bool):
        self.encendido = estado

    def __str__(self):
        estado_str = "Encendido" if self.encendido else "Apagado"
        return f"{self.nombre}: {estado_str}"

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

class BombaRiego(Actuador):
    def __init__(self): super().__init__("Bomba de Riego")
