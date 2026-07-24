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

class RegistroUsuarioForm(forms.Form):
    # Datos básicos de Usuario
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    
    # Rol
    ROLE_CHOICES = [
        ('EMPRESA', 'Empresa/Distribuidora'),
        ('VENDEDOR', 'Vendedor Independiente'),
        ('TENDERO', 'Tendero')
    ]
    rol = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, required=True)
    
    # Datos Empresa
    ruc = forms.CharField(max_length=20, required=False)
    razon_social = forms.CharField(max_length=150, required=False)
    representante_legal = forms.CharField(max_length=100, required=False)
    limite_compra_minimo = forms.FloatField(required=False)
    PLAN_CHOICES = [
        ('TRIAL', 'Prueba de 14 Días (Gratis)'),
        ('PREMIUM', 'Premium Pago ($9.99/mes)')
    ]
    plan_empresa = forms.ChoiceField(choices=PLAN_CHOICES, widget=forms.RadioSelect, required=False)
    
    # Datos Vendedor
    cedula = forms.CharField(max_length=20, required=False)
    
    # Datos Tendero
    nombre_local = forms.CharField(max_length=100, required=False)
    ruc_negocio = forms.CharField(max_length=20, required=False)
    direccion_fisica = forms.CharField(max_length=255, required=False)
    coordenadas_gps = forms.CharField(max_length=100, required=False)

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get("rol")
        
        if rol == 'EMPRESA':
            if not cleaned_data.get('ruc'):
                self.add_error('ruc', 'RUC es obligatorio para Empresa.')
            if not cleaned_data.get('razon_social'):
                self.add_error('razon_social', 'Razón Social es obligatoria para Empresa.')
            if not cleaned_data.get('representante_legal'):
                self.add_error('representante_legal', 'Representante Legal es obligatorio para Empresa.')
            if cleaned_data.get('limite_compra_minimo') is None:
                self.add_error('limite_compra_minimo', 'Límite de compra mínimo es obligatorio.')
            if not cleaned_data.get('plan_empresa'):
                self.add_error('plan_empresa', 'Debe seleccionar un plan de suscripción.')
                
        elif rol == 'VENDEDOR':
            if not cleaned_data.get('cedula'):
                self.add_error('cedula', 'Cédula es obligatoria para Vendedor.')
                
        elif rol == 'TENDERO':
            if not cleaned_data.get('nombre_local'):
                self.add_error('nombre_local', 'Nombre del Local es obligatorio.')
            if not cleaned_data.get('ruc_negocio'):
                self.add_error('ruc_negocio', 'RUC del Negocio es obligatorio.')
            if not cleaned_data.get('direccion_fisica'):
                self.add_error('direccion_fisica', 'Dirección Física es obligatoria.')
            if not cleaned_data.get('coordenadas_gps'):
                # Podría ser opcional, pero según modelo lo validamos
                self.add_error('coordenadas_gps', 'Coordenadas GPS son obligatorias.')
                
        return cleaned_data

class UsuarioBasicoForm(ModelForm):
    class Meta:
        from django.contrib.auth.models import User
        model = User
        fields = ['first_name', 'last_name', 'email']

class EmpresaPerfilForm(ModelForm):
    class Meta:
        from negocio.models import Empresa
        model = Empresa
        fields = ['telefono', 'razon_social', 'direccion_principal', 'foto_perfil', 'bot_voz_activa']

class TenderoPerfilForm(ModelForm):
    class Meta:
        from negocio.models import Tendero
        model = Tendero
        fields = ['telefono', 'nombre_local', 'direccion_fisica', 'referencias', 'foto_perfil', 'bot_voz_activa']

class VendedorPerfilForm(ModelForm):
    class Meta:
        from negocio.models import Vendedor
        model = Vendedor
        fields = ['telefono', 'zona_cobertura', 'foto_perfil', 'bot_voz_activa']
