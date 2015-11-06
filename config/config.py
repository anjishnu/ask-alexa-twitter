"""
This is the basic config file, encapsulating all configuration options
"""
from __future__ import print_function
import os
import json


# ---- Helper Functions ----
def path_relative_to_file(rel_path):
    dir_name = os.path.dirname(__file__)
    return os.path.join(dir_name, rel_path)

def load_json_schema(schema_location):
    with open(schema_location, 'r') as json_file:
        return json.load(json_file)


# --- CherryPyServer related configurations ---

SERVER_CONFIG_PATH = "config/server_config.json"

SERVER_CONFIG = load_json_schema(SERVER_CONFIG_PATH)
print ("Loaded server config file:")


# --- AMAZON related configurations ---


ALL_REQUESTS_VALID = True # Declares all incoming requests valid - (switches off oauth validation - useful for debugging)

# The redirect url is used in the account linking process to associate an amazon user account with your OAuth token
AMAZON_CREDENTIAL_PATH = path_relative_to_file("../keys/amazon.json")

BASE_REDIRECT_URL = load_json_schema(AMAZON_CREDENTIAL_PATH)['redirect_url'] # Different for each vendor 
# ^ YOU CAN HARDCODE YOURS HERE, but I suggest making a JSON schema for it just in case you decide to share your code

DEFAULT_INTENT_SCHEMA_LOCATION = "config/intent_schema.json"

NON_INTENT_REQUESTS = ["LaunchRequest", "SessionEndedRequest"]

INTENT_SCHEMA = load_json_schema(DEFAULT_INTENT_SCHEMA_LOCATION)



# --- TWITTER related configurations ---

TWITTER_CONFIG_PATH = os.path.realpath("keys/twitter_keys.json")
if os.path.exists(TWITTER_CONFIG_PATH):
    with open(TWITTER_CONFIG_PATH) as config_file:
        twitter_config = json.load(config_file)
    TWITTER_CONSUMER_KEY = twitter_config["consumer_key"]
    TWITTER_CONSUMER_SECRET = twitter_config["consumer_secret"]
else:
    raise Exception("Twitter config not found! at "+ twitter_config_path)

