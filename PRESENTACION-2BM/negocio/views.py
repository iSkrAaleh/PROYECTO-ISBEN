from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import openai
from django.db.models import Sum
from negocio.models import Empresa, Vendedor, Tendero, Producto, Pedido
from negocio.forms import ProductoForm, RegistroUsuarioForm, UsuarioBasicoForm, EmpresaPerfilForm, TenderoPerfilForm, VendedorPerfilForm

def index(request):
    return redirect('login')

def csrf_failure(request, reason=""):
    messages.info(request, 'Tu sesión de seguridad caducó o el navegador usó caché viejo, por favor intenta de nuevo')
    return redirect('login')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.data.get("username")
            raw_password = form.data.get("password")
            user = authenticate(username=username, password=raw_password)
            if user is not None:
                login(request, user)
                return redirect('hub')
        else:
            messages.info(request, 'Usuario o contraseña incorrectos')
            return redirect('login')
    else:
        form = AuthenticationForm()
        
    diccionario = {'form': form}
    return render(request, 'login.html', diccionario)

@login_required(login_url='/login/')
def hub_view(request):
    user = request.user
    
    # inicializamos las variables por defecto
    tipo_usuario = 'Admin/Otro'
    nombre_usuario = user.username
    plantilla = 'hub.html'
    
    # buscamos los perfiles asociados a este usuario en la base de datos
    empresas = Empresa.objects.filter(usuario=user).all()
    vendedores = Vendedor.objects.filter(usuario=user).all()
    tenderos = Tendero.objects.filter(usuario=user).all()

    if len(empresas) > 0:
        tipo_usuario = 'Empresa'
        nombre_usuario = empresas[0].razon_social
        plantilla = 'hub_empresa.html'
    elif len(vendedores) > 0:
        tipo_usuario = 'Vendedor'
        nombre_usuario = f"{user.first_name} {user.last_name}"
        plantilla = 'hub_vendedor.html'
    elif len(tenderos) > 0:
        tipo_usuario = 'Tendero'
        nombre_usuario = f"{user.first_name} {user.last_name}"
        plantilla = 'hub_tendero.html'
    else:
        pass # si no es ninguno de los roles definidos mantenemos el perfil basico
        
    contexto = {
        'tipo_usuario': tipo_usuario,
        'nombre_usuario': nombre_usuario
    }
    
    return render(request, plantilla, contexto)

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesion exitosamente')
    return redirect('login')

@login_required(login_url='/login/')
def listar_productos_empresa(request):
    mis_empresas = Empresa.objects.filter(usuario=request.user).all()
    if len(mis_empresas) > 0:
        # recuperamos la informacion de la empresa vinculada a la sesion actual
        mi_empresa = mis_empresas[0]
        
        # importamos el modelo producto para acceder al inventario
        from negocio.models import Producto
        
        # consultamos el catalogo de productos de esta empresa en especifico
        mis_productos = Producto.objects.filter(empresa=mi_empresa)
        
        diccionario = {'productos': mis_productos}
        return render(request, 'productos_empresa.html', diccionario)
        
    else:
        # bloqueamos el acceso a usuarios no autorizados y los redirigimos al inicio
        return redirect('hub')

@login_required(login_url='/login/')
def seleccionar_tendero_view(request, empresa_id):
    mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
    if len(mis_vendedores) == 0:
        return redirect('hub')
    mi_vendedor = mis_vendedores[0]
    
    # capturamos el termino de busqueda desde los parametros de la url
    q = request.GET.get('q', '')
    if q:
        lista_tenderos = Tendero.objects.filter(nombre_local__icontains=q)
    else:
        lista_tenderos = Tendero.objects.all()
        
    diccionario = {'tenderos': lista_tenderos, 'q': q, 'empresa_id': empresa_id}
    return render(request, 'seleccionar_tendero.html', diccionario)

