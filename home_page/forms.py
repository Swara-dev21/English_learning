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

    # UPDATED: Institute field with codes
    institute = forms.ChoiceField(
        choices=[("", "Select Institute")] + [
            ('Government Polytechnic, Nashik (5010)', 'Government Polytechnic, Nashik (5010)'),
            ('K.K. Wagh Education Society\'s K. K. Wagh Polytechnic, Nashik (5226)', 'K.K. Wagh Education Society\'s K. K. Wagh Polytechnic, Nashik (5226)'),
            ('SNJB\'s Shri. Hiralal Hastimal (Jain Brothers, Jalgaon) Polytechnic, Chandwad (5230)', 'SNJB\'s Shri. Hiralal Hastimal (Jain Brothers, Jalgaon) Polytechnic, Chandwad (5230)'),
            ('Late Bhausaheb Hiray Smarnika Samiti Trust Sanchalit Polytechnic, Malegaon, Nashik (5235)', 'Late Bhausaheb Hiray Smarnika Samiti Trust Sanchalit Polytechnic, Malegaon, Nashik (5235)'),
            ('Mahavir Polytechnic, Nashik (5238)', 'Mahavir Polytechnic, Nashik (5238)'),
            ('Guru Gobind Singh Foundation\'s Guru Gobind Singh Polytechnic, Nashik (5240)', 'Guru Gobind Singh Foundation\'s Guru Gobind Singh Polytechnic, Nashik (5240)'),
            ('Jagdamba Edu. Soc., Santosh N. Darade Polytechnic, Yeola, Nashik (5241)', 'Jagdamba Edu. Soc., Santosh N. Darade Polytechnic, Yeola, Nashik (5241)'),
            ('Nashik Gramin Shikshan Prasarak Mandals Brahma Valley Polytechnic, Nashik (5243)', 'Nashik Gramin Shikshan Prasarak Mandals Brahma Valley Polytechnic, Nashik (5243)'),
            ('MET\'s Institute of Technology Polytechnic, Bhujbal Knowledge City, Adgaon, Nashik (5244)', 'MET\'s Institute of Technology Polytechnic, Bhujbal Knowledge City, Adgaon, Nashik (5244)'),
            ('NDMVPS Samaj\'s Rajarshee Shahu Maharaj Polytechnic, Nashik (5247)', 'NDMVPS Samaj\'s Rajarshee Shahu Maharaj Polytechnic, Nashik (5247)'),
            ('Sunsuba Polytechnic, Igatpuri (5254)', 'Sunsuba Polytechnic, Igatpuri (5254)'),
            ('Matoshri Education Society, Matoshri Asarabai Polytechnic, Nashik (5256)', 'Matoshri Education Society, Matoshri Asarabai Polytechnic, Nashik (5256)'),
            ('Sandip Foundation\'s Sandip Polytechnic, Nashik (5258)', 'Sandip Foundation\'s Sandip Polytechnic, Nashik (5258)'),
            ('Jumma Masjid Charitable Trust\'s Polytechnic, Wadala Road, Wadala, Nashik (5260)', 'Jumma Masjid Charitable Trust\'s Polytechnic, Wadala Road, Wadala, Nashik (5260)'),
            ('Matoshri Education Society, Matoshri Institute of Technology, Dhanore, Nashik (5263)', 'Matoshri Education Society, Matoshri Institute of Technology, Dhanore, Nashik (5263)'),
            ('Maharashtra Shikshan Vikas Mandal\'s Loknete Gopalraoji Gulwe Polytechnic, Vilholi, Nashik (5357)', 'Maharashtra Shikshan Vikas Mandal\'s Loknete Gopalraoji Gulwe Polytechnic, Vilholi, Nashik (5357)'),
            ('Amruta Vaishnavi Education & Welfare Trust\'s Shatabdi Institute of Technology, Agastkhind, Tal. Sinner (5363)', 'Amruta Vaishnavi Education & Welfare Trust\'s Shatabdi Institute of Technology, Agastkhind, Tal. Sinner (5363)'),
            ('Potdar Foundation Taloda, Potdar Polytechnic, Patne, Malegaon, Nashik (5366)', 'Potdar Foundation Taloda, Potdar Polytechnic, Patne, Malegaon, Nashik (5366)'),
            ('Nashik Institute of Technology, Late Annasaheb Patil Polytechnic, Dindori Road, Cannol Road, MERI, Nashik (5369)', 'Nashik Institute of Technology, Late Annasaheb Patil Polytechnic, Dindori Road, Cannol Road, MERI, Nashik (5369)'),
            ('Karmaveer R.S. Wagh Education & Health Institute, Kadwa Polytechnic, Rajaram Nagar, Tal-Dindori, Nashik (5371)', 'Karmaveer R.S. Wagh Education & Health Institute, Kadwa Polytechnic, Rajaram Nagar, Tal-Dindori, Nashik (5371)'),
            ('K.V.N. Naik S. P. Sansth\'s Loknete Gopinathji Munde Institute of Engineering Education & Research, Nashik (5390)', 'K.V.N. Naik S. P. Sansth\'s Loknete Gopinathji Munde Institute of Engineering Education & Research, Nashik (5390)'),
            ('Shree Kapildhara Polytechnic, Igatpuri (5402)', 'Shree Kapildhara Polytechnic, Igatpuri (5402)'),
            ('Gurukul Education Society\'s Institute of Engineering & Technology, Nandgaon (5404)', 'Gurukul Education Society\'s Institute of Engineering & Technology, Nandgaon (5404)'),
            ('Maulana Mukhtar Ahmad Nadvi Technical Campus, Malegaon (5411)', 'Maulana Mukhtar Ahmad Nadvi Technical Campus, Malegaon (5411)'),
            ('Gokhale Education Society\'s Sir Dr. M.S. Gosavi Polytechnic Institute, Nashik Road (5434)', 'Gokhale Education Society\'s Sir Dr. M.S. Gosavi Polytechnic Institute, Nashik Road (5434)'),
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
        ('Electronics and Telecommunication Engineering', 'Electronics and Telecommunication Engineering'),
        ('Mechatronics Engineering', 'Mechatronics Engineering'),
        ('Polymer Engineering', 'Polymer Engineering'),
        ('Computer Technology', 'Computer Technology'),
        ('Interior Designing Engineering', 'Interior Designing Engineering'),
        ('Dress designing and garment manufacturing Eng.', 'Dress designing and garment manufacturing Eng.'),
        ('Artificial Intelligence', 'Artificial Intelligence'),
        ('Automobile Engineering', 'Automobile Engineering'),
        ('Chemical Engineering', 'Chemical Engineering'),
        ('Textile Engineering', 'Textile Engineering'),
        ('Instrumentation Engineering', 'Instrumentation Engineering'),
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
        # UPDATED: Institute field with codes for Profile Update
        self.fields['institute'].choices = [("", "Select Institute")] + [
            ('Government Polytechnic, Nashik (5010)', 'Government Polytechnic, Nashik (5010)'),
            ('K.K. Wagh Education Society\'s K. K. Wagh Polytechnic, Nashik (5226)', 'K.K. Wagh Education Society\'s K. K. Wagh Polytechnic, Nashik (5226)'),
            ('SNJB\'s Shri. Hiralal Hastimal (Jain Brothers, Jalgaon) Polytechnic, Chandwad (5230)', 'SNJB\'s Shri. Hiralal Hastimal (Jain Brothers, Jalgaon) Polytechnic, Chandwad (5230)'),
            ('Late Bhausaheb Hiray Smarnika Samiti Trust Sanchalit Polytechnic, Malegaon, Nashik (5235)', 'Late Bhausaheb Hiray Smarnika Samiti Trust Sanchalit Polytechnic, Malegaon, Nashik (5235)'),
            ('Mahavir Polytechnic, Nashik (5238)', 'Mahavir Polytechnic, Nashik (5238)'),
            ('Guru Gobind Singh Foundation\'s Guru Gobind Singh Polytechnic, Nashik (5240)', 'Guru Gobind Singh Foundation\'s Guru Gobind Singh Polytechnic, Nashik (5240)'),
            ('Jagdamba Edu. Soc., Santosh N. Darade Polytechnic, Yeola, Nashik (5241)', 'Jagdamba Edu. Soc., Santosh N. Darade Polytechnic, Yeola, Nashik (5241)'),
            ('Nashik Gramin Shikshan Prasarak Mandals Brahma Valley Polytechnic, Nashik (5243)', 'Nashik Gramin Shikshan Prasarak Mandals Brahma Valley Polytechnic, Nashik (5243)'),
            ('MET\'s Institute of Technology Polytechnic, Bhujbal Knowledge City, Adgaon, Nashik (5244)', 'MET\'s Institute of Technology Polytechnic, Bhujbal Knowledge City, Adgaon, Nashik (5244)'),
            ('NDMVPS Samaj\'s Rajarshee Shahu Maharaj Polytechnic, Nashik (5247)', 'NDMVPS Samaj\'s Rajarshee Shahu Maharaj Polytechnic, Nashik (5247)'),
            ('Sunsuba Polytechnic, Igatpuri (5254)', 'Sunsuba Polytechnic, Igatpuri (5254)'),
            ('Matoshri Education Society, Matoshri Asarabai Polytechnic, Nashik (5256)', 'Matoshri Education Society, Matoshri Asarabai Polytechnic, Nashik (5256)'),
            ('Sandip Foundation\'s Sandip Polytechnic, Nashik (5258)', 'Sandip Foundation\'s Sandip Polytechnic, Nashik (5258)'),
            ('Jumma Masjid Charitable Trust\'s Polytechnic, Wadala Road, Wadala, Nashik (5260)', 'Jumma Masjid Charitable Trust\'s Polytechnic, Wadala Road, Wadala, Nashik (5260)'),
            ('Matoshri Education Society, Matoshri Institute of Technology, Dhanore, Nashik (5263)', 'Matoshri Education Society, Matoshri Institute of Technology, Dhanore, Nashik (5263)'),
            ('Maharashtra Shikshan Vikas Mandal\'s Loknete Gopalraoji Gulwe Polytechnic, Vilholi, Nashik (5357)', 'Maharashtra Shikshan Vikas Mandal\'s Loknete Gopalraoji Gulwe Polytechnic, Vilholi, Nashik (5357)'),
            ('Amruta Vaishnavi Education & Welfare Trust\'s Shatabdi Institute of Technology, Agastkhind, Tal. Sinner (5363)', 'Amruta Vaishnavi Education & Welfare Trust\'s Shatabdi Institute of Technology, Agastkhind, Tal. Sinner (5363)'),
            ('Potdar Foundation Taloda, Potdar Polytechnic, Patne, Malegaon, Nashik (5366)', 'Potdar Foundation Taloda, Potdar Polytechnic, Patne, Malegaon, Nashik (5366)'),
            ('Nashik Institute of Technology, Late Annasaheb Patil Polytechnic, Dindori Road, Cannol Road, MERI, Nashik (5369)', 'Nashik Institute of Technology, Late Annasaheb Patil Polytechnic, Dindori Road, Cannol Road, MERI, Nashik (5369)'),
            ('Karmaveer R.S. Wagh Education & Health Institute, Kadwa Polytechnic, Rajaram Nagar, Tal-Dindori, Nashik (5371)', 'Karmaveer R.S. Wagh Education & Health Institute, Kadwa Polytechnic, Rajaram Nagar, Tal-Dindori, Nashik (5371)'),
            ('K.V.N. Naik S. P. Sansth\'s Loknete Gopinathji Munde Institute of Engineering Education & Research, Nashik (5390)', 'K.V.N. Naik S. P. Sansth\'s Loknete Gopinathji Munde Institute of Engineering Education & Research, Nashik (5390)'),
            ('Shree Kapildhara Polytechnic, Igatpuri (5402)', 'Shree Kapildhara Polytechnic, Igatpuri (5402)'),
            ('Gurukul Education Society\'s Institute of Engineering & Technology, Nandgaon (5404)', 'Gurukul Education Society\'s Institute of Engineering & Technology, Nandgaon (5404)'),
            ('Maulana Mukhtar Ahmad Nadvi Technical Campus, Malegaon (5411)', 'Maulana Mukhtar Ahmad Nadvi Technical Campus, Malegaon (5411)'),
            ('Gokhale Education Society\'s Sir Dr. M.S. Gosavi Polytechnic Institute, Nashik Road (5434)', 'Gokhale Education Society\'s Sir Dr. M.S. Gosavi Polytechnic Institute, Nashik Road (5434)'),
        ]
        
        self.fields['department'].choices = [
            ("", "Select Department"),
            ('Computer Engineering', 'Computer Engineering'),
            ('Information Technology', 'Information Technology'),
            ('Mechanical Engineering', 'Mechanical Engineering'),
            ('Civil Engineering', 'Civil Engineering'),
            ('Electrical Engineering', 'Electrical Engineering'),
            ('Electronics and Telecommunication Engineering', 'Electronics and Telecommunication Engineering'),
            ('Mechatronics Engineering', 'Mechatronics Engineering'),
            ('Polymer Engineering', 'Polymer Engineering'),
            ('Computer Technology', 'Computer Technology'),
            ('Interior Designing Engineering', 'Interior Designing Engineering'),
            ('Dress designing and garment manufacturing Eng.', 'Dress designing and garment manufacturing Eng.'),
            ('Artificial Intelligence', 'Artificial Intelligence'),
            ('Automobile Engineering', 'Automobile Engineering'),
            ('Chemical Engineering', 'Chemical Engineering'),
            ('Textile Engineering', 'Textile Engineering'),
            ('Instrumentation Engineering', 'Instrumentation Engineering'),
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