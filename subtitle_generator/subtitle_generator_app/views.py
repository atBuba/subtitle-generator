import os
import uuid
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.db.models import ProtectedError
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.conf import settings
from django.core.files.base import ContentFile
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
    """
    Страница детального просмотра проекта
    Автоматически создает проект, если он не существует
    """
    try:
        # Пытаемся найти существующий проект
        project = Project.objects.get(id=project_id)
        
    except Project.DoesNotExist:
        # Проект не найден - создаем новый
        
        # Получаем параметры из URL
        project_name = request.GET.get('project_name')
        audio_url = request.GET.get('audio_url')
        
        # Проверяем обязательные параметры
        if not project_name or not audio_url:
            messages.error(request, 'Параметры project_name и audio_url обязательны для создания проекта')
            return redirect('project_list')
        
        try:
            # Шаг 1: Создаем проект с конкретным ID
            project = Project.objects.create(
                id=project_id,
                name=project_name,
                status='draft'
            )
            
            # Шаг 2: Скачиваем аудио по URL
            response = requests.get(audio_url, timeout=60)
            response.raise_for_status()  # Проверка на ошибки HTTP
            
            # Определяем расширение файла из URL или Content-Type
            content_type = response.headers.get('content-type', '').lower()
            extension = 'mp3'  # по умолчанию
            
            if 'audio/wav' in content_type or audio_url.lower().endswith('.wav'):
                extension = 'wav'
            elif 'audio/ogg' in content_type or audio_url.lower().endswith('.ogg'):
                extension = 'ogg'
            elif 'audio/mp4' in content_type or 'audio/m4a' in content_type or audio_url.lower().endswith('.m4a'):
                extension = 'm4a'
            elif 'audio/flac' in content_type or audio_url.lower().endswith('.flac'):
                extension = 'flac'
            
            # Шаг 3: Сохраняем аудио файл в проект
            audio_content = ContentFile(response.content)
            # Генерируем чистое имя файла без uuid
            clean_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_name = clean_name.replace(' ', '_')
            audio_filename = f"{clean_name}.{extension}"
            project.audio.save(audio_filename, audio_content, save=False)
            project.save()
            
            # Шаг 4: Запускаем автоматическую обработку в фоне
            process_audio_task.delay(project.id)
            
            messages.success(
                request,
                f'Проект "{project_name}" создан! Обработка аудио началась автоматически.'
            )
            
        except requests.RequestException as e:
            # Ошибка при скачивании аудио
            messages.error(request, f'Ошибка загрузки аудио: {str(e)}')
            # Удаляем созданный проект
            if project and project.id:
                project.delete()
            return redirect('project_list')
            
        except Exception as e:
            # Любая другая ошибка
            messages.error(request, f'Ошибка создания проекта: {str(e)}')
            if project and project.id:
                project.delete()
            return redirect('project_list')
    
    # Отображаем страницу проекта
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
                    clean_filename = "".join(c for c in project.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    clean_filename = clean_filename.replace(' ', '_')
                    audio_filename = f"{clean_filename}.{file_extension}"
                    project.audio.save(audio_filename, audio_file, save=False)
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