@login_required(login_url='/login/')
def crear_pedido_view(request, empresa_id, tendero_id):
    mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
    tenderos_en_db = Tendero.objects.filter(id=tendero_id).all()
    empresas_en_db = Empresa.objects.filter(id=empresa_id).all()
    
    if len(mis_vendedores) == 0 or len(tenderos_en_db) == 0 or len(empresas_en_db) == 0:
        return redirect('hub')
        
    mi_vendedor = mis_vendedores[0]
    tendero_seleccionado = tenderos_en_db[0]
    empresa_seleccionada = empresas_en_db[0]
    from negocio.models import Producto
    
    # listamos unicamente los productos que se encuentran disponibles para la venta
    lista_productos = Producto.objects.filter(estado_activo=True, empresa=empresa_seleccionada)
    
    diccionario = {
        'tendero': tendero_seleccionado,
        'productos': lista_productos,
        'empresa_id': empresa_id
    }
    return render(request, 'crear_pedido.html', diccionario)

@login_required(login_url='/login/')
def guardar_pedido_view(request):
    if request.method == 'POST':
        mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
        if len(mis_vendedores) == 0:
            return redirect('hub')
        mi_vendedor = mis_vendedores[0]
        
        # identificamos al tendero seleccionado para la transaccion
        tendero_id = request.POST.get('tendero_id')
        
        from negocio.models import Tendero, Producto, Pedido, DetallePedido
        from django.utils import timezone
        
        mis_tenderos_form = Tendero.objects.filter(id=tendero_id).all()
        if len(mis_tenderos_form) == 0:
            return redirect('hub')
            
        tendero = mis_tenderos_form[0]
        
        # inicializamos el registro del pedido con valores en cero
        nuevo_pedido = Pedido(
            fecha_hora_emision=timezone.now(),
            subtotal_pedido=0.0,
            total_pedido=0.0,
            estado_pedido='Completado',
            metodo_generacion='Intermediario (Vendedor)',
            tendero=tendero,
            vendedor=mi_vendedor
        )
        nuevo_pedido.save()
        
        total_pedido = 0.0
        productos_agregados = 0
        
        # iteramos sobre el catalogo para procesar las cantidades ingresadas
        lista_productos = Producto.objects.filter(estado_activo=True)
        for producto in lista_productos:
            # capturamos la cantidad solicitada usando el identificador unico del producto
            cant_str = request.POST.get(f'cantidad_{producto.id}')
            
            # verificamos que se haya ingresado una cantidad valida
            if cant_str and cant_str != "":
                cantidad = int(cant_str)
                if cantidad > 0:
                    precio_str = request.POST.get(f'precio_venta_{producto.id}')
                    
                    if precio_str and precio_str != "":
                        precio_venta = float(precio_str)
                    else:
                        precio_venta = producto.precio_mayorista
                    
                    # comprobamos la disponibilidad en el inventario antes de continuar
                    if cantidad > producto.stock_actual:
                        messages.info(request, f'Saltamos {producto.nombre_producto}: falta de stock.')
                        continue
                        
                    # aplicamos regla de negocio para evitar ventas con perdidas operativas
                    if precio_venta < producto.precio_mayorista:
                        messages.info(request, f'Saltamos {producto.nombre_producto}: El precio de venta (${precio_venta}) no puede ser menor al costo de la empresa (${producto.precio_mayorista}).')
                        continue
                        
                    subtotal_linea = cantidad * precio_venta
                    total_pedido += subtotal_linea
                    
                    # registramos la linea de producto dentro del pedido actual
                    DetallePedido.objects.create(
                        cantidad_producto=cantidad,
                        precio_unitario_aplicado=precio_venta,
                        subtotal_linea=subtotal_linea,
                        pedido=nuevo_pedido,
                        producto=producto
                    )
                    
                    # actualizamos el inventario descontando las unidades vendidas
                    producto.stock_actual -= cantidad
                    producto.save()
                    productos_agregados += 1
        
        # verificamos si la operacion genero lineas validas antes de guardar
        if productos_agregados > 0:
            # consolidamos los montos finales del documento
            nuevo_pedido.subtotal_pedido = total_pedido
            nuevo_pedido.total_pedido = total_pedido
            # Asignamos la empresa del primer producto agregado
            primer_detalle = nuevo_pedido.detalles.first()
            if primer_detalle:
                nuevo_pedido.empresa = primer_detalle.producto.empresa
            # Calculamos comisión 5% para el vendedor
            nuevo_pedido.comision_generada = total_pedido * 0.05
            nuevo_pedido.save()
            messages.info(request, f'¡Pedido múltiple registrado! ({productos_agregados} tipos de productos)')
        else:
            # descartamos el registro temporal si no se procesaron productos
            nuevo_pedido.delete()
            messages.info(request, 'No se agregó ningún producto válido al pedido.')
            
        return redirect('hub')
    else:
        # evitamos accesos directos por url sin envio de datos
        return redirect('hub')

