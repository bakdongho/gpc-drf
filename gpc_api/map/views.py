from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view

from gpc_api.map.tests import scrapper
from .serializers import StoreSerializer
from .naver_scrapper import NaverScrapper

# Create your views here.
def check_health(request):
    return JsonResponse({"data": "server is alive."})


@api_view(["GET"])
def search_store(request):
    try:
        lat = request.GET["lat"]
        lng = request.GET["lng"]
        category = request.GET.get("category", None)
    except KeyError:
        return Response(data={"msg": "잘못된 요청입니다."}, status=400)
    scrapper =NaverScrapper()
    store_list = scrapper.run(lat, lng, category)
    serializer = StoreSerializer(store_list, many=True)
    return Response(serializer.data)
