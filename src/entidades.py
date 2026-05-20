"""
entidades.py — Clases base del Invernadero Virtual POO.
Sensores, actuadores, motor climático y modelo biológico de la planta.
"""

import random
import math


# ─── CAPA BASE ──────────────────────────────────────────────────────────────

class Sensor:
    """Clase base para todos los sensores del invernadero."""

    def __init__(self, nombre, unidad, valor_inicial):
        """
        Args:
            nombre (str): Nombre descriptivo del sensor.
            unidad (str): Unidad de medida (ej. '°C', '%').
            valor_inicial (float): Valor inicial simulado.
        """
        self.nombre = nombre
        self.unidad = unidad
        self.valor = valor_inicial

    def leer_valor(self):
        """
        Retorna el valor actual más una fluctuación aleatoria de ±0.5.

        La fluctuación se suma a una copia local para evitar deriva acumulativa
        (drift) en self.valor con cada llamada.

        Returns:
            float: Valor con ruido de sensor simulado.
        """
        fluctuacion = random.uniform(-0.5, 0.5)
        return round(self.valor + fluctuacion, 2)


class Actuador:
    """Clase base para ventilador, bomba de riego, iluminación y calefacción."""

    def __init__(self, nombre):
        """
        Args:
            nombre (str): Nombre del actuador.
        """
        self.nombre = nombre
        self.encendido = False
        self.potencia = 0.0   # Potencia real aplicada (con rampa suave), 0–100 %
        self.esfuerzo = 0.0   # Potencia objetivo calculada por el controlador, 0–100 %

    def alternar(self, estado: bool):
        """Enciende (True) o apaga (False) el actuador al 100 % o 0 % de golpe."""
        self.encendido = estado
        self.potencia = 100.0 if estado else 0.0

    def ajustar_potencia(self, valor: float):
        """
        Fija la potencia y actualiza el estado encendido/apagado.

        Args:
            valor (float): Potencia deseada. Se recorta al rango [0, 100].
        """
        self.potencia = max(0.0, min(100.0, float(valor)))
        self.encendido = self.potencia > 0

    def __str__(self):
        estado_str = "Encendido" if self.encendido else "Apagado"
        return f"{self.nombre}: {estado_str} ({self.potencia:.1f}%)"


# ─── MODELO BIOLÓGICO ────────────────────────────────────────────────────────