@login_required(login_url='/login/')
def seleccionar_empresa_view(request):
    mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
    if len(mis_vendedores) == 0:
        return redirect('hub')
    mi_vendedor = mis_vendedores[0]
    
    from negocio.models import Empresa, SolicitudVendedor
    
    empresas = Empresa.objects.all()
    lista_empresas_info = []
    
    for emp in empresas:
        solicitudes = SolicitudVendedor.objects.filter(vendedor=mi_vendedor, empresa=emp).all()
        solicitud = None
        if len(solicitudes) > 0:
            solicitud = solicitudes[0]
        
        estado_actual = "Ninguno"
        if solicitud:
            estado_actual = solicitud.estado_solicitud
            
        info = {
            'empresa': emp,
            'requiere_aprobacion': emp.requiere_aprobacion,
            'estado_solicitud': estado_actual
        }
        lista_empresas_info.append(info)
        
    diccionario = {'empresas_info': lista_empresas_info}
    return render(request, 'seleccionar_empresa.html', diccionario)

@login_required(login_url='/login/')
def enviar_solicitud_view(request, empresa_id):
    mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
    if len(mis_vendedores) == 0:
        return redirect('hub')
    mi_vendedor = mis_vendedores[0]
    
    from negocio.models import Empresa, SolicitudVendedor
    from django.utils import timezone
    
    empresas_form = Empresa.objects.filter(id=empresa_id).all()
    if len(empresas_form) == 0:
        return redirect('hub')
    empresa = empresas_form[0]
    
    solicitudes_previas = SolicitudVendedor.objects.filter(vendedor=mi_vendedor, empresa=empresa).all()
    if len(solicitudes_previas) == 0:
        SolicitudVendedor.objects.create(
            vendedor=mi_vendedor,
            empresa=empresa,
            fecha_solicitud=timezone.now(),
            estado_solicitud="Pendiente"
        )
        messages.info(request, f"¡Solicitud enviada a {empresa.razon_social}!")
    else:
        messages.info(request, "Ya habías enviado una solicitud a esta empresa.")
        
    return redirect('seleccionar_empresa')

@login_required(login_url='/login/')
def revisar_solicitudes_view(request):
    mis_empresas = Empresa.objects.filter(usuario=request.user).all()
    if len(mis_empresas) == 0:
        return redirect('hub')
    mi_empresa = mis_empresas[0]
    
    from negocio.models import SolicitudVendedor
    
    # filtramos las solicitudes de vinculacion que aun requieren revision
    pendientes = SolicitudVendedor.objects.filter(empresa=mi_empresa, estado_solicitud="Pendiente")
    
    diccionario = {'solicitudes': pendientes}
    return render(request, 'revisar_solicitudes.html', diccionario)

