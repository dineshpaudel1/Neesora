from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
        error_messages={'required': 'Please select a star rating.'},
    )

    class Meta:
        model = Review
        fields = ['rating', 'title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Summarise your experience (optional)',
                'class': 'review-input',
            }),
            'body': forms.Textarea(attrs={
                'placeholder': 'Share your thoughts about this product...',
                'class': 'review-input review-textarea',
                'rows': 4,
            }),
        }
        labels = {
            'title': 'Review title',
            'body': 'Your review',
        }
