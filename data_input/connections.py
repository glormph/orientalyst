import os, urllib2, logging, datetime
from lxml import etree
import constants

logger = logging.getLogger(__name__)

class EventorConnection(object):
    def __init__(self):
        self.baseurl = 'https://eventor.orientering.se/api'
        self.apikey = constants.API_KEY
    
    def download(self):
        url = os.path.join(self.baseurl, self.apicall)
        request = urllib2.Request(url, headers={'ApiKey': self.apikey} )
        xml = urllib2.urlopen(request).read()
        return etree.fromstring(xml)

    def download_all_members(self, orgnr):
        self.apicall = 'persons/organisations/{0}?includeContactDetails=true'.format(orgnr)
        return self.download()
    
    def download_competition_data(self, eventor_id): 
        self.apicall = 'competitor/{0}'.format(eventor_id)
        return self.download()
    
    def download_events(self, eventorID, fromdate=None, todate=None):
        url = 'results/person?personId={0}'.format(eventorID)
        if fromdate is not None:
            url = '{0}&fromDate={1}-{2}-{3}'.format(url, str(fromdate.year),
                    str(fromdate.month).zfill(2), str(fromdate.day).zfill(2) )
        if todate is not None:
            url = '{0}&toDate={1}-{2}-{3}'.format(url, str(todate.year),
                    str(todate.month).zfill(2), str(todate.day).zfill(2) )
        self.apicall = url
        return self.download()

    def download_results(self, eventorID):
        # set self.apicall here
        logger.debug('Downloading results for event {0}'.format(eventorID))
        url = \
        'results/event?eventId={0}&includeSplitTimes=true'.format(eventorID)
        self.apicall = url
        return self.download()
