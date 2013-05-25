from django.conf.urls import patterns, include, url
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^login/', 'django.contrib.auth.views.login'),
    url(r'^logout/', 'django.contrib.auth.views.logout'),
    url(r'^admin/', include(admin.site.urls)),
    )

urlpatterns += patterns('graphs.views',
        url(r'^$', 'home'),
        url(r'^race/(?P<race_id>\d+)/$', 'race'),
        url(r'^races/', 'userraces'),
        url(r'^about/', 'about'),
        
        url(r'^profile/', 'my_profile'),
        url(r'^urllogin/(?P<random_id>\w+)/', 'urllogin'),
        )

urlpatterns += patterns('',
        url(r'^user/password/reset/$', 'django.contrib.auth.views.password_reset', 
        {'post_reset_redirect' : '/user/password/reset/done/'}, name="password_reset"),
        url(r'^user/password/reset/done/$', 'django.contrib.auth.views.password_reset_done'),
        url(r'^user/password/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 
              'django.contrib.auth.views.password_reset_confirm', {'post_reset_redirect' : '/user/password/done/'}),
        url(r'^user/password/done/$', 'django.contrib.auth.views.password_reset_complete'),
        #url(r'^graph/(?P<race_ids>(?:\d+/)+)integrate', 'multirace'), # FIXME how to pass list?
        #url(r'^graph/dates/(?P<fromdate>\d+)/(?P<todate>\d+)/$', 'period'),

)
