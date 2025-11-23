from django.db import models
import os
import uuid

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
    subtitle = models.FileField(
        upload_to='subtitle/srt/',
        blank=True,
        null=True,
        verbose_name='Subtitle File'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
    
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
    
    def get_subtitle_path(self):
        """Возвращает полный путь к файлу субтитров"""
        if self.subtitle:
            return self.subtitle.path
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
    
    def get_subtitle_url(self):
        """Возвращает URL для файла субтитров"""
        if self.subtitle:
            return self.subtitle.url
        return None
