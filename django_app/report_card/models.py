from django.db import models


class UploadedBroadsheet(models.Model):
    """Model for uploaded Excel broadsheets."""
    file = models.FileField(upload_to='broadsheets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename
