from django.contrib import admin
from .models import UploadedBroadsheet


@admin.register(UploadedBroadsheet)
class UploadedBroadsheetAdmin(admin.ModelAdmin):
    list_display = ('filename', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    search_fields = ('filename',)
    ordering = ('-uploaded_at',)
