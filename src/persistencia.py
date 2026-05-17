import csv
from pathlib import Path
import datetime

class GestorPersistencia:
    """Clase encargada de gestionar la persistencia de datos del invernadero."""
    
    def __init__(self, ruta_archivo="data/historial.csv"):
        self.ruta = Path(ruta_archivo)
        self._inicializar_archivo()

    def _inicializar_archivo(self):
        """Crea el directorio y el archivo CSV con encabezados si no existe."""
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        if not self.ruta.exists():
            with self.ruta.open(mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Fecha_Hora", "Temperatura_C", "Humedad_Pct", "Ventilador", "Bomba_Riego"])

    def registrar_lectura(self, t, h, v, r):
        """Registra una nueva lectura de sensores y estado de actuadores."""
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.ruta.open(mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([fecha, t, h, v, r])

    def consultar_historial(self):
        """Lee el historial completo. Retorna una lista de diccionarios o lista vacía si no existe."""
        if not self.ruta.exists():
            return []
        
        historial = []
        try:
            with self.ruta.open(mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    historial.append(row)
        except Exception as e:
            print(f"Error al leer el historial: {e}")
            
        return historial
