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

r = ResponseBuilder()    
voice_cache = VoiceCache()


def default_handler(request):
    """ The default handler gets invoked if no handler is set for a request """
    return r.create_response(message="Just ask.")


@VoiceHandler(request_type="LaunchRequest")
def launch_request_handler(request):
    """
    Annoatate functions with @VoiceHandler so that they can be automatically mapped 
    to request types.
    Use the 'request_type' field to map them to non-intent requests
    """
    from lib.twitter_utils import local_cache as twitter_cache
    if request.access_token() in twitter_cache:
        twitter_cache[request.access_token()]["amzn_id"]= request.user_id()
        return r.create_response("Welcome, {}".format(twitter_cache[request.access_token()]["screen_name"]))

    card = r.create_card(title="Please log into twitter",
                         content=cherrypy.url() + "login/{}".format(request.user_id()))

    response = r.create_response(message="Welcome to twitter, looks like you haven't logged in! Log in via alexa.amazon.com.",
                                 card_obj=card)
    print (json.dumps(response, indent=4))    
    return response


@VoiceHandler(request_type="AMAZON.HelpIntent")
def help_intent_handler(request):
    msg = ("Currently we only support posting tweets."
           "To post a tweet, say 'post hello world' or 'tweet hello world'")
    return r.create_response(msg)


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
        get_home_timeline(request.access_token)
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


@VoiceHandler(intent="ListHomeTweets")
def list_home_tweets_handler(request):
    # Max number of tweets to be spoken out by Alexa
    max_tweets = 3
    #Processing tweets into chunks
    tweets = get_home_tweets(request.access_token())
    chunks = [tweets[start : end] for start, end 
              in zip(range(0, len(tweets), max_tweets), 
                     range(max_tweets, len(tweets), max_tweets))]
    next_queue = [" ".join(text_lst) for text_lst in chunks[1:]]
    next_cache[request.user_id()] = next_queue
    return r.create_response(message = " ".join(chunks[0]), 
                             end_session=False)


@VoiceHandler(intent="NextIntent")
def next_intent_handler(request):
    """
    Takes care of things whenver the user says 'next'
    """
    user_queue = next_cache[request.user_id()]
    if not user_queue.is_empty():
        message = user_queue.next_response()
        if user_queue.is_empty():
            end_session = True
        else:
            end_session = False
            message = message + ". Please, say 'next' if you want me to read out more. "
    else:
        message = "Sorry, couldn't find anything in your next queue"
        end_session = True
    return r.create_response(message=message,
                             end_session=end_session)
        
        
