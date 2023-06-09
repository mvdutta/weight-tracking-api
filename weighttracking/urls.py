from rest_framework import routers
from django.contrib import admin
from django.conf.urls import include
from django.urls import path
from weighttrackingapi.views import register_user, login_user, ResidentView, EmployeeView, WeightSheetView, WeightView, MessageView, EmployeeMessageView

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'residents', ResidentView, 'resident')
router.register(r'employees', EmployeeView, 'employee')
router.register(r'weightsheets', WeightSheetView, 'weightsheet')
router.register(r'weights', WeightView, 'weight')
router.register(r'messages', MessageView, 'message')
router.register(r'employeemessages', EmployeeMessageView, 'employeemessage')

urlpatterns = [
    # Requests to http://localhost:8000/register will be routed to the register_user function
    path('register', register_user),
    # Requests to http://localhost:8000/login will be routed to the login_user function
    path('login', login_user),
    path('', include(router.urls)),
    path('admin/', admin.site.urls),
]