@login_required(login_url='/login/')
def aprobar_solicitud_view(request, solicitud_id):
    mis_empresas = Empresa.objects.filter(usuario=request.user).all()
    if len(mis_empresas) == 0:
        return redirect('hub')
    mi_empresa = mis_empresas[0]
    
    from negocio.models import SolicitudVendedor
    
    # localizamos el registro de la solicitud mediante su identificador
    solicitudes = SolicitudVendedor.objects.filter(id=solicitud_id, empresa=mi_empresa).all()
    if len(solicitudes) == 0:
        return redirect('hub')
    solicitud = solicitudes[0]
    
    # actualizamos el estado operativo para confirmar la vinculacion
    solicitud.estado_solicitud = "Aprobado"
    solicitud.save()
    
    messages.info(request, f'¡Solicitud de {solicitud.vendedor.usuario.first_name} aprobada!')
    return redirect('revisar_solicitudes')

@login_required(login_url='/login/')
def seleccionar_empresa_tendero_view(request):
    mis_tenderos = Tendero.objects.filter(usuario=request.user).all()
    if len(mis_tenderos) == 0:
        return redirect('hub')
    mi_tendero = mis_tenderos[0]
    
    from negocio.models import Empresa
    
    empresas = Empresa.objects.all()
    
    diccionario = {'empresas': empresas}
    return render(request, 'seleccionar_empresa_tendero.html', diccionario)

@login_required(login_url='/login/')
def catalogo_tendero_view(request, empresa_id):
    mis_tenderos = Tendero.objects.filter(usuario=request.user).all()
    empresas_form = Empresa.objects.filter(id=empresa_id).all()
    if len(mis_tenderos) == 0 or len(empresas_form) == 0:
        return redirect('hub')
        
    mi_tendero = mis_tenderos[0]
    empresa_seleccionada = empresas_form[0]
    
    from negocio.models import Producto
    
    # obtenemos los articulos habilitados para el catalogo de este proveedor
    lista_productos = Producto.objects.filter(estado_activo=True, empresa=empresa_seleccionada)
    
    diccionario = {
        'empresa': empresa_seleccionada,
        'productos': lista_productos
    }
    return render(request, 'catalogo_tendero.html', diccionario)

@login_required(login_url='/login/')
def guardar_pedido_tendero_view(request):
    if request.method == 'POST':
        mis_tenderos = Tendero.objects.filter(usuario=request.user).all()
        if len(mis_tenderos) == 0:
            return redirect('hub')
        mi_tendero = mis_tenderos[0]
        
        from negocio.models import Empresa, Producto, Pedido, DetallePedido
        from django.utils import timezone
        
        empresa_id = request.POST.get('empresa_id')
        empresas_form = Empresa.objects.filter(id=empresa_id).all()
        if len(empresas_form) == 0:
            return redirect('hub')
        empresa_seleccionada = empresas_form[0]
        
        # recuperamos el listado de productos asociados al proveedor seleccionado
        productos_empresa = Producto.objects.filter(empresa=empresa_seleccionada, estado_activo=True)
        
        total_pedido = 0.0
        detalles_a_crear = []
        
        for producto in productos_empresa:
            cantidad_str = request.POST.get(f'cantidad_{producto.id}')
            
            if cantidad_str and cantidad_str != '' and int(cantidad_str) > 0:
                cantidad = int(cantidad_str)
                
                if cantidad > producto.stock_actual:
                    messages.info(request, f'Saltamos {producto.nombre_producto}: falta de stock.')
                    continue
                    
                # aplicamos tarifa base sin margenes de intermediacion
                precio_unitario = producto.precio_mayorista
                subtotal_linea = cantidad * precio_unitario
                total_pedido += subtotal_linea
                
                detalles_a_crear.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'subtotal': subtotal_linea,
                    'precio_unitario': precio_unitario
                })
        
        if len(detalles_a_crear) > 0:
            nuevo_pedido = Pedido.objects.create(
                fecha_hora_emision=timezone.now(),
                subtotal_pedido=total_pedido,
                total_pedido=total_pedido,
                estado_pedido='Recibido por Empresa', # asignamos estado inicial para inicio de gestion
                metodo_generacion='App Tendero',
                tendero=mi_tendero,
                vendedor=None # registramos la transaccion sin comisionista asociado
            )
            
            for det in detalles_a_crear:
                DetallePedido.objects.create(
                    cantidad_producto=det['cantidad'],
                    precio_unitario_aplicado=det['precio_unitario'],
                    subtotal_linea=det['subtotal'],
                    pedido=nuevo_pedido,
                    producto=det['producto']
                )
                
                # descontamos la cantidad solicitada del inventario disponible
                prod_db = det['producto']
                prod_db.stock_actual -= det['cantidad']
                prod_db.save()
                
            messages.info(request, f'¡Pedido de ${total_pedido} enviado a {empresa_seleccionada.razon_social} exitosamente!')
        else:
            messages.info(request, 'No elegiste ningún producto válido. Pedido cancelado.')
            
        return redirect('mis_pedidos_tendero')
    return redirect('hub')

