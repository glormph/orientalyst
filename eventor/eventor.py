import os, urllib2, logging
from lxml import etree

log = logging.getLogger(__name__)

def eventorAPICall(apikey, lookup):
    baseUrl = 'https://eventor.orientering.se/api'
        
    url = os.path.join(baseUrl, lookup)
    print url
    request = urllib2.Request(url, headers={'ApiKey': apikey} )
    xml = urllib2.urlopen(request).read()
    return etree.fromstring(xml)
