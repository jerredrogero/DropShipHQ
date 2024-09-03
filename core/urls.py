from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from core.views import bfmr_deals

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('delete_order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('settings/', views.settings, name='settings'),
    path('bfmr-deals/', bfmr_deals, name='bfmr_deals'),
    path('edit_order/<int:order_id>/', views.edit_order, name='edit_order'),
]