import datetime
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse, NoReverseMatch
from django.dispatch import receiver
from django.http import HttpResponse
from django.shortcuts import resolve_url
from django.test import TestCase
from dju_privateurl.models import PrivateUrl
from dju_privateurl.signals import privateurl_ok, privateurl_fail


class TestPrivateUrl(TestCase):
    def test_manager_create(self):
        t = PrivateUrl.create('test', expire=datetime.timedelta(days=5))
        self.assertIsInstance(t, PrivateUrl)
        self.assertIsNotNone(t.pk)
        with self.assertRaises(RuntimeError):
            for i in xrange(100):
                PrivateUrl.create('test', token_size=1)

    def test_manager_create_with_replace(self):
        PrivateUrl.create('test', replace=True)
        PrivateUrl.create('test', replace=True)
        self.assertEqual(PrivateUrl.objects.filter(action='test').count(), 2)
        user = get_user_model().objects.create(username='test', email='test@mail.com', password='test')
        PrivateUrl.create('test', user=user, replace=True)
        PrivateUrl.create('test', user=user, replace=True)
        self.assertEqual(PrivateUrl.objects.filter(action='test', user=user).count(), 1)

    def test_token_size(self):
        t = PrivateUrl.create('test', token_size=50)
        self.assertEqual(len(t.token), 50)
        for i in xrange(100):
            t = PrivateUrl.create('test', token_size=(40, 64))
            self.assertTrue(40 <= len(t.token) <= 64)
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=0)
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=-1)
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=(0, 0))
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=(40, 65))
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=(60, 40))
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=(-1, 40))
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=(-2, -1))
        self.assertRaises(AssertionError, PrivateUrl.create, 'test', token_size=(40, 40))

    def test_data(self):
        d = {'k': ['v']}
        t = PrivateUrl.create('test', data=d)
        self.assertIsNot(t.data, d)
        self.assertIsNot(t.data['k'], d['k'])

    def test_manager_get_or_none(self):
        t = PrivateUrl.create('test')
        j = PrivateUrl.objects.get_or_none(t.action, t.token)
        self.assertIsInstance(j, PrivateUrl)
        self.assertEqual(t.pk, j.pk)
        n = PrivateUrl.objects.get_or_none('none', 'none')
        self.assertIsNone(n)

    def test_get_absolute_url(self):
        t = PrivateUrl.create('test')
        url = reverse('dju_privateurl', kwargs={'action': t.action, 'token': t.token})
        self.assertEqual(t.get_absolute_url(), url)
        self.assertEqual(resolve_url(t), url)

    def test_is_available(self):
        t = PrivateUrl.create('test')
        self.assertTrue(t.is_available())
        t.used_limit = 1
        t.used_counter = 1
        self.assertFalse(t.is_available())
        t.used_limit = 0
        self.assertTrue(t.is_available())
        t.expire = datetime.datetime(2015, 10, 10, 10, 10, 10)
        self.assertTrue(t.is_available(dt=datetime.datetime(2015, 10, 10, 10, 10, 9)))
        self.assertFalse(t.is_available(dt=datetime.datetime(2015, 10, 10, 10, 10, 11)))

    def test_used_counter_inc(self):
        t = PrivateUrl.create('test')
        t.used_counter_inc()
        self.assertEqual(t.used_counter, 1)
        self.assertIsNotNone(t.first_used)
        self.assertIsNotNone(t.last_used)
        self.assertEqual(t.first_used, t.last_used)
        self.assertIsNotNone(t.pk)
        t.used_counter_inc()
        self.assertEqual(t.used_counter, 2)
        j = PrivateUrl.create('test', auto_delete=True)
        j.used_counter_inc()
        self.assertIsNone(j.pk)

    def test_long_action_name_fail(self):
        action = 'a' * 32
        a = PrivateUrl.create(action)
        b = PrivateUrl.objects.get(action=action)
        self.assertEqual(a, b)
        self.assertEqual(len(b.action), len(action))

    def test_reverse(self):
        a = PrivateUrl.create('a' * 32)
        try:
            a.get_absolute_url()
        except NoReverseMatch, e:
            raise self.failureException('Private url reverse url error ({}).'.format(e))


class TestPrivateUrlView(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestPrivateUrlView, cls).setUpClass()

        @receiver(privateurl_ok, weak=False, dispatch_uid='ok')
        def ok(request, obj, action, **kwargs):
            if action == 'test':
                return {'response': HttpResponse('ok')}

        @receiver(privateurl_fail, weak=False, dispatch_uid='fail')
        def fail(request, obj, action, **kwargs):
            if action == 'test':
                return {'response': HttpResponse('fail')}

    @classmethod
    def tearDownClass(cls):
        super(TestPrivateUrlView, cls).tearDownClass()
        privateurl_ok.disconnect(dispatch_uid='ok')
        privateurl_fail.disconnect(dispatch_uid='fail')

    def test_receivers(self):
        t = PrivateUrl.create('test')
        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'ok')
        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'fail')
        t.action = 'none'
        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_receivers2(self):
        t = PrivateUrl.create('test2')
        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 302)
        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 404)


class TestPrivateUrlAdmin(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestPrivateUrlAdmin, cls).setUpClass()
        PrivateUrl.create('test')
        get_user_model().objects.create_superuser('admin', 'admin@site.com', 'admin')

    def setUp(self):
        self.client.login(username='admin', password='admin')

    def tearDown(self):
        self.client.logout()

    def test_admin_list(self):
        response = self.client.get(resolve_url('admin:dju_privateurl_privateurl_changelist'))
        self.assertEqual(response.status_code, 200)
