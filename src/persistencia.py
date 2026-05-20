"""
persistencia.py — Módulo de gestión de datos del Invernadero Virtual POO.

Responsabilidad única: leer y escribir el historial de la simulación en un
archivo CSV. Ninguna otra capa del sistema accede directamente al disco;
todo pasa por GestorPersistencia, lo que facilita migrar a una base de datos
relacional en el futuro sin tocar el resto del código.

Autores:
    Dorance Agudelo Rodríguez
    Yulian Alexis Ricardo Serna
    Juan Gabriel Vega Ospina

Institución:
    Universidad Tecnológica de Pereira
    Facultad de Ingenierías — Ingeniería Eléctrica
"""

import csv
import math
from pathlib import Path
import datetime


class GestorPersistencia:
    """
    Gestiona la persistencia del historial de simulación en un archivo CSV.

    El archivo se crea automáticamente con sus cabeceras si no existe.
    Cada fila representa una lectura puntual de todos los sensores y
    el estado de los actuadores en ese instante de tiempo virtual.

    Attributes:
        ruta (Path): Ruta al archivo CSV de historial.
    """

    def __init__(self, ruta_archivo="data/historial.csv"):
        """
        Inicializa el gestor y garantiza que el archivo CSV exista.

        Args:
            ruta_archivo (str): Ruta relativa o absoluta al archivo CSV.
                                Por defecto: 'data/historial.csv'.
        """
        self.ruta = Path(ruta_archivo)
        self._inicializar_archivo()

    def _inicializar_archivo(self):
        """
        Crea el directorio y el archivo CSV con sus cabeceras si no existe.

        Se usa exist_ok=True para que no falle si la carpeta ya fue creada
        en una ejecución anterior. Las cabeceras definen el contrato de datos
        que comparten todos los módulos del sistema.
        """
        # Crear el directorio 'data/' si no existe (ej. primera ejecución)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

        if not self.ruta.exists():
            # Escribir la fila de cabeceras para que csv.DictReader funcione correctamente
            with self.ruta.open(mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Fecha_Hora", "Temperatura_C", "Humedad_Pct",
                    "Ventilador", "Aspersores", "Luminosidad_Lux",
                    "Iluminacion_LED", "Calefaccion_Pct", "Malla_Desplegada"
                ])

    def registrar_lectura(self, dia_virtual, fecha_sim, t, h,
                          v_pct, r_pct, luz=0, intensidad_luz=0,
                          calef_pct=0, malla=False):
        """
        Añade una nueva fila al historial CSV con los datos del ciclo actual.

        El timestamp usa el formato 'Día Virtual X - HH:MM:SS' para reflejar
        el tiempo simulado en lugar del reloj real del computador.

        Args:
            dia_virtual  (int):   Número del día virtual actual de la simulación.
            fecha_sim    (datetime.datetime | str): Hora simulada del registro.
            t            (float): Temperatura interior en °C.
            h            (float): Humedad relativa interior en %.
            v_pct        (float): Esfuerzo del ventilador en % (0–100).
            r_pct        (float): Esfuerzo de los aspersores en % (0–100).
            luz          (float): Luminosidad total percibida en Lux.
            intensidad_luz (float): Intensidad del LED de suplemento en % (0–100).
            calef_pct    (float): Potencia de la calefacción en % (0–100).
            malla        (bool):  Estado de la pantalla térmica (True = desplegada).
        """
        # Construir el timestamp en formato legible con el día virtual
        if hasattr(fecha_sim, 'strftime'):
            hora_str = fecha_sim.strftime("%H:%M:%S")
        else:
            hora_str = str(fecha_sim)

        fecha = f"Día Virtual {dia_virtual} - {hora_str}"

        # Abrir en modo 'append' para no sobreescribir datos previos
        with self.ruta.open(mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                fecha, t, h,
                round(v_pct, 1), round(r_pct, 1),
                luz, intensidad_luz, calef_pct, malla
            ])

    def consultar_historial(self):
        """
        Lee el archivo CSV completo y lo retorna como lista de diccionarios.

        Cada diccionario tiene como claves los nombres de las columnas del CSV.
        Si el archivo no existe o está vacío, retorna una lista vacía para que
        los módulos que la llaman no fallen con excepciones.

        Returns:
            list[dict]: Lista de registros. Vacía si no hay datos.
        """
        if not self.ruta.exists():
            return []

        historial = []
        try:
            with self.ruta.open(mode='r', encoding='utf-8') as f:
                # DictReader usa la primera fila como claves del diccionario
                reader = csv.DictReader(f)
                for row in reader:
                    historial.append(row)
        except Exception as e:
            print(f"Error al leer el historial: {e}")

        return historial

    def obtener_historial_paginado(self, pagina, limite=50):
        """
        Retorna un fragmento del historial para implementar la paginación en la UI.

        Lee TODO el historial en memoria y extrae el slice correspondiente a la
        página solicitada. Esto garantiza que los promedios globales calculados
        en la interfaz sean estadísticamente correctos (usan todos los datos,
        no solo la página visible).

        Args:
            pagina (int): Número de página a retornar (base 1, no base 0).
            limite (int): Cantidad máxima de registros por página. Default: 50.

        Returns:
            tuple:
                - list[dict]: Registros de la página solicitada.
                - int: Total de páginas disponibles.
                - int: Total de registros en el historial completo.
        """
        historial_completo = self.consultar_historial()
        total_registros = len(historial_completo)

        # Si no hay datos, retornar valores seguros para que la UI no falle
        if total_registros == 0:
            return [], 1, 0

        # Calcular el número total de páginas redondeando hacia arriba
        total_paginas = math.ceil(total_registros / limite)

        # Asegurar que la página solicitada esté dentro de los límites válidos
        pagina = max(1, min(pagina, total_paginas))

        # Calcular los índices de inicio y fin del slice
        inicio = (pagina - 1) * limite
        fin = inicio + limite

        fragmento = historial_completo[inicio:fin]

        return fragmento, total_paginas, total_registros
