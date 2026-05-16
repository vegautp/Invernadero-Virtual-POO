import random

class EntidadInvernadero:
    def __init__(self, nombre):
        self.nombre = nombre

class Sensor(EntidadInvernadero):
    def __init__(self, nombre, unidad, valor_inicial):
        super().__init__(nombre)
        self.unidad = unidad
        self.valor = valor_inicial

    def leer_valor(self):
        # Simula cambios aleatorios para la prueba
        self.valor += random.uniform(-0.8, 0.8)
        return round(self.valor, 2)

class Actuador(EntidadInvernadero):
    def __init__(self, nombre):
        super().__init__(nombre)
        self.activo = False

    def alternar(self, estado: bool):
        self.activo = estado

class SensorTemperatura(Sensor):
    def __init__(self): super().__init__("Temperatura", "°C", 24.0)

class SensorHumedad(Sensor):
    def __init__(self): super().__init__("Humedad", "%", 60.0)

class Ventilador(Actuador):
    def __init__(self): super().__init__("Ventilador")

class BombaRiego(Actuador):
    def __init__(self): super().__init__("Bomba de Riego")