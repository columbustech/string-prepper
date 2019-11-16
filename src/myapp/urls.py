from django.urls import path
from myapp.views import *

urlpatterns = [
    path('', upload, name='upload'),
    path('show_doc/', show_doc, name='show_doc'),
    path('choices/', choices, name='choices'),
    path('download/', download, name='download'),
    path('sample/', sample, name='sample'),
    path('upload_cdrive/', upload_cdrive, name='upload_cdrive'),
    path('exit_app/', exit_app, name='exit_app'),
    path('clean/', clean_strings, name='clean_strings'),
]
