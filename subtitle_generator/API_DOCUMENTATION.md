# Документация API - Генератор Субтитров

## Обзор

API для генератора субтитров предоставляет эндпоинты для:
- Генерации субтитров из аудио файлов
- Получения статуса проектов
- Загрузки и скачивания файлов
- Управления проектами

## Базовый URL
```
http://localhost:8000/
```

## Аутентификация
API в текущей версии не требует аутентификации. В продакшене рекомендуется добавить JWT или сессионную аутентификацию.

## Эндпоинты

### 1. Генерация субтитров

**POST** `/api/generate-subtitles/`

Генерирует субтитры из загруженного аудио файла.

#### Параметры запроса:
- `audio_file` (обязательный): Файл аудио (multipart/form-data)
- `project_name` (опциональный): Название проекта (по умолчанию "Untitled Project")

#### Поддерживаемые форматы аудио:
- MP3
- WAV  
- M4A
- FLAC
- OGG
- WMA

#### Пример запроса (cURL):
```bash
curl -X POST http://localhost:8000/api/generate-subtitles/ \
  -F "audio_file=@/path/to/audio.mp3" \
  -F "project_name=My Subtitle Project"
```

#### Успешный ответ (201):
```json
{
  "success": true,
  "project_id": 1,
  "project_name": "My Subtitle Project",
  "status": "completed",
  "audio_url": "/media/subtitle_generator_app/audio/unique_filename.mp3",
  "subtitle_url": "/media/subtitle_generator_app/subtitle/srt/unique_filename.srt",
  "created_at": "2023-11-21T14:03:47.276Z",
  "message": "Субтитры успешно сгенерированы!"
}
```

#### Ошибки:
```json
{
  "success": false,
  "error": "Audio file is required"
}
```

### 2. Получение статуса проекта

**GET** `/api/project/{project_id}/status/`

Возвращает подробную информацию о проекте.

#### Параметры:
- `project_id` (URL parameter): ID проекта

#### Пример запроса:
```bash
curl http://localhost:8000/api/project/1/status/
```

#### Успешный ответ (200):
```json
{
  "success": true,
  "project": {
    "project_id": 1,
    "project_name": "My Subtitle Project",
    "status": "completed",
    "audio_url": "/media/subtitle_generator_app/audio/unique_filename.mp3",
    "subtitle_url": "/media/subtitle_generator_app/subtitle/srt/unique_filename.srt",
    "created_at": "2023-11-21T14:03:47.276Z",
    "updated_at": "2023-11-21T14:05:12.345Z"
  }
}
```

### 3. Список всех проектов

**GET** `/api/projects/`

Возвращает список всех проектов с базовой информацией.

#### Пример запроса:
```bash
curl http://localhost:8000/api/projects/
```

#### Успешный ответ (200):
```json
{
  "success": true,
  "projects": [
    {
      "project_id": 1,
      "project_name": "My Subtitle Project",
      "status": "completed",
      "audio_url": "/media/subtitle_generator_app/audio/audio_file.mp3",
      "subtitle_url": "/media/subtitle_generator_app/subtitle/srt/subtitle_file.srt",
      "created_at": "2023-11-21T14:03:47.276Z",
      "updated_at": "2023-11-21T14:05:12.345Z"
    }
  ],
  "total": 1
}
```

### 4. Получение содержимого субтитров

**GET** `/api/project/{project_id}/subtitle-content/`

Возвращает содержимое файла субтитров в текстовом формате.

#### Параметры:
- `project_id` (URL parameter): ID проекта

#### Пример запроса:
```bash
curl http://localhost:8000/api/project/1/subtitle-content/
```

#### Успешный ответ (200):
```json
{
  "success": true,
  "content": "1\n00:00:00,000 --> 00:00:05,000\nПервая строка субтитров\n\n2\n00:00:05,000 --> 00:00:10,000\nВторая строка субтитров",
  "filename": "subtitle_file.srt"
}
```

#### Ошибка (404):
```json
{
  "success": false,
  "error": "Subtitle file not found for this project"
}
```

### 5. Обновление содержимого субтитров

**PUT** `/api/project/{project_id}/update-subtitle/`

Обновляет содержимое файла субтитров. Выполняет валидацию формата SRT.

#### Параметры:
- `project_id` (URL parameter): ID проекта
- `content` (body, обязательный): Новое содержимое субтитров в формате SRT

#### Пример запроса:
```bash
curl -X PUT http://localhost:8000/api/project/1/update-subtitle/ \
  -H "Content-Type: application/json" \
  -d '{
    "content": "1\n00:00:00,000 --> 00:00:05,000\nОбновленная строка субтитров\n\n2\n00:00:05,000 --> 00:00:10,000\nВторая строка"
  }'
```

#### Успешный ответ (200):
```json
{
  "success": true,
  "message": "Субтитры успешно обновлены!",
  "content_length": 150
}
```

#### Ошибки:
```json
{
  "success": false,
  "error": "Invalid SRT format. Please ensure the content follows the SRT standard."
}
```

```json
{
  "success": false,
  "error": "Content cannot be empty"
}
```

### 6. Скачивание файла субтитров

**GET** `/api/project/{project_id}/download-subtitle/`

Скачивает файл субтитров для указанного проекта.

