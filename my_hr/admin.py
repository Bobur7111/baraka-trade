from django.contrib import admin
from .models import Employee, Attendance

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'role', 'is_active')
    readonly_fields = ()

admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Attendance)