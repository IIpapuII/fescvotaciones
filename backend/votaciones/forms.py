from django import forms
from .models import Votante

class ValidacionIngresoForm(forms.Form):
    documento = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ingrese su número de documento',
            'autofocus': True
        }),
        label="Número de Documento"
    )
    
    def clean_documento(self):
        documento = self.cleaned_data['documento']
        if not documento.isdigit():
            raise forms.ValidationError("El documento debe contener solo números.")
        return documento
    
    def validar_votante(self):
        """Valida si el votante existe y puede votar"""
        documento = self.cleaned_data.get('documento')
        
        try:
            votante = Votante.objects.get(documento=documento)
            if votante.ya_voto:
                raise forms.ValidationError("Este votante ya ha ejercido su derecho al voto.")
            return votante
        except Votante.DoesNotExist:
            raise forms.ValidationError("Número de documento no encontrado en el padrón electoral.")
        
        try:
            votante = Votante.objects.get(
                documento=documento,
                tipo_persona=tipo_persona
            )
            if votante.ya_voto:
                raise forms.ValidationError("Este votante ya ha ejercido su derecho al voto.")
            return votante
        except Votante.DoesNotExist:
            raise forms.ValidationError("Votante no encontrado o tipo de persona incorrecto.")
