import os
import json
import time
import requests

# Константы
API_TOKEN = ""
BASE_URL = "https://mvsep.com/api/separation"

# Путь к вашему файлу (проверьте, что он существует)
MY_AUDIO = "/Users/nikitaklenskij/Documents/programs/subtitle-generator/subtitle_generator/subtitle_generator_app/media/audio/91ec145f-583b-4cc5-a88e-ea3f30fde8af_Radio_Tapok_-_Nochnye_vedmy_75359838_mp3.mp3"

# Если у вас уже есть хэш (например, из консоли) и вы хотите просто скачать — вставьте его сюда.
# Если оставить None, скрипт попытается загрузить файл заново.
EXISTING_HASH = "20251122173128-60ff8d1376-91ec145f-583b-4cc5-a88e-ea3f30fde8af-radio-tapok-nochnye-vedmy.mp3"
EXISTING_HASH = None


def create_separation(file_path, sep_type='40'):
    """
    Отправляет файл на разделение.
    sep_type='40' — BS Roformer (Vocals / Instrumental)
    """
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл не найден: {file_path}")
        return None

    url = f"{BASE_URL}/create"
    
    print(f"Загружаю файл: {file_path} ...")
    
    try:
        with open(file_path, 'rb') as f:
            files = {
                'audiofile': f,
                'api_token': (None, API_TOKEN),
                'sep_type': (None, str(sep_type)),
                'output_format': (None, '0'),  # 0 = mp3
                'is_demo': (None, '0'),
            }

            response = requests.post(url, files=files)
            
            # Проверяем статус ответа HTTP
            if response.status_code != 200:
                print(f"Ошибка HTTP {response.status_code}: {response.text}")
                return None
                
            data = response.json()
            
            if data.get('success'):
                task_hash = data['data']['hash']
                print(f"Задача успешно создана! Hash: {task_hash}")
                return task_hash
            else:
                print(f"Ошибка API при создании: {data.get('message')}")
                return None
                
    except Exception as e:
        print(f"Исключение при запросе: {e}")
        return None


def download_file(url, filename, save_path):
    """Скачивает один файл по URL"""
    try:
        print(f"Скачиваю {filename}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            full_path = os.path.join(save_path, filename)
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(1024 * 1024): # Чанки по 1МБ
                    f.write(chunk)
            print(f"-> Сохранено: {full_path}")
            return full_path
        else:
            print(f"Ошибка HTTP при скачивании {filename}: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
    return None


def check_and_download_result(task_hash, output_dir="./my_stems"):
    """
    Проверяет статус задачи. Если есть файлы — скачивает их.
    """
    url = f"{BASE_URL}/get"
    params = {'hash': task_hash}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # 1. Проверяем наличие ключа success
        if not data.get('success'):
            print(f"Ошибка API: {data.get('message', 'Неизвестная ошибка')}")
            return 'error'

        # 2. Извлекаем данные задачи
        task_data = data.get('data', {})
        
        # 3. ГЛАВНАЯ ПРОВЕРКА: Если есть список 'files', значит готово
        files_list = task_data.get('files')
        
        if files_list and len(files_list) > 0:
            print("Файлы найдены! Начинаю скачивание...")
            os.makedirs(output_dir, exist_ok=True)
            
            for file_info in files_list:
                # Получаем URL и чистим его от экранирования
                download_url = file_info['url'].replace('\\/', '/')
                filename = file_info['download']
                
                # Скачиваем
                download_file(download_url, filename, output_dir)
            
            return 'done'
            
        # 4. Если файлов нет, проверяем статус (для обработки ошибок)
        status = task_data.get('status')
        
        if status in ['error', 'failed']:
            print(f"Ошибка обработки на сервере: {task_data.get('message')}")
            return 'error'
            
        # Если ни файлов, ни ошибки -> значит еще обрабатывается
        print(f"Задача в процессе (статус: {status})...")
        return 'processing'

    except Exception as e:
        print(f"Ошибка в коде проверки: {e}")
        # Возвращаем processing, чтобы скрипт не падал, а попробовал снова
        return 'processing'



# ==========================================
# ОСНОВНОЙ БЛОК ЗАПУСКА
# ==========================================

if __name__ == "__main__":
    
    # ШАГ 1: Определяем хэш задачи
    current_hash = EXISTING_HASH
    
    # Если хэш не задан вручную, создаем новую задачу
    if not current_hash:
        print("Хэш не задан, создаем новую задачу...")
        current_hash = create_separation(MY_AUDIO, sep_type='40')
    
    # ШАГ 2: Если хэш есть (новый или старый), начинаем мониторинг
    if current_hash:
        print(f"Начинаю отслеживание задачи: {current_hash}")
        
        while True:
            status = check_and_download_result(current_hash, output_dir="./my_stems")
            
            if status == 'done':
                print("\nВсе готово! Файлы скачаны в папку my_stems.")
                break
            elif status == 'error':
                print("\nКритическая ошибка. Завершение работы.")
                break
            
            # Ждем 10 секунд
            time.sleep(10)
    else:
        print("Не удалось получить хэш задачи.")
