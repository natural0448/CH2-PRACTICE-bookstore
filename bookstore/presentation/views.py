from django.shortcuts import render
from bookstore.service.services import get_bookstore_standard_context
from bookstore.service.services import get_bookstore_Standardizated_data


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
