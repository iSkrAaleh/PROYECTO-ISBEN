from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from negocio.models import Empresa, Vendedor, Tendero

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
