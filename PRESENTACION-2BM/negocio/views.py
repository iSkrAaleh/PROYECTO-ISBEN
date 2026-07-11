from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from negocio.models import Empresa, Vendedor, Tendero

def index(request):
    return redirect('login')

def csrf_failure(request, reason=""):
    messages.warning(request, 'Tu sesión de seguridad caducó o el navegador usó caché viejo. Por favor intenta de nuevo.')
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
            messages.error(request, 'Usuario o contraseña incorrectos')
            return redirect('login')
    else:
        form = AuthenticationForm()
        
    diccionario = {'form': form}
    return render(request, 'login.html', diccionario)

@login_required(login_url='/login/')
def hub_view(request):
    user = request.user
    
    # Valores por defecto
    tipo_usuario = 'Admin/Otro'
    nombre_usuario = user.username
    plantilla = 'hub.html'
    
    # Bloque clásico de Try/Except aprendido en clase
    try:
        if user.empresa:
            tipo_usuario = 'Empresa'
            nombre_usuario = user.empresa.razon_social
            plantilla = 'hub_empresa.html'
    except Empresa.DoesNotExist:
        try:
            if user.vendedor:
                tipo_usuario = 'Vendedor'
                nombre_usuario = f"{user.first_name} {user.last_name}"
                plantilla = 'hub_vendedor.html'
        except Vendedor.DoesNotExist:
            try:
                if user.tendero:
                    tipo_usuario = 'Tendero'
                    nombre_usuario = f"{user.first_name} {user.last_name}"
                    plantilla = 'hub_tendero.html'
            except Tendero.DoesNotExist:
                pass # Se queda con los valores por defecto de Admin
        
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
    try:
        # Obtenemos la empresa del usuario logueado
        mi_empresa = request.user.empresa
        
        # Importar el modelo Producto localmente o arriba. Mejor lo importamos arriba, pero como estamos reemplazando un fragmento al final, asumo que Producto ya está importado o lo importamos aquí.
        from negocio.models import Producto
        
        # Filtramos solo los productos de esa empresa
        mis_productos = Producto.objects.filter(empresa=mi_empresa)
        
        diccionario = {'productos': mis_productos}
        return render(request, 'productos_empresa.html', diccionario)
        
    except Empresa.DoesNotExist:
        # Si un tendero intenta entrar aquí, lo regresamos a su hub
        return redirect('hub')

@login_required(login_url='/login/')
def seleccionar_tendero_view(request, empresa_id):
    try:
        mi_vendedor = request.user.vendedor
        
        # Buscador por GET
        q = request.GET.get('q', '')
        if q:
            lista_tenderos = Tendero.objects.filter(nombre_local__icontains=q)
        else:
            lista_tenderos = Tendero.objects.all()
            
        diccionario = {'tenderos': lista_tenderos, 'q': q, 'empresa_id': empresa_id}
        return render(request, 'seleccionar_tendero.html', diccionario)
        
    except Vendedor.DoesNotExist:
        # Si no es un vendedor, lo regresamos a su hub
        return redirect('hub')

@login_required(login_url='/login/')
def crear_pedido_view(request, empresa_id, tendero_id):
    try:
        # 1. Asegurarnos que es un vendedor
        mi_vendedor = request.user.vendedor
        
        # 2. Buscar el tendero y la empresa
        from negocio.models import Tendero, Producto, Empresa
        tendero_seleccionado = Tendero.objects.get(id=tendero_id)
        empresa_seleccionada = Empresa.objects.get(id=empresa_id)
        
        # 3. Traer solo los productos activos de ESTA empresa
        lista_productos = Producto.objects.filter(estado_activo=True, empresa=empresa_seleccionada)
        
        diccionario = {
            'tendero': tendero_seleccionado,
            'productos': lista_productos,
            'empresa_id': empresa_id
        }
        return render(request, 'crear_pedido.html', diccionario)
        
    except (Vendedor.DoesNotExist, Tendero.DoesNotExist, Empresa.DoesNotExist):
        # Si algo falla o no existe, regresa al hub
        return redirect('hub')

