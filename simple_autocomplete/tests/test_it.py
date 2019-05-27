import pickle
import sys

from django import forms
from django.core.handlers.wsgi import WSGIRequest
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.conf import settings
from django.urls import reverse

from simple_autocomplete.views import convert_searchtext_to_regex
from simple_autocomplete.widgets import AutoCompleteWidget
from simple_autocomplete.monkey import _simple_autocomplete_queryset_cache
from simple_autocomplete.tests.models import DummyModel


class EditDummyForm(forms.ModelForm):

    class Meta:
        model = DummyModel
        fields = '__all__'


class TestItCase(TestCase):

    def setUp(self):
        self.adam = User.objects.create_user(
            'adam sebastian baker', 'adam@foo.com', 'password'
        )
        self.eve = User.objects.create_user('eve', 'eve@foo.com', 'password')
        self.andre = User.objects.create_user(
            'andré', 'andre@foo.com', 'password'
        )

        self.dummy = DummyModel()
        self.dummy.save()
        self.client = Client()
        self.request = RequestFactory()

    def test_monkey(self):
        # Are we using the autocomplete widget?
        form = EditDummyForm(self.request, instance=self.dummy)
        self.failUnless(
            isinstance(form.fields['user'].widget, AutoCompleteWidget)
        )

    def test_regex_converter(self):
        result = convert_searchtext_to_regex('as baker')
        self.assertEqual(result, '''(a).*(s).*( ).*(b).*(a).*(k).*(e).*(r).*''')
        
    def check_match(self, token, query, expected_match):
        url = reverse('simple-autocomplete', args=[token])
        response = self.client.get(url, {'q': query})
        self.assertEqual(response.status_code, 200)
        if (not expected_match):
            self.assertEqual(response.content.decode("utf-8"), "[]")
        else:
            self.assertEqual(response.content.decode("utf-8"), f"[[1, \"{expected_match}\"]]")

    def test_json(self):
        # Find our token in cache
        for token, pickled in _simple_autocomplete_queryset_cache.items():
            app_label, model_name, dc = pickle.loads(pickled)
            if (app_label == 'auth') and (model_name == 'user'):
                break
        self.check_match(token, 'ada', 'adam sebastian baker')
        self.check_match(token, 'axs', '')
        self.check_match(token, 'bastia', 'adam sebastian baker')
        self.check_match(token, 'as baker', 'adam sebastian baker')
        
    def dont_test_unicode(self):
        # Find our token in cache
        for token, pickled in _simple_autocomplete_queryset_cache.items():
            app_label, model_name, dc = pickle.loads(pickled)
            if (app_label == 'auth') and (model_name == 'user'):
                break

        url = reverse('simple-autocomplete', args=[token])
        response = self.client.get(url, {'q': 'andr'})
        self.assertEqual(response.status_code, 200)
        if sys.version_info[0] > 2:
            self.assertEqual(response.content.decode("utf-8"), """[[3, "andr\\u00e9"]]""")
        else:
            self.assertEqual(response.content.decode("utf-8"), """[[3, "andr\u00e9"]]""")
