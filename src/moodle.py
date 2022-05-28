import json
import re
from datetime import datetime
import logging
import aiohttp
import aiohttp.web
import asyncio
from bs4 import BeautifulSoup, SoupStrainer


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


class Submission:
    context_id: str
    item_id: str
    client_id: str


class Moodle:
    def __init__(self):
        self.lms_url = "https://lms2.apiit.edu.my/"
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
        self.sess_key = None
        self.user_id = None
        self.session = aiohttp.ClientSession()

    def lms_url_builder(self, service_path, query):
        query_string = []
        for key in query.keys():
            query_string.append(
                f'{key}={query[key]}'
            )
        return f'{self.lms_url}{service_path}?{"&".join(query_string)}'

    async def login(self, credentials):
        login_url = "https://cas.apiit.edu.my/cas/login"
        payload = {
            'username': credentials['username'],
            'password': credentials['password'],
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
        response = await self.session.post(login_url, data = payload, headers = self.headers)
        if response.status == 200:
            logger.info("Logged in to Moodle!")
            self.sess_key = re.search(r'sesskey":"(.*?)"', await response.text()).group(1)
        elif response.status == 400:
            logger.critical("400 Bad Request: Malformed request!")
        elif response.status == 401:
            # Must catch this error
            logger.error("Moodle credentials invalid!")
            raise CredentialsInvalid

    async def get_events(self):
        url = self.lms_url_builder("lib/ajax/service.php",
                                   {
                                       'sesskey': self.sess_key,
                                       'core': "core_calendar_get_action_events_by_timesort"
                                   })
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

        response = await self.session.post(url, json = payload, headers = self.headers)
        events = await response.json()
        if not events[0]['error']:
            logger.debug("Request for events successful!")
            return events[0]['data']['events']
        else:
            # Must catch this exception
            logger.error("HTTP Error")
            raise aiohttp.web.HTTPError(reason = "Something went wrong", text = events[0]['exception']['message'])

    async def check_plagiarism(self, file_content, file_name):
        pre_check = await self.edit_submission()
        if pre_check is None:
            return
        file_id = await self.upload_file(file_content, file_name, pre_check)
        payload = {
            'lastmodified': datetime.now().timestamp(),
            'id': '113679',
            'userid': self.user_id,
            'action': 'savesubmission',
            'sesskey': self.sess_key,
            '_qf__mod_assign_submission_form': '1',
            'submissionstatement': '1',
            'files_filemanager': file_id,
            'submitbutton': 'Save changes'
        }
        logger.info("Attemping submission...")
        url = self.lms_url_builder('mod/assign/view.php', {})
        response = await self.session.post(url, data = payload, allow_redirects = False)
        check_url = response.headers['Location']
        while True:
            logger.info("Waiting for 2 minutes before checking plagiarism...")
            await asyncio.sleep(120)
            response = await self.session.get(check_url)
            response_html = await response.text()
            soup = BeautifulSoup(response_html, "lxml", parse_only = SoupStrainer('td', {'class': 'cell c1 lastcol'}))
            result = soup.find('div', {'class': 'tii_links_container'}).findAll('div', recursive = True)[1].getText()
            if result is not None:
                return result

    async def upload_file(self, file_content, file_name, submission_info):
        multipart_data = {
            'sesskey': self.sess_key,
            'repo_id': '4',
            'itemid': submission_info.item_id,
            'author': 'ANG RU XIAN .',
            'savepath': '/',
            'title': file_name,
            'overwrite': '1',
            'ctx_id': submission_info.context_id
        }
        payload = aiohttp.FormData()
        for key, value in multipart_data.items():
            payload.add_field(key, value)
        payload.add_field(name = 'repo_upload_file', value = file_content, filename = file_name,
                          content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response = await self.session.post('https://lms2.apiit.edu.my/repository/repository_ajax.php?action=upload',
                                           data = payload)
        response_json = json.loads(await response.text())
        return response_json['id']

    async def edit_submission(self):
        url = self.lms_url_builder("mod/assign/view.php",
                                   {
                                       'id': '113679',
                                       'action': 'editsubmission'
                                   })
        response = await self.session.get(url)
        logger.info("Getting submission info...")
        response_text = await response.text()
        submission_info = Submission()
        submission_info.context_id = re.search(r'contextid":(.*?),', response_text).group(1)
        submission_info.item_id = re.search(r'itemid":(.*?),', response_text).group(1)
        filecount = int(re.search(r'filecount":(.*?),', response_text).group(1))
        submission_info.client_id = re.search(r'client_id":"(.*?)"', response_text).group(1)
        soup = BeautifulSoup(response_text, "lxml")
        self.user_id = soup.find("input", type = "hidden", attrs = {"name": "userid"}).get("value")
        if filecount > 0:
            logger.info("There are existing files in the repo! Removing them before new submission...")
            return await self.remove_submission(113679)
        elif (submission_info.context_id and submission_info.item_id and submission_info.client_id and self.user_id):
            logger.info("Submission info parsing complete!")
            return submission_info
        return None

    async def remove_submission(self, page_id):
        url = self.lms_url_builder("mod/assign/view.php", {})
        check_url = self.lms_url_builder("mod/assign/view.php",
                                         {
                                             'id': page_id,
                                             'action': 'view'
                                         })

        payload = {
            'id': page_id,
            'action': 'removesubmission',
            'userid': self.user_id,
            'sesskey': self.sess_key
        }
        response = await self.session.post(url, data = payload, allow_redirects = False)
        if response.headers['Location'] == check_url:
            logger.info("Existing submission removed!")
            return await self.edit_submission()
        return False
        

async def main():
    try:
        moodle_session = Moodle()
        await moodle_session.login({'username': 'TP062253', 'password': '2TRY!vK6JTCF'})
        with open('1.pdf', 'rb') as f:
            text = f.read()
        print(await moodle_session.check_plagiarism(text, '1.pdf'))
        # with open('Part B.docx', 'rb') as f:
        #     print(await moodle_session.check_plagiarism(f, 'Part B.docx'))
    except Exception as e:
        logging.exception(e)
    finally:
        await moodle_session.session.close()


if __name__ == "__main__":
    formatter = logging.Formatter('%(asctime)s : %(name)s : %(levelname)s : %(message)s',
                                  datefmt = '%m/%d/%Y %I:%M:%S %p')
    stream_logger = logging.StreamHandler()
    stream_logger.setFormatter(formatter)
    logger.addHandler(stream_logger)
    logger.setLevel(level = logging.DEBUG)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())