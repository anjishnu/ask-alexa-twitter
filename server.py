import cherrypy
import json
import dialog
from lib.validation_utils import valid_alexa_request
from lib.twitter_utils import authenticate_user_page, get_access_token
from urllib.parse import urlparse
import os
import subprocess

SERVER_CONFIG_PATH = "config/server_config.json"

class SkillResponse(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        print (cherrypy.url())
        content_length = int(cherrypy.request.headers['Content-Length'])
        raw_body = cherrypy.request.body.read(content_length)
        input_json = json.loads(raw_body.decode("utf-8"))
        #is_valid_request = valid_alexa_request(cherrypy.request.headers, raw_body)
        is_valid_request = True
        if is_valid_request:
            print ("New Request Body:", json.dumps(input_json, indent=4))
            output_json = dialog.route_intent(input_json)
            return output_json
    

@cherrypy.popargs('user_id')
class UserAuth(object):
    @cherrypy.expose
    def index(self, oauth_token, oauth_verifier, user_id):
        """ Receive access token for user from twitter"""
        response_object = get_access_token(user_id, oauth_token, oauth_verifier)
        return json.dumps({"status": "Logged in successfully!"})

@cherrypy.popargs('user_id')
class Login(object):
    @cherrypy.expose
    def index(self, user_id):
        """ Create login screen for user login"""
        callback_url = cherrypy.request.base+"/get_auth/{}".format(user_id)
        return authenticate_user_page(user_id, callback_url)

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

    root = SkillResponse()
    root.get_auth = UserAuth()
    root.login = Login()

    cherrypy.quickstart(root, config=config)
