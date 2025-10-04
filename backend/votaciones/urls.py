from django.urls import path
from . import views

app_name = 'votaciones'

urlpatterns = [
    path('', views.index, name='index'),
    path('estudiantes/', views.tarjeton_estudiantes, name='tarjeton_estudiantes'),
    path('docentes/', views.tarjeton_docentes, name='tarjeton_docentes'),
    path('graduados/', views.tarjeton_graduados, name='tarjeton_graduados'),
    path('procesar-voto/', views.procesar_voto, name='procesar_voto'),
    path('gracias/', views.gracias, name='gracias'),
    # URLs del admin
    path('admin/dashboard/', views.dashboard_electoral, name='dashboard_electoral'),
    path('admin/reporte-pdf/', views.generar_reporte_pdf, name='reporte_pdf'),
    path('admin/estadisticas-json/', views.estadisticas_json, name='estadisticas_json'),
]