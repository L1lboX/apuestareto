from django import forms
from django.contrib.auth.forms import UserCreationForm
from userAPP.models import User


class RegistroForm(UserCreationForm):
    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'nombre', 'apellido',
            'telefono', 'dni', 'dni_digito_verificador',
            'fecha_nacimiento', 'password1', 'password2'
        ]
        labels = {
            'dni_digito_verificador': 'Digito verificador',
        }
        widgets = {
            'dni': forms.TextInput(attrs={'inputmode': 'numeric'}),
            'dni_digito_verificador': forms.TextInput(attrs={
                'maxlength': '1',
                'inputmode': 'numeric',
                'pattern': '[0-9]',
            }),
        }
