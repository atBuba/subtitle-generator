from django.db import models
import os
import uuid
import re

class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Project Name')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )
    audio = models.FileField(
        upload_to='audio/',
        blank=True,
        null=True,
        verbose_name='Audio File'
    )
    vocal_audio = models.FileField(
        upload_to='audio/',
        blank=True,
        null=True,
        verbose_name='Vocal Audio File'
    )
    instrumental_audio = models.FileField(
        upload_to='audio/',
        blank=True,
        null=True,
        verbose_name='Instrumental Audio File'
    )
    whisper_response = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Whisper Response JSON'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
    
    def format_timestamp(self, seconds):
        """Форматирует секунды в SRT timestamp формат (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_srt_from_whisper_response(self, response):
        """Генерирует SRT контент из Whisper verbose JSON ответа с отображением слов и их временных меток"""
        segments = response.get('segments', [])

        # Если segments есть, используем их с words
        if segments:
            srt_lines = []
            all_words = response.get('words', [])
            for i, segment in enumerate(segments, 1):
                start = self.format_timestamp(segment['start'])
                end = self.format_timestamp(segment['end'])

                srt_lines.append(str(i))
                srt_lines.append(f"{start} --> {end}")

                # Находим слова, которые принадлежат этому сегменту
                segment_words = [word for word in all_words if word['start'] >= segment['start'] and word['end'] <= segment['end']]
                for word in segment_words:
                    word_start = self.format_timestamp(word['start'])
                    word_end = self.format_timestamp(word['end'])
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
            start = self.format_timestamp(segment['start'])
            end = self.format_timestamp(segment['end'])

            srt_lines.append(str(i))
            srt_lines.append(f"{start} --> {end}")

            # Добавляем слова с их временными метками
            for word in segment['words']:
                word_start = self.format_timestamp(word['start'])
                word_end = self.format_timestamp(word['end'])
                word_text = word['word']
                srt_lines.append(f"{word_text} {word_start} --> {word_end}")

            srt_lines.append("")


        return "\n".join(srt_lines)

    def generate_standard_srt_from_whisper_response(self, response):
        """Генерирует стандартный SRT контент из Whisper verbose JSON ответа без временных меток слов"""
        segments = response.get('segments', [])

        srt_lines = []

        if segments:
            # Используем segments напрямую
            for i, segment in enumerate(segments, 1):
                start = self.format_timestamp(segment['start'])
                end = self.format_timestamp(segment['end'])
                text = segment.get('text', '').strip()

                if text:
                    srt_lines.append(str(i))
                    srt_lines.append(f"{start} --> {end}")
                    srt_lines.append(text)
                    srt_lines.append("")
        else:
            # Группируем words в сегменты
            words = response.get('words', [])
            if not words:
                return ""

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
                            'text': text
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
                        'text': text
                    })

            # Генерируем стандартный SRT
            for i, segment in enumerate(segments_grouped, 1):
                start = self.format_timestamp(segment['start'])
                end = self.format_timestamp(segment['end'])

                srt_lines.append(str(i))
                srt_lines.append(f"{start} --> {end}")
                srt_lines.append(segment['text'])
                srt_lines.append("")

        return "\n".join(srt_lines)

    def generate_ass_from_whisper_response(self, response):
        """Генерирует ASS контент из Whisper verbose JSON ответа с караоке эффектами"""
        segments = response.get('segments', [])
        words = response.get('words', [])

        # ASS header
        ass_content = """[Script Info]
