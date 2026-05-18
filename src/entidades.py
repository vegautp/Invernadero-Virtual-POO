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

    def evaluar_condiciones(self, temp, hum, luz=None, multiplicador=1.0, es_de_dia=True, estado_fotoperiodo=False):
        """
        Evalúa las condiciones ambientales y actualiza el crecimiento basándose en
        principios de fisiología vegetal.
        """
        alerta = ""
        
        # Requerimientos Dinámicos según Etapa
        if self.porcentaje_crecimiento <= 20:
            ideal_lux = 10000.0
        elif self.porcentaje_crecimiento <= 70:
            ideal_lux = 25000.0
        else:
            ideal_lux = 45000.0
            
        limite_estres_lux = 65000.0
        
        # Validaciones de estrés (prioridad biológica)
        if temp > 30.0:
            alerta = "Peligro de deshidratación y estrés térmico"
        elif hum > 80.0:
            alerta = "Riesgo de proliferación de patógenos fúngicos (ej. Botrytis)"
        elif hum < 40.0:
            alerta = "Transpiración excesiva, estrés hídrico inminente"
        elif luz is not None and luz > limite_estres_lux:
            alerta = "Peligro: Estrés lumínico severo (Cierre de estomas)"
        elif luz is not None and es_de_dia and not estado_fotoperiodo and luz < (ideal_lux * 0.7):
            alerta = "Luz natural insuficiente para la etapa actual"

        # Simulación de crecimiento
        if alerta:
            self.porcentaje_crecimiento -= 0.02 * multiplicador  # Regresión leve por estrés
        else:
            if 18.0 <= temp <= 25.0 and (luz is None or (ideal_lux * 0.7) <= luz <= limite_estres_lux):
                self.porcentaje_crecimiento += 0.05 * multiplicador
            else:
                self.porcentaje_crecimiento += 0.01 * multiplicador
                
        # Límites biológicos del ciclo de vida
        self.porcentaje_crecimiento = max(0.0, min(100.0, self.porcentaje_crecimiento))
            
        return alerta

