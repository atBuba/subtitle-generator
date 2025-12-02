from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

audio_file = open(r"C:\Users\User\Documents\program\subtitle-generator\subtitle_generator\subtitle_generator_app\media\audio\db7a9e22-97d6-47ec-afd1-0562d813e0cd_vocal.mp3", "rb")

transcript = client.audio.transcriptions.create(
    model="whisper-1",
    prompt="Transcribe the song lyrics accurately. Ignore silence.",
    file=audio_file,
    response_format="verbose_json",
    timestamp_granularities=["word", "segment"]  # Ключевой параметр для караоке [web:44]
)

print(transcript)

def build_karaoke_from_segments(transcript):
    # transcript — это объект TranscriptionVerbose от openai
    
    karaoke_lines = []

    # Обращаемся к transcript.segments напрямую
    # Если вдруг segments нет, берем пустой список
    segments_list = getattr(transcript, "segments", []) or []
    words_list = getattr(transcript, "words", []) or []

    for seg in segments_list:
        # У Pydantic-объектов доступ к полям через точку: seg.start, seg.end
        seg_start = seg.start
        seg_end = seg.end
        seg_text = seg.text.strip()

        # Фильтруем слова, попадающие в интервал сегмента
        # word.start и word.end тоже доступны через точку
        seg_words = [
            w for w in words_list
            if w.start >= seg_start and w.end <= seg_end
        ]

        # Пропускаем пустые/музыкальные сегменты без слов
        if not seg_words and not any(c.isalnum() for c in seg_text):
             continue

        line = {
            "segment_id": seg.id,
            "text": seg_text,
            "start": seg_start,
            "end": seg_end,
            "words": [
                {
                    "text": w.word,
                    "start": w.start,
                    "end": w.end
                } 
                for w in seg_words
            ]
        }
        karaoke_lines.append(line)

    return karaoke_lines

def format_time(seconds):
    """Преобразует секунды в формат H:MM:SS.cc для ASS"""
    # Защита от отрицательных значений
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def create_ass_file_from_whisper(karaoke_lines, output_path, font="Arial", font_size=48, color1="FFFFFF", color2="0000FF"):
    """
    karaoke_lines: список словарей, полученный из build_karaoke_from_segments
    output_path: путь куда сохранить .ass файл
    """
    
    # Цвета в ASS это BGR, а не RGB. Если у вас hex RGB, нужно перевернуть, если нет - оставить.
    # Обычно color1 - основной, color2 - цвет "заливки" (или наоборот в караоке)
    
    header = f"""[Script Info]
Title: Karaoke Lyrics
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},&H00{color1},&H00{color2},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    
    for line in karaoke_lines:
        # Берем старт/конец всей строки
        # Добавляем небольшой запас времени (как у вас было -0.4), но аккуратно
        start_time = max(0, line['start'] - 0.2) 
        end_time = line['end'] + 0.2
        
        karaoke_text = ""
        
        # Формируем строку с тегами \k
        # Логика: длительность слова = (конец_слова - начало_слова) * 100
        # Но для ПЛАВНОСТИ караоке часто берут (начало_след - начало_тек) или как у вас
        
        prev_end = start_time # Для отсчета первого слова
        
        for i, word in enumerate(line['words']):
            w_start = word['start']
            w_end = word['end']
            w_text = word['text']
            
            # Длительность заливки этого слова в сантисекундах
            # Вариант 1 (строго по длине слова): duration = (w_end - w_start) * 100
            # Вариант 2 (заливать до начала следующего): более плавный
            
            duration = (w_end - w_start) * 100
            
            # Теги:
            # \k - мгновенно, \kf - плавно (слева направо), \ko - плавно без контура
            # Добавляем \fad(400,0) и \an2 только в начало строки (как у вас)
            prefix = ""
            if i == 0:
                prefix = "{\\fad(400,0)\\an2}"
            
            # Собираем: {\теги\kfДлительность}Слово + пробел
            karaoke_text += f"{prefix}{{\\kf{int(duration)}}}{w_text} "

        # Формируем финальную строку события
        event_str = f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},Default,,0,0,0,,{karaoke_text.strip()}"
        events.append(event_str)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))
        
    return output_path

ass_path = "karaoke.ass" # Или ваше имя файла
create_ass_file_from_whisper(
    karaoke_lines=build_karaoke_from_segments(transcript), # Это результат build_karaoke_from_segments(transcript)
    output_path=ass_path,
    font="Arial",               # Можете подставить из переменной font
    font_size=60,
    color1="FFFFFF",            # Белый текст
    color2="00FFFF"             # Желтая/Синяя заливка (BGR формат: 00FFFF = Желтый)
)

