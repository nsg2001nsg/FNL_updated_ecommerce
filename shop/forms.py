from django import forms
from django.contrib.auth import authenticate
from .models import Address, Customer

class AddressForm(forms.ModelForm):
    address1 = forms.CharField(max_length=150, required=True)
    address2 = forms.CharField(max_length=150, required=False)
    default_address = forms.BooleanField(required=False)
    
    # Template uses these names instead of the model's exact field names
    number = forms.IntegerField(required=True)
    pin = forms.IntegerField(required=True)
    state = forms.CharField(max_length=30, required=True)

    class Meta:
        model = Address
        fields = ['name', 'city']

    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        if pin and not (100000 <= pin <= 999999):
            raise forms.ValidationError("Invalid Pincode. Must be 6 digits.")
        return pin

    def clean_number(self):
        number = self.cleaned_data.get('number')
        if number and not (6000000000 <= number <= 9999999999):
            raise forms.ValidationError("Invalid Contact Number. Must be 10 digits.")
        return number

    def save(self, commit=True):
        # We use commit=False because we need to manually assign the cleaned fields
        # that have different names in the template vs the model.
        # We also need the view to attach the customer (FK) before saving.
        instance = super().save(commit=False)
        instance.contact = self.cleaned_data['number']
        instance.pincode = self.cleaned_data['pin']
        instance.State = self.cleaned_data['state']
        
        addr1 = self.cleaned_data.get('address1', '')
        addr2 = self.cleaned_data.get('address2', '')
        instance.ship_to = f"{addr1} {addr2}".strip()
        
        if commit:
            instance.save()
        return instance

class SignupForm(forms.Form):
    email = forms.EmailField(max_length=40, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    cpassword = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Customer.objects.filter(email=email).exists():
            raise forms.ValidationError("Username already exists!")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        cpassword = cleaned_data.get('cpassword')

        if password and cpassword and password != cpassword:
            self.add_error('cpassword', "Password doesn't match!")
        
        return cleaned_data

class SigninForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            if not Customer.objects.filter(email=email).exists():
                 self.add_error('email', "User Does not exist!")
            else:
                 user = authenticate(email=email, password=password)
                 if user is None:
                     self.add_error('password', "Bad Credentials!")
                 else:
                     self.user_cache = user
        return cleaned_data
    
    def get_user(self):
        return getattr(self, 'user_cache', None)
