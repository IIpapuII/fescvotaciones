from django.db import models
from django.utils import timezone

# Create your models here.

class Votante(models.Model):
    TIPO_PERSONA_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('graduado', 'Graduado'),
    ]
    TIPO_VOTANTE_CHOICES = [
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual'),
        ('hibrido', 'Híbrido'),
    ]
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre completo")
    documento = models.CharField(max_length=20, unique=True, verbose_name="Número de documento")
    tipo_persona = models.CharField(
        max_length=15, 
        choices=TIPO_PERSONA_CHOICES,
        verbose_name="Tipo de persona"
    )
    tipo_votante = models.CharField(
        null=True, 
        blank=True,
        max_length=15, 
        choices=TIPO_VOTANTE_CHOICES,
        verbose_name="Tipo de votante"
    )
    ya_voto = models.BooleanField(default=False, verbose_name="Ya votó")
    ip_votacion = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name="IP de votación"
    )
    fecha_voto = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha y hora de voto"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Votante"
        verbose_name_plural = "Votantes"
        ordering = ['nombre']
        indexes = [models.Index(fields=['documento']),]
        unique_together = ['documento', 'tipo_persona']
    
    def __str__(self):
        return f"{self.nombre} - {self.documento}"
    
    def marcar_como_votado(self, ip_address):
        """Marca al votante como que ya votó y registra la IP"""
        self.ya_voto = True
        self.ip_votacion = ip_address
        self.fecha_voto = timezone.now()
        
        # Determinar tipo de votante automáticamente
        if ip_address is None:
            self.tipo_votante = 'presencial'
        else:
            self.tipo_votante = 'virtual'
        
        self.save()
    
    @classmethod
    def verificar_ip_duplicada(cls, ip_address):
        """Verifica si ya existe un voto desde esta IP"""
        if ip_address is None:
            # Los votos presenciales (IP None) no se validan por IP
            return False
        
        return cls.objects.filter(
            ya_voto=True,
            ip_votacion=ip_address
        ).exists()
    
    @classmethod
    def contar_votos_por_ip(cls, ip_address):
        """Cuenta cuántos votos hay desde una IP específica"""
        if ip_address is None:
            return 0
        
        return cls.objects.filter(
            ya_voto=True,
            ip_votacion=ip_address
        ).count()
    
    @classmethod
    def obtener_votantes_por_ip(cls, ip_address):
        """Obtiene todos los votantes que han votado desde una IP específica"""
        if ip_address is None:
            return cls.objects.none()
        
        return cls.objects.filter(
            ya_voto=True,
            ip_votacion=ip_address
        ).order_by('fecha_voto')
    
    def puede_votar_virtual(self):
        """Verifica si el votante puede votar virtualmente"""
        # Si ya está configurado como presencial, no puede votar virtual
        if self.tipo_votante == 'presencial':
            return False
        return True
    
    def debe_votar_presencial(self):
        """Verifica si el votante debe votar presencialmente"""
        return self.tipo_votante == 'presencial'
    
    def get_tipo_voto_display(self):
        """Retorna una descripción amigable del tipo de voto"""
        if not self.ya_voto:
            return "No ha votado"
        elif self.ip_votacion:
            return f"Virtual (IP: {self.ip_votacion})"
        else:
            return "Físico/Presencial"

