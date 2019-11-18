# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
import os, sys, json
import requests
import pdb
from myapp.models import Document
from myapp.forms import DocumentForm
from utils.utils import *

REDIRECT_URI = os.environ["CDRIVE_URL"] + "app/" + os.environ["COLUMBUS_USERNAME"] + "/string-prepper/"
APP_ID = os.environ["COLUMBUS_CLIENT_ID"]
APP_SECRET = os.environ["COLUMBUS_CLIENT_SECRET"]
TOKEN_URL = os.environ["AUTHENTICATION_URL"] + "o/token/"
AUTH_URL = os.environ["AUTHENTICATION_URL"] + "o/authorize/" + "?response_type=code" + "&client_id=" + os.environ["COLUMBUS_CLIENT_ID"] + "&redirect_uri=" + REDIRECT_URI + "&state=1234xyz"
CDRIVE_URL = os.environ["CDRIVE_API_URL"]
CDRIVE_UI_URL = os.environ["CDRIVE_URL"]
CLIENT_TOKEN_KEY = "procleaner_token"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CDRIVE_FILES_DIR = os.path.join(PROJECT_DIR, "cdrive_files")
CLEAN_FILES = os.path.join(os.path.join(os.path.join(os.path.join(PROJECT_DIR, "myapp"), "static"), "pdf"), "clean")
CLEAN_FILES_LOCAL = os.path.join(os.path.join(os.path.join(os.path.join(PROJECT_DIR, "myapp"), "static"), "pdf"), "clean_local")
CLEAN_FILES_CDRIVE = os.path.join(os.path.join(os.path.join(os.path.join(PROJECT_DIR, "myapp"), "static"), "pdf"), "clean_cdrive")
CLEAN_FILES_SUFFIX = ".clean"

def upload(request):
    """
    View for rendering upload page of the application.
    This view performs the following operations:
        1. Create a form consisting of an input field for a user to upload a file.
        2. Get the OAuth token for the user from authentication (if it doesn't
           exist).
        3. Get the list of files in current users' CDrive.
        4. Render the form and CDrive files.
    Arguments:
        request: The request object.
    Returns an HttpResponse object.
    """
    form = DocumentForm()
    if CLIENT_TOKEN_KEY not in request.session:
        if 'code' in request.GET:
            code = request.GET.get('code')
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
            }
            response = requests.post(
                url=TOKEN_URL,
                data=data
            )
            request.session[CLIENT_TOKEN_KEY] = response.json()['access_token']
            request.session.set_expiry(response.json()['expires_in'])
        else:
            return HttpResponseRedirect(AUTH_URL)
    return render(
        request,
        'upload.html',
        {'form': form, 'c_drive_ui_url': CDRIVE_UI_URL}
    )

def sample(request):
    """
    View for rendering the sample tuples of the uploaded file.
    This view does the following:
        1. Read the upload type.
        2. Save the uploaded file locally.
        3. Set session parameters to reference the file subsequently.
        4. Read and return a sample of tuples.
    Arguments:
        request: The request object.
    Returns an HttpResponse object.
    """
    upload_type = ""
    cdrive_file_path = request.POST.get('cdriveFile')
    if cdrive_file_path is not None:
        upload_type = "CDrive"
    elif 'docfile' in request.FILES:
        upload_type = "Local"
    if upload_type == "CDrive":
        token = request.session[CLIENT_TOKEN_KEY]
        get_url = CDRIVE_URL + "content/?path=" + str(cdrive_file_path)
        header = {"Authorization": "Bearer " + token}
        read_response = requests.get(url=get_url, headers=header)
        tuples = read_response.json().split("\n")
        uploaded_df = pd.DataFrame(tuples)
        uploaded_df.columns = ['foo']
        uploaded_df['id'] = range(0, len(uploaded_df))
        column_order = ['id', 'foo']
        if not os.path.exists(CDRIVE_FILES_DIR):
            os.makedirs(CDRIVE_FILES_DIR)
        index = cdrive_file_path.rfind("/")
        cdrive_file = cdrive_file_path[index+1:]
        parent_path = cdrive_file_path[0:index]
        uploaded_df[column_order].to_csv(os.path.join(CDRIVE_FILES_DIR, cdrive_file), index=False)
        sample_tuples = tuples[1:10]
        request.session['uploaded_file'] = cdrive_file
        request.session['cdrive_path'] = parent_path
        request.session['file_type'] = "CDrive"
    elif upload_type == "Local":
        uploaded_doc = Document(docfile=request.FILES['docfile'])
        uploaded_doc.save()
        uploaded_doc_path = os.path.join(PROJECT_DIR, uploaded_doc.docfile.url[1:])
        uploaded_df = pd.read_csv(uploaded_doc_path, names=['foo'])
        uploaded_df['id'] = range(0, len(uploaded_df))
        column_order = ['id', 'foo']
        whitespace_striper = lambda x: str(x).strip()
        uploaded_df['foo'] = uploaded_df['foo'].apply(whitespace_striper)
        uploaded_df[column_order].to_csv(uploaded_doc_path, index=False)
        request.session['uploaded_file'] = uploaded_doc.docfile.url
        request.session['uploaded_file_name'] = uploaded_doc.docfile.name
        request.session['file_type'] = "Local"
        sample_tuples = uploaded_df['foo'].head(10).tolist()
    return render(request, 'sample.html', {'sample_tuples': sample_tuples})

