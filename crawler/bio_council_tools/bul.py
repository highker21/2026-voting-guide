import urllib.parse
def burl(year,city_dir,fname):
    return 'https://bulletin.cec.gov.tw/'+urllib.parse.quote(f'01選舉公報/05直轄市議員/{year}年/{city_dir}/{fname}')
