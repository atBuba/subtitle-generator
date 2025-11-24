import os
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.db.models import ProtectedError
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.conf import settings
from .models import Project
from .forms import ProjectForm
from .ranged_file_response import ranged_file_response
from .services import audio_separator, whisper_client
from .tasks import process_audio_task

def project_list(request):
    """Страница со списком всех проектов"""
    projects = Project.objects.all()
    return render(request, 'subtitle_generator_app/project_list.html', {'projects': projects})

def project_delete(request, project_id):
    """Удаление проекта"""
    if request.method == 'POST':
        project = get_object_or_404(Project, id=project_id)
        project_name = project.name
        
        try:
            # Удаляем связанные файлы, если они существуют
            if project.audio:
                project.audio.delete(save=False)
            if project.vocal_audio:
                project.vocal_audio.delete(save=False)
            if project.instrumental_audio:
                project.instrumental_audio.delete(save=False)
            if project.subtitle:
                project.subtitle.delete(save=False)
                
            # Удаляем сам проект
            project.delete()
            messages.success(request, f'Проект "{project_name}" успешно удален!')
        except ProtectedError:
            messages.error(request, f'Проект "{project_name}" не может быть удален, так как на него ссылаются другие объекты.')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении проекта: {str(e)}')
    else:
        messages.error(request, 'Некорректный метод запроса для удаления проекта.')
    
    return redirect('project_list')

def project_detail(request, project_id):
    """Страница детального просмотра проекта"""
    project = get_object_or_404(Project, id=project_id)
    return render(request, 'subtitle_generator_app/project_detail.html', {'project': project})

def project_create(request):
    """Страница создания нового проекта"""
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.status = 'draft'
            
            if 'audio_file' in request.FILES:
                audio_file = request.FILES['audio_file']
                if audio_file:
                    # Сохраняем файл
                    file_extension = audio_file.name.split('.')[-1].lower()
                    unique_filename = f"{uuid.uuid4()}.{file_extension}"
                    project.audio.save(unique_filename, audio_file, save=False)
                    project.save()
                    
                    # Запускаем обработку в фоне
                    process_audio_task.delay(project.id)
                    
                    messages.success(
                        request,
                        f'Проект "{project.name}" создан! Обработка началась.'
                    )
                    return redirect('project_detail', project_id=project.id)
            else:
                project.save()
                messages.warning(
                    request,
                    f'Проект создан без аудиофайла.'
                )
                return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    
    return render(request, 'subtitle_generator_app/project_form.html', {'form': form})


@xframe_options_sameorigin
def serve_audio(request, project_id):
    """
    View для отдачи аудиофайлов с поддержкой HTTP Range Requests
    """
    project = get_object_or_404(Project, id=project_id)
    
    if not project.audio:
        raise Http404("Аудиофайл не найден")
    
    file_path = project.get_audio_path()
    if not file_path or not os.path.exists(file_path):
        raise Http404("Файл не найден")
    
    # Определяем content-type на основе расширения файла
    content_type = 'audio/mpeg'  # по умолчанию для .mp3
    if file_path.lower().endswith('.wav'):
        content_type = 'audio/wav'
    elif file_path.lower().endswith('.ogg'):
        content_type = 'audio/ogg'
    elif file_path.lower().endswith('.m4a'):
        content_type = 'audio/mp4'
    
    return ranged_file_response(request, file_path, content_type)
