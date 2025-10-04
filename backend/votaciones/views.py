from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.template.loader import get_template
from django.contrib.admin.views.decorators import staff_member_required
from collections import defaultdict
from datetime import datetime
import json

from .forms import ValidacionIngresoForm
from .models import Votante, Plancha, TipoConsejo, Voto, EstadisticaVotacion

def get_client_ip(request):
    """Obtiene la IP real del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def index(request):
    """Vista principal con formulario de validación de ingreso"""
    if request.method == 'POST':
        form = ValidacionIngresoForm(request.POST)
        if form.is_valid():
            try:
                votante = form.validar_votante()
                # Guardar datos del votante en la sesión
                request.session['votante_id'] = votante.id
                request.session['votante_nombre'] = votante.nombre
                request.session['votante_tipo'] = votante.tipo_persona
                request.session['votante_documento'] = votante.documento
                
                messages.success(request, f'¡Bienvenido/a {votante.nombre}!')
                
                # Redirigir según el tipo de persona
                if votante.tipo_persona == 'estudiante':
                    return redirect('votaciones:tarjeton_estudiantes')
                elif votante.tipo_persona == 'docente':
                    return redirect('votaciones:tarjeton_docentes')
                elif votante.tipo_persona == 'graduado':
                    return redirect('votaciones:tarjeton_graduados')
                else:
                    return redirect('votaciones:tarjetones')
                
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = ValidacionIngresoForm()
    
    return render(request, 'votaciones/index.html', {'form': form})

def tarjeton_estudiantes(request):
    """Vista de tarjetón para estudiantes"""
    if 'votante_id' not in request.session or request.session.get('votante_tipo') != 'estudiante':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('votaciones:index')
    
    # Obtener planchas para estudiantes agrupadas por consejo
    planchas = Plancha.objects.filter(
        tipo_persona='estudiante',
        activa=True
    ).select_related('tipo_consejo').prefetch_related('candidatos')
    
    # Agrupar por tipo de consejo
    planchas_por_consejo = defaultdict(list)
    for plancha in planchas:
        planchas_por_consejo[plancha.tipo_consejo].append(plancha)
    
    context = {
        'votante_nombre': request.session['votante_nombre'],
        'votante_tipo': 'Estudiante',
        'tipo_tarjeton': 'estudiantes',
        'planchas_por_consejo': dict(planchas_por_consejo)
    }
    
    return render(request, 'votaciones/tarjeton_estudiantes.html', context)

def tarjeton_docentes(request):
    """Vista de tarjetón para docentes"""
    if 'votante_id' not in request.session or request.session.get('votante_tipo') != 'docente':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('votaciones:index')
    
    # Obtener planchas para docentes agrupadas por consejo
    planchas = Plancha.objects.filter(
        tipo_persona='docente',
        activa=True
    ).select_related('tipo_consejo').prefetch_related('candidatos')
    
    # Agrupar por tipo de consejo
    planchas_por_consejo = defaultdict(list)
    for plancha in planchas:
        planchas_por_consejo[plancha.tipo_consejo].append(plancha)
    
    context = {
        'votante_nombre': request.session['votante_nombre'],
        'votante_tipo': 'Docente',
        'tipo_tarjeton': 'docentes',
        'planchas_por_consejo': dict(planchas_por_consejo)
    }
    
    return render(request, 'votaciones/tarjeton_docentes.html', context)

def tarjeton_graduados(request):
    """Vista de tarjetón para graduados"""
    if 'votante_id' not in request.session or request.session.get('votante_tipo') != 'graduado':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('votaciones:index')
    
    # Obtener planchas para graduados agrupadas por consejo
    planchas = Plancha.objects.filter(
        tipo_persona='graduado',
        activa=True
    ).select_related('tipo_consejo').prefetch_related('candidatos')
    
    # Agrupar por tipo de consejo
    planchas_por_consejo = defaultdict(list)
    for plancha in planchas:
        planchas_por_consejo[plancha.tipo_consejo].append(plancha)
    
    context = {
        'votante_nombre': request.session['votante_nombre'],
        'votante_tipo': 'Graduado',
        'tipo_tarjeton': 'graduados',
        'planchas_por_consejo': dict(planchas_por_consejo)
    }
    
    return render(request, 'votaciones/tarjeton_graduados.html', context)

def procesar_voto(request):
    """Procesa el voto y marca al votante como votado"""
    if 'votante_id' not in request.session:
        messages.error(request, 'Sesión expirada. Debe validar su ingreso nuevamente.')
        return redirect('votaciones:index')
    
    if request.method == 'POST':
        votante_id = request.session['votante_id']
        
        try:
            with transaction.atomic():
                votante = get_object_or_404(Votante, id=votante_id)
                
                if votante.ya_voto:
                    messages.error(request, 'Usted ya ha ejercido su derecho al voto.')
                    return redirect('votaciones:index')
                
                # Obtener IP del cliente
                ip_cliente = get_client_ip(request)
                
                # Procesar votos por cada consejo
                votos_procesados = 0
                
                for key, value in request.POST.items():
                    if key.startswith('voto_'):
                        consejo_id = key.split('_')[1]
                        plancha_id = value
                        
                        try:
                            consejo = get_object_or_404(TipoConsejo, id=consejo_id)
                            plancha = get_object_or_404(Plancha, id=plancha_id, tipo_persona=votante.tipo_persona)
                            
                            # Verificar que no haya votado ya en este consejo
                            if not Voto.objects.filter(votante=votante, tipo_consejo=consejo).exists():
                                Voto.objects.create(
                                    votante=votante,
                                    plancha=plancha,
                                    tipo_consejo=consejo,
                                    ip_votacion=ip_cliente
                                )
                                votos_procesados += 1
                        except Exception as e:
                            messages.error(request, f'Error procesando voto para {consejo.nombre}: {str(e)}')
                            return redirect('votaciones:index')
                
                if votos_procesados > 0:
                    # Marcar votante como votado
                    votante.marcar_como_votado(ip_cliente)
                    
                    # Limpiar sesión
                    request.session.flush()
                    
                    messages.success(request, f'¡Su voto ha sido registrado exitosamente! Se procesaron {votos_procesados} votos.')
                    return redirect('votaciones:gracias')
                else:
                    messages.error(request, 'No se procesó ningún voto. Verifique su selección.')
                    return redirect('votaciones:index')
                    
        except Exception as e:
            messages.error(request, f'Error procesando la votación: {str(e)}')
            return redirect('votaciones:index')
    
    return redirect('votaciones:index')

def gracias(request):
    """Página de agradecimiento post-voto"""
    return render(request, 'votaciones/gracias.html')

def dashboard_electoral(request):
    """Dashboard principal con métricas detalladas"""
    from django.db.models import Count, Q
    
    # Actualizar estadísticas
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    
    # Obtener resultados detallados por categoría
    def obtener_resultados_por_categoria(tipo_persona):
        consejos_data = []
        consejos = TipoConsejo.objects.filter(activo=True)
        
        for consejo in consejos:
            # Obtener planchas para este consejo y tipo de persona
            planchas = Plancha.objects.filter(
                tipo_consejo=consejo,
                tipo_persona=tipo_persona,
                activa=True
            ).annotate(
                votos_count=Count('voto', filter=Q(voto__votante__tipo_persona=tipo_persona))
            ).order_by('-votos_count', 'numero')
            
            # Calcular total de votos para este consejo
            total_votos = sum(p.votos_count for p in planchas)
            
            # Preparar datos de planchas con porcentajes
            planchas_data = []
            for plancha in planchas:
                porcentaje = (plancha.votos_count / total_votos * 100) if total_votos > 0 else 0
                planchas_data.append({
                    'numero': plancha.numero,
                    'nombre': plancha.nombre,
                    'votos': plancha.votos_count,
                    'porcentaje': round(porcentaje, 1)
                })
            
            consejos_data.append({
                'nombre': consejo.nombre,
                'total_votos': total_votos,
                'planchas': planchas_data
            })
        
        return consejos_data
    
    # Obtener datos por categoría
    resultados_estudiantes = obtener_resultados_por_categoria('estudiante')
    resultados_docentes = obtener_resultados_por_categoria('docente')
    resultados_graduados = obtener_resultados_por_categoria('graduado')
    
    # Datos para gráficos (manteniendo la lógica existente)
    votos_por_tipo = Voto.objects.values('votante__tipo_persona').annotate(
        total=Count('id')
    ).order_by('-total')
    
    votos_por_consejo = Voto.objects.values('tipo_consejo__nombre').annotate(
        total=Count('id')
    ).order_by('-total')
    
    votos_por_plancha = Voto.objects.values(
        'plancha__numero', 'plancha__nombre', 'plancha__tipo_persona'
    ).annotate(total=Count('id')).order_by('-total')[:10]
    
    context = {
        'estadisticas': estadisticas,
        'resultados_estudiantes': resultados_estudiantes,
        'resultados_docentes': resultados_docentes,
        'resultados_graduados': resultados_graduados,
        'votos_por_tipo': json.dumps(list(votos_por_tipo)),
        'votos_por_consejo': json.dumps(list(votos_por_consejo)),
        'votos_por_plancha': votos_por_plancha,
    }
    
    return render(request, 'admin/dashboard_electoral.html', context)

@staff_member_required
def generar_reporte_pdf(request):
    """Genera reporte PDF con logo de la universidad"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from django.conf import settings
    from django.db.models import Count, Q
    import os
    
    # Crear respuesta HTTP para PDF
    response = HttpResponse(content_type='application/pdf')
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = f'attachment; filename="reporte_electoral_fesc_{fecha_actual}.pdf"'
    
    # Crear documento PDF
    doc = SimpleDocTemplate(response, pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Contenedor para elementos del PDF
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#b71c1c')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#b71c1c')
    )
    
    # Logo de la universidad (si existe)
    logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', 'admin', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=2*inch, height=1*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 20))
        except:
            pass
    
    # Encabezado del reporte
    story.append(Paragraph("FUNDACIÓN DE ESTUDIOS SUPERIORES COMFANORTE", title_style))
    story.append(Paragraph("REPORTE ELECTORAL OFICIAL", title_style))
    story.append(Spacer(1, 20))
    
    # Información general
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    fecha_reporte = datetime.now().strftime("%d de %B de %Y a las %H:%M")
    
    info_data = [
        ['Fecha del reporte:', fecha_reporte],
        ['Total votantes registrados:', str(estadisticas.total_votantes)],
        ['Total votos emitidos:', str(estadisticas.total_votos_emitidos)],
        ['Porcentaje de participación:', f"{estadisticas.porcentaje_participacion:.1f}%"],
    ]
    
    info_table = Table(info_data, colWidths=[3*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 30))
    
    # Función para agregar resultados por categoría
    def agregar_categoria_al_reporte(titulo, tipo_persona, icono=""):
        story.append(Paragraph(f"{icono} {titulo.upper()}", heading_style))
        
        consejos = TipoConsejo.objects.filter(activo=True)
        
        for consejo in consejos:
            story.append(Paragraph(f"<b>{consejo.nombre}</b>", styles['Heading3']))
            
            # Obtener planchas para este consejo
            planchas = Plancha.objects.filter(
                tipo_consejo=consejo,
                tipo_persona=tipo_persona,
                activa=True
            ).annotate(
                votos_count=Count('voto', filter=Q(voto__votante__tipo_persona=tipo_persona))
            ).order_by('-votos_count', 'numero')
            
            if planchas:
                total_votos = sum(p.votos_count for p in planchas)
                
                # Crear tabla con resultados
                plancha_data = [['Plancha', 'Nombre', 'Votos', 'Porcentaje']]
                
                for plancha in planchas:
                    porcentaje = (plancha.votos_count / total_votos * 100) if total_votos > 0 else 0
                    ganador = " 👑" if plancha == planchas[0] and plancha.votos_count > 0 else ""
                    plancha_data.append([
                        f"#{plancha.numero}{ganador}",
                        plancha.nombre,
                        str(plancha.votos_count),
                        f"{porcentaje:.1f}%"
                    ])
                
                plancha_table = Table(plancha_data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 0.8*inch])
                plancha_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b71c1c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(plancha_table)
                story.append(Paragraph(f"<i>Total votos: {total_votos}</i>", styles['Normal']))
            else:
                story.append(Paragraph("Sin votos registrados", styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        story.append(Spacer(1, 20))
    
    # Agregar secciones por categoría
    agregar_categoria_al_reporte("Resultados Estudiantes", "estudiante", "🎓")
    agregar_categoria_al_reporte("Resultados Docentes", "docente", "👨‍🏫")
    agregar_categoria_al_reporte("Resultados Graduados", "graduado", "👨‍🎓")
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "Este reporte fue generado automáticamente por el Sistema Electoral FESC",
        ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=colors.grey)
    ))
    
    # Construir PDF
    doc.build(story)
    return response

@staff_member_required
def estadisticas_json(request):
    """API endpoint para actualización de estadísticas en tiempo real"""
    from django.db.models import Count
    
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    
    # Datos para gráficos actualizados
    votos_por_tipo = list(Voto.objects.values('votante__tipo_persona').annotate(
        total=Count('id')
    ).order_by('-total'))
    
    data = {
        'total_votantes': estadisticas.total_votantes,
        'total_votos': estadisticas.total_votos_emitidos,
        'porcentaje_participacion': float(estadisticas.porcentaje_participacion),
        'votos_estudiantes': estadisticas.votos_estudiantes,
        'votos_docentes': estadisticas.votos_docentes,
        'votos_graduados': estadisticas.votos_graduados,
        'ultima_actualizacion': estadisticas.ultima_actualizacion.isoformat(),
        'votos_por_tipo': votos_por_tipo,
    }
    
    return JsonResponse(data)
