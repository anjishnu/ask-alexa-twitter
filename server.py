import cherrypy
import json
import dialog
from lib.validation_utils import valid_alexa_request
from lib.twitter_utils import authenticate_user_page, get_access_token
from urllib.parse import urlparse
import os
import subprocess
import requests

from config.config import SERVER_CONFIG, ALL_REQUESTS_VALID, BASE_REDIRECT_URL


class SkillServer(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        content_length = int(cherrypy.request.headers['Content-Length'])
        raw_body = cherrypy.request.body.read(content_length)
        input_json = json.loads(raw_body.decode("utf-8"))
        is_valid_request = valid_alexa_request(cherrypy.request.headers, 
                                               raw_body) if not ALL_REQUESTS_VALID else True
        if is_valid_request:
            print ("New Request Body:", json.dumps(input_json, indent=4))
            output_json = dialog.route_intent(input_json)
            return output_json
    
    @cherrypy.expose
    def login(self, **kwargs):
        """ Create login screen for user login"""
        print (json.dumps(kwargs, indent=4))
        callback_url = cherrypy.request.base+"/get_auth/"
        return authenticate_user_page(callback_url, metadata=kwargs)

    @cherrypy.expose
    def get_auth(self, oauth_token, oauth_verifier):
        """ Receive access token for user from twitter"""
        url_fragments = get_access_token(oauth_token, oauth_verifier)
        redirect_url = BASE_REDIRECT_URL + "#" + url_fragments
        redirect_url = redirect_url.strip()
        raise cherrypy.HTTPRedirect(redirect_url)


if __name__ == "__main__":
    """
    Load the server config and launch the server
    """
    print (json.dumps(SERVER_CONFIG, indent=4))    
    config = {"global": SERVER_CONFIG}    
    cherrypy.config.update(SERVER_CONFIG)
    cherrypy.quickstart(SkillServer(), config=config)
