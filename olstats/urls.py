from django.conf.urls import patterns, include, url
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/logout/', 'django.contrib.auth.views.logout',
        {'next_page': '/'}),
    url(r'^accounts/login/', 'django.contrib.auth.views.login'),
    url(r'^accounts/signup/', 'accounts.views.signup'),
    )

urlpatterns += patterns('graphs.views',
        url(r'^$', 'home'),
        url(r'^race/(?P<race_id>\d+)/$', 'race'),
        url(r'^races/', 'userraces'),
        url(r'^about/', 'about'),
        
        url(r'^profile/', 'my_profile'),
        url(r'^urllogin/(?P<random_id>\w+)/', 'urllogin'),
        )

# oversee this stuff, we will not use the password reset stuff as we planned
# to, but maybe in the normal way
urlpatterns += patterns('',
        url(r'^user/password_reset/$', 'django.contrib.auth.views.password_reset', 
            {'post_reset_redirect' : '/user/password_reset/done/'}, name="password_reset"),
        url(r'^user/password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
        
        url(r'^user/password_reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 
              'django.contrib.auth.views.password_reset_confirm',
              {'post_reset_redirect' : '/user/password/done/'}),
        url(r'^user/password/done/$', 'django.contrib.auth.views.password_reset_complete'),
)

