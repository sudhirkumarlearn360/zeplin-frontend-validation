from django.urls import path
from . import views

app_name = 'validator'

urlpatterns = [
    path('', views.InputPageView.as_view(), name='input'),
    path('report/<int:pk>/', views.ReportPageView.as_view(), name='report'),
    path('report/<int:pk>/locate/<int:idx>/', views.LocateDefectView.as_view(), name='locate'),
    path('report/<int:pk>/locate_all/', views.LocateAllDefectsView.as_view(), name='locate_all'),
    path('reports/', views.ReportListView.as_view(), name='list'),
]