class Planta:
    """
    Modela el crecimiento y el estrés fisiológico del cultivo.

    La salud no es un atributo interno; el porcentaje de crecimiento sube
    o baja cada ciclo según las condiciones ambientales evaluadas.
    """

    def __init__(self):
        self.porcentaje_crecimiento = 0.0
        self.plantada = True

    def plantar(self):
        """Reinicia el ciclo de cultivo desde 0 %."""
        self.porcentaje_crecimiento = 0.0
        self.plantada = True

    def cosechar(self):
        """Finaliza el ciclo de cultivo y deja la planta en estado 'no plantada'."""
        self.porcentaje_crecimiento = 0.0
        self.plantada = False

    def evaluar_condiciones(self, temp, hum, luz=None,
                            multiplicador=1.0, es_de_dia=True,
                            estado_fotoperiodo=False):
        """
        Calcula el estrés del ciclo actual y ajusta el porcentaje de crecimiento.

        Reglas principales:
        - Temperatura > 30 °C o humedad fuera de [40, 80] % → alerta y regresión.
        - Condiciones óptimas (18–25 °C, luz adecuada) → crecimiento rápido.
        - Condiciones subóptimas pero sin alerta → crecimiento lento.
        - Bloqueo antirretroceso: el crecimiento no cae por debajo del umbral
          de la etapa ya superada (inmunidad de frontera).

        Args:
            temp         (float): Temperatura interior en °C.
            hum          (float): Humedad interior en %.
            luz          (float | None): Luminosidad total en Lux. None = ignorar.
            multiplicador (float): Factor de aceleración del tiempo virtual.
            es_de_dia    (bool): True si el reloj virtual está en período diurno.
            estado_fotoperiodo (bool): True durante el período de descanso nocturno
                                       (00:00–07:00). En ese período no se penaliza
                                       la falta de luz.

        Returns:
            str: Mensaje de alerta activa, o cadena vacía si todo está bien.
        """
        if not self.plantada:
            return "Esperando siembra..."

        alerta = ""

        # Requerimiento lumínico ideal según etapa de desarrollo
        if self.porcentaje_crecimiento <= 20:
            ideal_lux = 10000.0      # Semilla / Brote
        elif self.porcentaje_crecimiento <= 70:
            ideal_lux = 25000.0     # Vegetativo
        else:
            ideal_lux = 45000.0     # Floración / Fructificación

        limite_estres_lux = 65000.0  # Umbral de fotoinhibición

        # Inmunidad de frontera: evita penalizar justo al cruzar una nueva etapa
        en_frontera = False
        fronteras = [(20.0, 21.0), (40.0, 41.0), (70.0, 71.0), (90.0, 91.0)]
        for inferior, superior in fronteras:
            if inferior < self.porcentaje_crecimiento <= superior:
                en_frontera = True
                break

        # Evaluación de condiciones de estrés (orden de prioridad biológica)
        if temp > 30.0:
            alerta = "Peligro de deshidratación y estrés térmico"
        elif hum > 80.0:
            alerta = "Riesgo de proliferación de patógenos fúngicos (ej. Botrytis)"
        elif hum < 40.0:
            alerta = "Transpiración excesiva, estrés hídrico inminente"
        elif luz is not None and luz > limite_estres_lux:
            alerta = "Peligro: Estrés lumínico severo (Cierre de estomas)"
        elif luz is not None and not estado_fotoperiodo:
            # Fuera del período de descanso, verificar si hay luz suficiente
            if luz < (ideal_lux * 0.7):
                if not en_frontera:
                    alerta = f"Luz insuficiente para la etapa actual"

        # Piso biológico: el crecimiento no retrocede por debajo del umbral superado
        piso_biologico = 0.0
        for umbral in [20.0, 40.0, 70.0, 90.0]:
            if self.porcentaje_crecimiento > umbral:
                piso_biologico = umbral + 0.001

        # Ajuste de crecimiento según condiciones del ciclo
        if alerta:
            # Regresión leve proporcional al multiplicador de tiempo
            self.porcentaje_crecimiento -= 0.02 * multiplicador
        else:
            if 18.0 <= temp <= 25.0 and (luz is None or (ideal_lux * 0.7) <= luz <= limite_estres_lux):
                self.porcentaje_crecimiento += 0.05 * multiplicador  # Crecimiento óptimo
            else:
                self.porcentaje_crecimiento += 0.01 * multiplicador  # Crecimiento subóptimo

        # Aplicar límites: bloqueo antirretroceso (piso) y techo en 100 %
        self.porcentaje_crecimiento = max(piso_biologico, min(100.0, self.porcentaje_crecimiento))

        return alerta


# ─── MOTOR CLIMÁTICO ─────────────────────────────────────────────────────────

