"""Compatibility-only legacy MultiChain RPC wrapper implementation.

This module remains in the repository for backward compatibility and
regression coverage. The active FastAPI runtime path should use
`services.blockchain_service.BlockchainService` instead.
"""

# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

import base64
import json
import logging
import time
import urllib
import urllib.error
from collections import OrderedDict

from urllib import parse, request

import app_state

logger = logging.getLogger(__name__)


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

        return True

    def request(self, method, params=[]):
        payload = json.dumps(
            {"id": int(round(time.time() * 1000)), "method": method, "params": params}
        )

        headers = self.config["multichain-headers"].copy()
        headers["Content-Length"] = str(len(payload))

        try:
            data = str(payload)
            data = data.encode("utf-8")
            ureq = request.Request(self.config["multichain-url"], data=data)
            for header, value in headers.items():
                ureq.add_header(header, value)
            req = request.urlopen(ureq)  # nosec B310: URL is built from trusted RPC config
        except urllib.error.HTTPError as e:
            resp = e.read()
            try:
                req_json = json.loads(resp.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {
                    "result": None,
                    "error": f"HTTP {e.code}: {e.reason}",
                    "connection-error": False,
                }
            if req_json["error"] is not None:
                req_json["error"] = (
                    "Error "
                    + str(req_json["error"]["code"])
                    + ": "
                    + req_json["error"]["message"]
                )
            return req_json
        except urllib.error.URLError as e:
            error_str = "MultiChain is not running: " + str(e.reason)
            req_json = {"result": None, "error": error_str, "connection-error": True}
            return req_json
        except (OSError, ValueError, TypeError) as error:
            error_str = "MultiChain is not running: " + str(error)
            logger.warning("Legacy MultiChain RPC request failed: %s", error)
            return {
                "result": None,
                "error": error_str,
                "connection-error": True,
            }

        resp = req.read()
        try:
            req_json = json.loads(resp.decode("utf-8"), object_pairs_hook=OrderedDict)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            logger.warning("Legacy MultiChain RPC returned invalid JSON: %s", error)
            return {
                "result": None,
                "error": "Invalid JSON response from MultiChain",
                "connection-error": True,
            }

        if req_json is None:
            error_str = "MultiChain connection error"
            req_json = {"result": None, "error": error_str, "connection-error": True}

        return req_json
