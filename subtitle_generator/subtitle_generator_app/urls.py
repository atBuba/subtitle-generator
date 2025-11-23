from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    # Web views
    path('', views.project_list, name='project_list'),
    path('project/create/', views.project_create, name='project_create'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('project/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    path('project/<int:project_id>/audio/', views.serve_audio, name='serve_audio'),
    
    # API endpoints
    path('api/generate-subtitles/', api_views.generate_subtitles, name='generate_subtitles'),
    path('api/project/<int:project_id>/status/', api_views.get_project_status, name='project_status'),
    path('api/project/<int:project_id>/generate-subtitles/', api_views.generate_subtitles_for_project, name='generate_subtitles_for_project'),
    path('api/project/<int:project_id>/subtitle-content/', api_views.get_subtitle_content, name='subtitle_content'),
    path('api/project/<int:project_id>/update-subtitle/', api_views.update_subtitle_content, name='update_subtitle_content'),
    path('api/projects/', api_views.list_projects, name='list_projects'),
    path('api/project/<int:project_id>/download-subtitle/', api_views.download_subtitle, name='download_subtitle'),
]