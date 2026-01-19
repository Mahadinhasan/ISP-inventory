from django.contrib import admin
from .models import Material, Task, MaterialRequest,UserProfile,Material,Vendor,SystemSetting,NotificationSetting
# Register your models here.
admin.site.register(Material)
admin.site.register(Task)
admin.site.register(MaterialRequest)
admin.site.register(UserProfile)
admin.site.register(Vendor)
admin.site.register(SystemSetting)
admin.site.register(NotificationSetting)
