import os
import uuid
import re
import json
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.base import ContentFile
from django.conf import settings
from django.db import transaction
from .models import Project
from .services.whisper_client import transcribe_audio

def generate_unique_filename(original_filename, extension):
    """Генерирует уникальное имя файла"""
    unique_id = str(uuid.uuid4())[:8]
    return f"{unique_id}_{original_filename.replace('.', '_')}.{extension}"

def validate_srt_format(content):
    """
    Базовая валидация формата SRT
    """
    lines = content.strip().split('\n')
    
    # Проверяем, что есть хотя бы один блок субтитров
    i = 0
    block_count = 0
    
    while i < len(lines):
        # Пропускаем пустые строки
        if not lines[i].strip():
            i += 1
            continue
        
        # Номер субтитра (должен быть числом)
        try:
            int(lines[i].strip())
        except ValueError:
            return False
        
        i += 1
        if i >= len(lines):
            return False
        
        # Временные метки (формат: 00:00:00,000 --> 00:00:05,000)
        time_line = lines[i].strip()
        if ' --> ' not in time_line:
            return False
        
        parts = time_line.split(' --> ')
        if len(parts) != 2:
            return False
        
        # Простая проверка формата времени
        for part in parts:
            if not re.match(r'^\d{2}:\d{2}:\d{2},\d{3}$', part.strip()):
                return False
        
        i += 1
        
        # Текст субтитра (может быть несколько строк)
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        
        if not text_lines:  # Должен быть хотя бы один символ текста
            return False
        
        block_count += 1
        
        # Пропускаем пустую строку между блоками
        if i < len(lines) and not lines[i].strip():
            i += 1
    
    return block_count > 0