@login_required(login_url='/login/')
def guardar_pedido_view(request):
    if request.method == 'POST':
        try:
            mi_vendedor = request.user.vendedor
            
            # 1. Obtener ID del tendero
            tendero_id = request.POST.get('tendero_id')
            
            from negocio.models import Tendero, Producto, Pedido, DetallePedido
            from django.utils import timezone
            
            tendero = Tendero.objects.get(id=tendero_id)
            
            # 2. Creamos el Pedido general inicial en 0
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
            
            # 3. Recorremos todos los productos para ver cuáles se enviaron en el form
            lista_productos = Producto.objects.filter(estado_activo=True)
            for producto in lista_productos:
                # Los nombres de los inputs ahora incluyen el ID (ej: cantidad_5)
                cant_str = request.POST.get(f'cantidad_{producto.id}')
                
                # Si el campo cantidad no está vacío y es un número
                if cant_str and cant_str.isdigit():
                    cantidad = int(cant_str)
                    if cantidad > 0:
                        precio_str = request.POST.get(f'precio_venta_{producto.id}')
                        
                        if precio_str:
                            precio_venta = float(precio_str)
                        else:
                            precio_venta = producto.precio_mayorista
                        
                        # Validar stock
                        if cantidad > producto.stock_actual:
                            messages.warning(request, f'Saltamos {producto.nombre_producto}: falta de stock.')
                            continue
                            
                        # Validar que no pierda dinero (precio_venta >= precio_mayorista)
                        if precio_venta < producto.precio_mayorista:
                            messages.warning(request, f'Saltamos {producto.nombre_producto}: El precio de venta (${precio_venta}) no puede ser menor al costo de la empresa (${producto.precio_mayorista}).')
                            continue
                            
                        subtotal_linea = cantidad * precio_venta
                        total_pedido += subtotal_linea
                        
                        # Crear el Detalle
                        DetallePedido.objects.create(
                            cantidad_producto=cantidad,
                            precio_unitario_aplicado=precio_venta,
                            subtotal_linea=subtotal_linea,
                            pedido=nuevo_pedido,
                            producto=producto
                        )
                        
                        # Restar el stock
                        producto.stock_actual -= cantidad
                        producto.save()
                        productos_agregados += 1
            
            # 4. Finalizar
            if productos_agregados > 0:
                # Actualizar totales
                nuevo_pedido.subtotal_pedido = total_pedido
                nuevo_pedido.total_pedido = total_pedido
                nuevo_pedido.save()
                messages.info(request, f'¡Pedido múltiple registrado! ({productos_agregados} tipos de productos)')
            else:
                # Si no vendió nada, borramos el pedido vacío
                nuevo_pedido.delete()
                messages.error(request, 'No se agregó ningún producto válido al pedido.')
                
            return redirect('hub')
            
        except Exception as e:
            messages.error(request, 'Ocurrió un error procesando el pedido.')
            return redirect('hub')
    else:
        # Si alguien entra a esta URL sin enviar un formulario, lo regresamos
        return redirect('hub')

@login_required(login_url='/login/')
def seleccionar_empresa_view(request):
    try:
        mi_vendedor = request.user.vendedor
        from negocio.models import Empresa, SolicitudVendedor
        
        empresas = Empresa.objects.all()
        lista_empresas_info = []
        
        for emp in empresas:
            solicitud = SolicitudVendedor.objects.filter(vendedor=mi_vendedor, empresa=emp).first()
            
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
        
    except Vendedor.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def enviar_solicitud_view(request, empresa_id):
    try:
        mi_vendedor = request.user.vendedor
        from negocio.models import Empresa, SolicitudVendedor
        from django.utils import timezone
        
        empresa = Empresa.objects.get(id=empresa_id)
        
        existe = SolicitudVendedor.objects.filter(vendedor=mi_vendedor, empresa=empresa).exists()
        if not existe:
            SolicitudVendedor.objects.create(
                vendedor=mi_vendedor,
                empresa=empresa,
                fecha_solicitud=timezone.now(),
                estado_solicitud="Pendiente"
            )
            messages.success(request, f"¡Solicitud enviada a {empresa.razon_social}!")
        else:
            messages.warning(request, "Ya habías enviado una solicitud a esta empresa.")
            
        return redirect('seleccionar_empresa')
        
    except (Vendedor.DoesNotExist, Empresa.DoesNotExist):
        return redirect('hub')

