# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class Role(models.Model):
    name=models.charField(max_length=100)
    permissions = models.JSONField(default=dict)

    def __str__(self):
        return self.name

class User(AbstractUser):
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=true, related_name='users')
    phone = models.CharField(max_length=15, blank=true)
    consent_marketing = models.BooleanField(default=False)
    consent_data_processing = models.BooleanField(default=False)
    consent_data = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name=_('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username
