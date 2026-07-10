from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from negocio.forms import CustomLoginForm
from negocio.models import Empresa, Vendedor, Tendero

def index(request):
    return redirect('login')

def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.data.get("username")
            raw_password = form.data.get("password")
            user = authenticate(username=username, password=raw_password)
            if user is not None:
                login(request, user)
                
                # Identificar el rol del usuario (Opcional, para la sesión si se necesita en templates)
                if hasattr(user, 'empresa'):
                    request.session['tipo_usuario'] = 'Empresa'
                    request.session['nombre_usuario'] = user.empresa.razon_social
                elif hasattr(user, 'vendedor'):
                    request.session['tipo_usuario'] = 'Vendedor'
                    request.session['nombre_usuario'] = f"{user.first_name} {user.last_name}"
                elif hasattr(user, 'tendero'):
                    request.session['tipo_usuario'] = 'Tendero'
                    request.session['nombre_usuario'] = f"{user.first_name} {user.last_name}"
                else:
                    request.session['tipo_usuario'] = 'Admin/Otro'
                    request.session['nombre_usuario'] = user.username
                
                return redirect('hub')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        form = CustomLoginForm()
        
    diccionario = {'form': form}
    return render(request, 'login.html', diccionario)

@login_required(login_url='/login/')
def hub_view(request):
    user = request.user
    
    # Determinar el tipo y nombre de usuario al vuelo
    tipo_usuario = 'Admin/Otro'
    nombre_usuario = user.username
    
    if hasattr(user, 'empresa'):
        tipo_usuario = 'Empresa'
        nombre_usuario = user.empresa.razon_social
    elif hasattr(user, 'vendedor'):
        tipo_usuario = 'Vendedor'
        nombre_usuario = f"{user.first_name} {user.last_name}"
    elif hasattr(user, 'tendero'):
        tipo_usuario = 'Tendero'
        nombre_usuario = f"{user.first_name} {user.last_name}"
        
    contexto = {
        'tipo_usuario': tipo_usuario,
        'nombre_usuario': nombre_usuario
    }
    
    return render(request, 'hub.html', contexto)

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesion exitosamente')
    return redirect('login')
