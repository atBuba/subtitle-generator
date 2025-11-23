from django import forms
from .models import Project

class ProjectForm(forms.ModelForm):
    audio_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;',
            'accept': 'audio/*'
        })
    )
    
    class Meta:
        model = Project
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Введите название проекта'
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name.strip()) < 3:
            raise forms.ValidationError('Название проекта должно содержать минимум 3 символа')
        return name.strip()