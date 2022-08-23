from django.shortcuts import render

# This is rendering the dummy index file for react
def index(request, *args, **kwargs):
    return render(request, 'frontend/index.html')
