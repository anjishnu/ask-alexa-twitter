import requests
from requests_oauthlib import OAuth1
from urllib.parse import parse_qs
import cherrypy 
from collections import defaultdict 
import json
import os
import re

#Try to load twitter conifg path
twitter_config_path = os.path.realpath("keys/twitter_keys.json")
if os.path.exists(twitter_config_path):
    with open(twitter_config_path) as config_file:
        twitter_config = json.load(config_file)
    consumer_key = twitter_config["consumer_key"]
    consumer_secret = twitter_config["consumer_secret"]
else:
    raise Exception("Twitter config not found! at "+ twitter_config_path)


#Local cache caches tokens for different users 
local_cache = { "request_token" : defaultdict(),
                "request_secret": defaultdict(),
                "access_token"  : defaultdict(),
                "access_secret" : defaultdict(),
                "twitter_user_id" : defaultdict(),
                "screen_name"   : defaultdict()}

def get_cached_access_pair(user_id):
    if user_id in local_cache['access_token'] and user_id in local_cache['access_secret']:
        return local_cache['access_token'][user_id], local_cache['access_secret'][user_id]
        

def get_request_token(user_id="something", callback_url=None):
    url = "https://api.twitter.com/oauth/request_token"
    auth = OAuth1(consumer_key, consumer_secret)
    params = { "oauth_callback" : callback_url } 
    r = requests.post(url, auth=auth, params=params)
    response_obj = parse_qs(r.text)    
    local_cache["request_token"][user_id] = response_obj['oauth_token'][0]
    local_cache['request_secret'][user_id] = response_obj['oauth_token_secret'][0]    
    return response_obj['oauth_token_secret'], response_obj['oauth_token']
    

def authenticate_user_page(user_id="something", callback_url=""):
    url = "https://api.twitter.com/oauth/authenticate"
    oauth_secret, oauth_token = get_request_token(user_id, callback_url)
    params = { "force_login" : True,
               "oauth_token": oauth_token }
    r = requests.get(url, params=params)
    return r.text
    

def post_tweet(user_id, message):
    """
    Helper function to post a tweet 
    """
    if user_id not in local_cache['access_token']:
        return "couldn't find your credentials, have you logged in?"
    url = "https://api.twitter.com/1.1/statuses/update.json"    
    access_token = local_cache['access_token'][user_id]
    access_secret = local_cache['access_secret'][user_id]
    print (consumer_key, consumer_secret, access_token, access_secret)
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
    params = { "status" : message }
    r = requests.post(url, auth=auth, params=params)
    print (r.text)
    return "Successfully posted a tweet {}".format(message)


def get_access_token(user_id, oauth_token, oauth_verifier):
    url = "https://api.twitter.com/oauth/access_token"
    params = {"oauth_verifier" : oauth_verifier}
    request_token   = local_cache['request_token'][user_id]
    request_secret = local_cache['request_secret'][user_id]
    print(consumer_key, consumer_secret, request_token, request_secret)
    auth = OAuth1(consumer_key, consumer_secret, request_token, request_secret)
    r = requests.post(url, params = params, auth=auth)
    response_obj = parse_qs(r.text)

    local_cache['access_token'][user_id] = response_obj['oauth_token'][0]
    local_cache['access_secret'][user_id] = response_obj['oauth_token_secret'][0]
    local_cache['twitter_user_id'][user_id] = response_obj['user_id'][0]
    local_cache['screen_name'][user_id] = response_obj ['screen_name'][0]

    print (response_obj)
    return response_obj


def strip_html(text):
    out = []
    for token in text.split():
        if not token.startswith('http:') and not token.startswith('https:'):
            out += [token]
    return " ".join(out)


def get_home_tweets(user_id):
    url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
    access_token, access_secret = get_cached_access_pair(user_id)
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
    r = requests.get(url, auth=auth)

    output = [(tweet['user']['name'], strip_html(tweet['text'])) for tweet in r.json()]
    spoken = ["tweet number {num} by {user}. {text}.".format(num=index, user=user, text=text)
                       for index, (user, text) in enumerate(output)]
    return spoken