class MotorClimatico:
    """
    Motor climático con 3 bloques diarios fijos, transiciones suaves (Markov)
    y estados climáticos separados para el día y la noche.

    Bloques:
      - Bloque 0: 00:00 – 05:59 (Madrugada) → estados nocturnos
      - Bloque 1: 06:00 – 16:59 (Día)       → estados diurnos
      - Bloque 2: 17:00 – 23:59 (Noche)     → estados nocturnos
    """

    # Estados climáticos por tipo de período
    CLIMAS_DIA   = ["Soleado", "Nublado", "Día Opaco", "Lluvia", "Tormenta", "Frío"]
    CLIMAS_NOCHE = ["Despejado", "Nublado", "Lluvia", "Tormenta", "Frío"]

    # ── Cadenas de Markov ────────────────────────────────────────────────────
    # Pesos de transición hacia el siguiente BLOQUE DE DÍA (índices = CLIMAS_DIA)
    # CLIMAS_DIA = ["Soleado", "Nublado", "Día Opaco", "Lluvia", "Tormenta", "Frío"]
    # Se aumentaron significativamente las probabilidades para favorecer días "Soleados" (cálidos) como norma general.
    TRANS_A_DIA = {
        "Soleado":    [0.75, 0.13, 0.06, 0.03, 0.01, 0.02],
        "Nublado":    [0.50, 0.28, 0.12, 0.06, 0.01, 0.03],
        "Día Opaco":  [0.40, 0.25, 0.20, 0.10, 0.02, 0.03],
        "Lluvia":     [0.25, 0.20, 0.18, 0.25, 0.08, 0.04],
        "Tormenta":   [0.20, 0.15, 0.15, 0.35, 0.10, 0.05],
        "Frío":       [0.35, 0.18, 0.15, 0.12, 0.04, 0.16],
        "Despejado":  [0.80, 0.11, 0.05, 0.02, 0.01, 0.01],
    }
    # Pesos de transición hacia el siguiente BLOQUE DE NOCHE (índices = CLIMAS_NOCHE)
    # CLIMAS_NOCHE = ["Despejado", "Nublado", "Lluvia", "Tormenta", "Frío"]
    TRANS_A_NOCHE = {
        "Soleado":    [0.72, 0.15, 0.06, 0.02, 0.05],
        "Nublado":    [0.48, 0.30, 0.12, 0.05, 0.05],
        "Día Opaco":  [0.42, 0.25, 0.18, 0.08, 0.07],
        "Lluvia":     [0.30, 0.20, 0.32, 0.12, 0.06],
        "Tormenta":   [0.25, 0.15, 0.25, 0.25, 0.10],
        "Frío":       [0.40, 0.18, 0.12, 0.05, 0.25],
        "Despejado":  [0.80, 0.12, 0.04, 0.01, 0.03],
    }

    # ── Parámetros físicos ────────────────────────────────────────────────────
    PARAMS = {
        "Soleado":    {"temp_base": 33.0, "hum_base": 35.0, "oscilacion": 8.0},
        "Nublado":    {"temp_base": 23.0, "hum_base": 65.0, "oscilacion": 4.0},
        "Día Opaco":  {"temp_base": 20.0, "hum_base": 72.0, "oscilacion": 3.0},
        "Lluvia":     {"temp_base": 17.0, "hum_base": 90.0, "oscilacion": 2.0},
        "Tormenta":   {"temp_base": 15.0, "hum_base": 95.0, "oscilacion": 2.5},
        "Frío":       {"temp_base": 10.0, "hum_base": 80.0, "oscilacion": 3.5},
        "Despejado":  {"temp_base": 18.0, "hum_base": 55.0, "oscilacion": 5.5},
    }

    ICONOS = {
        "Soleado":    "☀️ Soleado",
        "Nublado":    "☁️ Nublado",
        "Día Opaco":  "🌫️ Día Opaco",
        "Lluvia":     "🌧️ Lluvia",
        "Tormenta":   "⛈️ Tormenta",
        "Frío":       "❄️ Frío",
        "Despejado":  "🌙 Despejado",
    }

    def __init__(self):
        self.bloque_actual = -1       # -1 fuerza la inicialización en el primer ciclo
        self.estado_actual = "Nublado"
        self.temp_exterior = 20.0
        self.hum_exterior  = 65.0

    # ── Utilidades internas ──────────────────────────────────────────────────
    @staticmethod
    def _bloque(hora: int) -> int:
        """0 = Madrugada 00-05 | 1 = Día 06-16 | 2 = Noche 17-23"""
        if hora < 6:   return 0
        if hora < 17:  return 1
        return 2

    def _transicionar(self, es_noche: bool) -> str:
        if es_noche:
            return random.choices(
                self.CLIMAS_NOCHE,
                weights=self.TRANS_A_NOCHE.get(self.estado_actual, [0.30, 0.30, 0.20, 0.10, 0.10]),
                k=1
            )[0]
        else:
            return random.choices(
                self.CLIMAS_DIA,
                weights=self.TRANS_A_DIA.get(self.estado_actual, [0.25, 0.30, 0.20, 0.13, 0.06, 0.06]),
                k=1
            )[0]

    def _predecir_dia(self) -> str:
        """Devuelve el estado climático más probable para el próximo bloque de día."""
        return random.choices(
            self.CLIMAS_DIA,
            weights=self.TRANS_A_DIA.get(self.estado_actual, [0.25, 0.30, 0.20, 0.13, 0.06, 0.06]),
            k=1
        )[0]

    # ── API pública ──────────────────────────────────────────────────────────
    def actualizar_clima(self, hora_actual):
        hora   = hora_actual.hour
        bloque = self._bloque(hora)

        if bloque != self.bloque_actual:
            # ── Cambio de bloque → transición Markov ──
            es_noche = (bloque != 1)
            self.estado_actual = self._transicionar(es_noche)
            self.bloque_actual = bloque

        self.actualizar_clima_exterior(hora_actual)

    def actualizar_clima_exterior(self, hora_actual):
        hora = hora_actual.hour
        p = self.PARAMS.get(self.estado_actual, self.PARAMS["Nublado"])

        # Ciclo higrotérmico diario: pico de calor a las 14:00
        factor_diario = math.cos((hora - 14) * 2 * math.pi / 24)

        self.temp_exterior = (
            p["temp_base"]
            + factor_diario * p["oscilacion"]
            + random.uniform(-0.4, 0.4)
        )
        self.hum_exterior = (
            p["hum_base"]
            - factor_diario * p["oscilacion"] * 1.5
            + random.uniform(-0.8, 0.8)
        )

        self.temp_exterior = max(-5.0, min(48.0, self.temp_exterior))
        self.hum_exterior  = max(10.0, min(100.0, self.hum_exterior))

    def generar_pronostico(self, hora_actual):
        hora   = hora_actual.hour
        bloque = self._bloque(hora)
        icono  = self.ICONOS.get(self.estado_actual, "🌡️")

        # ── Textos por estado y período ──────────────────────────────────────
        TEXTOS = {
            "Soleado": {
                0: "",   # nunca ocurre de día
                1: "Cielo despejado. Alta radiación solar y temperatura en aumento constante.",
                2: "",
            },
            "Nublado": {
                0: "Madrugada nublada. Temperatura estable y humedad media.",
                1: "Cielo cubierto. Radiación atenuada. LED suplementario activo.",
                2: "Noche nublada. Temperatura y humedad estables.",
            },
            "Día Opaco": {
                0: "",
                1: "Cielo opaco sin rayos directos. LED al máximo rendimiento.",
                2: "",
            },
            "Lluvia": {
                0: "Lluvia nocturna. Temperatura baja y alta humedad exterior.",
                1: "Lluvia activa. Alta humedad. Bomba de riego pausada.",
                2: "Lluvia nocturna persistente. Temperatura a la baja.",
            },
            "Tormenta": {
                0: "Tormenta en madrugada. Humedad extrema. Calefacción activa.",
                1: "Tormenta eléctrica. Baja luminosidad. Sistemas al máximo.",
                2: "Tormenta nocturna. Temperatura muy baja. Alta humedad.",
            },
            "Frío": {
                0: "Madrugada gélida. Calefacción prioritaria.",
                1: "Día frío. Baja radiación. Calefacción y LED activos.",
                2: "Noche gélida. Mínima por debajo de 8°C. Calefacción activa.",
            },
            "Despejado": {
                0: "Madrugada despejada y fresca. Cielo estrellado. Temperatura descendiendo.",
                1: "",
                2: "Noche despejada. Cielo estrellado. Temperatura estable a la baja.",
            },
        }

        detalle = TEXTOS.get(self.estado_actual, {}).get(bloque, "")

        if bloque == 0:
            pronostico = f"🌙 Madrugada: {detalle}"
        elif bloque == 1:
            periodo = "Mañana" if hora < 12 else "Tarde"
            pronostico = f"📅 {periodo}: {detalle}"
        else:
            # Bloque 2: tarde-noche con predicción del día siguiente
            pred_dia    = self._predecir_dia()
            icono_pred  = self.ICONOS.get(pred_dia, "🌡️")
            pronostico = f"🌆 Tarde-Noche: {detalle}"

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