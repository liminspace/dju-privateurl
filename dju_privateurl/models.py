# coding=utf-8
import copy
import random
import datetime
from types import NoneType
from math import ceil
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from dju_common.db import get_object_or_None
from dju_common.fields import JSONField


class PrivateUrlManager(models.Manager):
    def get_or_none(self, action, token):
        return get_object_or_None(self.select_related('user'), action=action, token=token)


class PrivateUrl(models.Model):
    TOKEN_MIN_SIZE = 8
    TOKEN_MAX_SIZE = 65

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), null=True, blank=True)
    action = models.SlugField(verbose_name=_('action'), max_length=32, db_index=True)
    token = models.SlugField(verbose_name=_('token'), max_length=TOKEN_MAX_SIZE)
    expire = models.DateTimeField(verbose_name=_('expire'), null=True, blank=True, db_index=True)
    data = JSONField(verbose_name=_('data'), use_decimal=True)
    created = models.DateTimeField(verbose_name=_('created'), auto_now_add=True, db_index=True)
    used_limit = models.PositiveIntegerField(verbose_name=_('used limit'), default=1, help_text=_('Set 0 to unlimit.'))
    used_counter = models.PositiveIntegerField(verbose_name=_('used counter'), default=0)
    first_used = models.DateTimeField(verbose_name=_('first used'), null=True, blank=True)
    last_used = models.DateTimeField(verbose_name=_('last used'), null=True, blank=True)
    auto_delete = models.BooleanField(verbose_name=_('auto delete'), default=False, db_index=True,
                                      help_text=_("Delete object if it can no longer be used."))

    objects = PrivateUrlManager()

    class Meta:
        db_table = 'dju_privateurl'
        ordering = ('-created',)
        unique_together = ('action', 'token')
        verbose_name = _('private url')
        verbose_name_plural = _('private urls')

    @classmethod
    def create(cls, action, user=None, expire=None, data=None, used_limit=1, auto_delete=False, token_size=None,
               replace=False, dash_split_each=None):
        """
        Створює новий об'єкт PrivateUrl
        :param action: назва події (slug)
        :param user: user or None
        :param expire: термін дії, datetime or timedelta or None
        :param data: додаткові дані, dict or None
        :param used_limit: обмеження по кількості використання, int
        :param auto_delete: автовидалення, якщо посилання буде недійсне, bool
        :param token_size: довжина токена, tuple (min, max) or number or None (=(40, 64))
        :param replace: чи видаляти попередні посилання для user та action, bool
        :param dash_split_each: розділяти токен знаком мінуса кожні N символів, int or None (= 12)
        :return: new saved object
        """
        if replace and user:
            with transaction.atomic():
                cls.objects.filter(action=action, user=user).delete()
        if data:
            data = copy.deepcopy(data)
        if isinstance(expire, datetime.timedelta):
            expire = timezone.now() + expire
        max_tries, n = 20, 0
        while True:
            try:
                with transaction.atomic():
                    token = cls.generate_token(size=token_size, dash_split_each=dash_split_each)
                    return cls.objects.create(user=user, action=action, token=token,
                                              expire=expire, data=data, used_limit=used_limit,
                                              auto_delete=auto_delete)
            except IntegrityError:
                n += 1
                if n > max_tries:
                    raise RuntimeError("It can't make PrivateUrl object (action={}, token_size={})".format(
                        action, token_size
                    ))

    def is_available(self, dt=None):
        """
        Повертає True, якщо об'єкт може бути використаний
        """
        if self.expire and self.expire <= (dt or timezone.now()):
            return False
        if self.used_limit and self.used_limit <= self.used_counter:
            return False
        return True

    def used_counter_inc(self):
        obj_is_exists = self.pk
        now = timezone.now()
        self.used_counter += 1
        if self.auto_delete and not self.is_available(dt=now):
            if obj_is_exists:
                self.delete()
            return
        uf = {'used_counter', 'last_used'}
        if not self.first_used:
            self.first_used = now
            uf.add('first_used')
        self.last_used = now
        if obj_is_exists:
            self.save(update_fields=uf)

    @classmethod
    def generate_token(cls, size=None, dash_split_each=None):
        """
        Генерує новий унікальний токен для action.
        size = (мінімальни розмір, максимальний розмір) або просто розмір
        """
        if not isinstance(size, (int, list, tuple, NoneType)):
            raise AttributeError('Attr size must be int, list, tuple or None.')
        if isinstance(size, (list, tuple)) and len(size) != 2:
            raise AttributeError('Attr size must contains two values.')
        if size is None:
            size = (36, 60)

        if not isinstance(dash_split_each, (int, NoneType)):
            raise AttributeError('Attr dash_split_each must be int or None')
        if dash_split_each is None:
            dash_split_each = 12
        elif dash_split_each < 4 and dash_split_each != 0:
            raise AttributeError('Attr dash_split_each must be 0 or minimum 4.')

        if dash_split_each:
            tm = int(ceil((cls.TOKEN_MAX_SIZE * dash_split_each) / (dash_split_each + 1.)))
        else:
            tm = cls.TOKEN_MAX_SIZE

        if isinstance(size, (list, tuple)):
            if not (cls.TOKEN_MIN_SIZE <= size[0] < tm and cls.TOKEN_MIN_SIZE < size[1] <= tm):
                raise AttributeError('Attr size and dash_split_each have incompatible values ({}..{}, {}).'.format(
                    size[0], size[1], dash_split_each
                ))
            if not (size[0] < size[1]):
                raise AttributeError('Attr size has incorrect values ({}..{}).'.format(size[0], size[1]))
            random.seed(get_random_string(length=100))
            _size = random.randint(*size)
        else:
            if not (cls.TOKEN_MIN_SIZE <= size <= tm):
                raise AttributeError('Attr size and dash_split_each have incompatible values ({}, {}).'.format(
                    size, dash_split_each
                ))
            _size = size

        token = get_random_string(length=_size)
        if dash_split_each > 0:
            n = dash_split_each
            while n < len(token):
                token = token[:n] + '-' + token[n:]
                n += dash_split_each + 1

        return token

    def get_absolute_url(self):
        return reverse('dju_privateurl', kwargs={'action': self.action, 'token': self.token})
