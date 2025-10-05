from datetime import datetime
from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import ResultadoVotacion, Votante, TipoConsejo, Plancha, Candidato, Voto, EstadisticaVotacion
from .utils.generar_reporte import generar_reporte_pdf

@admin.register(Votante)
class VotanteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'documento', 'tipo_persona', 'tipo_votante', 'ya_voto', 'fecha_voto', 'ip_votacion', 'acciones_jurado']
    list_filter = ['tipo_persona', 'tipo_votante', 'ya_voto', 'fecha_voto']
    search_fields = ['nombre', 'documento']
    # Removemos readonly_fields del nivel de clase
    actions = ['marcar_como_votado_fisico', 'desmarcar_voto']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'documento', 'tipo_persona', 'tipo_votante')
        }),
        ('Estado de Votación', {
            'fields': ('ya_voto', 'ip_votacion', 'fecha_voto')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Controlar campos readonly según el tipo de usuario"""
        # Campos que siempre son readonly para todos
        base_readonly = ['created_at', 'updated_at']
        
        if request.user.is_superuser:
            # Los superusuarios solo tienen readonly los timestamps
            return base_readonly
        else:
            # Los usuarios normales tienen readonly casi todos los campos importantes
            return base_readonly + [
                'fecha_voto', 
                'ya_voto', 
                'ip_votacion',
                'nombre', 
                'documento', 
                'tipo_persona', 
                'tipo_votante'
            ]
    
    def acciones_jurado(self, obj):
        """Botones de acción para el jurado"""
        if obj.ya_voto:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Votó</span><br>'
                '<small style="color: #666;">{}</small>',
                'Virtual' if obj.ip_votacion else 'Físico'
            )
        else:
            return format_html(
                '<a class="button" href="{}?ids={}" '
                'style="display: inline-block; background: linear-gradient(90deg, #e31e24 0%, #ff5f6d 100%); '
                'color: #fff !important; padding: 5px 12px; border: none; border-radius: 5px; font-size: 12px; '
                'font-weight: 600; box-shadow: 0 2px 8px rgba(227,30,36,0.12); transition: background 0.2s; '
                'text-decoration: none; cursor: pointer;">'
                '<span style="vertical-align: middle; margin-right: 5px;">'
                '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="white" viewBox="0 0 24 24" style="display:inline-block;vertical-align:middle;"><path d="M19 7V4a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v3H2v2h2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9h2V7h-3zm-10 0V4h6v3h-6zm10 13H5V9h14v11zm-7-9v4h2v-4h3l-4-4-4 4h3z"/></svg>'
                '</span>'
                '<span style="color: #fff !important; vertical-align: middle;">Confirmar voto fisico</span></a>',
                reverse('admin:marcar_voto_fisico'),
                obj.id
            )
    acciones_jurado.short_description = 'Acciones Jurado'
    acciones_jurado.allow_tags = True
    
    def marcar_como_votado_fisico(self, request, queryset):
        """Acción para marcar votantes como votados físicamente"""
        count = 0
        for votante in queryset:
            if not votante.ya_voto:
                votante.marcar_como_votado(ip_address=None)  # None indica voto físico
                votante.tipo_votante = 'presencial'
                votante.save()
                count += 1
        
        self.message_user(
            request, 
            f'{count} votante(s) marcado(s) como votado(s) físicamente.',
            messages.SUCCESS
        )
    marcar_como_votado_fisico.short_description = "Marcar como votado físico"
    
    def desmarcar_voto(self, request, queryset):
        """Acción para desmarcar votantes (solo en casos especiales)"""
        if not request.user.is_superuser:
            self.message_user(
                request,
                'Solo los superusuarios pueden desmarcar votos.',
                messages.ERROR
            )
            return
        
        count = 0
        for votante in queryset:
            if votante.ya_voto:
                # Eliminar votos asociados
                Voto.objects.filter(votante=votante).delete()
                # Desmarcar votante
                votante.ya_voto = False
                votante.ip_votacion = None
                votante.fecha_voto = None
                votante.save()
                count += 1
        
        self.message_user(
            request,
            f'{count} votante(s) desmarcado(s). Sus votos han sido eliminados.',
            messages.WARNING
        )
    desmarcar_voto.short_description = "⚠️ Desmarcar voto (Solo Superusuarios)"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def get_actions(self, request):
        """Filtrar acciones según el tipo de usuario"""
        actions = super().get_actions(request)
        
        # Solo mostrar la acción de desmarcar voto a superusuarios
        if not request.user.is_superuser and 'desmarcar_voto' in actions:
            del actions['desmarcar_voto']
        
        return actions

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
    list_display = ['numero', 'nombre', 'tipo_consejo', 'tipo_persona', 'total_votos', 'activa'
]
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

# Vista especial para manejo de jurado
def vista_jurado(request):
    """Vista especial para que el jurado marque votantes"""
    if request.method == 'POST':
        documento = request.POST.get('documento', '').strip()
        if documento:
            try:
                with transaction.atomic():
                    votante = get_object_or_404(Votante, documento=documento)
                    
                    if votante.ya_voto:
                        messages.error(
                            request, 
                            f'{votante.nombre} ya ha ejercido su derecho al voto.'
                        )
                    else:
                        votante.marcar_como_votado(ip_address=None)  # Voto físico
                        votante.tipo_votante = 'presencial'
                        votante.save()
                        
                        messages.success(
                            request,
                            f'✓ {votante.nombre} marcado como votado físicamente.'
                        )
                        
                        # Actualizar estadísticas
                        EstadisticaVotacion.actualizar_estadisticas()
                        
            except Votante.DoesNotExist:
                messages.error(
                    request,
                    f'No se encontró votante con documento: {documento}'
                )
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    
    # Obtener estadísticas rápidas
    total_votantes = Votante.objects.count()
    ya_votaron = Votante.objects.filter(ya_voto=True).count()
    votos_fisicos = Votante.objects.filter(ya_voto=True, ip_votacion__isnull=True).count()
    votos_virtuales = Votante.objects.filter(ya_voto=True, ip_votacion__isnull=False).count()
    
    # Últimos votantes marcados
    ultimos_votos = Votante.objects.filter(ya_voto=True).order_by('-fecha_voto')[:10]
    
    context = {
        'title': 'Panel del Jurado - Voto Físico',
        'opts': {'app_label': 'votaciones'},
        'has_permission': True,
        'total_votantes': total_votantes,
        'ya_votaron': ya_votaron,
        'votos_fisicos': votos_fisicos,
        'votos_virtuales': votos_virtuales,
        'porcentaje_participacion': round((ya_votaron / total_votantes * 100) if total_votantes > 0 else 0, 1),
        'ultimos_votos': ultimos_votos,
    }
    
    return render(request, 'admin/vista_jurado.html', context)

def marcar_voto_fisico(request):
    """Vista para marcar voto físico individual"""
    if request.method == 'POST':
        votante_ids = request.POST.getlist('ids')
        count = 0
        
        for votante_id in votante_ids:
            try:
                votante = get_object_or_404(Votante, id=votante_id)
                if not votante.ya_voto:
                    votante.marcar_como_votado(ip_address=None)
                    votante.tipo_votante = 'presencial'
                    votante.save()
                    count += 1
            except Exception as e:
                messages.error(request, f'Error con votante {votante_id}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'{count} votante(s) marcado(s) como votado(s) físicamente.')
        
        return HttpResponseRedirect(reverse('admin:votaciones_votante_changelist'))
    
    # Obtener IDs de la URL
    ids = request.GET.get('ids', '').split(',')
    votantes = Votante.objects.filter(id__in=ids, ya_voto=False)
    
    context = {
        'title': 'Confirmar Voto Físico',
        'votantes': votantes,
        'opts': {'app_label': 'votaciones'},
    }
    
    return render(request, 'admin/confirmar_voto_fisico.html', context)

def buscar_votante_api(request):
    """API para búsqueda rápida de votantes"""
    query = request.GET.get('q', '').strip()
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    votantes = Votante.objects.filter(
        Q(documento__icontains=query) | Q(nombre__icontains=query)
    )[:10]
    
    results = []
    for votante in votantes:
        results.append({
            'id': votante.id,
            'documento': votante.documento,
            'nombre': votante.nombre,
            'tipo_persona': votante.get_tipo_persona_display(),
            'ya_voto': votante.ya_voto,
            'tipo_voto': 'Virtual' if votante.ip_votacion else 'Físico' if votante.ya_voto else 'No ha votado'
        })
    
    return JsonResponse({'results': results})

# Agregar URLs personalizadas
def get_admin_urls():
    from django.urls import path
    urls = [
        path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
        path('estadisticas-json/', admin.site.admin_view(estadisticas_json), name='estadisticas_json'),
        path('marcar-voto-fisico/', admin.site.admin_view(marcar_voto_fisico), name='marcar_voto_fisico'),
        path('buscar-votante/', admin.site.admin_view(buscar_votante_api), name='buscar_votante_api'),
        path('reporte-pdf/', admin.site.admin_view(generar_reporte_pdf), name='reporte_pdf'),
    ]
    return urls

# Agregar URLs personalizadas al admin
original_get_urls = admin.site.get_urls

def get_urls():
    return get_admin_urls() + original_get_urls()

admin.site.get_urls = get_urls