@login_required(login_url='/login/')
def revisar_solicitudes_view(request):
    try:
        # Nos aseguramos de que quien entra sea una EMPRESA
        mi_empresa = request.user.empresa
        from negocio.models import SolicitudVendedor
        
        # Traemos solo las solicitudes "Pendientes" que le pertenecen a esta empresa
        pendientes = SolicitudVendedor.objects.filter(empresa=mi_empresa, estado_solicitud="Pendiente")
        
        diccionario = {'solicitudes': pendientes}
        return render(request, 'revisar_solicitudes.html', diccionario)
        
    except Empresa.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def aprobar_solicitud_view(request, solicitud_id):
    try:
        mi_empresa = request.user.empresa
        from negocio.models import SolicitudVendedor
        
        # Buscamos esa solicitud en específico
        solicitud = SolicitudVendedor.objects.get(id=solicitud_id, empresa=mi_empresa)
        
        # Le cambiamos el estado y guardamos
        solicitud.estado_solicitud = "Aprobado"
        solicitud.save()
        
        messages.success(request, f'¡Solicitud de {solicitud.vendedor.usuario.first_name} aprobada!')
        return redirect('revisar_solicitudes')
        
    except Empresa.DoesNotExist:
        return redirect('hub')
    except SolicitudVendedor.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def seleccionar_empresa_tendero_view(request):
    try:
        mi_tendero = request.user.tendero
        from negocio.models import Empresa
        
        empresas = Empresa.objects.all()
        
        diccionario = {'empresas': empresas}
        return render(request, 'seleccionar_empresa_tendero.html', diccionario)
        
    except Tendero.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def catalogo_tendero_view(request, empresa_id):
    try:
        mi_tendero = request.user.tendero
        from negocio.models import Empresa, Producto
        
        empresa_seleccionada = Empresa.objects.get(id=empresa_id)
        
        # Filtramos solo los productos activos que le pertenecen a esta empresa
        lista_productos = Producto.objects.filter(estado_activo=True, empresa=empresa_seleccionada)
        
        diccionario = {
            'empresa': empresa_seleccionada,
            'productos': lista_productos
        }
        return render(request, 'catalogo_tendero.html', diccionario)
        
    except Tendero.DoesNotExist:
        return redirect('hub')
    except Empresa.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def guardar_pedido_tendero_view(request):
    if request.method == 'POST':
        try:
            mi_tendero = request.user.tendero
            from negocio.models import Empresa, Producto, Pedido, DetallePedido
            from django.utils import timezone
            
            empresa_id = request.POST.get('empresa_id')
            empresa_seleccionada = Empresa.objects.get(id=empresa_id)
            
            # Filtramos los productos de esta empresa
            productos_empresa = Producto.objects.filter(empresa=empresa_seleccionada, estado_activo=True)
            
            total_pedido = 0.0
            detalles_a_crear = []
            
            for producto in productos_empresa:
                cantidad_str = request.POST.get(f'cantidad_{producto.id}')
                
                if cantidad_str and cantidad_str.strip() != '' and int(cantidad_str) > 0:
                    cantidad = int(cantidad_str)
                    
                    if cantidad > producto.stock_actual:
                        messages.warning(request, f'Saltamos {producto.nombre_producto}: falta de stock.')
                        continue
                        
                    # El tendero compra al costo mayorista directo
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
                    estado_pedido='Recibido por Empresa', # El estado inicial para el seguimiento
                    metodo_generacion='App Tendero',
                    tendero=mi_tendero,
                    vendedor=None # Compra directa
                )
                
                for det in detalles_a_crear:
                    DetallePedido.objects.create(
                        cantidad_producto=det['cantidad'],
                        precio_unitario_aplicado=det['precio_unitario'],
                        subtotal_linea=det['subtotal'],
                        pedido=nuevo_pedido,
                        producto=det['producto']
                    )
                    
                    # Restar stock
                    prod_db = det['producto']
                    prod_db.stock_actual -= det['cantidad']
                    prod_db.save()
                    
                messages.success(request, f'¡Pedido de ${total_pedido} enviado a {empresa_seleccionada.razon_social} exitosamente!')
            else:
                messages.error(request, 'No elegiste ningún producto válido. Pedido cancelado.')
                
            return redirect('mis_pedidos_tendero')
            
        except Tendero.DoesNotExist:
            return redirect('hub')
        except Empresa.DoesNotExist:
            return redirect('hub')
    return redirect('hub')

@login_required(login_url='/login/')
def mis_pedidos_tendero_view(request):
    try:
        mi_tendero = request.user.tendero
        from negocio.models import Pedido
        
        # Traemos todos los pedidos de este tendero, ordenados del más nuevo al más viejo
        pedidos = Pedido.objects.filter(tendero=mi_tendero).order_by('-fecha_hora_emision')
        
        diccionario = {'pedidos': pedidos}
        return render(request, 'mis_pedidos_tendero.html', diccionario)
        
    except Tendero.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def gestionar_pedidos_empresa_view(request):
    try:
        mi_empresa = request.user.empresa
        from negocio.models import Pedido
        
        # Estilo estudiante: Traemos todos y filtramos a mano
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
        
    except Empresa.DoesNotExist:
        return redirect('hub')

@login_required(login_url='/login/')
def actualizar_estado_pedido_view(request, pedido_id):
    if request.method == 'POST':
        try:
            mi_empresa = request.user.empresa
            from negocio.models import Pedido
            
            nuevo_estado = request.POST.get('nuevo_estado')
            
            # Aseguramos que el pedido existe y le pertenece a la empresa (por sus productos)
            pedido = Pedido.objects.filter(id=pedido_id, detalles__producto__empresa=mi_empresa).distinct().first()
            
            if pedido and nuevo_estado:
                pedido.estado_pedido = nuevo_estado
                pedido.save()
                messages.success(request, f'El estado del Pedido #{pedido.id} ha sido cambiado a "{nuevo_estado}".')
            else:
                messages.error(request, 'Error de seguridad o pedido no encontrado.')
                
            return redirect('gestionar_pedidos_empresa')
            
        except Empresa.DoesNotExist:
            return redirect('hub')
    return redirect('hub')
