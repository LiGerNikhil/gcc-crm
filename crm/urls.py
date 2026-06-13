"""
URL configuration for crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('leads/', include('leads.urls')),
    path('imports/', include('excel.urls')),
    path('pdf/', include('pdf.urls')),
    path('images/', include('imager.urls')),
    path('documents/', include('documents.urls')),
    path('org/', include(('accounts.org_urls', 'org'))),
    path('analytics/', include('analytics.urls')),
    path('audit/', include('audit.urls')),
    path('api/', include('accounts.api_urls')),
    path('api/', include('leads.api_urls')),
    path('api/', include('excel.api_urls')),
    path('api/', include('pdf.api_urls')),
    path('api/', include('imager.api_urls')),
    path('api/', include('analytics.api_urls')),
    path('api/', include('audit.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