class TipoConsejo(models.Model):
    """Tipos de consejos disponibles para votar"""
    nombre = models.CharField(max_length=100, verbose_name="Nombre del consejo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Tipo de Consejo"
        verbose_name_plural = "Tipos de Consejos"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

class Plancha(models.Model):
    """Planchas candidatas por tipo de consejo y tipo de persona"""
    numero = models.PositiveIntegerField(verbose_name="Número de plancha")
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la plancha")
    tipo_consejo = models.ForeignKey(TipoConsejo, on_delete=models.CASCADE, verbose_name="Tipo de consejo")
    tipo_persona = models.CharField(
        max_length=15,
        choices=Votante.TIPO_PERSONA_CHOICES,
        verbose_name="Tipo de persona que puede votar"
    )
    imagen_tarjeton = models.ImageField(
        upload_to='tarjetones/',
        blank=True,
        null=True,
        verbose_name="Imagen del tarjetón"
    )
    activa = models.BooleanField(default=True, verbose_name="Plancha activa")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plancha"
        verbose_name_plural = "Planchas"
        ordering = ['tipo_consejo', 'numero']
        unique_together = ['numero', 'tipo_consejo', 'tipo_persona']
    
    def __str__(self):
        return f"Plancha {self.numero} - {self.nombre} ({self.tipo_consejo})"

class Candidato(models.Model):
    """Candidatos que conforman las planchas"""
    CARGO_CHOICES = [
        ('principal', 'Principal'),
        ('suplente', 'Suplente'),
    ]
    
    plancha = models.ForeignKey(Plancha, on_delete=models.CASCADE, related_name='candidatos')
    nombre = models.CharField(max_length=200, verbose_name="Nombre completo")
    cargo = models.CharField(max_length=20, choices=CARGO_CHOICES, verbose_name="Cargo en la plancha")
    foto = models.ImageField(upload_to='candidatos/', blank=True, null=True, verbose_name="Foto del candidato")
    
    class Meta:
        verbose_name = "Candidato"
        verbose_name_plural = "Candidatos"
        ordering = ['plancha', 'cargo', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.cargo} ({self.plancha})"

class Voto(models.Model):
    """Registro temporal de votos emitidos - SE ELIMINA AL FINALIZAR PROCESO ELECTORAL"""
    votante = models.ForeignKey(Votante, on_delete=models.CASCADE, verbose_name="Votante")
    plancha = models.ForeignKey(Plancha, on_delete=models.CASCADE, verbose_name="Plancha votada")
    tipo_consejo = models.ForeignKey(TipoConsejo, on_delete=models.CASCADE, verbose_name="Tipo de consejo")
    ip_votacion = models.GenericIPAddressField(verbose_name="IP de votación")
    fecha_voto = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora del voto")
    
    # Campo para marcar si ya fue contabilizado en ResultadoVotacion
    contabilizado = models.BooleanField(default=False, verbose_name="Ya contabilizado")
    
    class Meta:
        verbose_name = "Voto (Temporal)"
        verbose_name_plural = "Votos (Temporales)"
        ordering = ['-fecha_voto']
        unique_together = ['votante', 'tipo_consejo']  # Un voto por consejo por votante
    
    def __str__(self):
        return f"Voto temporal de {self.votante.nombre} - {self.plancha}"

class ResultadoVotacion(models.Model):
    """Tabla principal para conteo de votos sin identificar votantes"""
    plancha = models.ForeignKey(Plancha, on_delete=models.CASCADE, verbose_name="Plancha")
    tipo_consejo = models.ForeignKey(TipoConsejo, on_delete=models.CASCADE, verbose_name="Tipo de consejo")
    tipo_persona = models.CharField(
        max_length=15,
        choices=Votante.TIPO_PERSONA_CHOICES,
        verbose_name="Tipo de votante"
    )
    cantidad_votos = models.PositiveIntegerField(default=0, verbose_name="Cantidad de votos")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    
    class Meta:
        verbose_name = "Resultado de Votación"
        verbose_name_plural = "Resultados de Votación"
        ordering = ['tipo_consejo', 'tipo_persona', '-cantidad_votos']
        unique_together = ['plancha', 'tipo_consejo', 'tipo_persona']
    
    def __str__(self):
        return f"{self.plancha} - {self.cantidad_votos} votos ({self.get_tipo_persona_display()})"
    
    @classmethod
    def registrar_voto(cls, plancha, tipo_consejo, tipo_persona):
        """Registra un voto incrementando el contador"""
        resultado, created = cls.objects.get_or_create(
            plancha=plancha,
            tipo_consejo=tipo_consejo,
            tipo_persona=tipo_persona,
            defaults={'cantidad_votos': 0}
        )
        resultado.cantidad_votos += 1
        resultado.save()
        return resultado
    
    @classmethod
    def obtener_resultados_por_consejo(cls, tipo_consejo, tipo_persona):
        """Obtiene resultados ordenados por cantidad de votos para un consejo específico"""
        return cls.objects.filter(
            tipo_consejo=tipo_consejo,
            tipo_persona=tipo_persona
        ).select_related('plancha').order_by('-cantidad_votos', 'plancha__numero')
    
    @classmethod
    def contabilizar_votos_pendientes(cls):
        """Contabiliza votos temporales que no han sido procesados"""
        votos_pendientes = Voto.objects.filter(contabilizado=False)
        count = 0
        
        for voto in votos_pendientes:
            cls.registrar_voto(
                plancha=voto.plancha,
                tipo_consejo=voto.tipo_consejo,
                tipo_persona=voto.votante.tipo_persona
            )
            voto.contabilizado = True
            voto.save()
            count += 1
        
        return count
    
    @classmethod
    def limpiar_datos_temporales(cls):
        """Elimina todos los votos temporales después de contabilizar"""
        cls.contabilizar_votos_pendientes()
        count = Voto.objects.count()
        Voto.objects.all().delete()
        return count

class EstadisticaVotacion(models.Model):
    """Estadísticas precalculadas para el dashboard"""
    total_votantes = models.PositiveIntegerField(default=0)
    total_votos_emitidos = models.PositiveIntegerField(default=0)
    votos_estudiantes = models.PositiveIntegerField(default=0)
    votos_docentes = models.PositiveIntegerField(default=0)
    votos_graduados = models.PositiveIntegerField(default=0)
    porcentaje_participacion = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Estadística de Votación"
        verbose_name_plural = "Estadísticas de Votación"
    
    def __str__(self):
        return f"Estadísticas - {self.ultima_actualizacion.strftime('%d/%m/%Y %H:%M')}"
    
    @classmethod
    def actualizar_estadisticas(cls):
        """Actualiza las estadísticas de votación usando ResultadoVotacion"""
        from django.db.models import Sum
        
        # Contabilizar votos pendientes primero
        ResultadoVotacion.contabilizar_votos_pendientes()
        
        # Obtener o crear registro de estadísticas
        estadistica, created = cls.objects.get_or_create(id=1)
        
        # Calcular estadísticas
        estadistica.total_votantes = Votante.objects.count()
        estadistica.total_votos_emitidos = Votante.objects.filter(ya_voto=True).count()
        estadistica.votos_estudiantes = Votante.objects.filter(ya_voto=True, tipo_persona='estudiante').count()
        estadistica.votos_docentes = Votante.objects.filter(ya_voto=True, tipo_persona='docente').count()
        estadistica.votos_graduados = Votante.objects.filter(ya_voto=True, tipo_persona='graduado').count()
        
        # Calcular porcentaje de participación
        if estadistica.total_votantes > 0:
            estadistica.porcentaje_participacion = (estadistica.total_votos_emitidos / estadistica.total_votantes) * 100
        else:
            estadistica.porcentaje_participacion = 0
            
        estadistica.save()
        return estadistica
