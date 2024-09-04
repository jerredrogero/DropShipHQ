from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from core.views import bfmr_deals
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .forms import UserCreationForm
from .views import CustomPasswordResetDoneView
from django.contrib import messages


class CustomLoginView(auth_views.LoginView):
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['password'].label = _("Password")
        return form

class UserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = _("Password")
        self.fields['password2'].label = _("Password confirmation")

class CustomSignupView(auth_views.FormView):
    form_class = UserCreationForm
    template_name = 'core/signup.html'
    success_url = '/'  # Redirect to home page after successful signup

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class CustomPasswordResetView(auth_views.PasswordResetView):
    success_url = reverse_lazy('home')  # Replace 'home' with your home page URL name
    
    def form_valid(self, form):
        messages.success(self.request, "We've emailed you instructions for setting your password. You should receive them shortly.")
        return super().form_valid(form)

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signup/', CustomSignupView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('delete-order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('settings/', views.settings, name='settings'),
    path('bfmr-deals/', bfmr_deals, name='bfmr_deals'),
    path('edit-order/<int:order_id>/', views.edit_order, name='edit_order'),
    path('deal-calculator/', views.deal_calculator, name='deal_calculator'),
    path('delete-buying-group/<int:pk>/', views.delete_buying_group, name='delete_buying_group'),
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]