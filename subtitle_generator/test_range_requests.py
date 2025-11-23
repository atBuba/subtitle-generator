#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы HTTP Range Requests
"""
import requests
import sys
import os

def test_range_requests():
    """Тестируем Range Requests для аудиофайлов"""
    base_url = "http://127.0.0.1:8000"
    
    print("Тестирование HTTP Range Requests...")
    print("=" * 50)
    
    # Получаем список проектов
    try:
        response = requests.get(f"{base_url}/api/projects/")
        if response.status_code != 200:
            print(f"❌ Ошибка получения списка проектов: {response.status_code}")
            return
        
        projects = response.json().get('projects', [])
        if not projects:
            print("❌ Нет доступных проектов с аудиофайлами")
            return
        
        # Находим проект с аудиофайлом
        project_with_audio = None
        for project in projects:
            if project.get('audio'):
                project_with_audio = project
                break
        
        if not project_with_audio:
            print("❌ Нет проектов с аудиофайлами")
            return
        
        project_id = project_with_audio['id']
        print(f"✅ Найден проект с аудиофайлом: {project_with_audio['name']} (ID: {project_id})")
        
        # Тестируем обычный запрос (без Range)
        print("\n1. Тест обычного запроса (без Range заголовка):")
        response = requests.get(f"{base_url}/project/{project_id}/audio/")
        print(f"   Статус: {response.status_code}")
        print(f"   Accept-Ranges: {response.headers.get('Accept-Ranges', 'отсутствует')}")
        print(f"   Content-Length: {response.headers.get('Content-Length', 'отсутствует')}")
        
        if response.status_code == 200 and response.headers.get('Accept-Ranges') == 'bytes':
            print("   ✅ Обычный запрос работает, сервер поддерживает Range Requests")
        else:
            print("   ❌ Проблемы с обычным запросом")
        
        # Тестируем Range запрос
        print("\n2. Тест Range запроса (первые 1024 байта):")
        headers = {'Range': 'bytes=0-1023'}
        response = requests.get(f"{base_url}/project/{project_id}/audio/", headers=headers)
        print(f"   Статус: {response.status_code}")
        print(f"   Content-Range: {response.headers.get('Content-Range', 'отсутствует')}")
        print(f"   Content-Length: {response.headers.get('Content-Length', 'отсутствует')}")
        
        if response.status_code == 206:
            print("   ✅ Range запрос работает! Перемотка должна работать в браузере")
            print("   ✅ Сервер корректно обрабатывает частичные запросы")
        else:
            print("   ❌ Range запрос не работает")
            print("   ❌ Перемотка в браузере не будет работать")
        
        # Тестируем Range запрос с конца файла
        print("\n3. Тест Range запроса (последние 500 байт):")
        headers = {'Range': 'bytes=-500'}
        response = requests.get(f"{base_url}/project/{project_id}/audio/", headers=headers)
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 206:
            print("   ✅ Range запрос с конца файла работает")
        else:
            print("   ❌ Range запрос с конца файла не работает")
        
        print("\n" + "=" * 50)
        if response.status_code == 206:
            print("🎉 Тесты пройдены! Перемотка аудиофайлов должна работать корректно.")
        else:
            print("⚠️  Тесты не пройдены. Возможны проблемы с перемоткой.")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к серверу. Убедитесь, что сервер Django запущен.")
        print("   Запустите: python manage.py runserver")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_range_requests()