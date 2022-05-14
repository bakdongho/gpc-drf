from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
def home(request):
    return JsonResponse({'data':'server is alive.'})

def map(request):
    