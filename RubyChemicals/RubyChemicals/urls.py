from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', include('FrontEnd.urls')),
    path('user-api/', include('UserDetail.urls')),
    path('operation-api/', include('Operations.urls')),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
