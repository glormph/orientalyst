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
    
    def download_competition_data(self):
        self.apicall = 'competitors?organisationId={0}'.format(constants.ORGANISATION_ID)
        return self.download()
    
    def download_events(self, eventorID, fromdate=None, todate=None):
        url = 'results/person?personId={0}'.format(eventorID)
        now = datetime.datetime.now()

        if fromdate is not None:
            frd = '{0}-{1}-{2}'.format( str(fromdate.year),
                    str(fromdate.month).zfill(2), str(fromdate.day).zfill(2))
            td = '{0}-{1}-{2}'.format( str(now.year), str(now.month).zfill(2),
                        str(now.day).zfill(2))
            url = '{0}&fromDate={1}&toDate={2}'.format(url, frd, td)
        if todate is not None:
            url = '{0}&toDate={1}-{2}-{3}'.format(url, str(todate.year),
                    str(todate.month).zfill(2), str(todate.day).zfill(2) )
        self.apicall = url
        return self.download()

    def download_results(self, personid, eventid):
        self.apicall = 'results/person?personId={0}&eventIds={1}&' \
              'includeSplitTimes=true&top=10000'.format(personid, eventid)
        return self.download()

