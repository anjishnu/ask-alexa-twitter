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
server_cache_state = twitter_cache.get_server_state()
if 'twitter_keys' not in server_cache_state:
    server_cache_state['twitter_keys'] = (TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)


def default_handler(request):
    """ The default handler gets invoked if no handler is set for a request """
    return launch_request_handler(request)


@VoiceHandler(request_type="LaunchRequest")
def launch_request_handler(request):
    """ Annotate functions with @VoiceHandler so that they can be automatically mapped 
    to request types. Use the 'request_type' field to map them to non-intent requests """

    if request.access_token() in twitter_cache.users():
        user_cache = twitter_cache.get_user_state(request.access_token())        
        user_cache["amzn_id"]= request.user_id()
        return r.create_response("Welcome, {}".format(user_cache["screen_name"]))

    card = r.create_card(title="Please log into twitter",
                         content=cherrypy.url() + "login/{}".format(request.user_id()))
    response = r.create_response(message="Welcome to twitter, looks like you haven't logged in!"
                                 " Log in via the alexa app.", card_obj=card)
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
    if tweet:
        user_state = twitter_cache.get_user_state(request.access_token())

        def action():
            return post_tweet(request.access_token(), tweet)
        message = "I am ready to post the tweet, {}. Please say yes to confirm or stop to cancel.".format(tweet)
        user_state['pending_action'] = {"action" : action,
                                        "description" : message} 
        return r.create_response(message=message, end_session=False)
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
        # chunks = chunk_list(tweets, max_response_tweets)
        # next_cache[request.user_id()] = response_list
        twitter_cache.initialize_user_queue(user_id=request.access_token(),
                                            queue=tweets)
        text_to_read_out = twitter_cache.user_queue(request.access_token()).read_out_next(max_response_tweets)        
        message = msg_prefix + text_to_read_out + ", say 'next' to hear more."
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
    return tweet_list_handler(request, tweet_list_builder=get_latest_twitter_mentions, msg_prefix="Looking tweets that mention you.")


@VoiceHandler(intent="ListHomeTweets")
def list_home_tweets_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_home_tweets)


@VoiceHandler(intent="UserTweets")
def list_user_tweets_handler(request):
    """ by default gets tweets for current user """
    return tweet_list_handler(request, tweet_list_builder=get_user_latest_tweets)


@VoiceHandler(intent="RetweetsOfMe")
def list_retweets_of_me_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_retweets_of_me, msg_prefix="Looking for retweets.")


@VoiceHandler(intent="FindFavouriteTweets")
def find_my_favourites_handler(request):
    return tweet_list_handler(request, tweet_list_builder=get_my_favourite_tweets, msg_prefix="Finding your favourite tweets.")


def focused_on_tweet(request):
    """
    Return index if focused on tweet False if couldn't
    """
    slots = request.get_slot_map()
    if "Index" in slots:
        index = int(slots['Index'])

    elif "Ordinal" in slots:
        parse_ordinal = lambda inp : int("".join([l for l in inp if l in string.digits]))
        index = parse_ordinal(slots['Ordinal'])
    else:
        return False
        
    index = index - 1 # Going from regular notation to CS
    user_state = twitter_cache.get_user_state(request.access_token())
    queue = user_state['user_queue'].queue()
    if index < len(queue):
        # Analyze tweet in queue
        tweet_to_analyze = queue[index]
        user_state['focus_tweet'] = tweet_to_analyze
        return index + 1
        twitter_cache.serialize()
    return False

"""
Definining API for executing pending actions:
action = function that does everything you want and returns a 'message' to return.
description = read out in case there is a pending action at startup. 
other metadata will be added as time progresses
"""

@VoiceHandler(intent="ReplyIntent")
def reply_handler(request):
    message = "Sorry, I couldn't tell which tweet you want to reply to. "
    slots = request.get_slot_map()
    user_state = twitter_cache.get_user_state(request.access_token())
    if not slots["Tweet"]:
        return reply_focus_handler(request)
    else:
        can_reply = False
        if slots['Tweet'] and not (slots['Ordinal'] or slots['Index']):
            user_state = twitter_cache.get_user_state(request.access_token())
            if 'focus_tweet' in user_state: # User is focused on a tweet
                can_reply = True
        else:
            index = focused_on_tweet(request)
            if index: can_reply = True
        if can_reply: # Successfully focused on a tweet
            index, focus_tweet = user_state['focus_tweet']
            tweet_message = "@{0} {1}".format(focus_tweet.get_screen_name(),
                                          slots['Tweet'])
            params = {"in_reply_to_status_id": focus_tweet.get_id()}

            
            def action():
                print ("Performing action! lambda functions are awesome!")
                message = post_tweet(request.access_token(), tweet_message, params)
                del user_state['focus_tweet']
                return message

            message = "I am ready to post the tweet, {}. Please say yes to confirm or stop to cancel.".format(slots['Tweet'])
            user_state['pending_action'] = {"action" : action,
                                            "description" : message }

    return r.create_response(message=message)


@VoiceHandler(intent="YesIntent")
def confirm_action_handler(request):
    message = "okay."
    user_state = twitter_cache.get_user_state(request.access_token())
    if 'pending_action' in user_state:
        params = user_state['pending_action']
        # Perform action
        message = params['action']()
        if 'message' in params:
            message = params['message']
        if 'callback' in params:
            params['callback']()
        del user_state['pending_action']
        print ("successfully executed command")
    return r.create_response(message)


@VoiceHandler(intent="NoIntent")
def cancel_action_handler(request):
    message = "okay."
    user_state = twitter_cache.get_user_state(request.access_token())
    if 'pending_action' in user_state:
        del user_state['pending_action'] # Clearing out the user's pending action
        print ("cleared user_state")
        message += " i won't do it."
    return r.create_response(message)


@VoiceHandler(intent="ReplyFocus")
def reply_focus_handler(request):    
    msg = "Sorry, I couldn't tell which tweet you wanted to reply to."
    index = focused_on_tweet(request)
    if index:
        return r.create_response(message="Do you want to reply to tweet {} ? If so say reply, followed by your message".format(index))
    return r.create_response(message=msg, end_session=False)


@VoiceHandler(intent="MoreInfo")
def more_info_handler(request):
    index = focused_on_tweet(request)
    if index:
        user_state = twitter_cache.get_user_state(request.access_token())
        index, tweet = user_state['focus_tweet']
        message = " ".join(["details about tweet number {}.".format(index+1), tweet.detailed_description(),"To reply, say 'reply' followed by your message"])
        return r.create_response(message=message, end_session=False)
    return reply_focus_handler(request)

@VoiceHandler(intent="NextIntent")
def next_intent_handler(request):
    """
    Takes care of things whenver the user says 'next'
    """

    message = "Sorry, couldn't find anything in your next queue"
    end_session = True
    if True:
        user_queue = twitter_cache.user_queue(request.access_token())
        if not user_queue.is_finished():
            message = user_queue.read_out_next()
            if not user_queue.is_finished():
                end_session = False
                message = message + ". Please, say 'next' if you want me to read out more. "
    return r.create_response(message=message,
                             end_session=end_session)
        

@VoiceHandler(intent="PreviousIntent")
def previous_intent_handler(request):
    user_queue = twitter_cache.user_queue(request.access_token())
    if user_queue and user_queue.has_prev():
        message = user_queue.read_out_prev()
    else:
        message = "I couldn't find anything to repeat"
    return r.create_response(message=message)
