import os
import uuid
import time
import shutil
from django.conf import settings
from . import demucs_client


def separate_audio(project_id, audio_path):
    """
    Разделяет аудио файл на вокал и инструментал с использованием Demucs API.
    Возвращает пути к созданным файлам вокала и инструментала.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found at: {audio_path}")

    # Создаем временную директорию для сохранения результатов разделения
    temp_output_dir = os.path.join(settings.MEDIA_ROOT, 'temp_separation', str(project_id))
    os.makedirs(temp_output_dir, exist_ok=True)

    try:
        # Шаг 1: Отправляем файл на разделение
        task_hash = demucs_client.create_separation(audio_path, sep_type='40')
        if not task_hash:
            raise Exception("Failed to create separation task")

        # Шаг 2: Ожидаем завершения разделения
        print(f"Ожидаем завершения разделения для задачи: {task_hash}")
        while True:
            status = demucs_client.check_and_download_result(task_hash, output_dir=temp_output_dir)
            
            if status == 'done':
                print("Разделение завершено!")
                break
            elif status == 'error':
                raise Exception("Ошибка при разделении аудио")
            
            # Ждем 10 секунд перед следующей проверкой
            time.sleep(10)

        # Шаг 3: Находим файлы вокала и инструментала в директории
        vocal_file = None
        instrumental_file = None
        
        print(f"Проверяем файлы в директории: {temp_output_dir}")
        for filename in os.listdir(temp_output_dir):
            print(f"Найден файл: {filename}")
            if 'vocals' in filename.lower() or 'vocal' in filename.lower():
                vocal_file = os.path.join(temp_output_dir, filename)
                print(f"Найден вокальный файл: {vocal_file}")
            elif 'other' in filename.lower() or 'instrumental' in filename.lower() or 'instr' in filename.lower():
                instrumental_file = os.path.join(temp_output_dir, filename)
                print(f"Найден инструментальный файл: {instrumental_file}")

        if not vocal_file or not instrumental_file:
            # Если не нашли файлы по ключевым словам, пробуем использовать все доступные файлы
            files = [f for f in os.listdir(temp_output_dir) if f.endswith('.mp3')]
            print(f"Всего найдено mp3 файлов: {len(files)}")
            
            if len(files) >= 2:
                # Предполагаем, что первый файл - вокал, второй - инструментал
                vocal_file = os.path.join(temp_output_dir, files[0])
                instrumental_file = os.path.join(temp_output_dir, files[1])
                print(f"Используем альтернативное определение файлов:")
                print(f"  Вокал: {vocal_file}")
                print(f"  Инструментал: {instrumental_file}")
            else:
                raise Exception("Не удалось найти достаточное количество файлов after разделения")

        # Шаг 4: Генерируем уникальные имена для файлов
        file_extension = 'mp3'  # Предполагаем, что всегда mp3
        
        vocal_filename = f"{uuid.uuid4()}_vocal.{file_extension}"
        instrumental_filename = f"{uuid.uuid4()}_instrumental.{file_extension}"

        # Шаг 5: Перемещаем файлы в постоянное хранилище
        audio_storage_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(audio_storage_dir, exist_ok=True)

        vocal_destination = os.path.join(audio_storage_dir, vocal_filename)
        instrumental_destination = os.path.join(audio_storage_dir, instrumental_filename)

        print(f"Перемещаем вокальный файл из {vocal_file} в {vocal_destination}")
        print(f"Перемещаем инструментальный файл из {instrumental_file} in {instrumental_destination}")
        
        shutil.move(vocal_file, vocal_destination)
        shutil.move(instrumental_file, instrumental_destination)

        # Шаг 6: Возвращаем пути к файлам относительно MEDIA_ROOT
        vocal_path = os.path.join('audio', vocal_filename)
        instrumental_path = os.path.join('audio', instrumental_filename)
        
        print(f"Возвращаем пути:")
        print(f"  Вокал: {vocal_path}")
        print(f"  Инструментал: {instrumental_path}")

        return vocal_path, instrumental_path

    finally:
        # Очищаем временную директорию
        if os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)