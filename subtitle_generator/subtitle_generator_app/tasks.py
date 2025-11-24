import os
import uuid
from celery import shared_task
from django.conf import settings
from .models import Project
from .services import audio_separator, whisper_client


@shared_task(bind=True, max_retries=3)
def process_audio_task(self, project_id):
    """Фоновая обработка аудио: разделение + транскрипция"""
    try:
        project = Project.objects.get(id=project_id)
        project.status = 'processing'
        project.save()
        
        print(f"[Celery] Начинаем обработку проекта {project_id}")
        
        # Шаг 1: Разделение аудио
        audio_path = project.get_audio_path()
        vocal_path, instrumental_path = audio_separator.separate_audio(
            project.id, audio_path
        )
        
        project.vocal_audio.name = vocal_path
        project.instrumental_audio.name = instrumental_path
        project.save()
        
        print(f"[Celery] Разделение завершено для проекта {project_id}")
        
        # Шаг 2: Транскрипция
        vocal_full_path = os.path.join(settings.MEDIA_ROOT, vocal_path)
        srt_content = whisper_client.transcribe_audio_vocal(vocal_full_path)
        
        # Шаг 3: Сохранение субтитров
        srt_filename = f"{uuid.uuid4()}_{project.name}_subtitles.srt"
        srt_path = os.path.join('subtitle/srt', srt_filename)
        full_srt_path = os.path.join(settings.MEDIA_ROOT, srt_path)
        
        os.makedirs(os.path.dirname(full_srt_path), exist_ok=True)
        
        with open(full_srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        project.subtitle.name = srt_path
        project.status = 'completed'
        project.save()
        
        print(f"[Celery] Проект {project_id} успешно обработан")
        
        return {'status': 'completed', 'project_id': project_id}
        
    except Exception as exc:
        print(f"[Celery] ОШИБКА при обработке проекта {project_id}: {exc}")
        
        try:
            project = Project.objects.get(id=project_id)
            project.status = 'failed'
            project.save()
        except:
            pass
        
        # Повторная попытка через минуту
        raise self.retry(exc=exc, countdown=60)
