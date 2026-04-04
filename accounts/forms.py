import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Create Password (8-16 chars)',
        'class': 'auth-input'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password',
        'class': 'auth-input'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Enter Username', 'class': 'auth-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter Email Address', 'class': 'auth-input'}),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not (8 <= len(password) <= 16):
            raise ValidationError("Password must be between 8 and 16 characters long.")
        
        # Check for at least one letter, one number, and one special character
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError("Password must contain at least one letter.")
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character.")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
