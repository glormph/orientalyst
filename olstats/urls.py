from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^login/', 'django.contrib.auth.views.login'),
    url(r'^logout/', 'django.contrib.auth.views.logout'),
    url(r'^admin/', include(admin.site.urls)),
    )

urlpatterns += patterns('race.views',
    url(r'^race/$', 'index'),
    
    # Examples:
    # url(r'^$', 'olstats.views.home', name='home'),
    # url(r'^olstats/', include('olstats.foo.urls')),
)

urlpatterns += patterns('graphs.views',
        #url(r'^$', 'index'), # or login page?
        url(r'^graph/$', 'home'),
        url(r'^graph/(?P<race_id>\d+)/$', 'race'),
        url(r'^graph/(?P<race_ids>(?:\d+/)+)integrate', 'multirace'), # FIXME how to pass list?
        url(r'^graph/dates/(?P<fromdate>\d+)/(?P<todate>\d+)/$', 'period'),

)
