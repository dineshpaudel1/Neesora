from uuid import uuid4

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.text import slugify

from .models import CustomerProfile

User = get_user_model()


class RegistrationForm(forms.Form):
    email = forms.EmailField()
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput,
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. Please log in."
            )
        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The passwords do not match.")
        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        email_name = slugify(email.partition("@")[0]) or "neesora-customer"
        username = f"{email_name[:130]}-{uuid4().hex[:12]}"
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=self.cleaned_data["password1"],
            )
            CustomerProfile.objects.create(user=user)
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if email and password:
            user = User.objects.filter(email__iexact=email).first()
            if user is not None:
                self.cleaned_data["username"] = user.get_username()
        return super().clean()


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(
            request,
            "Your Neesora account has been created successfully.",
        )
        return redirect("accounts:account")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def account(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    return render(request, "accounts/account.html", {"profile": profile})


@login_required
def profile(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.full_name = request.POST.get("full_name", profile.full_name)
        profile.phone_number = request.POST.get("phone_number", profile.phone_number)
        profile.address = request.POST.get("address", profile.address)
        profile.city = request.POST.get("city", profile.city)
        profile.province = request.POST.get("province", profile.province)
        profile.postal_code = request.POST.get("postal_code", profile.postal_code)
        if request.FILES.get("profile_image"):
            profile.profile_image = request.FILES["profile_image"]
        profile.save()
        messages.success(request, "Your profile details were updated successfully.")
        return redirect("accounts:account")
    return render(request, "accounts/profile.html", {"profile": profile})
