from django import forms

PROFILER_CHOICES = (('1', 'Find Similarity'), ('2', 'Profile'), ('3', 'Find Errors'))

class DocumentForm(forms.Form):
    docfile = forms.FileField(
        label = 'Select a File',
        help_text = 'max. 42 megabytes',
        required = False
    )

class ProfilerChoiceForm(forms.Form):
    profiler_choice_label = forms.ChoiceField(widget=forms.RadioSelect, choices=PROFILER_CHOICES)
