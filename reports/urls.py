from django.urls import path
from . import views

urlpatterns = [
    path('report/new/', views.create_report, name='create_report'),
    path('listings/', views.listings, name='listings'),
    path('item/<int:report_id>/', views.item_details, name='item_details'),
    path('report-item/<int:report_id>/', views.report_item, name='report_item'),
    path('report/resolve/<int:report_id>/', views.close_case_manual, name='close_case_manual'),
    path('report/edit/<int:report_id>/', views.edit_report, name='edit_report'),
    path('report/flag/<int:report_id>/', views.flag_report, name='flag_report'),
    path('report/flag-reason/<int:report_id>/', views.report_item_page, name='report_item_page'),
]