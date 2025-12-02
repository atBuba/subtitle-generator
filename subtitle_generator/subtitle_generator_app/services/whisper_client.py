import os
from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def transcribe_audio_vocal(vocal_file_path):
    """
    Транскрибирует вокальную дорожку в формат verbose JSON с timestamps слов.
    """
    if not os.path.exists(vocal_file_path):
        raise FileNotFoundError(f"Vocal audio file not found at: {vocal_file_path}")

    with open(vocal_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            prompt="Transcribe the song lyrics accurately. Ignore silence.",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            temperature=0.2,
        )

    return transcription.to_dict()

def transcribe_audio(file_path):
    """
    Отправляет файл в Whisper и возвращает контент SRT.
    Устаревшая функция, оставлена для совместимости.
    """
    return transcribe_audio_vocal(file_path)

