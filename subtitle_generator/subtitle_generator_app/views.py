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
            # Устанавливаем статус Draft по умолчанию
            project.status = 'processing'  # Меняем на processing, так как начнем обработку
            
            # Обработка загруженного аудио файла
            if 'audio_file' in request.FILES:
                audio_file = request.FILES['audio_file']
                if audio_file:
                    # Генерируем уникальное имя файла
                    file_extension = audio_file.name.split('.')[-1].lower()
                    unique_filename = f"{uuid.uuid4()}_{audio_file.name.replace('.', '_')}.{file_extension}"
                    
                    # Сохраняем аудио файл
                    project.audio.save(unique_filename, audio_file, save=False)
                    
                    # Сохраняем проект для получения ID
                    project.save()
                    
                    try:
                        # Шаг 1: Разделяем аудио на вокал и инструментал
                        audio_path = project.get_audio_path()
                        vocal_path, instrumental_path = audio_separator.separate_audio(project.id, audio_path)
                        
                        # Шаг 2: Сохраняем пути к разделенным файлам
                        project.vocal_audio.name = vocal_path
                        project.instrumental_audio.name = instrumental_path
                        project.save()
                        
                        # Шаг 3: Транскрибируем вокальную дорожку
                        vocal_full_path = os.path.join(settings.MEDIA_ROOT, vocal_path)
                        print(vocal_full_path)
                        srt_content = whisper_client.transcribe_audio_vocal(vocal_full_path)
                        
                        # Шаг 4: Сохраняем субтитры
                        srt_filename = f"{uuid.uuid4()}_{project.name}_subtitles.srt"
                        srt_path = os.path.join('subtitle/srt', srt_filename)
                        full_srt_path = os.path.join(settings.MEDIA_ROOT, srt_path)
                        
                        with open(full_srt_path, 'w', encoding='utf-8') as f:
                            f.write(srt_content)
                        
                        project.subtitle.name = srt_path
                        project.status = 'completed'
                        project.save()
                        
                        messages.success(request, f'Проект "{project.name}" успешно создан и обработан!')
                        
                    except Exception as e:
                        project.status = 'failed'
                        project.save()
                        messages.error(request, f'Ошибка при обработке аудио: {str(e)}')
                        return redirect('project_detail', project_id=project.id)
                    
                    return redirect('project_detail', project_id=project.id)
            else:
                project.save()
                messages.success(request, f'Проект "{project.name}" успешно создан!')
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
