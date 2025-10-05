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
from .models import Votante, Plancha, TipoConsejo, Voto, EstadisticaVotacion, ResultadoVotacion

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
                
                # NUEVA VALIDACIÓN: Verificar si es votante presencial
                if votante.debe_votar_presencial():
                    messages.error(
                        request, 
                        f'Estimado/a {votante.nombre}, su perfil está configurado para votación PRESENCIAL. '
                        'Debe dirigirse a las urnas físicas habilitadas en la institución para ejercer su derecho al voto. '
                        'NO puede votar a través de este sistema virtual. '
                        'Consulte con el personal electoral sobre la ubicación de las urnas.'
                    )
                    
                    # Log de intento de acceso virtual por votante presencial
                    import logging
                    logger = logging.getLogger('votaciones.seguridad')
                    logger.warning(
                        f'Intento de acceso virtual bloqueado. Votante presencial: {votante.nombre} '
                        f'({votante.documento}), Tipo: {votante.tipo_votante}, IP: {get_client_ip(request)}'
                    )
                    
                    # Retornar al formulario con el error
                    return render(request, 'votaciones/index.html', {'form': form})
                
                # Si llegó aquí, es un votante virtual válido
                # Guardar datos del votante en la sesión
                request.session['votante_id'] = votante.id
                request.session['votante_nombre'] = votante.nombre
                request.session['votante_tipo'] = votante.tipo_persona
                request.session['votante_documento'] = votante.documento
                
                messages.success(request, f'¡Bienvenido/a {votante.nombre}! Puede proceder a votar virtualmente.')
                
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
    
    # NUEVA VALIDACIÓN: Verificar que el votante en sesión pueda votar virtualmente
    try:
        votante_id = request.session['votante_id']
        votante = get_object_or_404(Votante, id=votante_id)
        
        if votante.debe_votar_presencial():
            messages.error(
                request,
                'Su perfil está configurado para votación presencial. '
                'No puede acceder al sistema virtual de votación.'
            )
            request.session.flush()  # Limpiar sesión
            return redirect('votaciones:index')
            
        if votante.ya_voto:
            messages.error(request, 'Usted ya ha ejercido su derecho al voto.')
            request.session.flush()
            return redirect('votaciones:index')
            
    except Exception as e:
        messages.error(request, 'Error validando acceso. Intente nuevamente.')
        request.session.flush()
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
    
    # NUEVA VALIDACIÓN: Verificar que el votante en sesión pueda votar virtualmente
    try:
        votante_id = request.session['votante_id']
        votante = get_object_or_404(Votante, id=votante_id)
        
        if votante.debe_votar_presencial():
            messages.error(
                request,
                'Su perfil está configurado para votación presencial. '
                'No puede acceder al sistema virtual de votación.'
            )
            request.session.flush()  # Limpiar sesión
            return redirect('votaciones:index')
            
        if votante.ya_voto:
            messages.error(request, 'Usted ya ha ejercido su derecho al voto.')
            request.session.flush()
            return redirect('votaciones:index')
            
    except Exception as e:
        messages.error(request, 'Error validando acceso. Intente nuevamente.')
        request.session.flush()
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
    
    # NUEVA VALIDACIÓN: Verificar que el votante en sesión pueda votar virtualmente
    try:
        votante_id = request.session['votante_id']
        votante = get_object_or_404(Votante, id=votante_id)
        
        if votante.debe_votar_presencial():
            messages.error(
                request,
                'Su perfil está configurado para votación presencial. '
                'No puede acceder al sistema virtual de votación.'
            )
            request.session.flush()  # Limpiar sesión
            return redirect('votaciones:index')
            
        if votante.ya_voto:
            messages.error(request, 'Usted ya ha ejercido su derecho al voto.')
            request.session.flush()
            return redirect('votaciones:index')
            
    except Exception as e:
        messages.error(request, 'Error validando acceso. Intente nuevamente.')
        request.session.flush()
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
                
                # NUEVA VALIDACIÓN: Verificar si es un votante presencial intentando votar virtualmente
                if votante.debe_votar_presencial() and ip_cliente:
                    messages.error(
                        request, 
                        'Su perfil está configurado para votación presencial. '
                        'Debe dirigirse a las urnas físicas para ejercer su derecho al voto. '
                        'No puede votar a través del sistema virtual.'
                    )
                    
                    # Log de seguridad
                    import logging
                    logger = logging.getLogger('votaciones.seguridad')
                    logger.warning(
                        f'Intento de voto virtual por votante presencial. '
                        f'Votante: {votante.nombre} ({votante.documento}), '
                        f'Tipo configurado: {votante.tipo_votante}, IP: {ip_cliente}'
                    )
                    
                    return redirect('votaciones:index')
                
                # Verificar si ya existe un voto desde esta IP (solo para votos virtuales)
                if ip_cliente and Votante.verificar_ip_duplicada(ip_cliente):
                    # Obtener información de los votantes previos desde esta IP
                    votantes_previos = Votante.obtener_votantes_por_ip(ip_cliente)
                    nombres_previos = [v.nombre for v in votantes_previos[:3]]  # Máximo 3 nombres
                    
                    if len(nombres_previos) == 1:
                        mensaje_error = f'Ya se ha registrado un voto desde esta dirección IP por parte de: {nombres_previos[0]}. Por seguridad, no se permite votar desde la misma IP múltiples veces.'
                    else:
                        nombres_texto = ', '.join(nombres_previos[:-1]) + f' y {nombres_previos[-1]}'
                        if len(votantes_previos) > 3:
                            nombres_texto += f' (y {len(votantes_previos) - 3} más)'
                        mensaje_error = f'Ya se han registrado votos desde esta dirección IP por parte de: {nombres_texto}. Por seguridad, no se permite votar desde la misma IP múltiples veces.'
                    
                    messages.error(request, mensaje_error)
                    
                    # Log de seguridad
                    import logging
                    logger = logging.getLogger('votaciones.seguridad')
                    logger.warning(f'Intento de voto duplicado desde IP {ip_cliente}. Votante: {votante.nombre} ({votante.documento}). Votos previos: {len(votantes_previos)}')
                    
                    return redirect('votaciones:index')
                
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
                                # Crear voto temporal
                                voto = Voto.objects.create(
                                    votante=votante,
                                    plancha=plancha,
                                    tipo_consejo=consejo,
                                    ip_votacion=ip_cliente
                                )
                                
                                # Registrar inmediatamente en ResultadoVotacion
                                ResultadoVotacion.registrar_voto(
                                    plancha=plancha,
                                    tipo_consejo=consejo,
                                    tipo_persona=votante.tipo_persona
                                )
                                
                                # Marcar como contabilizado
                                voto.contabilizado = True
                                voto.save()
                                
                                votos_procesados += 1
                        except Exception as e:
                            messages.error(request, f'Error procesando voto para {consejo.nombre}: {str(e)}')
                            return redirect('votaciones:index')
                
                if votos_procesados > 0:
                    # Marcar votante como votado
                    votante.marcar_como_votado(ip_cliente)
                    
                    # Limpiar sesión
                    request.session.flush()
                    
                    # Log de voto exitoso
                    import logging
                    logger = logging.getLogger('votaciones.exito')
                    tipo_voto = 'presencial' if ip_cliente is None else 'virtual'
                    logger.info(f'Voto registrado exitosamente. Votante: {votante.nombre} ({votante.documento}), Tipo: {tipo_voto}, IP: {ip_cliente or "N/A"}, Votos procesados: {votos_procesados}')
                    
                    messages.success(request, f'¡Su voto ha sido registrado exitosamente! Se procesaron {votos_procesados} votos.')
                    return redirect('votaciones:gracias')
                else:
                    messages.error(request, 'No se procesó ningún voto. Verifique su selección.')
                    return redirect('votaciones:index')
                    
        except Exception as e:
            # Log de error
            import logging
            logger = logging.getLogger('votaciones.error')
            logger.error(f'Error procesando votación. Votante ID: {votante_id}, IP: {get_client_ip(request)}, Error: {str(e)}')
            
            messages.error(request, f'Error procesando la votación: {str(e)}')
            return redirect('votaciones:index')
    
    return redirect('votaciones:index')

