# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, related_name="users"
    )
    phone = models.CharField(max_length=15, blank=True)
    consent_marketing = models.BooleanField(default=False)
    consent_data_processing = models.BooleanField(default=False)
    consent_data = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_set",  # Add this line
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_set",  # Add this line
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_query_name="user",
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.username