class MotorClimatico:
    """
    Simula el clima exterior con transiciones probabilísticas (cadenas de Markov)
    y curvas térmicas diarias realistas.

    El día se divide en 3 bloques:
      - Bloque 0: 00:00–05:59 (Madrugada) → estados nocturnos
      - Bloque 1: 06:00–17:59 (Día)       → estados diurnos
      - Bloque 2: 18:00–23:59 (Tarde-Noche) → estados nocturnos

    Al cambiar de bloque, se elige el nuevo estado climático usando la cadena de
    Markov correspondiente (TRANS_A_DIA o TRANS_A_NOCHE), lo que garantiza
    transiciones coherentes (no pasa de Soleado a Tormenta instantáneamente).
    """

    CLIMAS_DIA   = ["Soleado", "Nublado", "Día Opaco", "Lluvia", "Tormenta", "Frío"]
    CLIMAS_NOCHE = ["Despejado", "Nublado", "Lluvia", "Tormenta", "Frío"]

    # Pesos de transición al siguiente bloque de DÍA (índices = CLIMAS_DIA)
    TRANS_A_DIA = {
        "Soleado":    [0.75, 0.13, 0.06, 0.03, 0.01, 0.02],
        "Nublado":    [0.50, 0.28, 0.12, 0.06, 0.01, 0.03],
        "Día Opaco":  [0.40, 0.25, 0.20, 0.10, 0.02, 0.03],
        "Lluvia":     [0.25, 0.20, 0.18, 0.25, 0.08, 0.04],
        "Tormenta":   [0.20, 0.15, 0.15, 0.35, 0.10, 0.05],
        "Frío":       [0.35, 0.18, 0.15, 0.12, 0.04, 0.16],
        "Despejado":  [0.80, 0.11, 0.05, 0.02, 0.01, 0.01],
    }

    # Pesos de transición al siguiente bloque de NOCHE (índices = CLIMAS_NOCHE)
    TRANS_A_NOCHE = {
        "Soleado":    [0.72, 0.15, 0.06, 0.02, 0.05],
        "Nublado":    [0.48, 0.30, 0.12, 0.05, 0.05],
        "Día Opaco":  [0.42, 0.25, 0.18, 0.08, 0.07],
        "Lluvia":     [0.30, 0.20, 0.32, 0.12, 0.06],
        "Tormenta":   [0.25, 0.15, 0.25, 0.25, 0.10],
        "Frío":       [0.40, 0.18, 0.12, 0.05, 0.25],
        "Despejado":  [0.80, 0.12, 0.04, 0.01, 0.03],
    }

    # Parámetros físicos base por estado climático
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
        self.bloque_actual = -1       # -1 fuerza la transición en el primer ciclo
        self.estado_actual = "Nublado"
        self.temp_exterior = 20.0
        self.hum_exterior  = 65.0

    @staticmethod
    def _bloque(hora: int) -> int:
        """
        Determina el bloque del día a partir de la hora.

        Returns:
            int: 0 = Madrugada (00–05) | 1 = Día (06–17) | 2 = Noche (18–23)
        """
        if hora < 6:  return 0
        if hora < 18: return 1
        return 2

    def _transicionar(self, es_noche: bool) -> str:
        """
        Elige el próximo estado climático usando la cadena de Markov.

        Args:
            es_noche (bool): True si el siguiente bloque es nocturno.

        Returns:
            str: Nombre del nuevo estado climático.
        """
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
        """
        Predice el clima más probable para el próximo bloque de día.

        Returns:
            str: Estado climático predicho.
        """
        return random.choices(
            self.CLIMAS_DIA,
            weights=self.TRANS_A_DIA.get(self.estado_actual, [0.25, 0.30, 0.20, 0.13, 0.06, 0.06]),
            k=1
        )[0]

    def actualizar_clima(self, hora_actual, salto_temporal=False):
        """
        Revisa si cambió el bloque horario y, de ser así, ejecuta la transición Markov.

        Args:
            hora_actual     (datetime): Hora simulada actual.
            salto_temporal  (bool): Si True, se omite la inercia térmica.
        """
        hora   = hora_actual.hour
        bloque = self._bloque(hora)

        if bloque != self.bloque_actual:
            # Cambio de bloque: seleccionar nuevo estado climático
            es_noche = (bloque != 1)
            self.estado_actual = self._transicionar(es_noche)
            self.bloque_actual = bloque

        self.actualizar_clima_exterior(hora_actual, salto_temporal)

    def actualizar_clima_exterior(self, hora_actual, salto_temporal=False):
        """
        Calcula la temperatura y humedad exterior con curva térmica diaria
        e inercia progresiva (máx. 0.05 °C y 0.1 % por ciclo).

        La curva térmica replica el comportamiento real:
        - Sube gradualmente desde las 06:00 hasta las 12:00.
        - Se sostiene con caída mínima entre 12:00 y 15:00.
        - Cae suavemente de 15:00 a 18:00.
        - Continúa descendiendo toda la noche.

        Args:
            hora_actual    (datetime): Hora simulada actual.
            salto_temporal (bool): Si True, se asigna el valor objetivo directamente
                                   sin inercia (útil tras un salto manual de tiempo).
        """
        hora_float = hora_actual.hour + hora_actual.minute / 60.0
        p = self.PARAMS.get(self.estado_actual, self.PARAMS["Nublado"])

        # Calcular el factor diario según el tramo horario
        if 6.0 <= hora_float < 12.0:
            frac = (hora_float - 6.0) / 6.0
            factor_diario = -1.0 + math.sin(frac * math.pi / 2) * 2.0
        elif 12.0 <= hora_float <= 15.0:
            frac = (hora_float - 12.0) / 3.0
            factor_diario = 1.0 - (0.1 * frac)
        elif 15.0 < hora_float <= 18.0:
            frac = (hora_float - 15.0) / 3.0
            factor_diario = -1.0 + 1.9 * math.cos(frac * math.pi / 2)
        else:
            # Período nocturno: descenso continuo
            if hora_float > 18.0:
                h_noche = hora_float - 18.0
            else:
                h_noche = hora_float + 6.0
            frac = h_noche / 12.0
            factor_diario = -1.0 - math.sin(frac * math.pi) * 0.2

        # Temperatura y humedad objetivo para este instante
        target_temp = (
            p["temp_base"]
            + factor_diario * p["oscilacion"]
            + random.uniform(-0.4, 0.4)
        )
        target_hum = (
            p["hum_base"]
            - factor_diario * p["oscilacion"] * 1.5
            + random.uniform(-0.8, 0.8)
        )

        # En salto temporal o primer ciclo: asignar directamente (sin inercia)
        if salto_temporal or not hasattr(self, 'temp_exterior_target'):
            self.temp_exterior = target_temp
            self.hum_exterior = target_hum

        self.temp_exterior_target = target_temp
        self.hum_exterior_target = target_hum

        # Inercia térmica: avanzar máx. 0.05 °C por ciclo hacia el objetivo
        if self.temp_exterior < self.temp_exterior_target:
            self.temp_exterior += min(0.05, self.temp_exterior_target - self.temp_exterior)
        elif self.temp_exterior > self.temp_exterior_target:
            self.temp_exterior -= min(0.05, self.temp_exterior - self.temp_exterior_target)

        # Inercia de humedad: avanzar máx. 0.1 % por ciclo hacia el objetivo
        if self.hum_exterior < self.hum_exterior_target:
            self.hum_exterior += min(0.1, self.hum_exterior_target - self.hum_exterior)
        elif self.hum_exterior > self.hum_exterior_target:
            self.hum_exterior -= min(0.1, self.hum_exterior - self.hum_exterior_target)

        # Recortar a rangos físicamente posibles
        self.temp_exterior = max(-5.0, min(48.0, self.temp_exterior))
        self.hum_exterior  = max(10.0, min(100.0, self.hum_exterior))

    def generar_pronostico(self, hora_actual):
        """
        Genera el texto de pronóstico visible en la interfaz.

        Args:
            hora_actual (datetime): Hora simulada actual.

        Returns:
            str: Cadena con emoji, período del día y descripción del clima.
        """
        hora   = hora_actual.hour
        bloque = self._bloque(hora)
        icono  = self.ICONOS.get(self.estado_actual, "🌡️")

        TEXTOS = {
            "Soleado": {
                0: "",
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
            # Bloque nocturno: incluir predicción del día siguiente
            pred_dia   = self._predecir_dia()
            icono_pred = self.ICONOS.get(pred_dia, "🌡️")
            pronostico = f"🌆 Tarde-Noche: {detalle}"

        return pronostico


# ─── CLASES CONCRETAS ────────────────────────────────────────────────────────

class SensorTemperatura(Sensor):
    """Sensor de temperatura interior. Valor inicial: 25.0 °C."""
    def __init__(self, valor_inicial=25.0):
        super().__init__("Temperatura", "°C", valor_inicial)


class SensorHumedad(Sensor):
    """Sensor de humedad relativa interior. Valor inicial: 60.0 %."""
    def __init__(self, valor_inicial=60.0):
        super().__init__("Humedad", "%", valor_inicial)


class SensorLuminosidad(Sensor):
    """
    Sensor de luminosidad. El Controlador gestiona la curva Día/Noche
    actualizando self.valor; aquí solo se añade el ruido del sensor.
    """
    def __init__(self, valor_inicial=0.0):
        super().__init__("Luminosidad", "Lux", valor_inicial)

    def leer_valor(self):
        """
        Retorna la luminosidad con fluctuación de ±50 Lux.

        Returns:
            float: Luminosidad en Lux (mínimo 0.0).
        """
        fluctuacion = random.uniform(-50, 50)
        return round(max(0.0, self.valor + fluctuacion), 2)


class Ventilador(Actuador):
    """Actuador de ventilación forzada."""
    def __init__(self):
        super().__init__("Ventilador")


class BombaRiego(Actuador):
    """Actuador de la bomba de riego / aspersores."""
    def __init__(self):
        super().__init__("Bomba de Riego")


class SistemaIluminacion(Actuador):
    """Actuador del sistema de iluminación LED suplementaria."""
    def __init__(self):
        super().__init__("Sistema de Iluminación")
        self.intensidad = 0.0  # Porcentaje de intensidad activa (0–100 %)


class Calefaccion:
    """
    Actuador de calefacción. No hereda de Actuador porque su control es
    estrictamente proporcional y nunca usa el método alternar().
    """
    def __init__(self):
        self.encendido = False
        self.potencia  = 0.0   # Potencia real con rampa suave (0–100 %)
        self.esfuerzo  = 0.0   # Potencia objetivo calculada por el controlador

    def alternar(self, estado):
        """Enciende o apaga la calefacción."""
        self.encendido = estado