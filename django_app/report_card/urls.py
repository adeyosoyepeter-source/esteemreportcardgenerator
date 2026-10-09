from django.urls import path
from . import views

app_name = 'report_card'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/upload/', views.upload_broadsheet, name='upload'),
    path('api/generate-pdfs/', views.generate_pdfs, name='generate_pdfs'),
    path('api/generate-single/', views.generate_single_pdf, name='generate_single'),
]