@csrf_exempt
@require_http_methods(["POST"])
def generate_subtitles(request):
    """
    API endpoint для генерации субтитров из аудио файла
    Принимает: multipart/form-data с полем 'audio_file' и 'project_name'
    Возвращает: JSON с информацией о созданном проекте
    """
    try:
        # Получаем данные из запроса
        audio_file = request.FILES.get('audio_file')
        project_name = request.POST.get('project_name', 'Untitled Project')
        
        if not audio_file:
            return JsonResponse({
                'success': False,
                'error': 'Audio file is required'
            }, status=400)
        
        # Валидация типа файла
        allowed_extensions = ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'wma']
        file_extension = audio_file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            return JsonResponse({
                'success': False,
                'error': f'Unsupported file type: {file_extension}. Allowed types: {", ".join(allowed_extensions)}'
            }, status=400)
        
        # Создаем проект в транзакции
        with transaction.atomic():
            # Создаем новый проект
            project = Project.objects.create(
                name=project_name,
                status='processing'
            )
            
            # Генерируем уникальные имена файлов
            audio_filename = generate_unique_filename(audio_file.name, file_extension)
            subtitle_filename = generate_unique_filename(project_name.replace(' ', '_'), 'srt')
            
            # Сохраняем аудио файл
            project.audio.save(audio_filename, audio_file, save=False)
            
            # Генерируем субтитры
            audio_path = project.get_audio_path()
            
            try:
                # Используем функцию транскрибации
                srt_content = transcribe_audio(audio_path)
                
                # Сохраняем субтитры в файл
                subtitle_content = ContentFile(srt_content.encode('utf-8'))
                project.subtitle.save(subtitle_filename, subtitle_content, save=False)
                
                # Обновляем статус проекта
                project.status = 'completed'
                project.save()
                
                # Возвращаем успешный ответ
                return JsonResponse({
                    'success': True,
                    'project_id': project.id,
                    'project_name': project.name,
                    'status': project.status,
                    'audio_url': project.get_audio_url(),
                    'subtitle_url': project.get_subtitle_url(),
                    'created_at': project.created_at.isoformat(),
                    'message': 'Субтитры успешно сгенерированы!'
                }, status=201)
                
            except Exception as e:
                # В случае ошибки при генерации субтитров
                project.status = 'failed'
                project.save()
                
                return JsonResponse({
                    'success': False,
                    'error': f'Error generating subtitles: {str(e)}',
                    'project_id': project.id
                }, status=500)
                
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_project_status(request, project_id):
    """
    API endpoint для получения статуса проекта
    """
    try:
        project = Project.objects.get(id=project_id)
        
        response_data = {
            'project_id': project.id,
            'project_name': project.name,
            'status': project.status,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
        }
        
        if project.audio:
            response_data['audio_url'] = project.get_audio_url()
        if project.subtitle:
            response_data['subtitle_url'] = project.get_subtitle_url()
        
        return JsonResponse({
            'success': True,
            'project': response_data
        })
        
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Project not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving project: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def list_projects(request):
    """
    API endpoint для получения списка всех проектов
    """
    try:
        projects = Project.objects.all().order_by('-created_at')
        
        projects_data = []
        for project in projects:
            project_data = {
                'project_id': project.id,
                'project_name': project.name,
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat(),
            }
            
            if project.audio:
                project_data['audio_url'] = project.get_audio_url()
            if project.subtitle:
                project_data['subtitle_url'] = project.get_subtitle_url()
                
            projects_data.append(project_data)
        
        return JsonResponse({
            'success': True,
            'projects': projects_data,
            'total': len(projects_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error listing projects: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def generate_subtitles_for_project(request, project_id):
    """
    API endpoint для генерации субтитров для существующего проекта
    """
    try:
        project = Project.objects.get(id=project_id)
        
        if not project.audio:
            return JsonResponse({
                'success': False,
                'error': 'Audio file not found for this project'
            }, status=400)
        
        if project.subtitle:
            return JsonResponse({
                'success': False,
                'error': 'Subtitle file already exists for this project'
            }, status=400)
        
        # Обновляем статус проекта
        project.status = 'processing'
        project.save()
        
        # Генерируем субтитры
        audio_path = project.get_audio_path()
        
        try:
            # Генерируем уникальное имя для файла субтитров
            subtitle_filename = f"{project.id}_{project.name.replace(' ', '_')}_subtitles.srt"
            
            # Используем функцию транскрибации
            srt_content = transcribe_audio(audio_path)
            
            # Сохраняем субтитры в файл
            subtitle_content = ContentFile(srt_content.encode('utf-8'))
            project.subtitle.save(f"{subtitle_filename}", subtitle_content, save=False)
            
            # Обновляем статус проекта
            project.status = 'completed'
            project.save()
            
            # Возвращаем успешный ответ
            return JsonResponse({
                'success': True,
                'message': 'Субтитры успешно сгенерированы!',
                'subtitle_url': project.get_subtitle_url(),
                'status': project.status
            })
            
        except Exception as e:
            # В случае ошибки при генерации субтитров
            project.status = 'failed'
            project.save()
            
            return JsonResponse({
                'success': False,
                'error': f'Error generating subtitles: {str(e)}'
            }, status=500)
            
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Project not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_subtitle_content(request, project_id):
    """
    API endpoint для получения содержимого файла субтитров
    """
    try:
        project = Project.objects.get(id=project_id)
        
        if not project.subtitle:
            return JsonResponse({
                'success': False,
                'error': 'Subtitle file not found for this project'
            }, status=404)
        
        # Читаем содержимое файла субтитров
        subtitle_path = project.get_subtitle_path()
        with open(subtitle_path, 'r', encoding='utf-8') as subtitle_file:
            content = subtitle_file.read()
        
        return JsonResponse({
            'success': True,
            'content': content,
            'filename': os.path.basename(project.subtitle.name)
        })
        
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Project not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error reading subtitle content: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
def update_subtitle_content(request, project_id):
    """
    API endpoint для обновления содержимого файла субтитров
    """
    try:
        project = Project.objects.get(id=project_id)
        
        if not project.subtitle:
            return JsonResponse({
                'success': False,
                'error': 'Subtitle file not found for this project'
            }, status=404)
        
        # Получаем данные из запроса
        try:
            data = json.loads(request.body)
            new_content = data.get('content', '')
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        
        if not new_content.strip():
            return JsonResponse({
                'success': False,
                'error': 'Content cannot be empty'
            }, status=400)
        
        # Валидация базового формата SRT
        if not validate_srt_format(new_content):
            return JsonResponse({
                'success': False,
                'error': 'Invalid SRT format. Please ensure the content follows the SRT standard.'
            }, status=400)
        
        # Сохраняем обновленное содержимое
        subtitle_path = project.get_subtitle_path()
        with open(subtitle_path, 'w', encoding='utf-8') as subtitle_file:
            subtitle_file.write(new_content)
        
        # Обновляем время модификации проекта
        project.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Субтитры успешно обновлены!',
            'content_length': len(new_content)
        })
        
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Project not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error updating subtitle content: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def download_subtitle(request, project_id):
    """
    API endpoint для скачивания файла субтитров
    """
    try:
        project = Project.objects.get(id=project_id)
        
        if not project.subtitle:
            return JsonResponse({
                'success': False,
                'error': 'Subtitle file not found for this project'
            }, status=404)
        
        # Возвращаем файл для скачивания
        subtitle_file = open(project.get_subtitle_path(), 'rb')
        response = FileResponse(subtitle_file, as_attachment=True, filename=os.path.basename(project.subtitle.name))
        return response
        
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Project not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error downloading subtitle: {str(e)}'
        }, status=500)