from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from core.views import bfmr_deals
from django.utils.translation import gettext_lazy as _
from .views import bfmr_deals
from .views import bfmr_deals, get_item_id

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('pricing/', views.pricing, name='pricing'),
    path('upgrade/<str:plan>/', views.upgrade_plan, name='upgrade_plan'),
    path('upgrade_success/', views.upgrade_success, name='upgrade_success'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('delete-order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('settings/', views.account_settings, name='settings'),
    path('edit-order/<int:order_id>/', views.edit_order, name='edit_order'),
    path('deal-calculator/', views.deal_calculator, name='deal_calculator'),
    path('delete-buying-group/<int:buying_group_id>/', views.delete_buying_group, name='delete_buying_group'),
    path('bfmr-deals/', bfmr_deals, name='bfmr_deals'),
    path('get-item-id/', get_item_id, name='get_item_id'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('update-paid-status/<int:order_id>/', views.update_paid_status, name='update_paid_status'),
]