import os
import uuid
from celery import shared_task
from django.conf import settings
from .models import Project
from .services import audio_separator, whisper_client


def format_timestamp(seconds):
    """Форматирует секунды в SRT timestamp формат (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_whisper_response(response):
    """Генерирует SRT контент из Whisper verbose JSON ответа с отображением слов и их временных меток"""
    segments = response.get('segments', [])

    # Если segments есть, используем их с words
    if segments:
        srt_lines = []
        all_words = response.get('words', [])
        for i, segment in enumerate(segments, 1):
            start = format_timestamp(segment['start'])
            end = format_timestamp(segment['end'])

            srt_lines.append(str(i))
            srt_lines.append(f"{start} --> {end}")

            # Находим слова, которые принадлежат этому сегменту
            segment_words = [word for word in all_words if word['start'] >= segment['start'] and word['end'] <= segment['end']]
            for word in segment_words:
                word_start = format_timestamp(word['start'])
                word_end = format_timestamp(word['end'])
                word_text = word['word']
                srt_lines.append(f"{word_text} {word_start} --> {word_end}")

            srt_lines.append("")
        return "\n".join(srt_lines)

    # Если segments нет, группируем words в сегменты
    words = response.get('words', [])
    if not words:
        return ""

    # Группируем слова в сегменты по времени (например, каждые 5 секунд или по смыслу)
    segments_grouped = []
    current_segment = []
    segment_start = None
    segment_end = None

    for word in words:
        if segment_start is None:
            segment_start = word['start']
        segment_end = word['end']
        current_segment.append(word)

        # Создаем новый сегмент каждые 5 секунд или если текст становится слишком длинным
        if segment_end - segment_start >= 5 or len(' '.join(w['word'] for w in current_segment)) > 100:
            text = ' '.join(w['word'] for w in current_segment).strip()
            if text:
                segments_grouped.append({
                    'start': segment_start,
                    'end': segment_end,
                    'text': text,
                    'words': current_segment
                })
            current_segment = []
            segment_start = None

    # Добавляем последний сегмент
    if current_segment:
        text = ' '.join(w['word'] for w in current_segment).strip()
        if text:
            segments_grouped.append({
                'start': segment_start if segment_start is not None else words[-1]['start'],
                'end': segment_end if segment_end is not None else words[-1]['end'],
                'text': text,
                'words': current_segment
            })

    # Генерируем SRT
    srt_lines = []
    for i, segment in enumerate(segments_grouped, 1):
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])

        srt_lines.append(str(i))
        srt_lines.append(f"{start} --> {end}")

        # Добавляем слова с их временными метками
        for word in segment['words']:
            word_start = format_timestamp(word['start'])
            word_end = format_timestamp(word['end'])
            word_text = word['word']
            srt_lines.append(f"{word_text} {word_start} --> {word_end}")

        srt_lines.append("")

    return "\n".join(srt_lines)


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
        whisper_response = whisper_client.transcribe_audio_vocal(vocal_full_path)

        # Сохраняем JSON ответ
        project.whisper_response = whisper_response
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