def choices(request):
    """
    View for rendering the choices for profiling and cleaning.
    Arguments:
        request: The request object.
    Returns an HttpResponse object.
    """
    profiler_options = [["1", "Clean Strings"], ["2", "Profile Strings"], ["3", "Debug Strings"]]
    return render(request, 'choices.html', {'profiler_options': profiler_options})

@csrf_exempt
def upload_cdrive(request):
    """
    View for uploading the clean file to CDrive.
    This view does the following:
        1. Retrives the path of clean file on local.
        2. Uploads the file to CDrive using it's API.
    Arguments:
        request: The request object.
    Returns an HttpResponse object.
    """
    uploaded_file = request.session.get('uploaded_file')
    parent_path = request.session.get('cdrive_path')
    clean_file_name = os.path.basename(uploaded_file) + CLEAN_FILES_SUFFIX
    clean_file_path = os.path.join(CLEAN_FILES, clean_file_name)
    files = {'file': (clean_file_name, open(clean_file_path, 'rb')), 'path': (None, parent_path)}
    post_url = CDRIVE_URL + "upload/"
    token = request.session[CLIENT_TOKEN_KEY]
    header = {"Authorization": "Bearer " + token}
    try:
        upload_response = requests.post(post_url, files=files, headers=header)
        django_response = HttpResponse(
            content=upload_response.content,
            status=upload_response.status_code,
            content_type=upload_response.headers['Content-Type']
        )
    except:
        django_response = HttpResponseBadRequest
    return django_response

@csrf_exempt
def exit_app(request):
    """
    View for performing a clean exit when the user wants to go back to CDrive.
    This view does the following:
        1. Delete any session data stored (Token, etc).
        2. Delete uploaded and cleaned files, if they exist. 
        3. Delete model object, if it exists.
    Arguments:
        request: The request object.
    Returns an empty HttpResponse object.
    """
    if "uploaded_file" in request.session:
        uploaded_file = request.session.get('uploaded_file')
        del request.session["uploaded_file"]   
    if "file_type" in request.session:
        if request.session["file_type"] == "CDrive":
            uploaded_file_path = os.path.join(CDRIVE_FILES_DIR, uploaded_file)
        else:
            uploaded_file_path = os.path.join(PROJECT_DIR, uploaded_file[1:])
            uploaded_file_name = request.session.get('uploaded_file_name')
            Document.objects.filter(docfile=uploaded_file_name).delete()
        if os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)
        clean_file_name = os.path.basename(uploaded_file) + CLEAN_FILES_SUFFIX
        clean_file_path = os.path.join(CLEAN_FILES, clean_file_name)
        if os.path.exists(clean_file_path):
            os.remove(clean_file_path)
    if CLIENT_TOKEN_KEY in request.session:
        del request.session[CLIENT_TOKEN_KEY]
    if "file_type" in request.session:
        del request.session["file_type"]
    if "uploaded_file_name" in request.session:
        del request.session["uploaded_file_name"]
    if "cdrive_path" in request.session:
        del request.session["cdrive_path"]
    return HttpResponse('')

def download(request):
    """
    View for rendering the download page of the application.
    Arguments:
        request: The request object.
    Returns an HttpResponse object.
    """
    uploaded_file = request.session.get('uploaded_file')
    if request.session["file_type"] == "CDrive":
        uploaded_file_path = os.path.join(CDRIVE_FILES_DIR, uploaded_file)
    else:
        uploaded_file_path = os.path.join(PROJECT_DIR, uploaded_file[1:])
    clean_file_name = os.path.basename(uploaded_file) + CLEAN_FILES_SUFFIX
    clean_file_path = os.path.join(CLEAN_FILES, clean_file_name)
    if not os.path.exists(CLEAN_FILES):
        os.makedirs(CLEAN_FILES)
    uploaded_df = pd.read_csv(uploaded_file_path)
    uploaded_df.to_csv(clean_file_path, index=False)
    return render(request,
                  'download.html',
                      {
                          'clean_file_name': clean_file_name,
                          'clean_file_path': clean_file_path,
                          'c_drive_ui_url': CDRIVE_UI_URL
                      }
                 )

