from django.utils import timezone
from datetime import time

def esta_en_horario_electoral():
    """Función utilitaria para verificar horarios electorales"""
    now = timezone.localtime()
    dia_semana = now.weekday()  # 0=Lunes, 6=Domingo
    hora_actual = now.time()
    
    # Horarios definidos
    horarios_lunes_viernes = [
        (time(8, 0), time(11, 0)),    # 8:00 am - 11:00 am
        (time(14, 0), time(17, 0)),   # 2:00 pm - 5:00 pm  
        (time(18, 0), time(20, 30)),  # 6:00 pm - 8:30 pm
    ]
    
    horarios_sabado = [
        (time(8, 0), time(11, 0)),    # 8:00 am - 11:00 am
        (time(13, 0), time(17, 0)),   # 1:00 pm - 5:00 pm
    ]
    
    # Lunes a Viernes (0-4)
    if 0 <= dia_semana <= 4:
        for inicio, fin in horarios_lunes_viernes:
            if inicio <= hora_actual <= fin:
                return True
    
    # Sábado (5)
    elif dia_semana == 5:
        for inicio, fin in horarios_sabado:
            if inicio <= hora_actual <= fin:
                return True
    
    return False

def obtener_info_horarios():
    """Obtiene información completa de horarios para mostrar al usuario"""
    return {
        'lunes_viernes': [
            "8:00 AM - 11:00 AM",
            "2:00 PM - 5:00 PM", 
            "6:00 PM - 8:30 PM"
        ],
        'sabado': [
            "8:00 AM - 11:00 AM",
            "1:00 PM - 5:00 PM"
        ],
        'domingo': "Sin votación"
    }
