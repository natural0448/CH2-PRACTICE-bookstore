from django.http import JsonResponse

from db_mount.service.services import get_orm_items, get_raw_items


def orm_items(request):
    return JsonResponse({"items": get_orm_items()})


def raw_items(request):
    return JsonResponse({"items": get_raw_items()})
