from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('hub/', views.hub_view, name='hub'),
    path('logout/', views.logout_view, name='logout'),
]
