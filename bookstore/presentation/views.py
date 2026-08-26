from django.shortcuts import render
from bookstore.service.services import get_bookstore_standard_context
from bookstore.service.services import get_bookstore_Standardizated_data
from bookstore.service.services import get_bookstore_Standard_enterty
from bookstore.service.services import get_day5_orm_dashboard
from bookstore.service.services import get_day5_raw_dashboard
from bookstore.service.services import get_day6_feature_dashboard_context
from bookstore.service.services import get_day7_quality_dashboard_context
from bookstore.service.services import get_day7_inquality_dashboard_context
from bookstore.service.services import get_day8_release_dashboard_context

def day2_dashboard(request):
    #bookstore 내부 데이터 표준화 사전 생성 완료 여부를 확인해 화면으로 노출하는 함수입니다.
    #services.py의 get_bookstore_data_standard_context() 함수를 호출하여, context를 리턴받습니다.
    context = get_bookstore_standard_context()
    return render(request, "day2_dashboard.html", context)
    
def day3_dashboard(request):
    #bookstore 내부 데이터 표준화 완료 여부를 확인해 보여주는 함수입니다.
    #services.py의 get_bookstore_Standardizated_data() 함수를 호출하여, 데이터 표준화 완료 여부를 확인하고, 그 결과를 day3_dashboard.html 템플릿에 전달합니다.
    validate_result = get_bookstore_Standardizated_data()
    return render(request, "day3_dashboard.html", validate_result)


def day4_dashboard(request):
    #bookstore 내부 데이터 표준화 완료 여부를 확인해 보여주는 함수입니다.
    #services.py의 get_bookstore_Standardard_enterty() 함수를 호출하여, enterty 결정사항을 확인하고, 그 결과를 day4_dashboard.html 템플릿에 전달합니다.
    enterty_decision = get_bookstore_Standard_enterty()
    return render(request, "day4_dashboard.html", enterty_decision)


def day5_orm_dashboard(request):
    return render(
        request,
        "day5_dashboard.html",
        get_day5_orm_dashboard(),
    )


def day5_raw_dashboard(request):
    return render(
        request,
        "day5_dashboard.html",
        get_day5_raw_dashboard(),
    )

def day6_dashboard(request):
    as_of_date = request.GET.get("as_of_date", "2026-08-12")
    context = get_day6_feature_dashboard_context(as_of_date)
    return render(
        request,
        "day6_dashboard.html",
        context,
    )

def day7_dashboard(request):
    context = get_day7_quality_dashboard_context()
    return render(
        request,
        "day7_dashboard.html",
        context,
    )

def day7_data_check_dashboard(request):
    uploaded_file = None
    if request.method == "POST":
        uploaded_file = (
            request.FILES.get("data_file")
            or request.FILES.get("csv_file")
        )
    context = get_day7_inquality_dashboard_context(uploaded_file)
    if request.method == "POST" and uploaded_file is None:
        context["upload_error"] = "데이터 파일을 선택해 주세요."
    return render(
        request,
        "day7_data_check_dashboard.html",
        context,
    )


def day8_dashboard(request):
    context = get_day8_release_dashboard_context()
    return render(request,"day8_dashboard.html",context,)