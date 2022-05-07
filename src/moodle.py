import requests
import re
from datetime import datetime
import logging


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CredentialsInvalid(Exception):
    """
     An exception class that is raised when the credentials are invalid.

     Attributes
     ----------
     message : str
       Error message string.

     Methods
     -------
     __str__:
       Overwrites str() to return error message string.
     """

    def __init__(self, message, *args, **kwargs):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """
        Overwrites str() to return error message string.

        Returns
        -------
        self.message : Error message string
        """
        return self.message


class Moodle:
    def __init__(self, credentials):
        self.credentials = credentials
        self.lms_url = "https://lms2.apiit.edu.my/lib/ajax/service.php"
        self.headers = {
            'sec-ch-ua': '\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"101\", \"Microsoft Edge\";v=\"101\"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': "Windows",
            'Origin': 'https://cas.apiit.edu.my',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32" ',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://cas.apiit.edu.my/cas/login',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-TW;q=0.7,zh;q=0.6'
        }
        self.sess_key, self.session = self.login()

    def url_builder(self, core):
        return f'{self.lms_url}?sesskey={self.sess_key}&info={core}'

    def login(self):
        login_url = "https://cas.apiit.edu.my/cas/login"
        session = requests.session()
        payload = {
            'username': self.credentials['username'],
            'password': self.credentials['password'],
            'rememberMe': 'true',
            'execution': '2907bd9b-7941-4cf6-8b21-825f1f1a2a05_ZXlKaGJHY2lPaUpJVXpVeE1pSjkuai94V1VPVkl3L2IxZkVXcmIrdlhs'
                         'Yk1Tc0ZxRkxWc0lSMnQzZWhWK0N2SEZDUGZYOS9LbzhLM1pqVml4WlRZRVIyQk1hVUYycitmUnNMK05oL1NpZmhpZzgzV'
                         '1BPdE9VdXRwWDlscWlSMWc3N1hNV005RnZEbUtRZU1PaC9HbXlBRDBQQW90SlRmVklrQ0JxemFIcDdJTGF3cUVnS2tON1'
                         'd0a2lSYnB0cll2VG5LcDRRMEtQN2RCZEh0MW9ic21nU2szUlY4eUp4YjkzUTZKNWI1NVFzNERoemx3MEdRY2pIS2VkeG0'
                         '2bUhPRkNlSTlTSGUxU3BOdnpTdkhUTklSMHVqd0lnNzBLdXBua09ZaTViZVAwcDNMMTZUS0dIeWU2cDhVeUMrK0QwelND'
                         'N3VyNjdTeHA0b01rTVhyUnVEWlVTVEZ4N0dyc2hYNGVSMWFFZGlkeWpiRVF4K3BSenlrR3YxM2N5QnFTaWhYUkpkY3lFM'
                         'jBSMlIzbmptT1Jaek4wYldpVVEvTEJlNmdqNDFTYWFUOW1MTnVvUmUveXJOK1FDd2VvbFZqQ1FLZExaY2Y3b1NxaDVBcV'
                         'ptMEZwdXN0TVJwNDdsemxZKzZFL1haV2VOVGxEZ3pFOTNCMXlGS3prb1pTNy8vTUFPY3pOZFM4SWxYRHhreW96R1EvSHR'
                         'EeUdZMithUDRyeVBIUGRnWHJRK0dEcVhualF3UlZJQld0dGdOQkVBRmRsUzRtQ0JUM21oNzBHQk54MURJcGZzWGFVMWg1'
                         'QVkza1hkMG43NHB0dE16c3BrbXpDZXhSSFp2WWJTQzIzTUUwbG5ZOU05NXVCaUs2RExFZ1VUMXVJRFNQMnVUOEhxRlNBV'
                         '0hDcURZQ3h0REFuSmxuUEYwdE5MaHNNOHJvcDFqVkIzSFowajBWcGVVWW9FSnJxa2hlNFNUc1kyeFBtNU4xV1BGeUE3SW'
                         'toYmtlWmxuTmVrQTNqZDVVb0ZuOWsxWjh1WU0xTTVGV2FvRGl6MXFGRXJLZHdWK0licDBSSEozZVFGdzU1S3JDY1hvZkE'
                         'vMkxleEFXL2V0S3VLb2dPa1haMzhKV3FleUpJblV2TUVQWXVFbUdVSmRLU3pibVQ2KzJSVExlV3A3N1hJOThJeXVjek8y'
                         'LzZjZHdxSFN6QnNWdytrT0UyeTBMQTlhK2hHNTEvRXgydHhvbkhRT0VVdVJZL1MwcnR5QW9IbWZudUUrZ0VoTndTdDltL'
                         '09wTGdjck85emczWjJBTytRNWV6bVhDT3Z4amZiS25VQ2pzQnY3cTl2aFU4YjdHZy8xMCtleXg4d1lNNFNnbGhIRnd6ZX'
                         'p3OFZ3cUFVUW84WFE4cldqei94UGFGWlVObGh2MHprRktsdXJNSkdkSEtPY29aNHNvT0hpdnBybGJMTlpPajkzNDZpVjQ'
                         '5aFNJa2c2VVJ1T1hUZkdlZHhkNlJncFIvMVRXQlhkbWJ4dXJFMER4aytmMm81azVyWjZ3dnJZQ29sYzRmYWVrPS44dDM5'
                         'NUJ2NHVoSExLb1B0X0otRDJ1TlRia2t0aGFxYXBjbTh6Mkl5WnJrNndsYXRJdU9ZOXFaQkQ1NDlJcUtfSXlQUEQ0Undpd'
                         'jZWZlJyOUJJdzFBQQ==',
            '_eventId': 'submit',
            'geolocation': ''
        }
        response = session.post(login_url, headers = self.headers, data = payload)
        if response.status_code == '200' or 200:
            logger.info("Logged in to Moodle!")
            sess_key = re.search(r'sesskey":"(.*?)"', response.text).group(1)
            return sess_key, session
        elif response.status_code == '400' or 400:
            logger.critical("400 Bad Request: Malformed request!")
        elif response.status_code == '401' or 401:
            # Must catch this error
            logger.error("Moodle credentials invalid!")
            raise CredentialsInvalid

    def get_events(self):
        url = self.url_builder("core_calendar_get_action_events_by_timesort")
        payload = [
            {
                "index": 0,
                "methodname": "core_calendar_get_action_events_by_timesort",
                "args": {
                    "limitnum": 26,
                    "timesortfrom": int(datetime.now().timestamp()),
                    "limittononsuspendedevents": True
                }
            }
        ]

        events = self.session.post(url, json = payload, headers = self.headers).json()
        if not events[0]['error']:
            logger.debug("Request for events successful!")
            return events[0]['data']['events']
        else:
            # Must catch this exception
            logger.error("HTTP Error")
            raise requests.HTTPError(events[0]['exception']['message'])


if __name__ == "__main__":
    pass