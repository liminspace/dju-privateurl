from django.conf.urls import url
from . import views


urlpatterns = [
    url(
        r'^(?P<action>[-a-zA-Z0-9_]{1,32})/(?P<token>[-a-zA-Z0-9_]{1,64})$',
        views.privateurl_view,
        name='dju_privateurl'
    ),
]