Title: Karaoke Lyrics
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,60,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # Собираем сегменты
        karaoke_segments = []

        if segments:
            for segment in segments:
                seg_start = segment['start']
                seg_end = segment['end']
                seg_text = segment.get('text', '').strip()

                # Фильтруем слова для сегмента
                segment_words = [w for w in words if w['start'] >= seg_start and w['end'] <= seg_end]

                if segment_words:
                    karaoke_segments.append({
                        'start': seg_start,
                        'end': seg_end,
                        'words': segment_words
                    })
        else:
            # Группируем words в сегменты
            if words:
                current_segment = []
                segment_start = None
                segment_end = None

                for word in words:
                    if segment_start is None:
                        segment_start = word['start']
                    segment_end = word['end']
                    current_segment.append(word)

                    if segment_end - segment_start >= 5 or len(' '.join(w['word'] for w in current_segment)) > 100:
                        if current_segment:
                            karaoke_segments.append({
                                'start': segment_start,
                                'end': segment_end,
                                'words': current_segment
                            })
                        current_segment = []
                        segment_start = None

                if current_segment:
                    karaoke_segments.append({
                        'start': segment_start if segment_start is not None else words[-1]['start'],
                        'end': segment_end if segment_end is not None else words[-1]['end'],
                        'words': current_segment
                    })

        # Создаем караоке Dialogue для сегментов
        for segment in karaoke_segments:
            start_time = max(0, segment['start'] - 0.2)
            end_time = segment['end'] + 0.2

            karaoke_text = "{\\fad(400,0)\\an2}"

            for i, word in enumerate(segment['words']):
                w_start = word['start']
                w_end = word['end']
                w_text = word['word']

                duration = int((w_end - w_start) * 100)
                karaoke_text += f"{{\\kf{duration}}}{w_text} "

            event_str = f"Dialogue: 0,{self.format_timestamp_ass(start_time)},{self.format_timestamp_ass(end_time)},Default,,0,0,0,,{karaoke_text.strip()}"
            events.append((start_time, event_str))

        # Добавляем ноты для длинных пауз
        if karaoke_segments:
            sorted_segments = sorted(karaoke_segments, key=lambda x: x['start'])

            for i in range(len(sorted_segments) - 1):
                current_end = sorted_segments[i]['end']
                next_start = sorted_segments[i + 1]['start']
                pause_duration = next_start - current_end

                if pause_duration > 5:
                    # Добавляем ноты каждые 0.4 секунды
                    note_positions = [(1240, 540), (1340, 540), (1440, 540)]
                    note_index = 0
                    current_time = current_end

                    while current_time < next_start:
                        note_end = min(current_time + 0.8, next_start)
                        pos_x, pos_y = note_positions[note_index % len(note_positions)]

                        note_event = f"Dialogue: 0,{self.format_timestamp_ass(current_time)},{self.format_timestamp_ass(note_end)},Default,,0,0,0,,{{\\an5\\fad(200,200)\\fs100\\c&HFFFFFF&}}{{\\pos({pos_x},{pos_y})}}♫"
                        events.append((current_time, note_event))

                        current_time += 0.4
                        note_index += 1

        # Сортируем события по времени
        events.sort(key=lambda x: x[0])

        # Добавляем события в контент
        for _, event in events:
            ass_content += event + "\n"

        return ass_content

    def format_timestamp_ass(self, seconds):
        """Форматирует секунды в ASS timestamp формат (H:MM:SS.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def get_subtitle_content(self):
        """Возвращает содержимое субтитров в формате SRT, сгенерированное из whisper_response"""
        if not self.whisper_response:
            return ""
        return self.generate_srt_from_whisper_response(self.whisper_response)

    def get_standard_srt_content(self):
        """Возвращает содержимое субтитров в стандартном формате SRT, сгенерированное из whisper_response"""
        if not self.whisper_response:
            return ""
        return self.generate_standard_srt_from_whisper_response(self.whisper_response)

    def get_ass_content(self):
        """Возвращает содержимое субтитров в формате ASS, сгенерированное из whisper_response"""
        if not self.whisper_response:
            return ""
        return self.generate_ass_from_whisper_response(self.whisper_response)

    def get_subtitle_filename(self):
        """Возвращает имя файла субтитров на основе названия проекта"""
        clean_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_')
        return f"{clean_name}.srt"

    def get_ass_filename(self):
        """Возвращает имя файла ASS субтитров на основе названия проекта"""
        clean_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_')
        return f"{clean_name}.ass"

    def has_subtitles(self):
        """Проверяет, есть ли субтитры для проекта"""
        return self.whisper_response is not None and bool(self.whisper_response.get('words', []) or self.whisper_response.get('segments', []))

    def __str__(self):
        return self.name
    
    def get_audio_path(self):
        """Возвращает полный путь к аудио файлу"""
        if self.audio:
            return self.audio.path
        return None
    
    def get_vocal_path(self):
        """Возвращает полный путь к вокальному файлу"""
        if self.vocal_audio:
            return self.vocal_audio.path
        return None
    
    def get_instrumental_path(self):
        """Возвращает полный путь к инструментальному файлу"""
        if self.instrumental_audio:
            return self.instrumental_audio.path
        return None
    
    
    def get_audio_url(self):
        """Возвращает URL для аудио файла"""
        if self.audio:
            return self.audio.url
        return None
    
    def get_vocal_url(self):
        """Возвращает URL для вокального файла"""
        if self.vocal_audio:
            return self.vocal_audio.url
        return None
    
    def get_instrumental_url(self):
        """Возвращает URL для инструментального файла"""
        if self.instrumental_audio:
            return self.instrumental_audio.url
        return None
    