@login_required(login_url='/login/')
def mis_pedidos_tendero_view(request):
    mis_tenderos = Tendero.objects.filter(usuario=request.user).all()
    if len(mis_tenderos) == 0:
        return redirect('hub')
    mi_tendero = mis_tenderos[0]
    
    from negocio.models import Pedido
    
    # consultamos el historial de ordenes ordenado cronologicamente
    pedidos = Pedido.objects.filter(tendero=mi_tendero).order_by('-fecha_hora_emision')
    
    diccionario = {'pedidos': pedidos}
    return render(request, 'mis_pedidos_tendero.html', diccionario)

@login_required(login_url='/login/')
def gestionar_pedidos_empresa_view(request):
    mis_empresas = Empresa.objects.filter(usuario=request.user).all()
    if len(mis_empresas) == 0:
        return redirect('hub')
    mi_empresa = mis_empresas[0]
    
    from negocio.models import Pedido
    
    # obtenemos todos los pedidos y los ordenamos por fecha de emision reciente
    todos_los_pedidos = Pedido.objects.all().order_by('-fecha_hora_emision')
    pedidos = []
    
    for ped in todos_los_pedidos:
        es_mio = False
        for det in ped.detalles.all():
            if det.producto.empresa == mi_empresa:
                es_mio = True
                
        if es_mio:
            pedidos.append(ped)
    
    diccionario = {'pedidos': pedidos}
    return render(request, 'gestionar_pedidos_empresa.html', diccionario)

@login_required(login_url='/login/')
def actualizar_estado_pedido_view(request, pedido_id):
    if request.method == 'POST':
        mis_empresas = Empresa.objects.filter(usuario=request.user).all()
        if len(mis_empresas) > 0:
            mi_empresa = mis_empresas[0]
            from negocio.models import Pedido
            
            nuevo_estado = request.POST.get('nuevo_estado')
            
            # buscamos el pedido especifico en la base de datos
            todos_pedidos = Pedido.objects.filter(id=pedido_id).all()
            if len(todos_pedidos) > 0:
                pedido = todos_pedidos[0]
                
                es_mio = False
                for det in pedido.detalles.all():
                    if det.producto.empresa == mi_empresa:
                        es_mio = True
                
                if es_mio and nuevo_estado:
                    pedido.estado_pedido = nuevo_estado
                    pedido.save()
                    messages.info(request, f'El estado del Pedido #{pedido.id} ha sido cambiado a "{nuevo_estado}".')
                else:
                    messages.info(request, 'Error de seguridad o pedido no encontrado.')
            else:
                messages.info(request, 'Error de seguridad o pedido no encontrado.')
                
            return redirect('gestionar_pedidos_empresa')
            
        else:
            return redirect('hub')
    return redirect('hub')

