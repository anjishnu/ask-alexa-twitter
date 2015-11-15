from lib.dialog_utils import VoiceHandler, ResponseBuilder, VoiceCache
from lib.twitter_utils import post_tweet, get_home_tweets
import cherrypy
import json

"""
In this file we specify default event handlers which are then populated into the handler map using metaprogramming
Copyright Anjishnu Kumar 2015

Each VoiceHandler function receives a ResponseBuilder object as input and outputs a Response object 
A response object is defined as the output of ResponseBuilder.create_response()
"""

import cherrypy
import json
from lib.dialog_utils import VoiceHandler, ResponseBuilder as r, VoiceCache, VoiceQueue, chunk_list
from lib.twitter_utils import (post_tweet, get_home_tweets, get_retweets_of_me, 
                               get_my_favourite_tweets, get_my_favourite_tweets, 
                               get_latest_twitter_mentions, search_for_tweets_about,
                               get_user_latest_tweets)

# -- Config setup -- 
from config.config import TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET
from lib.twitter_utils import local_cache as twitter_cache

# Run this code once on startup to load twitter keys into credentials
if 'twitter_keys' not in twitter_cache:
    twitter_cache['twitter_keys'] = (TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)


next_cache = VoiceCache()


def default_handler(request):
    """ The default handler gets invoked if no handler is set for a request """
    return r.create_response(message="Just ask.")


@VoiceHandler(request_type="LaunchRequest")
def launch_request_handler(request):
    """ Annotate functions with @VoiceHandler so that they can be automatically mapped 
    to request types. Use the 'request_type' field to map them to non-intent requests """

    if request.access_token() in twitter_cache:
        twitter_cache[request.access_token()]["amzn_id"]= request.user_id()
        return r.create_response("Welcome, {}".format(twitter_cache[request.access_token()]["screen_name"]))

    card = r.create_card(title="Please log into twitter",
                         content=cherrypy.url() + "login/{}".format(request.user_id()))

    response = r.create_response(message="Welcome to twitter, looks like you haven't logged in!"
                                 " Log in via alexa.amazon.com.", card_obj=card)
    print (json.dumps(response, indent=4))    
    return response




@VoiceHandler(request_type="SessionEndedRequest")
def session_ended_request_handler(request):
    return r.create_response(message="Goodbye!")


@VoiceHandler(intent='PostTweet')
def post_tweet_intent_handler(request):
    """
    Use the 'intent' field in the VoiceHandler to map to the respective intent.
    """
    tweet = request.get_slot_value("Tweet")
    tweet = tweet if tweet else ""    

    # Use ResponseBuilder object to build responses and UI cards
    if tweet:
        return r.create_response(message=post_tweet(request.access_token(), tweet),
                                 end_session=True)
    else:
        # No tweet could be disambiguated
        message = " ".join(
            [
                "I'm sorry, I couldn't understand what you wanted to tweet.",
                "Please prepend the message with either post or tweet"
            ]
        )
        return r.create_response(message=message, end_session=False)


@VoiceHandler(intent="AMAZON.HelpIntent")
def help_intent_handler(request):
    msg = ("Currently we only support posting tweets."
           "To post a tweet, say 'post hello world' or 'tweet hello world'")
    return r.create_response(msg)


@VoiceHandler(intent="AMAZON.StopIntent")
def session_ended_request_handler(request):
    print ("Executing handler")
    return r.create_response(message="Goodbye!")


def tweet_list_handler(request, tweet_list_builder, msg_prefix=""):

    """ This is a generic function to handle any intent that reads out a list of tweets"""
    max_response_tweets = 3
    # tweet_list_builder is a function that takes a unique identifier and returns a list of things to say
    tweets = tweet_list_builder(request.access_token())
    print (len(tweets), 'tweets found')
    if tweets:
        chunks = chunk_list(tweets, max_response_tweets)
        response_list = [" ".join(text_lst) for text_lst in chunks]
        next_cache[request.user_id()] = response_list
        message = msg_prefix + next_cache[request.user_id()].next_response() + ", say 'next' to hear more."
        return r.create_response(message=message,
                                 end_session=False)
    else:
        return r.create_response(message="Sorry, no tweets found, please try something else", 
                                 end_session=False)


@VoiceHandler(intent="SearchTweets")
def search_tweets_handler(request):
    search_topic = request.get_slot_value("Topic")
    max_tweets = 3
    if search_topic:
        message = "Tweets about {}".format(search_topic)
        def search_tweets_builder(uid):
            params = {
                "q" : search_topic,
                "result_type" : "popular"
            }
            return search_for_tweets_about(request.access_token(), params)

        return tweet_list_handler(request, tweet_list_builder=search_tweets_builder)
    else:
         return r.create_response("I couldn't find a topic to search for in your request")


@VoiceHandler(intent="FindLatestMentions")
def list_mentions_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_latest_twitter_mentions)


@VoiceHandler(intent="ListHomeTweets")
def list_home_tweets_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_home_tweets)


@VoiceHandler(intent="UserTweets")
def list_user_tweets_handler(request):
    """ by default gets tweets for current user """
    return tweet_list_handler(request, tweet_list_builder=get_user_latest_tweets)


@VoiceHandler(intent="RetweetsOfMe")
def list_retweets_of_me_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_retweets_of_me)


@VoiceHandler(intent="FindFavouriteTweets")
def find_my_favourites_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_my_favourite_tweets)
              

@VoiceHandler(intent="NextIntent")
def next_intent_handler(request):
    """
    Takes care of things whenver the user says 'next'
    """

    message = "Sorry, couldn't find anything in your next queue"
    end_session = True
    try:
        user_queue = next_cache[request.user_id()]
        if not user_queue.is_empty():
            message = user_queue.next_response()
            if user_queue.is_empty():
                end_session = True
            else:
                end_session = False
                message = message + ". Please, say 'next' if you want me to read out more. "
    except:
        pass
    return r.create_response(message=message,
                             end_session=end_session)
        

@VoiceHandler(intent="PreviousIntent")
def previous_intent_handler(request):
    user_queue = next_cache[request.user_id()]
    previous_response = user_queue.previous_response()
    print (user_queue.prev)
    if previous_response:
        message = previous_response
    else:
        message = "I couldn't find anything to repeat"
    return r.create_response(message=message)