#### Параметры:
- `project_id` (URL parameter): ID проекта

#### Пример запроса:
```bash
curl -o subtitle.srt http://localhost:8000/api/project/1/download-subtitle/
```

#### Успешный ответ:
- Файл .srt возвращается как вложение (Content-Disposition: attachment)

#### Ошибка (404):
```json
{
  "success": false,
  "error": "Subtitle file not found for this project"
}
```

## Статусы проектов

- `draft` - Черновик (только создан)
- `processing` - Обрабатывается (идет генерация субтитров)
- `completed` - Завершен (субтитры сгенерированы)
- `failed` - Ошибка (произошла ошибка при генерации)

## Использование с фронтендом

### JavaScript (fetch API)
```javascript
// Генерация субтитров
async function generateSubtitles(audioFile, projectName) {
  const formData = new FormData();
  formData.append('audio_file', audioFile);
  formData.append('project_name', projectName);

  try {
    const response = await fetch('/api/generate-subtitles/', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('Проект создан:', result.project_id);
      console.log('Аудио URL:', result.audio_url);
      console.log('Субтитры URL:', result.subtitle_url);
    } else {
      console.error('Ошибка:', result.error);
    }
  } catch (error) {
    console.error('Ошибка сети:', error);
  }
}

// Проверка статуса проекта
async function getProjectStatus(projectId) {
  try {
    const response = await fetch(`/api/project/${projectId}/status/`);
    const result = await response.json();
    
    if (result.success) {
      return result.project;
    } else {
      console.error('Ошибка:', result.error);
      return null;
    }
  } catch (error) {
    console.error('Ошибка сети:', error);
    return null;
  }
}

// Получение списка проектов
async function getProjects() {
  try {
    const response = await fetch('/api/projects/');
    const result = await response.json();
    
    if (result.success) {
      return result.projects;
    } else {
      console.error('Ошибка:', result.error);
      return [];
    }
  } catch (error) {
    console.error('Ошибка сети:', error);
    return [];
  }
}

// Получение содержимого субтитров
async function getSubtitleContent(projectId) {
  try {
    const response = await fetch(`/api/project/${projectId}/subtitle-content/`);
    const result = await response.json();
    
    if (result.success) {
      return result.content;
    } else {
      console.error('Ошибка:', result.error);
      return null;
    }
  } catch (error) {
    console.error('Ошибка сети:', error);
    return null;
  }
}

// Обновление содержимого субтитров
async function updateSubtitleContent(projectId, newContent) {
  try {
    const response = await fetch(`/api/project/${projectId}/update-subtitle/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: newContent
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('Субтитры обновлены:', result.message);
      return true;
    } else {
      console.error('Ошибка:', result.error);
      return false;
    }
  } catch (error) {
    console.error('Ошибка сети:', error);
    return false;
  }
}
```

### React пример компонента
```jsx
import React, { useState, useEffect } from 'react';

const SubtitleGenerator = () => {
  const [audioFile, setAudioFile] = useState(null);
  const [projectName, setProjectName] = useState('');
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!audioFile) {
      alert('Пожалуйста, выберите аудио файл');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    formData.append('project_name', projectName || 'Untitled Project');

    try {
      const response = await fetch('/api/generate-subtitles/', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        alert('Субтитры успешно сгенерированы!');
        loadProjects();
      } else {
        alert('Ошибка: ' + result.error);
      }
    } catch (error) {
      alert('Ошибка сети: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadProjects = async () => {
    try {
      const response = await fetch('/api/projects/');
      const result = await response.json();
      
      if (result.success) {
        setProjects(result.projects);
      }
    } catch (error) {
      console.error('Ошибка загрузки проектов:', error);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div>
      <h2>Генератор Субтитров</h2>
      
      <form onSubmit={handleGenerate}>
        <div>
          <label>Название проекта:</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="Введите название проекта"
          />
        </div>
        
        <div>
          <label>Аудио файл:</label>
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setAudioFile(e.target.files[0])}
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Генерирую...' : 'Генерировать субтитры'}
        </button>
      </form>

      <h3>Список проектов:</h3>
      <ul>
        {projects.map(project => (
          <li key={project.project_id}>
            <strong>{project.project_name}</strong> - {project.status}
            {project.subtitle_url && (
              <a href={project.subtitle_url} download>
                Скачать субтитры
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SubtitleGenerator;
```

## Обработка ошибок

API возвращает HTTP коды статуса для индикации результата:
- 200: Успешный запрос
- 201: Ресурс создан успешно
- 400: Неверный запрос (проверьте параметры)
- 404: Ресурс не найден
- 500: Внутренняя ошибка сервера

## Ограничения

- Максимальный размер загружаемого файла зависит от настроек Django (по умолчанию 10MB)
- Поддерживаются только аудио форматы, указанные выше
- API синхронный - время обработки зависит от длительности аудио файла

## Логирование

Все операции логируются в стандартном выводе Django. Для продакшена рекомендуется настроить централизованное логирование.

## Безопасность

- Все API эндпоинты защищены от CSRF в режиме разработки
- Рекомендуется добавить аутентификацию для продакшена
- Проверяйте типы загружаемых файлов
- Ограничивайте максимальный размер файлов