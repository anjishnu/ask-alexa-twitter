from lib.dialog_utils import VoiceHandler, ResponseBuilder
from lib.twitter_utils import post_tweet
import cherrypy
import json

"""
In this file we specify default event handlers which are then populated into the handler map using metaprogramming
Copyright Anjishnu Kumar 2015

Each VoiceHandler function receives a ResponseBuilder object as input and outputs a Response object 
A response object is defined as the output of ResponseBuilder.create_response()
"""

r = ResponseBuilder()

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
    if request.user_id() in twitter_cache['access_token']:
        return r.create_response("Welcome, {}".format(twitter_cache["screen_name"][request.user_id()]))

    card = r.create_card(title="Please log into twitter",
                         subtitle=None,
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
        return r.create_response(message=post_tweet(request.user_id(), tweet),
                                 end_session=True)
    else:
        # No tweet could be disambiguated
        return r.create_response(message="I'm sorry, I couldn't understand what you wanted to tweet."
                                 "Please prepend the message with either post or tweet",
                                 end_session=False)


