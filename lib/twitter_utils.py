import requests
from requests_oauthlib import OAuth1
from urllib.parse import parse_qs, urlencode
import cherrypy 
from collections import defaultdict 
import json
import os
import re
from collections import defaultdict


#Try to load twitter conifg path

twitter_config_path = os.path.realpath("keys/twitter_keys.json")
if os.path.exists(twitter_config_path):
    with open(twitter_config_path) as config_file:
        twitter_config = json.load(config_file)
    consumer_key = twitter_config["consumer_key"]
    consumer_secret = twitter_config["consumer_secret"]
else:
    raise Exception("Twitter config not found! at "+ twitter_config_path)


class LocalCache(object):
    def __init__(self):
        self.memcache = defaultdict(dict)

    def __setitem__(self, key, item):
        self.memcache[key] = item

    def __getitem__(self, key):
        return self.memcache[key]
    
    def __repr__(self):
        return repr(self.memcache)

    def __len__(self):
        return len(self.memcache)

    def __delitem__(self, key):
        del self.memcache[key]

    def clear_memory(self):
        return self.memcache.clear()

    def update_memory(self, *args, **kwargs):
        return self.memcache.update(*args, **kwargs)

    def keys(self):
        return self.memcache.keys()

    def values(self):
        return self.memcache.values()

    def items(self):
        return self.memcache.items()

    def __contains__(self, item):
        return item in self.memcache

    def __iter__(self):
        return iter(self.memcache)

#Local cache caches tokens for different users 
local_cache = LocalCache()

def get_cached_access_pair(uid):
    if uid in local_cache:
        return local_cache[uid]['access_token'], local_cache[uid]['access_secret']
        

def get_request_token(callback_url=None):
    url = "https://api.twitter.com/oauth/request_token"
    auth = OAuth1(consumer_key, consumer_secret)
    params = { "oauth_callback" : callback_url } 
    r = requests.post(url, auth=auth, params=params)
    response_obj = parse_qs(r.text)    
    local_cache["request_token"] = response_obj['oauth_token'][0]
    local_cache['request_secret'] = response_obj['oauth_token_secret'][0]    
    return response_obj['oauth_token_secret'], response_obj['oauth_token']
    

def authenticate_user_page(callback_url="", metadata=None):
    url = "https://api.twitter.com/oauth/authenticate"
    oauth_secret, oauth_token = get_request_token(callback_url)
    local_cache['metadata'] = metadata
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
    access_token = local_cache[uid]['access_token']
    access_secret = local_cache[uid]['access_secret']
    print (consumer_key, consumer_secret, access_token, access_secret)
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
    params = { "status" : message }
    r = requests.post(url, auth=auth, params=params)
    print (r.text)
    return "Successfully posted a tweet {}".format(message)


def get_access_token(oauth_token, oauth_verifier):
    url = "https://api.twitter.com/oauth/access_token"
    params = {"oauth_verifier" : oauth_verifier}

    request_token  = local_cache['request_token']
    request_secret = local_cache['request_secret']
    auth = OAuth1(consumer_key, consumer_secret, request_token, request_secret)
    r = requests.post(url, params = params, auth=auth)
    response_obj = parse_qs(r.text)


    uid = response_obj['oauth_token'][0]

    local_cache[uid]['access_token'] = response_obj['oauth_token'][0]
    local_cache[uid]['access_secret'] = response_obj['oauth_token_secret'][0]
    local_cache[uid]['twitter_user_id'] = response_obj['user_id'][0]
    local_cache[uid]['screen_name'] = response_obj ['screen_name'][0]    
    
    fragments = {
        "state" : local_cache['metadata']['state'],
        "access_token" : uid,
        "token_type" : "Bearer"
    }
    return urlencode(fragments)


def strip_html(text):
    """ Get rid of ugly twitter html """
    return " ".join([token for token in text.split() 
                     if not token.startswith('http:')
                     and not token.startswith('https:')])
    

def get_home_tweets(user_id):
    url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
    access_token, access_secret = get_cached_access_pair(user_id)
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
    r = requests.get(url, auth=auth)

    # Clean tweets and enumerate
    output = [(tweet['user']['name'], strip_html(tweet['text'])) for tweet in r.json()]

    # Convert them into a spoken form.
    spoken = ["tweet number {num} by {user}. {text}.".format(num=index+1, user=user, text=text)
                       for index, (user, text) in enumerate(output)]
    return spoken
