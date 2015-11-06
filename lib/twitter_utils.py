import requests
from requests_oauthlib import OAuth1
from urllib.parse import parse_qs, urlencode
import cherrypy 
from collections import defaultdict 
import json
import os
import re
from collections import defaultdict

class LocalCache(object):
    """Generic class for encapsulating twitter credential caching"""
    def __init__(self, backup = "twitter.cache"):
        self.backup = backup
        self.deserialize()

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

    def deserialize(self):
        cache_loaded = False
        if os.path.exists(self.backup) and not os.path.isdir(self.backup):
            try:
                with open(self.backup) as backupfile:
                    print ("Attempting to reload cache")
                    self.memcache = json.load(backupfile)
                    cache_loaded = True
            except:
                print ("Cache file corrupted...")
        if not cache_loaded:
            # Creating a fresh cache                                                                                                                    
            self.memcache = defaultdict(dict)
            

    def serialize(self):
        with open(self.backup, 'w') as backupfile:
            backupfile.write(json.dumps(self.memcache, indent=4))
        

    def __contains__(self, item):
        return item in self.memcache

    def __iter__(self):
        return iter(self.memcache)
    

#Local cache caches tokens for different users 
local_cache = LocalCache()


def get_cached_access_pair(uid):
    if uid in local_cache:
        return local_cache[uid]['access_token'], local_cache[uid]['access_secret']
    else:
        raise ValueError


def get_request_token(callback_url=None):
    url = "https://api.twitter.com/oauth/request_token"
    consumer_key, consumer_secret = local_cache['twitter_keys']    
    auth = OAuth1(consumer_key, consumer_secret)
    params = { "oauth_callback" : callback_url } 
    print (params)
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
    url = "https://api.twitter.com/1.1/statuses/update.json"    
    params = { "status" : message }
    r = make_twitter_request(url, user_id, params)
    return "Successfully posted a tweet {}".format(message)


def get_access_token(oauth_token, oauth_verifier):
    url = "https://api.twitter.com/oauth/access_token"
    params = {"oauth_verifier" : oauth_verifier}
    request_token  = local_cache['request_token']
    request_secret = local_cache['request_secret']
    consumer_key, consumer_secret = local_cache['twitter_keys']
    auth = OAuth1(consumer_key, consumer_secret, request_token, request_secret)

    r = requests.post(url, params = params, auth=auth)
    response_obj = parse_qs(r.text)

    uid = response_obj['oauth_token'][0]    
    print ("Access token", uid)
    local_cache[uid]['access_token'] = response_obj['oauth_token'][0]
    local_cache[uid]['access_secret'] = response_obj['oauth_token_secret'][0]
    local_cache[uid]['twitter_user_id'] = response_obj['user_id'][0]
    local_cache[uid]['screen_name'] = response_obj ['screen_name'][0]        
    local_cache.serialize()
    fragments = {
        "state" : local_cache['metadata']['state'],
        "access_token" : uid,
        "token_type" : "Bearer"
    }
    return urlencode(fragments)


def strip_html(text):
    """ Get rid of ugly twitter html """
    def reply_to(text):
        replying_to = []
        split_text = text.split()
        for index, token in enumerate(split_text):
            if token.startswith('@'): replying_to.append(token[1:])
            else:
                message = split_text[index:]
                break
        rply_msg = ""
        if len(replying_to) > 0:
            rply_msg = "Replying to "
            for token in replying_to[:-1]: rply_msg += token+","                
            if len(replying_to)>1: rply_msg += 'and '
            rply_msg += replying_to[-1]+". "
        return rply_msg + " ".join(message)
        
    text = reply_to(text)      
    text = text.replace('@', ' ')
    return " ".join([token for token in text.split() 
                     if  ('http:' not in token) and ('https:' not in token)])

    
def get_twitter_auth(user_id):
    consumer_key, consumer_secret = local_cache['twitter_keys']
    access_token, access_secret = get_cached_access_pair(user_id)
    return OAuth1(consumer_key, consumer_secret, access_token, access_secret)


def process_tweets(tweet_list):
    """ Clean tweets and enumerate, preserving only things that we are interested in """  
    processed = []
    for tweet in tweet_list:
        text = strip_html(tweet['text'])
        user_mentions = tweet['entities']['user_mentions']
        text = text.replace('@', 'at ')
        for user in user_mentions:            
            text = text.replace(user['screen_name'], user['name'])
        processed += [(tweet['user']['name'], text)]
    return processed


def make_twitter_request(url, user_id, params={}):
    """ Generically make a request to twitter API using a particular user's authorization """
    return requests.get(url, auth=get_twitter_auth(user_id), params=params)
   

def read_out_tweets(processed_tweets, speech_convertor=None):
    """
    Input - list of processed 'Tweets'
    output - list of spoken responses
    """
    return ["tweet number {num} by {user}. {text}.".format(num=index+1, user=user, text=text)
               for index, (user, text) in enumerate(processed_tweets)]


def request_tweet_list_spoken_form(url, user_id, params={}):
    try:
        return read_out_tweets(process_tweets(make_twitter_request(url, user_id).json()))
    except ValueError:
        return ["Sorry, your credentials could not be found"]


def get_home_tweets(user_id, input_params={}):
    url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
    print ("Trying to get home tweets")
    response = request_tweet_list_spoken_form(url, user_id)
    return response


def get_retweets_of_me(user_id, input_params={}):
    """ returns recently retweeted  tweets """
    url = "https://api.twitter.com/1.1/statuses/retweets_of_me.json"
    print ("trying to get retweets")
    return request_tweet_list_spoken_form(url, user_id)


def get_my_favourite_tweets(user_id, input_params = {}):
    """ Returns a user's favourite tweets """
    url = "https://api.twitter.com/1.1/favorites/list.json"
    return request_tweet_list_spoken_form(url, user_id)


def get_user_latest_tweets(user_id, params={}):
    url = "https://api.twitter.com/1.1/statuses/user_timeline.json?"
    return request_tweet_list_spoken_form(url, user_id, params)
    

def get_latest_twitter_mentions(user_id):
    url = "https://api.twitter.com/1.1/statuses/mentions_timeline.json"
    return request_tweet_list_spoken_form(url, user_id)


def search_for_tweets_about(user_id, params):
    """ Search twitter API """
    url = "https://api.twitter.com/1.1/search/tweets.json"
    response = make_twitter_request(url, user_id, params)
    return read_out_tweets(process_tweets(response.json()["statuses"]))

    