def gracias(request):
    """Página de agradecimiento post-voto"""
    return render(request, 'votaciones/gracias.html')

def dashboard_electoral(request):
    """Dashboard principal con métricas detalladas usando ResultadoVotacion"""
    from django.db.models import Sum
    
    # Actualizar estadísticas
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    
    # Obtener resultados detallados por categoría usando ResultadoVotacion
    def obtener_resultados_por_categoria(tipo_persona):
        consejos_data = []
        consejos = TipoConsejo.objects.filter(activo=True)
        
        for consejo in consejos:
            # Obtener resultados para este consejo y tipo de persona
            resultados = ResultadoVotacion.obtener_resultados_por_consejo(consejo, tipo_persona)
            
            # Calcular total de votos para este consejo
            total_votos = sum(r.cantidad_votos for r in resultados)
            
            # Preparar datos de planchas con porcentajes
            planchas_data = []
            for resultado in resultados:
                porcentaje = (resultado.cantidad_votos / total_votos * 100) if total_votos > 0 else 0
                planchas_data.append({
                    'numero': resultado.plancha.numero,
                    'nombre': resultado.plancha.nombre,
                    'votos': resultado.cantidad_votos,
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
    
    # Datos para gráficos usando ResultadoVotacion
    votos_por_tipo = []
    for tipo in ['estudiante', 'docente', 'graduado']:
        total = ResultadoVotacion.objects.filter(tipo_persona=tipo).aggregate(
            total=Sum('cantidad_votos')
        )['total'] or 0
        votos_por_tipo.append({
            'votante__tipo_persona': tipo,
            'total': total
        })
    
    votos_por_consejo = []
    consejos = TipoConsejo.objects.filter(activo=True)
    for consejo in consejos:
        total = ResultadoVotacion.objects.filter(tipo_consejo=consejo).aggregate(
            total=Sum('cantidad_votos')
        )['total'] or 0
        votos_por_consejo.append({
            'tipo_consejo__nombre': consejo.nombre,
            'total': total
        })
    
    votos_por_plancha = ResultadoVotacion.objects.select_related('plancha').values(
        'plancha__numero', 'plancha__nombre', 'tipo_persona'
    ).annotate(total=Sum('cantidad_votos')).order_by('-total')[:10]
    
    context = {
        'estadisticas': estadisticas,
        'resultados_estudiantes': resultados_estudiantes,
        'resultados_docentes': resultados_docentes,
        'resultados_graduados': resultados_graduados,
        'votos_por_tipo': json.dumps(votos_por_tipo),
        'votos_por_consejo': json.dumps(votos_por_consejo),
        'votos_por_plancha': votos_por_plancha,
    }
    
    return render(request, 'admin/dashboard_electoral.html', context)

@staff_member_required
def generar_reporte_pdf(request):
    """Genera reporte PDF usando ResultadoVotacion"""
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
    
    # Función para agregar resultados por categoría usando ResultadoVotacion
    def agregar_categoria_al_reporte(titulo, tipo_persona, icono=""):
        story.append(Paragraph(f"{icono} {titulo.upper()}", heading_style))
        
        consejos = TipoConsejo.objects.filter(activo=True)
        
        for consejo in consejos:
            story.append(Paragraph(f"<b>{consejo.nombre}</b>", styles['Heading3']))
            
            # Obtener resultados para este consejo
            resultados = ResultadoVotacion.obtener_resultados_por_consejo(consejo, tipo_persona)
            
            if resultados:
                total_votos = sum(r.cantidad_votos for r in resultados)
                
                # Crear tabla con resultados
                plancha_data = [['Plancha', 'Nombre', 'Votos', 'Porcentaje']]
                
                for i, resultado in enumerate(resultados):
                    porcentaje = (resultado.cantidad_votos / total_votos * 100) if total_votos > 0 else 0
                    ganador = " 👑" if i == 0 and resultado.cantidad_votos > 0 else ""
                    plancha_data.append([
                        f"#{resultado.plancha.numero}{ganador}",
                        resultado.plancha.nombre,
                        str(resultado.cantidad_votos),
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
    from django.db.models import Sum
    
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    
    # Datos para gráficos actualizados usando ResultadoVotacion
    votos_por_tipo = []
    for tipo in ['estudiante', 'docente', 'graduado']:
        total = ResultadoVotacion.objects.filter(tipo_persona=tipo).aggregate(
            total=Sum('cantidad_votos')
        )['total'] or 0
        votos_por_tipo.append({
            'votante__tipo_persona': tipo,
            'total': total
        })
    
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
