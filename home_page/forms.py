from django import forms
from captcha.fields import CaptchaField
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()  # <- important parentheses

class StudentLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter your email','autocomplete':'off','autofill':'off'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter your Roll Number','autocomplete':'new-password','autofill':'off'
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
        widget=forms.TextInput(attrs={'placeholder': 'Enter your username','autocomplete':'off'})
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email','autocomplete':'off'})
    )

    institute = forms.ChoiceField(
    choices=[("","Select Institute"),
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
    )


    department = forms.ChoiceField(
    choices=[
        ("","Select Department"),
        ('Computer Engineering', 'Computer Engineering'),
        ('Information Technology', 'Information Technology'),
        ('Mechanical Engineering', 'Mechanical Engineering'),
        ('Civil Engineering', 'Civil Engineering'),
        ('Electrical Engineering', 'Electrical Engineering'),
        ('Electronics Engineering','Electronics Engineering'),
        ('Mechatronis Engineering','Mechatronics Enginnering'),
        ('Polymer Engineering','Polyemer Engineering'),
    ]
)


    year = forms.ChoiceField(
        choices=[
            ("","Select Year Of Study"),
            ('1st Year', '1st Year'),
            ('2nd Year', '2nd Year'),
            ('3rd Year', '3rd Year'),
        ]
    )

    # Password fields
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your roll number','autocomplete':'new-password'})
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your roll number','autocomplete':'new-password'})
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
