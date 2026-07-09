from django.shortcuts import render, redirect
from django.contrib import messages
from negocio.models import Empresa, Vendedor, Tendero

def index(request):
    return redirect('login')

def login_view(request):
    if request.session.get('usuario_id'):
        return redirect('hub')
        
    if request.method == 'POST':
        correo = request.POST.get('correo')
        password = request.POST.get('password')
        
        # Verificar la empresa
        empresa = Empresa.objects.filter(correo_electronico=correo, password_hash=password).first()
        if empresa:
            request.session['usuario_id'] = empresa.id
            request.session['tipo_usuario'] = 'Empresa'
            request.session['correo'] = empresa.correo_electronico
            return redirect('hub')
            
        # se verififca el vndedor
        vendedor = Vendedor.objects.filter(correo_electronico=correo, password_hash=password).first()
        if vendedor:
            request.session['usuario_id'] = vendedor.id
            request.session['tipo_usuario'] = 'Vendedor'
            request.session['correo'] = vendedor.correo_electronico
            return redirect('hub')
            
        # Verificar el tendedero
        tendero = Tendero.objects.filter(correo_electronico=correo, password_hash=password).first()
        if tendero:
            request.session['usuario_id'] = tendero.id
            request.session['tipo_usuario'] = 'Tendero'
            request.session['correo'] = tendero.correo_electronico
            return redirect('hub')
            
        messages.error(request, 'Correo o contraseña incorrectos')
        
    return render(request, 'login.html')

def hub_view(request):
    if not request.session.get('usuario_id'):
        messages.warning(request, 'Debe iniciar sesion primero')
        return redirect('login')
        
    return render(request, 'hub.html')

def logout_view(request):
    request.session.flush()
    messages.info(request, 'Has cerrado sesion exitosamente')
    return redirect('login')
