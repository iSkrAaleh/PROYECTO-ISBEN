from django.db import models
from django.contrib.auth.models import User

class Empresa(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="empresa")
    telefono = models.CharField(max_length=20, default="")
    ruc = models.CharField(max_length=20)
    razon_social = models.CharField(max_length=150)
    representante_legal = models.CharField(max_length=100)
    limite_compra_minimo = models.FloatField()
    estado_verificacion = models.BooleanField(default=False)
    requiere_aprobacion = models.BooleanField(default=False)

    # Lógica Freemium/Premium
    PLAN_CHOICES = (
        ('TRIAL', 'Prueba 14 Días'),
        ('PREMIUM', 'Premium'),
    )
    tipo_plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='TRIAL')
    suscripcion_activa = models.BooleanField(default=True)
    fecha_vencimiento_prueba = models.DateTimeField(null=True, blank=True)
    
    # Nuevos campos de Perfil
    direccion_principal = models.CharField(max_length=255, default="", blank=True)
    foto_perfil = models.ImageField(upload_to='perfiles/empresas/', null=True, blank=True)
    bot_voz_activa = models.BooleanField(default=False, verbose_name='Activar respuestas por voz del Tigre Bot')

    def __str__(self):
        return "%s %s %s" % (self.ruc, self.razon_social, self.representante_legal)

class Vendedor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vendedor")
    telefono = models.CharField(max_length=20, default="")
    cedula = models.CharField(max_length=20)
    nota_capacitacion = models.FloatField(default=0.0)
    estado_aprobacion = models.BooleanField(default=False)
    
    # Nuevos campos de Perfil
    zona_cobertura = models.CharField(max_length=150, default="", blank=True)
    foto_perfil = models.ImageField(upload_to='perfiles/vendedores/', null=True, blank=True)
    bot_voz_activa = models.BooleanField(default=False, verbose_name='Activar respuestas por voz del Tigre Bot')

    def __str__(self):
        return "%s %s %s" % (self.cedula, self.usuario.first_name, self.usuario.last_name)

class Tendero(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="tendero")
    telefono = models.CharField(max_length=20, default="")
    nombre_local = models.CharField(max_length=100)
    direccion_fisica = models.CharField(max_length=255)
    ruc_negocio = models.CharField(max_length=20)
    coordenadas_gps = models.CharField(max_length=100)
    
    # Nuevos campos de Perfil
    referencias = models.CharField(max_length=255, default="", blank=True)
    foto_perfil = models.ImageField(upload_to='perfiles/tenderos/', null=True, blank=True)
    bot_voz_activa = models.BooleanField(default=False, verbose_name='Activar respuestas por voz del Tigre Bot')

    def __str__(self):
        return "%s %s" % (self.nombre_local, self.ruc_negocio)

class Suscripcion(models.Model):
    tipo_plan = models.CharField(max_length=50)
    costo_plan = models.FloatField()
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    estado_pago = models.BooleanField(default=False)
    
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name="suscripcion")

    def __str__(self):
        return "%s %.2f" % (self.tipo_plan, self.costo_plan)

class Producto(models.Model):
    codigo_sku = models.CharField(max_length=50)
    nombre_producto = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    precio_mayorista = models.FloatField()
    stock_actual = models.IntegerField(default=0)
    estado_activo = models.BooleanField(default=True)
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="productos")

    def __str__(self):
        return "%s %s %.2f" % (self.codigo_sku, self.nombre_producto, self.precio_mayorista)

class Pedido(models.Model):
    fecha_hora_emision = models.DateTimeField()
    subtotal_pedido = models.FloatField(default=0.0)
    total_pedido = models.FloatField(default=0.0)
    estado_pedido = models.CharField(max_length=50)
    metodo_generacion = models.CharField(max_length=50)
    
    tendero = models.ForeignKey(Tendero, on_delete=models.CASCADE, related_name="pedidos", null=True, blank=True)
    
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, related_name="pedidos_levantados", null=True, blank=True)

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="pedidos_empresa", null=True, blank=True)
    comision_generada = models.FloatField(default=0.0)
    comision_pagada = models.BooleanField(default=False)

    def __str__(self):
        return "%s %s" % (self.estado_pedido, self.metodo_generacion)

class DetallePedido(models.Model):
    cantidad_producto = models.IntegerField()
    precio_unitario_aplicado = models.FloatField()
    subtotal_linea = models.FloatField()
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="detalles_pedido")

    def __str__(self):
        return "%d %.2f" % (self.cantidad_producto, self.precio_unitario_aplicado)

class SolicitudVendedor(models.Model):
    # establecemos la relacion entre el intermediario y el proveedor
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, related_name="solicitudes")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="solicitudes_recibidas")
    
    # registramos la fecha de creacion del documento
    fecha_solicitud = models.DateTimeField()
    
    # definimos el estado inicial del flujo de aprobacion
    estado_solicitud = models.CharField(max_length=50, default="Pendiente")

    def __str__(self):
        # retornamos un texto representativo de la solicitud
        return "%s a %s - %s" % (self.vendedor.usuario.username, self.empresa.razon_social, self.estado_solicitud)
