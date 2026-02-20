from django import forms
from captcha.fields import CaptchaField
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from .models import StudentProfile

User = get_user_model()

class StudentLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter your email',
            'autocomplete': 'off',
            'autofill': 'off'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter your password',
            'autocomplete': 'new-password',
            'autofill': 'off'
        })
    )

    captcha = CaptchaField()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError("Email not registered")

            if not user.check_password(password):
                raise forms.ValidationError("Incorrect password")

            cleaned_data['user'] = user  # store user for view
        return cleaned_data
    
    
class RegisterForm(forms.Form):
    # User fields
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autocomplete': 'off'
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autocomplete': 'off'
        })
    )

    institute = forms.ChoiceField(
        choices=[("", "Select Institute")] + [
            ('Government Polytechnic, Nashik', 'Government Polytechnic, Nashik'),
            ('Guru Gobind Singh Polytechnic, Nashik', 'Guru Gobind Singh Polytechnic, Nashik'),
            ('KK Wagh Polytechnic, Nashik', 'KK Wagh Polytechnic, Nashik'),
            ('KK Wagh Women’s Polytechnic, Nashik', 'KK Wagh Women’s Polytechnic, Nashik'),
            ('HHJB Polytechnic, Nashik', 'HHJB Polytechnic, Nashik'),
            ('SND Polytechnic, Yeola (Nashik district)', 'SND Polytechnic, Yeola (Nashik district)'),
            ('Brahma Valley Polytechnic, Nashik district', 'Brahma Valley Polytechnic, Nashik district'),
            ('MET Institute of Technology Polytechnic, Adgaon (Nashik)', 'MET Institute of Technology Polytechnic, Adgaon (Nashik)'),
            ('RSM Polytechnic, Nashik', 'RSM Polytechnic, Nashik'),
            ('AKM Polytechnic, Igatpuri (Nashik district)', 'AKM Polytechnic, Igatpuri (Nashik district)'),
            ('Matoshri Asarabai Polytechnic, Nashik', 'Matoshri Asarabai Polytechnic, Nashik'),
            ('Sandip Polytechnic, Nashik', 'Sandip Polytechnic, Nashik'),
            ('JM Charitable Trust Polytechnic, Nashik', 'JM Charitable Trust Polytechnic, Nashik'),
            ('LGG Polytechnic, Vilhole (Nashik)', 'LGG Polytechnic, Vilhole (Nashik)'),
            ('Shatabdi Institute of Technology Polytechnic (Sinner, Nashik)', 'Shatabdi Institute of Technology Polytechnic (Sinner, Nashik)'),
            ('Potdar Polytechnic, Malegaon (Nashik)', 'Potdar Polytechnic, Malegaon (Nashik)'),
            ('Kadwa Polytechnic, Dindori (Nashik district)', 'Kadwa Polytechnic, Dindori (Nashik district)'),
            ('Vidya Institute of Technology Polytechnic, Dhanore (Nashik)', 'Vidya Institute of Technology Polytechnic, Dhanore (Nashik)'),
            ('Shri Kapildhara Polytechnic (Igatpuri, Nashik district)', 'Shri Kapildhara Polytechnic (Igatpuri, Nashik district)'),
            ('K.V.N. Naik S.P. Sanstha’s Polytechnic, Nashik', 'K.V.N. Naik S.P. Sanstha’s Polytechnic, Nashik'),
            ('SNJB’s Shri Hiralal Hastimal (Jain Brothers) Polytechnic (Chandwad, Nashik district)', 'SNJB’s Shri Hiralal Hastimal (Jain Brothers) Polytechnic (Chandwad, Nashik district)'),
            ('Swami Polytechnic (Abhona, Kalwan, Nashik district)', 'Swami Polytechnic (Abhona, Kalwan, Nashik district)'),
            ('Sunsuba Polytechnic (Laxminagar, Igatpuri, Nashik district)', 'Sunsuba Polytechnic (Laxminagar, Igatpuri, Nashik district)'),
            ('Gurukul Education Society’s Institute of Engineering & Technology (Nandgaon, Nashik district)', 'Gurukul Education Society’s Institute of Engineering & Technology (Nandgaon, Nashik district)'),
            ('Maulana Mukhtar Ahmad Nadvi Technical Campus (Malegaon, Nashik district)', 'Maulana Mukhtar Ahmad Nadvi Technical Campus (Malegaon, Nashik district)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    department = forms.ChoiceField(
        choices=[
            ("", "Select Department"),
            ('Computer Engineering', 'Computer Engineering'),
            ('Information Technology', 'Information Technology'),
            ('Mechanical Engineering', 'Mechanical Engineering'),
            ('Civil Engineering', 'Civil Engineering'),
            ('Electrical Engineering', 'Electrical Engineering'),
            ('Electronics Engineering', 'Electronics Engineering'),
            ('Mechatronics Engineering', 'Mechatronics Engineering'),
            ('Polymer Engineering', 'Polymer Engineering'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    year = forms.ChoiceField(
        choices=[
            ("", "Select Year Of Study"),
            ('1st Year', '1st Year'),
            ('2nd Year', '2nd Year'),
            ('3rd Year', '3rd Year'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Password fields
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your roll number',
            'autocomplete': 'new-password'
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your roll number',
            'autocomplete': 'new-password'
        })
    )

    # Captcha
    captcha = CaptchaField()

    # Password validation
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email',
            'autocomplete': 'off'
        }),
        validators=[EmailValidator()]
    )
    captcha = CaptchaField()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No account found with this email address.")
        return email


class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your roll number',
            'autocomplete': 'new-password'
        })
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your roll number',
            'autocomplete': 'new-password'
        })
    )
    captcha = CaptchaField()

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        # Add password strength validation
        if new_password and len(new_password) < 4:
            raise forms.ValidationError("Password must be at least 4 characters long")
        
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = StudentProfile
        fields = ['institute', 'department', 'year']
        widgets = {
            'institute': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add the same choices as in RegisterForm
        self.fields['institute'].choices = [("", "Select Institute")] + [
            ('Government Polytechnic, Nashik', 'Government Polytechnic, Nashik'),
            ('Guru Gobind Singh Polytechnic, Nashik', 'Guru Gobind Singh Polytechnic, Nashik'),
            ('KK Wagh Polytechnic, Nashik', 'KK Wagh Polytechnic, Nashik'),
            ('KK Wagh Women’s Polytechnic, Nashik', 'KK Wagh Women’s Polytechnic, Nashik'),
            ('HHJB Polytechnic, Nashik', 'HHJB Polytechnic, Nashik'),
            ('SND Polytechnic, Yeola (Nashik district)', 'SND Polytechnic, Yeola (Nashik district)'),
            ('Brahma Valley Polytechnic, Nashik district', 'Brahma Valley Polytechnic, Nashik district'),
            ('MET Institute of Technology Polytechnic, Adgaon (Nashik)', 'MET Institute of Technology Polytechnic, Adgaon (Nashik)'),
            ('RSM Polytechnic, Nashik', 'RSM Polytechnic, Nashik'),
            ('AKM Polytechnic, Igatpuri (Nashik district)', 'AKM Polytechnic, Igatpuri (Nashik district)'),
            ('Matoshri Asarabai Polytechnic, Nashik', 'Matoshri Asarabai Polytechnic, Nashik'),
            ('Sandip Polytechnic, Nashik', 'Sandip Polytechnic, Nashik'),
            ('JM Charitable Trust Polytechnic, Nashik', 'JM Charitable Trust Polytechnic, Nashik'),
            ('LGG Polytechnic, Vilhole (Nashik)', 'LGG Polytechnic, Vilhole (Nashik)'),
            ('Shatabdi Institute of Technology Polytechnic (Sinner, Nashik)', 'Shatabdi Institute of Technology Polytechnic (Sinner, Nashik)'),
            ('Potdar Polytechnic, Malegaon (Nashik)', 'Potdar Polytechnic, Malegaon (Nashik)'),
            ('Kadwa Polytechnic, Dindori (Nashik district)', 'Kadwa Polytechnic, Dindori (Nashik district)'),
            ('Vidya Institute of Technology Polytechnic, Dhanore (Nashik)', 'Vidya Institute of Technology Polytechnic, Dhanore (Nashik)'),
            ('Shri Kapildhara Polytechnic (Igatpuri, Nashik district)', 'Shri Kapildhara Polytechnic (Igatpuri, Nashik district)'),
            ('K.V.N. Naik S.P. Sanstha’s Polytechnic, Nashik', 'K.V.N. Naik S.P. Sanstha’s Polytechnic, Nashik'),
            ('SNJB’s Shri Hiralal Hastimal (Jain Brothers) Polytechnic (Chandwad, Nashik district)', 'SNJB’s Shri Hiralal Hastimal (Jain Brothers) Polytechnic (Chandwad, Nashik district)'),
            ('Swami Polytechnic (Abhona, Kalwan, Nashik district)', 'Swami Polytechnic (Abhona, Kalwan, Nashik district)'),
            ('Sunsuba Polytechnic (Laxminagar, Igatpuri, Nashik district)', 'Sunsuba Polytechnic (Laxminagar, Igatpuri, Nashik district)'),
            ('Gurukul Education Society’s Institute of Engineering & Technology (Nandgaon, Nashik district)', 'Gurukul Education Society’s Institute of Engineering & Technology (Nandgaon, Nashik district)'),
            ('Maulana Mukhtar Ahmad Nadvi Technical Campus (Malegaon, Nashik district)', 'Maulana Mukhtar Ahmad Nadvi Technical Campus (Malegaon, Nashik district)'),
        ]
        
        self.fields['department'].choices = [
            ("", "Select Department"),
            ('Computer Engineering', 'Computer Engineering'),
            ('Information Technology', 'Information Technology'),
            ('Mechanical Engineering', 'Mechanical Engineering'),
            ('Civil Engineering', 'Civil Engineering'),
            ('Electrical Engineering', 'Electrical Engineering'),
            ('Electronics Engineering', 'Electronics Engineering'),
            ('Mechatronics Engineering', 'Mechatronics Engineering'),
            ('Polymer Engineering', 'Polymer Engineering'),
        ]
        
        self.fields['year'].choices = [
            ("", "Select Year Of Study"),
            ('1st Year', '1st Year'),
            ('2nd Year', '2nd Year'),
            ('3rd Year', '3rd Year'),
        ]


class PasswordChangeForm(forms.Form):
    """Form for changing password"""
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
            'autocomplete': 'current-password'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        })
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Current password is incorrect")
        return old_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')
        
        if new_password and confirm_new_password and new_password != confirm_new_password:
            raise forms.ValidationError("New passwords do not match")
        
        # Add password strength validation
        if new_password and len(new_password) < 4:
            raise forms.ValidationError("New password must be at least 4 characters long")
        
        return cleaned_data