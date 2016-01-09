from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DJUPrivateURLConfig(AppConfig):
    name = 'dju_privateurl'
    verbose_name = _('Django Utils: Private URL')
