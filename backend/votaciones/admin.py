from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models import Count
from .models import Votante, TipoConsejo, Plancha, Candidato, Voto, EstadisticaVotacion

@admin.register(Votante)
class VotanteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'documento', 'tipo_persona', 'ya_voto', 'fecha_voto', 'ip_votacion']
    list_filter = ['tipo_persona', 'ya_voto', 'fecha_voto']
    search_fields = ['nombre', 'documento']
    readonly_fields = ['created_at', 'updated_at', 'fecha_voto']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'documento', 'tipo_persona')
        }),
        ('Estado de Votación', {
            'fields': ('ya_voto', 'ip_votacion', 'fecha_voto')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TipoConsejo)
class TipoConsejoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'total_planchas']
    list_filter = ['activo']
    search_fields = ['nombre']
    
    def total_planchas(self, obj):
        return obj.plancha_set.count()
    total_planchas.short_description = 'Total Planchas'

class CandidatoInline(admin.TabularInline):
    model = Candidato
    extra = 2
    fields = ['nombre', 'cargo', 'foto']

@admin.register(Plancha)
class PlanchaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nombre', 'tipo_consejo', 'tipo_persona', 'total_votos', 'activa']
    list_filter = ['tipo_consejo', 'tipo_persona', 'activa']
    search_fields = ['nombre', 'numero']
    inlines = [CandidatoInline]
    
    def total_votos(self, obj):
        return obj.voto_set.count()
    total_votos.short_description = 'Total Votos'

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'plancha', 'cargo']
    list_filter = ['cargo', 'plancha__tipo_consejo', 'plancha__tipo_persona']
    search_fields = ['nombre', 'plancha__nombre']

@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ['votante', 'plancha', 'tipo_consejo', 'fecha_voto', 'ip_votacion']
    list_filter = ['tipo_consejo', 'fecha_voto', 'plancha__tipo_persona']
    search_fields = ['votante__nombre', 'votante__documento', 'plancha__nombre']
    readonly_fields = ['fecha_voto']
    
    def has_add_permission(self, request):
        return False  # No permitir agregar votos manualmente
    
    def has_change_permission(self, request, obj=None):
        return False  # No permitir editar votos

@admin.register(EstadisticaVotacion)
class EstadisticaVotacionAdmin(admin.ModelAdmin):
    list_display = ['total_votantes', 'total_votos_emitidos', 'porcentaje_participacion', 'ultima_actualizacion']
    readonly_fields = ['ultima_actualizacion']
    
    def changelist_view(self, request, extra_context=None):
        # Actualizar estadísticas antes de mostrar
        EstadisticaVotacion.actualizar_estadisticas()
        return super().changelist_view(request, extra_context)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

# Personalizar el admin principal
class VotacionesAdminSite(admin.AdminSite):
    site_header = "FESC Votaciones - Administración"
    site_title = "FESC Votaciones"
    index_title = "Panel de Administración Electoral"
    
    def index(self, request, extra_context=None):
        """Redirigir al dashboard personalizado"""
        return HttpResponseRedirect(reverse('votaciones:dashboard_electoral'))

# Registrar el admin personalizado
admin_site = VotacionesAdminSite(name='votaciones_admin')

# Re-registrar todos los modelos en el admin personalizado
admin_site.register(Votante, VotanteAdmin)
admin_site.register(TipoConsejo, TipoConsejoAdmin)
admin_site.register(Plancha, PlanchaAdmin)
admin_site.register(Candidato, CandidatoAdmin)
admin_site.register(Voto, VotoAdmin)
admin_site.register(EstadisticaVotacion, EstadisticaVotacionAdmin)

# Personalizar el admin site con dashboard
admin.site.site_header = 'FESC Votaciones - Dashboard'
admin.site.site_title = 'Dashboard Electoral'
admin.site.index_title = 'Panel de Control Electoral'

def dashboard_view(request):
    """Vista del dashboard electoral"""
    # Actualizar estadísticas
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    
    # Obtener datos para gráficos
    votos_por_tipo = list(Votante.objects.filter(ya_voto=True).values('tipo_persona').annotate(total=Count('id')))
    votos_por_consejo = list(Voto.objects.values('tipo_consejo__nombre').annotate(total=Count('id')))
    votos_por_plancha = list(Voto.objects.values('plancha__nombre', 'plancha__numero', 'plancha__tipo_persona').annotate(total=Count('id')).order_by('-total')[:10])
    
    # Estadísticas por hora (últimas 24 horas)
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    ahora = timezone.now()
    hace_24h = ahora - timedelta(hours=24)
    
    votos_por_hora = []
    for i in range(24):
        hora_inicio = hace_24h + timedelta(hours=i)
        hora_fin = hora_inicio + timedelta(hours=1)
        votos_hora = Voto.objects.filter(fecha_voto__range=(hora_inicio, hora_fin)).count()
        votos_por_hora.append({
            'hora': hora_inicio.strftime('%H:00'),
            'votos': votos_hora
        })
    
    context = {
        'title': 'Dashboard Electoral FESC',
        'estadisticas': estadisticas,
        'votos_por_tipo': json.dumps(votos_por_tipo),
        'votos_por_consejo': json.dumps(votos_por_consejo),
        'votos_por_plancha': votos_por_plancha,
        'votos_por_hora': json.dumps(votos_por_hora),
        'opts': {'app_label': 'votaciones'},
        'has_permission': True,
    }
    
    return render(request, 'admin/dashboard_electoral.html', context)

def estadisticas_json(request):
    """API para obtener estadísticas actualizadas"""
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    
    # Datos adicionales para gráficos en tiempo real
    votos_por_tipo = list(Votante.objects.filter(ya_voto=True).values('tipo_persona').annotate(total=Count('id')))
    
    data = {
        'total_votantes': estadisticas.total_votantes,
        'total_votos': estadisticas.total_votos_emitidos,
        'porcentaje_participacion': float(estadisticas.porcentaje_participacion),
        'votos_estudiantes': estadisticas.votos_estudiantes,
        'votos_docentes': estadisticas.votos_docentes,
        'votos_graduados': estadisticas.votos_graduados,
        'votos_por_tipo': votos_por_tipo,
        'ultima_actualizacion': estadisticas.ultima_actualizacion.isoformat(),
    }
    return JsonResponse(data)

# Registrar URLs personalizadas
def get_admin_urls():
    from django.urls import path
    urls = [
        path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
        path('estadisticas-json/', admin.site.admin_view(estadisticas_json), name='estadisticas_json'),
    ]
    return urls

# Agregar URLs personalizadas al admin
original_get_urls = admin.site.get_urls

def get_urls():
    return get_admin_urls() + original_get_urls()

admin.site.get_urls = get_urls
