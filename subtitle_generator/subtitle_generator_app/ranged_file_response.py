"""
Custom RangedFileResponse для поддержки HTTP Range Requests
"""
import os
from django.http import HttpResponse, Http404


def ranged_file_response(request, file_path, content_type='audio/mpeg'):
    """
    Возвращает HTTP Response с поддержкой Range Requests для аудиофайлов
    """
    try:
        # Открываем файл и получаем его размер
        file_size = os.path.getsize(file_path)
        file_obj = open(file_path, 'rb')
        
        # Получаем Range заголовок из запроса
        range_header = request.META.get('HTTP_RANGE')
        
        if range_header and range_header.startswith('bytes='):
            try:
                # Парсим Range заголовок
                range_spec = range_header[6:]  # Убираем 'bytes='
                if '-' in range_spec:
                    start_str, end_str = range_spec.split('-', 1)
                    
                    if not start_str:
                        # bytes=-500 (последние 500 bytes)
                        start = max(0, file_size - int(end_str))
                        end = file_size - 1
                    elif not end_str:
                        # bytes=500- (от 500 bytes до конца)
                        start = int(start_str)
                        end = file_size - 1
                    else:
                        # bytes=500-999 (от 500 до 999 bytes)
                        start = int(start_str)
                        end = min(int(end_str), file_size - 1)
                    
                    if start > end or start < 0:
                        raise ValueError("Невалидный диапазон")
                    
                    # Устанавливаем позицию в файле
                    file_obj.seek(start)
                    content_length = end - start + 1
                    
                    # Создаем ответ с частичным контентом
                    response = HttpResponse(
                        content=file_obj.read(content_length),
                        content_type=content_type,
                        status=206  # Partial Content
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                    response['Content-Length'] = str(content_length)
                    
                else:
                    raise ValueError("Невалидный формат диапазона")
            except (ValueError, IndexError):
                # При ошибке парсинга возвращаем весь файл
                file_obj.seek(0)
                response = HttpResponse(
                    content=file_obj.read(),
                    content_type=content_type,
                    status=200
                )
                response['Content-Length'] = str(file_size)
        else:
            # Нет Range заголовка - возвращаем весь файл
            file_obj.seek(0)
            response = HttpResponse(
                content=file_obj.read(),
                content_type=content_type,
                status=200
            )
            response['Content-Length'] = str(file_size)
        
        # Добавляем обязательные заголовки для поддержки Range Requests
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        
        # Устанавливаем обработчик закрытия файла
        response.file_to_close = file_obj
        
        return response
    
    except FileNotFoundError:
        raise Http404("Файл не найден")
    except Exception:
        if 'file_obj' in locals():
            file_obj.close()
        raise