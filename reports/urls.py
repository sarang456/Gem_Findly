from django.urls import path
from . import views

urlpatterns = [
    path('report/new/', views.create_report, name='create_report'),
    path('listings/', views.listings, name='listings'),
    path('item/<int:report_id>/', views.item_details, name='item_details'),
    path('report-item/<int:report_id>/', views.report_item, name='report_item'),
    path('report/resolve/<int:report_id>/', views.close_case_manual, name='close_case_manual'),
]