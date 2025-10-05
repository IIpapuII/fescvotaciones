def generar_reporte_pdf(request):
    """Genera reporte PDF oficial e institucional con logo de la universidad"""
    from django.http import HttpResponse
    from django.utils import timezone
    from ..models import Votante, TipoConsejo, Plancha, ResultadoVotacion, EstadisticaVotacion

    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
        from reportlab.graphics.shapes import Drawing, Line
        from reportlab.graphics import renderPDF
    except ImportError:
        # Si reportlab no está instalado, mostrar error
        response = HttpResponse(content_type='text/html')
        response.write("""
        <h1>Error: Librería no instalada</h1>
        <p>Para generar reportes PDF, debe instalar la librería reportlab:</p>
        <pre>pip install reportlab</pre>
        <p><a href="/admin/">Volver al admin</a></p>
        """)
        return response
    
    from django.conf import settings
    from django.db.models import Sum
    import os
    
    # Crear respuesta HTTP para PDF
    response = HttpResponse(content_type='application/pdf')
    fecha_actual = timezone.now()
    fecha_str = fecha_actual.strftime("%Y%m%d_%H%M")
    response['Content-Disposition'] = f'attachment; filename="acta_electoral_oficial_fesc_{fecha_str}.pdf"'
    
    # Crear documento PDF con márgenes oficiales
    doc = SimpleDocTemplate(
        response, 
        pagesize=A4,
        rightMargin=2*cm, 
        leftMargin=2*cm,
        topMargin=2*cm, 
        bottomMargin=2*cm,
        title="Acta Electoral Oficial - FESC"
    )
    
    # Contenedor para elementos del PDF
    story = []
    
    # Estilos institucionales
    styles = getSampleStyleSheet()
    
    # Estilo para encabezado institucional
    header_style = ParagraphStyle(
        'InstitutionalHeader',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo para título del documento
    title_style = ParagraphStyle(
        'DocumentTitle',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=30,
        spaceBefore=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#b71c1c'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=15,
        spaceBefore=20,
        textColor=colors.HexColor('#2d3748'),
        fontName='Helvetica-Bold'
    )
    
    # Estilo para texto oficial
    official_text_style = ParagraphStyle(
        'OfficialText',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#2d3748'),
        fontName='Helvetica'
    )
    
    # Estilo para información legal
    legal_style = ParagraphStyle(
        'LegalText',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#4a5568'),
        fontName='Helvetica'
    )
    
    # Logo institucional
    logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', 'admin', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=3*inch, height=1.5*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.5*inch))
        except:
            pass
    
    # Encabezado institucional oficial
    story.append(Paragraph("FUNDACIÓN DE ESTUDIOS SUPERIORES COMFANORTE", header_style))
    story.append(Paragraph("FESC", header_style))
    story.append(Spacer(1, 0.3*inch))

    # Título del documento
    story.append(Paragraph("ACTA OFICIAL DE RESULTADOS ELECTORALES", title_style))
    story.append(Paragraph("PROCESO ELECTORAL INSTITUCIONAL", subtitle_style))
    
    # Información del documento
    estadisticas = EstadisticaVotacion.actualizar_estadisticas()
    fecha_reporte = fecha_actual.strftime("%d de %B de %Y")
    hora_reporte = fecha_actual.strftime("%H:%M")
    
    # Encabezado del acta
    story.append(Paragraph("INFORMACIÓN DEL PROCESO ELECTORAL", subtitle_style))
    
    info_oficial = f"""
    Por medio del presente documento, la Fundación de Estudios Superiores Comfanorte (FESC), 
    en cumplimiento de su normativa institucional y en ejercicio de la democracia participativa, 
    certifica los resultados oficiales del proceso electoral llevado a cabo mediante el Sistema 
    Electoral Digital Institucional.
    """
    story.append(Paragraph(info_oficial, official_text_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Datos oficiales del proceso - MEJORADO
    info_data = [
        ['FECHA DE GENERACIÓN:', f"{fecha_reporte}"],
        ['HORA DE GENERACIÓN:', f"{hora_reporte}"],
        ['VOTANTES HABILITADOS:', f"{estadisticas.total_votantes:,}"],
        ['VOTOS VÁLIDOS EMITIDOS:', f"{estadisticas.total_votos_emitidos:,}"],
        ['PARTICIPACIÓN ELECTORAL:', f"{estadisticas.porcentaje_participacion:.2f}%"],
        ['VOTOS ESTUDIANTES:', f"{estadisticas.votos_estudiantes:,}"],
        ['VOTOS DOCENTES:', f"{estadisticas.votos_docentes:,}"],
        ['VOTOS GRADUADOS:', f"{estadisticas.votos_graduados:,}"],
    ]
    
    # Crear tabla con mejor formato
    info_table = Table(info_data, colWidths=[5.5*cm, 4.5*cm])
    info_table.setStyle(TableStyle([
        # Encabezado de toda la tabla
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Fuentes y tamaños
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        
        # Espaciado y padding
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        
        # Colores de fondo alternados
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4f8')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e8f4f8')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#e8f4f8')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.white),
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#e8f4f8')),
        ('BACKGROUND', (0, 7), (-1, 7), colors.white),
        
        # Bordes principales
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1a365d')),
        ('INNERGRID', (0, 0), (-1, -1), 0.8, colors.HexColor('#cbd5e0')),
        
        # Destacar información importante
        ('TEXTCOLOR', (0, 4), (0, 4), colors.HexColor('#b71c1c')),  # Participación
        ('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'),  # Porcentaje participación
        ('TEXTCOLOR', (1, 4), (1, 4), colors.HexColor('#b71c1c')),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.4*inch))
    
    # Agregar resumen estadístico adicional
    story.append(Paragraph("RESUMEN ESTADÍSTICO", subtitle_style))
    
    # Calcular totales por tipo de voto
    votos_fisicos = Votante.objects.filter(ya_voto=True, ip_votacion__isnull=True).count()
    votos_virtuales = Votante.objects.filter(ya_voto=True, ip_votacion__isnull=False).count()
    
    resumen_data = [
        ['MODALIDAD DE VOTACIÓN', 'CANTIDAD', 'PORCENTAJE'],
        ['Votos Presenciales (Físicos)', f"{votos_fisicos:,}", f"{(votos_fisicos/estadisticas.total_votos_emitidos*100):.1f}%" if estadisticas.total_votos_emitidos > 0 else "0%"],
        ['Votos Virtuales (Digitales)', f"{votos_virtuales:,}", f"{(votos_virtuales/estadisticas.total_votos_emitidos*100):.1f}%" if estadisticas.total_votos_emitidos > 0 else "0%"],
        ['TOTAL VOTOS EMITIDOS', f"{estadisticas.total_votos_emitidos:,}", "100%"],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[5*cm, 2.5*cm, 2.5*cm])
    resumen_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Contenido
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        
        # Fila total
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f8ff')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1a365d')),
        
        # Espaciado
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Bordes
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#1a365d')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        
        # Filas alternadas
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.white),
    ]))
    
    story.append(resumen_table)
    story.append(Spacer(1, 0.4*inch))
    
    # Función para agregar resultados por categoría con formato oficial
    def agregar_categoria_oficial(titulo, tipo_persona, icono=""):
        story.append(PageBreak())  # Nueva página para cada categoría
        story.append(Paragraph(f"RESULTADOS OFICIALES - {titulo.upper()}", subtitle_style))
        
        categoria_intro = f"""
        A continuación se presentan los resultados oficiales correspondientes a la categoría de 
        {titulo.lower()}, organizados por tipo de consejo y en orden descendente según la 
        cantidad de votos obtenidos por cada plancha electoral.
        """
        story.append(Paragraph(categoria_intro, official_text_style))
        story.append(Spacer(1, 0.2*inch))
        
        consejos = TipoConsejo.objects.filter(activo=True)
        
        for consejo in consejos:
            story.append(Paragraph(f"CONSEJO: {consejo.nombre.upper()}", 
                         ParagraphStyle('ConsejoTitle', parent=subtitle_style, fontSize=12, 
                                      textColor=colors.HexColor('#b71c1c'))))
            
            # Obtener resultados para este consejo usando ResultadoVotacion
            resultados = ResultadoVotacion.obtener_resultados_por_consejo(consejo, tipo_persona)
            
            if resultados:
                total_votos = sum(r.cantidad_votos for r in resultados)
                
                # Crear tabla con resultados oficiales
                plancha_data = [['POSICIÓN', 'PLANCHA N°', 'NOMBRE DE LA PLANCHA', 'VOTOS OBTENIDOS', 'PORCENTAJE']]
                
                for i, resultado in enumerate(resultados, 1):
                    porcentaje = (resultado.cantidad_votos / total_votos * 100) if total_votos > 0 else 0
                    posicion = f"{i}°"
                    if i == 1 and resultado.cantidad_votos > 0:
                        posicion += " 🏆"
                    
                    plancha_data.append([
                        posicion,
                        f"#{resultado.plancha.numero}",
                        resultado.plancha.nombre,
                        f"{resultado.cantidad_votos:,}",
                        f"{porcentaje:.2f}%"
                    ])
                
                plancha_table = Table(plancha_data, colWidths=[2*cm, 2*cm, 6*cm, 3*cm, 2.5*cm])
                plancha_table.setStyle(TableStyle([
                    # Encabezado
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    
                    # Contenido
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    
                    # Ganador destacado
                    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0fff4')),
                    ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#22543d')),
                    ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                    
                    # Bordes y grillas
                    ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1a365d')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#a0aec0')),
                    
                    # Filas alternadas
                    ('BACKGROUND', (0, 2), (-1, -1), colors.HexColor('#f8f9fa')),
                ]))
                
                # Aplicar color alternado a filas
                for row in range(2, len(plancha_data)):
                    if row % 2 == 0:
                        plancha_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, row), (-1, row), colors.white)
                        ]))
                
                story.append(plancha_table)
                
                # Resumen del consejo
                resumen = f"Total de votos válidos para {consejo.nombre}: {total_votos:,}"
                story.append(Spacer(1, 0.15*inch))
                story.append(Paragraph(resumen, 
                           ParagraphStyle('Resumen', parent=official_text_style, 
                                        fontName='Helvetica-Bold', fontSize=10,
                                        textColor=colors.HexColor('#2d3748'))))
            else:
                story.append(Paragraph("No se registraron votos para este consejo.", official_text_style))
            
            story.append(Spacer(1, 0.3*inch))
    
    # Agregar secciones por categoría
    agregar_categoria_oficial("Estudiantes", "estudiante", "🎓")
    agregar_categoria_oficial("Docentes", "docente", "👨‍🏫")
    agregar_categoria_oficial("Graduados", "graduado", "👨‍🎓")
    
    # Página final con certificaciones
    story.append(PageBreak())
    story.append(Paragraph("CERTIFICACIÓN Y VALIDEZ DEL DOCUMENTO", subtitle_style))
    
    certificacion = f"""
    El presente Acta Oficial de Resultados Electorales constituye el documento formal y definitivo 
    que certifica los resultados del proceso electoral institucional de la Fundación de Estudios 
    Superiores Comfanorte (FESC), realizado mediante el Sistema Electoral Digital Institucional.
    
    Los datos aquí consignados corresponden al estado final del proceso electoral al momento de 
    la generación de este documento ({fecha_reporte} a las {hora_reporte}) y han sido verificados 
    mediante los mecanismos de control y auditoria establecidos en la normativa institucional.
    
    Este documento tiene plena validez legal e institucional para todos los efectos académicos 
    y administrativos derivados del proceso electoral.
    """
    story.append(Paragraph(certificacion, official_text_style))
    story.append(Spacer(1, 0.4*inch))
    
    # Información técnica del sistema
    story.append(Paragraph("INFORMACIÓN TÉCNICA DEL SISTEMA", subtitle_style))
    
    info_tecnica = f"""
    • Sistema: Plataforma Electoral Digital FESC
    • Fecha de generación: {fecha_reporte} a las {hora_reporte}
    • Documento generado automáticamente por el sistema
    • Integridad de datos verificada mediante controles internos
    • Este documento es una representación fiel de los datos almacenados en el sistema electoral
    """
    story.append(Paragraph(info_tecnica, legal_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Firma digital institucional
    story.append(Paragraph("____________________________________", 
                 ParagraphStyle('Firma', parent=styles['Normal'], alignment=TA_CENTER)))
    story.append(Paragraph("SISTEMA ELECTORAL DIGITAL FESC", 
                 ParagraphStyle('FirmaText', parent=legal_style, alignment=TA_CENTER, 
                              fontName='Helvetica-Bold')))
    story.append(Paragraph(f"Documento generado automáticamente el {fecha_reporte}", 
                 ParagraphStyle('FechaFirma', parent=legal_style, alignment=TA_CENTER)))
    
    # Pie de página con información legal
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "Este documento ha sido generado automáticamente por el Sistema Electoral Digital de la "
        "Fundación de Estudios Superiores Comfanorte (FESC) y constituye el registro oficial "
        "de los resultados electorales institucionales.",
        ParagraphStyle('PiePagina', parent=legal_style, alignment=TA_CENTER, 
                      fontSize=8, textColor=colors.HexColor('#718096'))
    ))
    
    # Construir PDF
    try:
        doc.build(story)
    except Exception as e:
        # En caso de error, generar un PDF simple con el error
        simple_story = [
            Paragraph("Error generando reporte completo", title_style),
            Paragraph(f"Error: {str(e)}", official_text_style),
            Paragraph("Se ha generado un reporte básico con las estadísticas disponibles.", official_text_style),
            Spacer(1, 0.2*inch)
        ]
        
        # Agregar estadísticas básicas
        for item in info_data:
            simple_story.append(Paragraph(f"{item[0]} {item[1]}", official_text_style))
        
        doc.build(simple_story)
    
    return response
