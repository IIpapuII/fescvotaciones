from django import forms
from .models import Votante

class ValidacionIngresoForm(forms.Form):
    documento = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su número de documento',
            'autocomplete': 'off'
        }),
        label='Número de Documento'
    )
    
    def clean_documento(self):
        documento = self.cleaned_data['documento']
        if not documento.isdigit():
            raise forms.ValidationError("El documento debe contener solo números.")
        return documento
    
    def validar_votante(self):
        """Valida que el votante exista y pueda votar"""
        documento = self.cleaned_data['documento']
        
        try:
            votante = Votante.objects.get(documento=documento)
            
            if votante.ya_voto:
                raise forms.ValidationError(
                    f'El votante {votante.nombre} ya ha ejercido su derecho al voto el '
                    f'{votante.fecha_voto.strftime("%d/%m/%Y a las %H:%M")}.'
                )
            
            # NUEVA VALIDACIÓN: Verificar tipo de votante y agregar información
            if votante.debe_votar_presencial():
                raise forms.ValidationError(
                    f'El votante {votante.nombre} está configurado para VOTACIÓN PRESENCIAL. '
                    f'Debe dirigirse a las urnas físicas para votar. No puede usar el sistema virtual.'
                )
            
            return votante
            
        except Votante.DoesNotExist:
            raise forms.ValidationError(
                'El número de documento ingresado no se encuentra registrado en el sistema electoral. '
                'Verifique el número e intente nuevamente.'
            )
