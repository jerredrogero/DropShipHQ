from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from core.views import bfmr_deals
from django.utils.translation import gettext_lazy as _
from .views import bfmr_deals
from django.contrib import messages
from .views import bfmr_deals, get_item_id


class CustomPasswordResetView(auth_views.PasswordResetView):
    success_url = reverse_lazy('home')  # Replace 'home' with your home page URL name
    
    def form_valid(self, form):
        messages.success(self.request, "We've emailed you instructions for setting your password. You should receive them shortly.")
        return super().form_valid(form)

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('pricing/', views.pricing, name='pricing'),
    path('upgrade/<str:plan>/', views.upgrade_plan, name='upgrade_plan'),
    path('upgrade_success/', views.upgrade_success, name='upgrade_success'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('', views.home, name='home'),
    path('delete-order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('settings/', views.account_settings, name='settings'),
    path('bfmr-deals/', bfmr_deals, name='bfmr_deals'),
    path('edit-order/<int:order_id>/', views.edit_order, name='edit_order'),
    path('deal-calculator/', views.deal_calculator, name='deal_calculator'),
    path('delete-buying-group/<int:buying_group_id>/', views.delete_buying_group, name='delete_buying_group'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('bfmr-deals/', bfmr_deals, name='bfmr_deals'),
    path('get-item-id/', get_item_id, name='get_item_id'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]