# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

import base64
import json
import time
import urllib
import urllib.error
from collections import OrderedDict

# import requests
from urllib import parse, request

import app_state
import utils


def is_missing(config, key):
    """Check if a config key is missing or empty."""
    if key not in config:
        return True
    if config[key] is None:
        return True
    if len(str(config[key])) == 0:
        return True
    return False


class MCEChain:
    """MultiChain blockchain connection wrapper."""
    
    def __init__(self, name):
        self.name = name
        self.config = app_state.get_state().settings[name].copy()
        self.config["ini-name"] = name
        self.config["path-name"] = parse.quote_plus(self.config["name"])
        self.config["path-ini-name"] = parse.quote_plus(name)

    def initialize(self):
        """Initialize the chain connection with RPC credentials."""
        url = "http://127.0.0.1"
        if not is_missing(self.config, "rpchost"):
            url = f"http://{self.config['rpchost']}"

        url = url + ":" + str(self.config["rpcport"])
        userpass64 = base64.b64encode(
            (self.config["rpcuser"] + ":" + self.config["rpcpassword"]).encode("ascii")
        ).decode("ascii")

        headers = {
            "Content-Type": "application/json",
            "Connection": "close",
            "Authorization": "Basic " + userpass64,
        }

        self.config["multichain-url"] = url
        self.config["multichain-headers"] = headers

        #        print(self.config)

        return True

    def request(self, method, params=[]):
        payload = json.dumps(
            {"id": int(round(time.time() * 1000)), "method": method, "params": params}
        )

        headers = self.config["multichain-headers"].copy()
        headers["Content-Length"] = str(len(payload))

        try:
            #        req = requests.post(cfg.multichain_url, data=payload, headers=headers)

            data = str(payload)
            data = data.encode("utf-8")
            ureq = request.Request(self.config["multichain-url"], data=data)
            for header, value in headers.items():
                ureq.add_header(header, value)
            req = request.urlopen(ureq)
        except urllib.error.HTTPError as e:
            resp = e.read()
            req_json = json.loads(resp.decode("utf-8"))
            if req_json["error"] is not None:
                req_json["error"] = (
                    "Error " + str(req_json["error"]["code"]) + ": " + req_json["error"]["message"]
                )
            return req_json
        except urllib.error.URLError as e:
            error_str = "MultiChain is not running: " + str(e.reason)
            req_json = {"result": None, "error": error_str, "connection-error": True}
            return req_json

        #        except Exception as error:
        #            print("C")
        #            error_str="MultiChain is not running: " + str(error)
        #            print(str(error))
        #            req_json={
        #                'result': None,
        #                'error' : error_str,
        #                'connection-error' : True
        #            }
        #            utils.print_error(error_str)
        #            return req_json

        resp = req.read()
        #        req_json=json.loads(resp.decode('utf-8'))
        req_json = json.loads(resp.decode("utf-8"), object_pairs_hook=OrderedDict)

        if req_json is None:
            error_str = "MultiChain connection error"
            req_json = {"result": None, "error": error_str, "connection-error": True}
        #            utils.print_error(error_str)

        return req_json
