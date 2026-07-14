from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ModelForm
from negocio.models import Producto

# usamos el formulario de autenticacion de django para manejar el login de forma segura
# definimos la estructura del formulario delegando la presentacion a las hojas de estilo

class ProductoForm(ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo_sku', 'nombre_producto', 'descripcion', 'precio_mayorista', 'stock_actual', 'estado_activo']
