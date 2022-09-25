from os.path import exists, realpath, dirname
from configparser import ConfigParser
from datetime import datetime
import urllib.parse
import subprocess
import requests
import json

d = realpath(dirname(__file__))
config = ConfigParser()
config_name = f"{d}/gog.ini"
login_name = f"{d}/goglogin"
cache_name = f"{d}/games.json"

# these are used by Gog in a few places
client_id='46899977096215655'
client_secret='9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9'
redirect_url='https://embed.gog.com/on_login_success?origin=client'

if exists(config_name):
  config.read(config_name)

cache = {}
if exists(cache_name):
  with open(cache_name, 'r') as jsonfile:
    cache = json.load(jsonfile)

# show login screen, get initial tokens
# requires goglogin: https://github.com/notnullgames/goglogin
def login():
  # TODO: download & extract goglogin
  code = subprocess.run(login_name, stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
  return json.loads(requests.get(f'https://auth.gog.com/token?client_id={client_id}&client_secret={client_secret}&grant_type=authorization_code&code={code}&redirect_uri={urllib.parse.quote(redirect_url)}').text)

# get fresh token with a refresh token
def refresh(refresh_token):
  return json.loads(requests.get(f'https://auth.gog.com/token?client_id={client_id}&client_secret={client_secret}&grant_type=refresh_token&refresh_token={refresh_token}').text)

# get list of owned game IDs
def owned(access_token):
  return json.loads(requests.get(f'https://embed.gog.com/user/data/games', headers={'Authorization': f'Bearer {access_token}'}).text)['owned']

# get details about game ID
def details(access_token, id):
  try:
    return cache[str(id)]
  except:
    print(f"no cache: {id}")
    cache[id] = json.loads(requests.get(f'https://embed.gog.com/account/gameDetails/{id}.json', headers={'Authorization': f'Bearer {access_token}'}).text)
    with open(cache_name, 'w') as jsonfile:
      json.dump(cache, jsonfile)
    return cache[id]

# wrapper around token collection & loading/saving
def get_token():
  try:
    if datetime.now().timestamp() < float(config["Auth"]["expires"]):
      return config["Auth"]["access_token"]
    else:
      r = refresh(config["Auth"]["refresh_token"])
      config["Auth"]["expires"] = str(r["expires_in"] + datetime.now().timestamp())
      config["Auth"]["refresh_token"] = r["refresh_token"]
      config["Auth"]["access_token"] = r["access_token"]
      with open(config_name, 'w') as configfile:
        config.write(configfile)
      return config["Auth"]["access_token"]
  except:
    r = login()
    config["Auth"]["expires"] = str(r["expires_in"] + datetime.now().timestamp())
    config["Auth"]["refresh_token"] = r["refresh_token"]
    config["Auth"]["access_token"] = r["access_token"]
    with open(config_name, 'w') as configfile:
      config.write(configfile)
    return config["Auth"]["access_token"]


class Plugin:
  # get full info for current games
  # can be called from JavaScript using call_plugin_function("token")
  async def games(self):
    token = get_token()
    games = {}
    for game_id in owned(token):
      games[game_id] = details(token, game_id)
    return games

  # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
  async def _main(self):
    pass
