from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('hub/', views.hub_view, name='hub'),
    path('logout/', views.logout_view, name='logout'),
    path('mis-productos/', views.listar_productos_empresa, name='listar_productos_empresa'),
    path('seleccionar-empresa/', views.seleccionar_empresa_view, name='seleccionar_empresa'),
    path('enviar-solicitud/<int:empresa_id>/', views.enviar_solicitud_view, name='enviar_solicitud'),
    path('seleccionar-tendero/<int:empresa_id>/', views.seleccionar_tendero_view, name='seleccionar_tendero'),
    path('crear-pedido/<int:empresa_id>/<int:tendero_id>/', views.crear_pedido_view, name='crear_pedido'),
    path('guardar-pedido/', views.guardar_pedido_view, name='guardar_pedido'),
    path('revisar-solicitudes/', views.revisar_solicitudes_view, name='revisar_solicitudes'),
    path('aprobar-solicitud/<int:solicitud_id>/', views.aprobar_solicitud_view, name='aprobar_solicitud'),
    path('comprar-empresa/', views.seleccionar_empresa_tendero_view, name='seleccionar_empresa_tendero'),
    path('catalogo-tendero/<int:empresa_id>/', views.catalogo_tendero_view, name='catalogo_tendero'),
    path('guardar-pedido-tendero/', views.guardar_pedido_tendero_view, name='guardar_pedido_tendero'),
    path('mis-pedidos-tendero/', views.mis_pedidos_tendero_view, name='mis_pedidos_tendero'),
    path('gestionar-pedidos/', views.gestionar_pedidos_empresa_view, name='gestionar_pedidos_empresa'),
    path('actualizar-estado-pedido/<int:pedido_id>/', views.actualizar_estado_pedido_view, name='actualizar_estado_pedido'),
]