@login_required(login_url='/login/')
def crear_producto_view(request):
    mis_empresas = Empresa.objects.filter(usuario=request.user).all()
    if len(mis_empresas) > 0:
        mi_empresa = mis_empresas[0]
        
        # VALIDACIÓN DE LÍMITES - LÓGICA FREEMIUM / TRIAL
        if mi_empresa.tipo_plan == 'TRIAL':
            if mi_empresa.fecha_vencimiento_prueba and timezone.now() > mi_empresa.fecha_vencimiento_prueba:
                messages.error(request, 'Tu prueba de 14 días ha finalizado. Por favor, mejora al plan PREMIUM para seguir creando productos.')
                return redirect('listar_productos_empresa')
                
            cantidad_productos = Producto.objects.filter(empresa=mi_empresa).count()
            if cantidad_productos >= 20:
                messages.error(request, 'Límite alcanzado: Tu plan TRIAL solo permite crear 20 productos. Por favor, mejora al plan PREMIUM.')
                return redirect('listar_productos_empresa')
        
        if request.method == 'POST':
            formulario = ProductoForm(request.POST)
            if formulario.is_valid():
                producto = formulario.save(commit=False)
                producto.empresa = mi_empresa
                producto.save()
                messages.info(request, 'Producto agregado exitosamente')
                return redirect('listar_productos_empresa')
        else:
            formulario = ProductoForm()
            
        diccionario = {'formulario': formulario}
        return render(request, 'crear_producto.html', diccionario)
        
    else:
        return redirect('hub')

@login_required(login_url='/login/')
def mis_rutas_view(request):
    mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
    if len(mis_vendedores) > 0:
        mi_vendedor = mis_vendedores[0]
        # Mostrar todos los tenderos como "clientes" de la ruta
        tenderos = Tendero.objects.all()
        return render(request, 'mis_rutas.html', {'tenderos': tenderos})
    else:
        return redirect('hub')

@login_required(login_url='/login/')
def mapa_cliente_view(request, tendero_id):
    try:
        tendero = Tendero.objects.get(id=tendero_id)
        return render(request, 'mapa_cliente.html', {'tendero': tendero})
    except Tendero.DoesNotExist:
        return redirect('hub')

def registro_view(request):
    if request.user.is_authenticated:
        return redirect('hub')
        
    if request.method == 'POST':
        formulario = RegistroUsuarioForm(request.POST)
        if formulario.is_valid():
            datos = formulario.cleaned_data
            
            try:
                user = User.objects.create_user(
                    username=datos['username'],
                    password=datos['password'],
                    first_name=datos['first_name'],
                    last_name=datos['last_name'],
                    email=datos['email']
                )
            except Exception as e:
                messages.error(request, 'Error al crear usuario. Verifica que el username no esté en uso.')
                return render(request, 'registro.html', {'formulario': formulario})
                
            rol = datos['rol']
            
            if rol == 'EMPRESA':
                tipo_plan = datos['plan_empresa']
                fecha_vencimiento = None
                suscripcion_activa = True
                
                if tipo_plan == 'TRIAL':
                    fecha_vencimiento = timezone.now() + timedelta(days=14)
                
                Empresa.objects.create(
                    usuario=user,
                    ruc=datos['ruc'],
                    razon_social=datos['razon_social'],
                    representante_legal=datos['representante_legal'],
                    limite_compra_minimo=datos['limite_compra_minimo'],
                    tipo_plan=tipo_plan,
                    fecha_vencimiento_prueba=fecha_vencimiento,
                    suscripcion_activa=suscripcion_activa,
                    estado_verificacion=True
                )
                
            elif rol == 'VENDEDOR':
                Vendedor.objects.create(
                    usuario=user,
                    cedula=datos['cedula'],
                    estado_aprobacion=True
                )
                
            elif rol == 'TENDERO':
                Tendero.objects.create(
                    usuario=user,
                    nombre_local=datos['nombre_local'],
                    ruc_negocio=datos['ruc_negocio'],
                    direccion_fisica=datos['direccion_fisica'],
                    coordenadas_gps=datos['coordenadas_gps']
                )
                
            login(request, user)
            messages.success(request, '¡Registro exitoso! Bienvenido a ISBEN.')
            return redirect('hub')
            
    else:
        formulario = RegistroUsuarioForm()
        
    return render(request, 'registro.html', {'formulario': formulario})

