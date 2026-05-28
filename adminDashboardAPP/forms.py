from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from decimal import Decimal
from eventoAPP.models import Evento, Mercado, Seleccion

class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['local', 'visitante', 'fecha_inicio']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'input'}),
        }

    def clean_fecha_inicio(self):
        fecha = self.cleaned_data['fecha_inicio']
        if fecha < timezone.now():
            raise forms.ValidationError('La fecha del evento no puede ser pasada.')
        return fecha

class MercadoForm(forms.ModelForm):
    class Meta:
        model = Mercado
        fields = []  # No se exponen campos, se crea automáticamente con tipo 1X2
        widgets = {
            'tipo': forms.HiddenInput(),
        }

class SeleccionForm(forms.ModelForm):
    class Meta:
        model = Seleccion
        fields = ['tipo', 'cuota']
        widgets = {
            'cuota': forms.NumberInput(attrs={'step': '0.01', 'class': 'input'}),
        }

# Formsets para crear mercado y sus selecciones en un solo paso
MercadoFormSet = inlineformset_factory(
    Evento,
    Mercado,
    form=MercadoForm,
    extra=1,
    can_delete=False,
)

# Tres selecciones (1, X, 2) por mercado
SeleccionFormSet = inlineformset_factory(
    Mercado,
    Seleccion,
    form=SeleccionForm,
    extra=3,
    max_num=3,
    can_delete=False,
)
