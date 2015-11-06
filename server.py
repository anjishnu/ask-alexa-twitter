import cherrypy
import json
import dialog
from lib.validation_utils import valid_alexa_request
from lib.twitter_utils import authenticate_user_page, get_access_token
from urllib.parse import urlparse
import os
import subprocess
import requests

SERVER_CONFIG_PATH = "config/server_config.json"
ALWAYS_VALID = True

class SkillServer(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        print (cherrypy.url())
        content_length = int(cherrypy.request.headers['Content-Length'])
        raw_body = cherrypy.request.body.read(content_length)
        input_json = json.loads(raw_body.decode("utf-8"))
        is_valid_request = valid_alexa_request(cherrypy.request.headers, 
                                               raw_body) if not ALWAYS_VALID else True
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
        redirect_url = get_access_token(oauth_token, oauth_verifier)
        raise cherrypy.HTTPRedirect(redirect_url)


if __name__ == "__main__":
    """
    Load the server config and launch the server
    """
    with open(SERVER_CONFIG_PATH, 'r') as server_conf_file:

        server_config = json.load(server_conf_file)
        print ("Loaded server config file:")

    print (json.dumps(server_config, indent=4))    
    config = {"global": server_config}    
    cherrypy.config.update(server_config)
    cherrypy.quickstart(SkillServer(), config=config)
