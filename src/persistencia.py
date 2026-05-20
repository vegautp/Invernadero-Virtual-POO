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
                writer.writerow(["Fecha_Hora", "Temperatura_C", "Humedad_Pct", "Ventilador", "Aspersores", "Luminosidad_Lux", "Iluminacion_LED", "Calefaccion_Pct", "Malla_Desplegada"])

    def registrar_lectura(self, dia_virtual, fecha_sim, t, h, v_pct, r_pct, luz=0, intensidad_luz=0, calef_pct=0, malla=False):
        """Registra una nueva lectura de sensores y estado de actuadores."""
        # Formato solicitado por el usuario: "Día Virtual [X] - [Hora Simulada]"
        if hasattr(fecha_sim, 'strftime'):
            hora_str = fecha_sim.strftime("%H:%M:%S")
        else:
            hora_str = str(fecha_sim)
        fecha = f"Día Virtual {dia_virtual} - {hora_str}"
        with self.ruta.open(mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([fecha, t, h, round(v_pct, 1), round(r_pct, 1), luz, intensidad_luz, calef_pct, malla])

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

    def obtener_historial_paginado(self, pagina, limite=50):
        """
        Devuelve un fragmento del historial para la paginación.
        Retorna (fragmento_datos, total_paginas, total_registros).
        """
        historial_completo = self.consultar_historial()
        total_registros = len(historial_completo)
        
        if total_registros == 0:
            return [], 1, 0
            
        import math
        total_paginas = math.ceil(total_registros / limite)
        
        # Validar la página actual
        pagina = max(1, min(pagina, total_paginas))
        
        inicio = (pagina - 1) * limite
        fin = inicio + limite
        
        fragmento = historial_completo[inicio:fin]
        
        return fragmento, total_paginas, total_registros