def clean_strings(request):
    """
    View for performing value normalization part of the application.
    This view does the following:
        1. Retrives the file name from the session.
        2. Retrives values to be merged from the request (if they exist) and uses 
           them to normalize strings.
        3. Retrives similar strings to display in the next iteration.
    Arguments:
        request: The request object.
    Returns an HttpResponse object.
    """
    uploaded_file = request.session.get('uploaded_file')
    if request.session["file_type"] == "CDrive":
        uploaded_file_path = os.path.join(CDRIVE_FILES_DIR, uploaded_file)
    else:
        uploaded_file_path = os.path.join(PROJECT_DIR, uploaded_file[1:])
    if request.method == 'POST':
        if "merge" in request.POST:
            values = ','.join(request.POST.getlist('merge'))
            normalize_strings(uploaded_file_path, values)
        similar_strings = get_similar_strings(uploaded_file_path)
        similar_strings_1 = []
        similar_strings_2 = []
        similar_strings_3 = []
        num_strings = len(similar_strings)
        show_normalizer = True
        if num_strings == 0:
            show_normalizer = False
        num_each = len(similar_strings) // 3
        similar_strings_1 = similar_strings[0:num_each]
        similar_strings_2 = similar_strings[num_each:2 * num_each]
        similar_strings_3 = similar_strings[2 * num_each:]
        return render(request, 'clean_strings.html', 
                      {'file_path': uploaded_file,
                       'similar_strings_1': similar_strings_1,
                       'similar_strings_2': similar_strings_2,
                       'similar_strings_3': similar_strings_3,
                       'show_normalizer': show_normalizer
                      })

def show_doc(request):
    uploaded_file = request.session.get('uploaded_file')
    if request.session["file_type"] == "CDrive":
        uploaded_file_path = os.path.join(CDRIVE_FILES_DIR, uploaded_file)
    else:
        uploaded_file_path = os.path.join(PROJECT_DIR, uploaded_file[1:])
    if request.method == 'POST':
        profiler_choice = request.POST['profiler_choice']
        if profiler_choice != "1":
            column_name = 'foo'
            table_A_path = uploaded_file_path
            A = pd.read_csv(table_A_path) #headers will be inferred automatically
            total_n_values = len(A)

            # find missing values so as to calculate further errors on only non-missing entries
            n_missing, pervasiveness_missing, type_missing_values_caught, col_missing = contains_missing_values_global_syn(A, column_name)
            
            # A only with non-missing values
            A_without_missing_values = A[~A[col_missing]]
            
            total_non_missing_values = len(A_without_missing_values)
            

            if profiler_choice == "2":

                # redirect to show_stats page with modified arguments than the normal case, if no non-missing values in file.
                if total_non_missing_values == 0:
                    message = "No non-missing strings to find statistics on."
                    return render(request, 'show_stats.html', {
                        'total_values': total_n_values,
                    'n_non_missing': total_non_missing_values,
                    'message': message,
                    'n_values': total_non_missing_values,
                    'n_missing': n_missing,
                    'pervasiveness_missing': pervasiveness_missing,
                    'type_missing_values_caught': type_missing_values_caught,
                    'lengths': 0,
                    'lengths_words': 0,
                    'c_drive_ui_url': CDRIVE_UI_URL
                    })

                # calculate stats for strings lengths
                stats, lengths = stats_length_strings(A_without_missing_values, column_name)
                # calculate stats for no. of words in strings
                stats_words, lengths_words, num_capitals = stats_words_in_strings(A_without_missing_values, column_name)

                # json_data = json.dumps({"lengths": lengths})
                return render(request, 'show_stats.html', 
                    {'total_values': total_n_values,
                    'n_non_missing': total_non_missing_values,
                    'n_values': total_non_missing_values,
                    'n_missing': n_missing,
                    'pervasiveness_missing': pervasiveness_missing,
                    'type_missing_values_caught': type_missing_values_caught,
                    'stats': stats, 
                    'lengths': lengths,
                    'stats_words': stats_words,
                    'lengths_words': lengths_words,
                    'num_capitals': num_capitals,
                    'c_drive_ui_url': CDRIVE_UI_URL
                    })
            else:

                # redirect to show_errors page with modified arguments than the normal case, if no non-missing values in file.
                if total_non_missing_values == 0:
                    message = "No non-missing strings to find errors on."
                    return render(request, 'show_errors.html', {
                        'total_values': total_n_values,
                    'n_non_missing': total_non_missing_values,
                    'message': message,
                    'n_values': total_non_missing_values,
                    'n_missing': n_missing,
                    'pervasiveness_missing': pervasiveness_missing,
                    'type_missing_values_caught': type_missing_values_caught,
                    'c_drive_ui_url': CDRIVE_UI_URL
                    })
                # find uniqueness
                n_uniques, pervasiveness_uniques, duplicates = fraction_uniques(A_without_missing_values, column_name)

                # type recognition in non-missing values of column given by column_name
                type_pervasiveness_dict = type_recognition(A_without_missing_values, column_name)

                # return the different errors to the corresponding html
                return render(request, 'show_errors.html', {
                    'total_values': total_n_values,
                    'n_non_missing': total_non_missing_values,
                    'n_values': total_non_missing_values,
                    'n_uniques': n_uniques,
                    'pervasiveness_uniques': pervasiveness_uniques, 
                    'duplicates': duplicates,
                    'n_missing': n_missing,
                    'pervasiveness_missing': pervasiveness_missing,
                    'type_missing_values_caught': type_missing_values_caught,
                    'type_pervasiveness_dict': type_pervasiveness_dict,
                    'c_drive_ui_url': CDRIVE_UI_URL
                    })

