from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from datetime import time
import logging

class HorarioElectoralMiddleware:
    """Middleware que controla el acceso al sistema durante horarios específicos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('votaciones.horarios')
        print("🕐 Middleware de Horarios Electoral inicializado")
    
    def __call__(self, request):
        # Debug: mostrar información de la petición
        print(f"🔍 Middleware procesando: {request.path}")
        
        # Verificar si es una ruta del sistema electoral
        if self.es_ruta_electoral(request.path):
            print(f"📋 Ruta electoral detectada: {request.path}")
            
            if not self.esta_en_horario_electoral():
                print("⏰ FUERA DE HORARIO - Mostrando página de restricción")
                return self.respuesta_fuera_de_horario(request)
            else:
                print("✅ DENTRO DE HORARIO - Permitiendo acceso")
        else:
            print(f"🔓 Ruta no electoral: {request.path}")
        
        response = self.get_response(request)
        return response
    
    def es_ruta_electoral(self, path):
        """Determina si la ruta requiere validación de horarios"""
        # Normalizar la ruta removiendo trailing slash
        path_normalized = path.rstrip('/')
        
        rutas_electorales = [
            '/votaciones',
            '/votaciones/estudiantes',
            '/votaciones/docentes', 
            '/votaciones/graduados',
            '/votaciones/procesar-voto',
        ]
        
        # Excluir rutas administrativas y de reporte
        rutas_excluidas = [
            '/admin',
            '/votaciones/gracias',
            '/static',
            '/media',
        ]
        
        print(f"🔍 Verificando ruta: '{path}' (normalizada: '{path_normalized}')")
        
        # Si es una ruta excluida, no aplicar restricción
        for excluida in rutas_excluidas:
            if path.startswith(excluida):
                print(f"   ❌ Ruta excluida: {excluida}")
                return False
        
        # Verificar si es una ruta electoral (usando la ruta normalizada)
        for ruta in rutas_electorales:
            if path_normalized == ruta or path.startswith(ruta + '/'):
                print(f"   ✅ Ruta electoral encontrada: {ruta}")
                return True
        
        print(f"   ➖ No es ruta electoral")
        return False
    
    def esta_en_horario_electoral(self):
        """Verifica si estamos en horario electoral válido"""
        now = timezone.localtime()
        dia_semana = now.weekday()  # 0=Lunes, 6=Domingo
        hora_actual = now.time()
        
        # Debug: mostrar información de tiempo
        print(f"📅 Fecha actual: {now}")
        print(f"📅 Día de la semana: {dia_semana} (0=Lunes, 6=Domingo)")
        print(f"🕐 Hora actual: {hora_actual}")
        
        # PARA TESTING: Comentar las siguientes líneas para permitir acceso 24/7
        # return True
        
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
            print("📅 Es día de semana (Lunes-Viernes)")
            for i, (inicio, fin) in enumerate(horarios_lunes_viernes):
                print(f"   Verificando horario {i+1}: {inicio} - {fin}")
                if inicio <= hora_actual <= fin:
                    print(f"   ✅ Está dentro del horario {i+1}")
                    return True
        
        # Sábado (5)
        elif dia_semana == 5:
            print("📅 Es sábado")
            for i, (inicio, fin) in enumerate(horarios_sabado):
                print(f"   Verificando horario {i+1}: {inicio} - {fin}")
                if inicio <= hora_actual <= fin:
                    print(f"   ✅ Está dentro del horario {i+1}")
                    return True
        
        # Domingo (6) - No hay votación
        else:
            print("📅 Es domingo - Sin votación")
        
        print("❌ FUERA DE HORARIO")
        return False
    
    def obtener_proximo_horario(self):
        """Obtiene información del próximo horario electoral"""
        now = timezone.localtime()
        dia_semana = now.weekday()
        hora_actual = now.time()
        
        # Horarios para mostrar al usuario
        if 0 <= dia_semana <= 4:  # Lunes a Viernes
            horarios_texto = [
                "8:00 AM - 11:00 AM",
                "2:00 PM - 5:00 PM", 
                "6:00 PM - 8:30 PM"
            ]
            horarios_time = [
                (time(8, 0), time(11, 0)),
                (time(14, 0), time(17, 0)),
                (time(18, 0), time(20, 30)),
            ]
            
            # Buscar el próximo horario del día
            for i, (inicio, fin) in enumerate(horarios_time):
                if hora_actual < inicio:
                    return f"hoy de {horarios_texto[i]}"
                elif inicio <= hora_actual <= fin:
                    return "ahora mismo (horario activo)"
            
            # Si no hay más horarios hoy, mostrar mañana
            if dia_semana < 4:  # Lunes a Jueves
                return "mañana de 8:00 AM - 11:00 AM"
            elif dia_semana == 4:  # Viernes
                return "mañana (sábado) de 8:00 AM - 11:00 AM"
        
        elif dia_semana == 5:  # Sábado
            horarios_texto = [
                "8:00 AM - 11:00 AM",
                "1:00 PM - 5:00 PM"
            ]
            horarios_time = [
                (time(8, 0), time(11, 0)),
                (time(13, 0), time(17, 0)),
            ]
            
            for i, (inicio, fin) in enumerate(horarios_time):
                if hora_actual < inicio:
                    return f"hoy de {horarios_texto[i]}"
                elif inicio <= hora_actual <= fin:
                    return "ahora mismo (horario activo)"
            
            # Después del sábado, siguiente lunes
            return "el lunes de 8:00 AM - 11:00 AM"
        
        else:  # Domingo
            return "mañana (lunes) de 8:00 AM - 11:00 AM"
    
    def respuesta_fuera_de_horario(self, request):
        """Respuesta cuando se accede fuera de horario"""
        now = timezone.localtime()
        proximo_horario = self.obtener_proximo_horario()
        
        print("🚫 Generando respuesta de fuera de horario")
        
        # Log del intento de acceso fuera de horario
        self.logger.warning(
            f'Acceso fuera de horario electoral. IP: {self.get_client_ip(request)}, '
            f'Fecha/Hora: {now.strftime("%d/%m/%Y %H:%M:%S")}, '
            f'Ruta: {request.path}'
        )
        
        # Nombres de días en español
        dias_espanol = {
            'Monday': 'Lunes',
            'Tuesday': 'Martes', 
            'Wednesday': 'Miércoles',
            'Thursday': 'Jueves',
            'Friday': 'Viernes',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        
        # Nombres de meses en español
        meses_espanol = {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
        
        dia_nombre = dias_espanol.get(now.strftime("%A"), now.strftime("%A"))
        mes_nombre = meses_espanol.get(now.strftime("%B"), now.strftime("%B"))
        fecha_formateada = f"{now.day} de {mes_nombre} de {now.year}"
        
        context = {
            'titulo': 'Sistema Electoral Fuera de Horario',
            'fecha_actual': fecha_formateada,
            'hora_actual': now.strftime("%H:%M:%S"),
            'dia_semana': dia_nombre,
            'proximo_horario': proximo_horario,
            'horarios_lunes_viernes': [
                "8:00 AM - 11:00 AM",
                "2:00 PM - 5:00 PM",
                "6:00 PM - 8:30 PM"
            ],
            'horarios_sabado': [
                "8:00 AM - 11:00 AM", 
                "1:00 PM - 5:00 PM"
            ]
        }
        
        try:
            return render(request, 'votaciones/fuera_de_horario.html', context)
        except Exception as e:
            print(f"❌ Error renderizando template: {e}")
            # Fallback: respuesta HTML simple
            from django.http import HttpResponse
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Sistema Fuera de Horario</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    h1 {{ color: #b71c1c; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🕐 Sistema Electoral Fuera de Horario</h1>
                    <p>El sistema de votación no está disponible en este momento.</p>
                    <p><strong>Fecha actual:</strong> {fecha_formateada}</p>
                    <p><strong>Hora actual:</strong> {now.strftime("%H:%M:%S")}</p>
                    <p><strong>Próximo horario:</strong> {proximo_horario}</p>
                    <hr>
                    <h3>Horarios de Votación</h3>
                    <p><strong>Lunes a Viernes:</strong><br>
                    8:00 AM - 11:00 AM<br>
                    2:00 PM - 5:00 PM<br>
                    6:00 PM - 8:30 PM</p>
                    <p><strong>Sábados:</strong><br>
                    8:00 AM - 11:00 AM<br>
                    1:00 PM - 5:00 PM</p>
                    <p><a href="/admin/">Acceso Administrativo</a></p>
                </div>
            </body>
            </html>
            """
            return HttpResponse(html)
    
    def get_client_ip(self, request):
        """Obtiene la IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
