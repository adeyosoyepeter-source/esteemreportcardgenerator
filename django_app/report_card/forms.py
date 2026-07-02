from django import forms


class BroadsheetUploadForm(forms.Form):
    """Form for uploading Excel broadsheet and report metadata."""
    TERM_CHOICES = [
        ('First Term', 'First Term'),
        ('Second Term', 'Second Term'),
        ('Third Term', 'Third Term'),
    ]

    term = forms.ChoiceField(
        label='Term',
        choices=TERM_CHOICES,
        initial='First Term',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    year = forms.CharField(
        label='Academic Year',
        max_length=9,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 2025/2026'
        })
    )
    file = forms.FileField(
        label='Excel Broadsheet',
        help_text='Upload an .xlsx file',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx',
            'class': 'form-control'
        })
    )
