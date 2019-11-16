# String Profiler and Cleaner

## Description
This repository contains the source files for Django application to developed
to perform profiling and cleaning of a list of strings.

## Setup
```
> git clone https://github.com/danish778866/ProCleaner.git
> cd ProCleaner
> virtualenv myenv
> # Add APP_SECRET to myenv/bin/activate in order to interact with CDrive.
> source myenv/bin/activate
> pip install -r requirements.txt
> cd mysite
> python manage.py makemigrations myapp
> python manage.py migrate
> python manage.py runserver # Access via http://0.0.0.0:8000/myapp/list/
```

## Organization
The organization of this repository is as follows:
* `mysite/utils/`: The module containing utility code used by the application.
* `mysite/myapp`: The application.