@login_required(login_url='/login/')
def perfil_view(request):
    user = request.user
    
    # Determinar el rol
    es_empresa = hasattr(user, 'empresa')
    es_vendedor = hasattr(user, 'vendedor')
    es_tendero = hasattr(user, 'tendero')
    
    perfil_instance = None
    PerfilFormClass = None
    
    if es_empresa:
        perfil_instance = user.empresa
        PerfilFormClass = EmpresaPerfilForm
    elif es_vendedor:
        perfil_instance = user.vendedor
        PerfilFormClass = VendedorPerfilForm
    elif es_tendero:
        perfil_instance = user.tendero
        PerfilFormClass = TenderoPerfilForm
        
    if request.method == 'POST':
        form_basico = UsuarioBasicoForm(request.POST, instance=user)
        form_perfil = None
        if PerfilFormClass and perfil_instance:
            form_perfil = PerfilFormClass(request.POST, request.FILES, instance=perfil_instance)
            
        if form_basico.is_valid() and (not form_perfil or form_perfil.is_valid()):
            form_basico.save()
            if form_perfil:
                form_perfil.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('perfil')
        else:
            messages.error(request, 'Error al actualizar el perfil. Por favor revisa los campos.')
    else:
        form_basico = UsuarioBasicoForm(instance=user)
        form_perfil = PerfilFormClass(instance=perfil_instance) if PerfilFormClass else None

    # Recopilar datos analíticos / solo lectura según rol
    datos_extra = {}
    if es_empresa:
        datos_extra['vendedores_aprobados'] = perfil_instance.solicitudes_recibidas.filter(estado_solicitud='Aprobada').count()
        # Verificar vencimiento
        if perfil_instance.tipo_plan == 'TRIAL' and perfil_instance.fecha_vencimiento_prueba:
            restante = (perfil_instance.fecha_vencimiento_prueba - timezone.now()).days
            datos_extra['dias_trial'] = max(0, restante)
            
    elif es_vendedor:
        datos_extra['empresas_vinculadas'] = perfil_instance.solicitudes.filter(estado_solicitud='Aprobada').count()
        
    contexto = {
        'form_basico': form_basico,
        'form_perfil': form_perfil,
        'es_empresa': es_empresa,
        'es_vendedor': es_vendedor,
        'es_tendero': es_tendero,
        'datos_extra': datos_extra,
        'perfil_instance': perfil_instance
    }
    
    return render(request, 'perfil.html', contexto)

