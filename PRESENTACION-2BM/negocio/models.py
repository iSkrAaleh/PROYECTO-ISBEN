from django.db import models

class Usuario(models.Model):
    correo_electronico = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=255)
    rol_sistema = models.CharField(max_length=50)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class Empresa(Usuario):
    ruc = models.CharField(max_length=20)
    razon_social = models.CharField(max_length=150)
    representante_legal = models.CharField(max_length=100)
    telefono_contacto = models.CharField(max_length=20)
    limite_compra_minimo = models.FloatField()
    estado_verificacion = models.BooleanField(default=False)

    def __str__(self):
        return "%s %s %s" % (self.ruc, self.razon_social, self.representante_legal)

class Vendedor(Usuario):
    cedula = models.CharField(max_length=20)
    nombres_apellidos = models.CharField(max_length=150)
    telefono_movil = models.CharField(max_length=20)
    nota_capacitacion = models.FloatField(default=0.0)
    estado_aprobacion = models.BooleanField(default=False)

    def __str__(self):
        return "%s %s" % (self.cedula, self.nombres_apellidos)

class Tendero(Usuario):
    nombre_local = models.CharField(max_length=100)
    direccion_fisica = models.CharField(max_length=255)
    ruc_negocio = models.CharField(max_length=20)
    coordenadas_gps = models.CharField(max_length=100)

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
    fecha_hora_emision = models.DateTimeField(auto_now_add=True)
    subtotal_pedido = models.FloatField(default=0.0)
    total_pedido = models.FloatField(default=0.0)
    estado_pedido = models.CharField(max_length=50)
    metodo_generacion = models.CharField(max_length=50)
    
    tendero = models.ForeignKey(Tendero, on_delete=models.CASCADE, related_name="pedidos", null=True, blank=True)
    
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, related_name="pedidos_levantados", null=True, blank=True)

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
