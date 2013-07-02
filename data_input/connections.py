import os, urllib2, logging
from lxml import etree
import constants

log = logging.getLogger(__name__)

class EventorConnection(object):
    def __init__(self):
        self.baseurl = 'https://eventor.orientering.se/api'
        self.apikey = constants.API_KEY
    
    def get_request(self):
        url = os.path.join(self.baseurl, self.apicall)
        request = urllib2.Request(url, headers={'ApiKey': self.apikey} )
        xml = urllib2.urlopen(request).read()
        return etree.fromstring(xml)

    def download(self):
        try:
            results = self.get_request()
        except urllib2.HTTPError, e:
            # FIXME figure out when error occurs
            # FIXME respect 404, 500, 403, 401, etc, in e.code
            print 'Error occurred in communication with eventor server'
            print e
            return None
        else:
            return results
    
    def download_all_members(self, orgnr):
        self.apicall = 'persons/organisations/{0}?includeContactDetails=true'.format(orgnr)
        return self.download()
    
    def download_competition_data(self, eventor_id): 
        self.apicall = 'competitor/{0}'.format(eventor_id)
        return self.download()

    def download_results(self, person, events=None, days=None):
        # set self.apicall here
        url = 'results/person?personId={0}&top=500&includeSplitTimes=true'.format(person.eventorID)
        
        if days is not None:
            # Specify whether to get all results or the ones from a certain date
            now = datetime.datetime.now()
            fromdate = now - datetime.timedelta(days)
            url = '{0}&fromDate={1}-{2}-{3}'.format(url, str(fromdate.year),
                    str(fromdate.month).zfill(2), str(fromdate.day).zfill(2) )

        elif events is not None:
            url = '{0}&eventIds={1}'.format(url, ','.join(events))
        
        self.apicall = url
        return self.download()
