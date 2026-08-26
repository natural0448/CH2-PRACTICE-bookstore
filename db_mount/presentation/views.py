from django.http import JsonResponse
from django.shortcuts import render

from db_mount.service.services import (
    create_orm_item,
    create_raw_item,
    get_orm_items,
    get_raw_items,
)


def orm_item_form(request):
    context = {"name": ""}

    if request.method == "POST":
        context["name"] = request.POST.get("name", "")
        save_mode = request.POST.get("save_mode", "orm")

        try:
            if save_mode == "raw":
                context["created_item"] = create_raw_item(context["name"])
                context["created_item"]["mode"] = "Raw SQL"
            else:
                context["created_item"] = create_orm_item(context["name"])
                context["created_item"]["mode"] = "ORM"
            context["name"] = ""
        except ValueError as error:
            context["form_error"] = str(error)

    return render(request, "db_mount/orm_item_form.html", context)


def orm_items(request):
    return JsonResponse(
        {"items": get_orm_items()},
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )


def raw_items(request):
    return JsonResponse(
        {"items": get_raw_items()},
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
