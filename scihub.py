from bs4 import BeautifulSoup
import requests
import re
import lxml
import io

class SciHub():
  def __init__(self, doi):
    self.doi = doi
    # Regex for parsing DOI Number
    self.doi_regex = re.compile(r'10.\d{4,9}/[-._;()/:a-z0-9A-Z]+')

  def check_doi_format(self):
    return self.doi_regex.search(self.doi)
  
  def search_sci_hub(self):
    sess = requests.Session()
    headers = {
      'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }
    try:
      sci_hub = "https://sci-hub.hkvisa.net/" + self.doi
      html = sess.get(sci_hub, headers = headers).text
      soup = BeautifulSoup(html, 'lxml')
      link = soup.find_all('iframe')
      if not link:
          link = soup.find_all("embed", type="application/pdf")
      unparsed_title = soup.find("div", id = "citation", onclick = "clip(this)")      # Get title of Journal
      title_pattern = re.compile(r'(<i>)([a-zA-Z0-9\s.-:-]+)([.])')
      unformatted_title = title_pattern.search(str(unparsed_title)).group(2)
      if not unformatted_title:
          fname = self.fix_string(self.doi) + ".pdf"
      else:
          fname = self.fix_string(unformatted_title) + ".pdf"
      pdf = sess.get(link[0]['src'], headers = headers) 
      return io.BytesIO(pdf.content), fname
    # Journal article not available in Sci Hub database
    except IndexError as e:     
        print("Link not found!")

  # Remove invalid characters from file name
  def fix_string(self, string):
    special_char = re.compile(r'[~#%&*{}\\:<>?/+=|]')
    return re.sub(special_char, "_", string)
