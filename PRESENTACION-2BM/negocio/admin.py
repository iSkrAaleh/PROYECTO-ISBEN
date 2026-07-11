from django.contrib import admin

# Importamos los modelos que creamos
from .models import Empresa, Vendedor, Tendero, Suscripcion, Producto, Pedido, DetallePedido, SolicitudVendedor

# Registramos los modelos para que aparezcan en el panel de administrador
admin.site.register(Empresa)
admin.site.register(Vendedor)
admin.site.register(Tendero)
admin.site.register(Suscripcion)
admin.site.register(Producto)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(SolicitudVendedor)
