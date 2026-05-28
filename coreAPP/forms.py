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
            'telefono', 'dni', 'fecha_nacimiento', 'password1', 'password2'
        ]
