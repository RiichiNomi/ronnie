import dotenv
import os
import requests
import urllib.parse

from bs4 import BeautifulSoup

def get_log(logid):
    dotenv.load_dotenv('variables.env')

    base_url = os.environ.get('TENHOU_XML_LOG_BASE_URL')
    user_agent = os.environ.get('USER_AGENT')

    headers = {'User-Agent': user_agent}

    r = requests.get(base_url + logid, headers=headers)

    return r.text

def parse(log):
    return BeautifulSoup(log, features='lxml')

def get_players(parsed):
    players = [parsed.find('un')['n%d' % i] for i in range(0, 4)]

    return [urllib.parse.unquote(p) for p in players]

def get_final_scores(parsed):
    all_agari = parsed.findAll('agari')

    last = len(all_agari)-1

    scores = all_agari[last]['owari'].split(',')

    return scores