@csrf_exempt
@login_required(login_url='/login/')
def tigre_bot_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pregunta = data.get('pregunta', '')
            
            # Verificar si el usuario tiene activada la voz
            bot_voz_activa = False
            if hasattr(request.user, 'empresa'):
                bot_voz_activa = request.user.empresa.bot_voz_activa
            elif hasattr(request.user, 'vendedor'):
                bot_voz_activa = request.user.vendedor.bot_voz_activa
            elif hasattr(request.user, 'tendero'):
                bot_voz_activa = request.user.tendero.bot_voz_activa

            # Inicializar cliente OpenAI
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # System Prompt (Contexto RAG de ISBEN)
            system_prompt = """
            Eres 'Tigre Bot', el asistente virtual multimodal y amigable del sistema ISBEN.
            Tu objetivo es ayudar a combatir el analfabetismo digital. Responde de forma EXTREMADAMENTE SENCILLA, PACIENTE y CORTA (máximo 3 oraciones). 
            Hablas con tenderos, empresas y vendedores independientes.
            Contexto del sistema ISBEN para Tenderos:
            - Si preguntan cómo hacer un pedido o comprar: Diles literalmente: "Haz clic en 'Ver Catálogo' en tu Panel, luego elige una distribuidora y dale a 'Ver Productos'. Ingresa la 'Cantidad a pedir' y finalmente presiona 'Confirmar Mi Compra'."
            - Si preguntan por sus compras anteriores: Diles literalmente: "Haz clic en 'Ver Historial y Rastreo' en tu panel principal."
            - Si preguntan cómo cambiar datos del local: Diles: "Haz clic en 'Gestionar Local' desde tu panel principal."
            - Si preguntan por pagos: Los tenderos pagan al recibir el pedido (contra-entrega) o a 14 días.
            Usa emojis amigables. No des detalles técnicos. Si no sabes algo, diles que llamen al soporte al 0999999999.
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": pregunta}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            respuesta_texto = response.choices[0].message.content
            
            return JsonResponse({
                'respuesta': respuesta_texto,
                'hablar': bot_voz_activa
            })
            
        except Exception as e:
            return JsonResponse({'respuesta': '¡Uy! Me he tropezado un poco, intenta preguntarme de nuevo.', 'hablar': False})
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='/login/')
def ver_comisiones_vendedor(request):
    mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()
    if len(mis_vendedores) == 0:
        return redirect('hub')
    mi_vendedor = mis_vendedores[0]
    
    # Historial detallado
    historial_pedidos = Pedido.objects.filter(vendedor=mi_vendedor, estado_pedido='Completado').order_by('-fecha_hora_emision')
    
    # Agregaciones ORM
    total_historico = historial_pedidos.aggregate(Sum('comision_generada'))['comision_generada__sum'] or 0.0
    total_pendiente = historial_pedidos.filter(comision_pagada=False).aggregate(Sum('comision_generada'))['comision_generada__sum'] or 0.0
    total_pagado = historial_pedidos.filter(comision_pagada=True).aggregate(Sum('comision_generada'))['comision_generada__sum'] or 0.0

    contexto = {
        'total_historico': total_historico,
        'total_pendiente': total_pendiente,
        'total_pagado': total_pagado,
        'historial_pedidos': historial_pedidos
    }
    return render(request, 'comisiones_vendedor.html', contexto)

@login_required(login_url='/login/')
def gestionar_comisiones_empresa(request):
    mis_empresas = Empresa.objects.filter(usuario=request.user).all()
    if len(mis_empresas) == 0:
        return redirect('hub')
    mi_empresa = mis_empresas[0]
    
    # Pedidos completados que pertenecen a esta empresa, fueron generados por un vendedor y no han sido pagados
    pedidos_pendientes = Pedido.objects.filter(empresa=mi_empresa, vendedor__isnull=False, estado_pedido='Completado', comision_pagada=False)
    
    # Agrupamos por vendedor en un diccionario para la vista
    vendedores_deuda = {}
    for pedido in pedidos_pendientes:
        vid = pedido.vendedor.id
        if vid not in vendedores_deuda:
            vendedores_deuda[vid] = {
                'vendedor': pedido.vendedor,
                'total_deuda': 0.0,
                'cantidad_pedidos': 0
            }
        vendedores_deuda[vid]['total_deuda'] += pedido.comision_generada
        vendedores_deuda[vid]['cantidad_pedidos'] += 1
        
    contexto = {
        'vendedores_deuda': vendedores_deuda.values()
    }
    return render(request, 'gestionar_comisiones_empresa.html', contexto)

@login_required(login_url='/login/')
def liquidar_comisiones_vendedor(request, vendedor_id):
    if request.method == 'POST':
        mis_empresas = Empresa.objects.filter(usuario=request.user).all()
        if len(mis_empresas) == 0:
            return redirect('hub')
        mi_empresa = mis_empresas[0]
        
        # Marcar como pagados los pedidos pendientes del vendedor con esta empresa
        pedidos_pendientes = Pedido.objects.filter(empresa=mi_empresa, vendedor_id=vendedor_id, estado_pedido='Completado', comision_pagada=False)
        pedidos_pendientes.update(comision_pagada=True)
        
        messages.info(request, 'Las comisiones del vendedor han sido liquidadas exitosamente.')
        
    return redirect('gestionar_comisiones_empresa')