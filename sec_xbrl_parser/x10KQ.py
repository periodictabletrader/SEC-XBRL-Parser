import datetime
import requests
from bs4 import BeautifulSoup
from .enum import XBRLEnum
from .constants import REQ_HEADERS


class XBRL10KQParser(object):

    def __init__(self, cik, filing_type=XBRLEnum.X10K.value, limit=None, dateb=None):
        self.cik = cik
        self.limit = limit
        self.dateb = self._parse_date(dateb)
        filings_url_params = {
            'action': XBRLEnum.COMPANY.value,
            'CIK': self.cik,
            'type': filing_type
        }
        self.filings_response = requests.get(self.browse_url, params=filings_url_params, headers=REQ_HEADERS)
        self.xbrl_urls = self.get_xbrl_urls(self.filings_response.text)

    @property
    def browse_url(self):
        return 'https://www.sec.gov/cgi-bin/browse-edgar'

    @property
    def url(self):
        return 'https://www.sec.gov'

    @classmethod
    def _parse_date(cls, eff_date):
        if isinstance(eff_date, datetime.datetime):
            eff_date = eff_date.date()
        elif isinstance(eff_date, datetime.date):
            pass
        elif isinstance(eff_date, str):
            eff_date = datetime.datetime.strptime(eff_date, '%Y%m%d')
            eff_date = eff_date.date()
        elif eff_date is None:
            eff_date = datetime.date.today()
        return eff_date

    def get_xbrl_urls(self, edgar_str):
        soup = BeautifulSoup(edgar_str, 'html.parser')
        link_tags = soup.find_all('a', id='documentsbutton')
        doc_links = [f'{self.url}{link_tag["href"]}' for link_tag in link_tags]
        xbrl_links = []
        for link in doc_links:
            doc_resp = requests.get(link)
            if doc_resp.status_code == 200:
                doc_str = doc_resp.text
                soup = BeautifulSoup(doc_str, 'html.parser')
                amend_label = soup.find('div', id='formName')
                if amend_label and '[amend]' in amend_label.text.lower():
                    # Skip amended filings for now as I'm unsure of how to parse them
                    continue
                table_tag = soup.find('table', class_='tableFile', summary='Data Files')
                if table_tag:
                    # If this table_tag doesn't exist, then it's likely the old style SEC filing so ignore these for now
                    rows = table_tag.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) > 3:
                            if 'XBRL INSTANCE DOCUMENT' in cells[1].text:
                                xbrl_links.append('https://www.sec.gov' + cells[2].a['href'])
        return xbrl_links
