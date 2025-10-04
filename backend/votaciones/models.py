from django.db import models
from django.utils import timezone

# Create your models here.

class Votante(models.Model):
    TIPO_PERSONA_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('graduado', 'Graduado'),
        ('administrativo', 'Administrativo'),
    ]
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre completo")
    documento = models.CharField(max_length=20, unique=True, verbose_name="Número de documento")
    tipo_persona = models.CharField(
        max_length=15, 
        choices=TIPO_PERSONA_CHOICES,
        verbose_name="Tipo de persona"
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
    
    def __str__(self):
        return f"{self.nombre} - {self.documento}"
    
    def marcar_como_votado(self, ip_address):
        """Marca al votante como que ya votó y registra la IP"""
        self.ya_voto = True
        self.ip_votacion = ip_address
        self.fecha_voto = timezone.now()
        self.save()

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
    """Registro de votos emitidos"""
    votante = models.ForeignKey(Votante, on_delete=models.CASCADE, verbose_name="Votante")
    plancha = models.ForeignKey(Plancha, on_delete=models.CASCADE, verbose_name="Plancha votada")
    tipo_consejo = models.ForeignKey(TipoConsejo, on_delete=models.CASCADE, verbose_name="Tipo de consejo")
    ip_votacion = models.GenericIPAddressField(verbose_name="IP de votación")
    fecha_voto = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora del voto")
    
    class Meta:
        verbose_name = "Voto"
        verbose_name_plural = "Votos"
        ordering = ['-fecha_voto']
        unique_together = ['votante', 'tipo_consejo']  # Un voto por consejo por votante
    
    def __str__(self):
        return f"Voto de {self.votante.nombre} - {self.plancha}"

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
        """Actualiza las estadísticas de votación"""
        from django.db.models import Count
        
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
