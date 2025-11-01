#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stream handler for MultiChain Explorer."""

import json
import logging
from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template

logger = logging.getLogger(__name__)


class StreamHandler(BaseHandler):
    """Handler for stream-related requests."""

    def handle_streams_list(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List all streams."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get streams - service.rpc() returns the result directly
        try:
            streams = service.rpc("liststreams", ["*", True])
            if not streams:
                streams = []
            else:
                # Ensure each stream has proper item counts
                for stream in streams:
                    # Get item count for each stream if not present
                    if "items" not in stream or not isinstance(stream.get("items"), (int, float)):
                        try:
                            # Get actual count from liststreamitems
                            stream_items = service.rpc(
                                "liststreamitems", [stream["name"], False, 1]
                            )
                            stream["items"] = len(stream_items) if stream_items else 0
                        except:
                            stream["items"] = 0

                    if "confirmed" not in stream or not isinstance(
                        stream.get("confirmed"), (int, float)
                    ):
                        stream["confirmed"] = stream.get("items", 0)

        except Exception as e:
            logger.error(f"Error fetching streams: {e}")
            streams = []

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(streams),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_streams = streams[page_info["start"] : page_info["start"] + page_info["count"]]

        html = render_template(
            "pages/streams.html",
            {
                "title": f"Streams - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "streams": paginated_streams,
                **self.unpack_pagination(page_info, f"/{chain.config['path-name']}/streams"),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_stream_detail(
        self, chain: Any, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show stream details."""
        service = BlockchainService(chain)

        # Get stream info - service.rpc() returns the result directly (a list)
        try:
            streams = service.rpc("liststreams", [stream_name, True])
            if not streams or len(streams) == 0:
                return self.not_found(f"Stream {stream_name} not found")
            stream = streams[0]

            # Fix items count if it's not a number
            if "items" not in stream or not isinstance(stream.get("items"), (int, float)):
                try:
                    # Get actual count from liststreamitems
                    stream_items = service.rpc("liststreamitems", [stream_name, False, 1])
                    stream["items"] = len(stream_items) if stream_items else 0
                except:
                    stream["items"] = 0

            if "confirmed" not in stream or not isinstance(stream.get("confirmed"), (int, float)):
                stream["confirmed"] = stream.get("items", 0)

        except Exception as e:
            logger.error(f"Error fetching stream {stream_name}: {e}")
            return self.not_found(f"Stream {stream_name} not found")

        html = render_template(
            "pages/stream.html",
            {
                "title": f"Stream {stream_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream": stream,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_stream_items(
        self, chain: Any, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List items in a stream."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get item count - service.rpc() returns result directly
        try:
            # liststreamitems returns a list of items
            count_items = service.rpc("liststreamitems", [stream_name, False, 1, 0])
            total_count = len(count_items) if count_items else 0
        except Exception as e:
            logger.error(f"Error getting stream item count: {e}")
            total_count = 0

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=total_count,
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        items = []
        if total_count > 0:
            try:
                items = service.rpc(
                    "liststreamitems",
                    [stream_name, True, page_info["count"], page_info["start"]],
                )
            except Exception as e:
                logger.error(f"Error fetching stream items: {e}")
                items = []

        html = render_template(
            "pages/stream_items.html",
            {
                "title": f"Items - {stream_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream_name": stream_name,
                "items": items,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/stream/{stream_name}/items"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_stream_keys(
        self, chain: Any, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List keys in a stream."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get keys - service.rpc() returns result directly
        try:
            keys = service.rpc("liststreamkeys", [stream_name, "*", False, 1000, 0])
            if not keys:
                keys = []
        except Exception as e:
            logger.error(f"Error fetching stream keys: {e}")
            keys = []

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(keys),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_keys = keys[page_info["start"] : page_info["start"] + page_info["count"]]

        html = render_template(
            "pages/stream_keys.html",
            {
                "title": f"Keys - {stream_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream_name": stream_name,
                "keys": paginated_keys,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/stream/{stream_name}/keys"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_stream_publishers(
        self, chain: Any, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List publishers of a stream."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get publishers - service.rpc() returns result directly
        try:
            publishers = service.rpc("liststreampublishers", [stream_name, "*", False, 1000, 0])
            if not publishers:
                publishers = []
        except Exception as e:
            logger.error(f"Error fetching stream publishers: {e}")
            publishers = []

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(publishers),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_publishers = publishers[
            page_info["start"] : page_info["start"] + page_info["count"]
        ]

        html = render_template(
            "pages/stream_publishers.html",
            {
                "title": f"Publishers - {stream_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream_name": stream_name,
                "publishers": paginated_publishers,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/stream/{stream_name}/publishers"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_stream_permissions(
        self, chain: Any, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show permissions for a stream."""
        service = BlockchainService(chain)

        # Get stream permissions - service.rpc() returns result directly
        try:
            permissions = service.rpc("listpermissions", [stream_name])
            if not permissions:
                permissions = []
        except Exception as e:
            logger.error(f"Error fetching stream permissions: {e}")
            permissions = []

        html = render_template(
            "pages/stream_permissions.html",
            {
                "title": f"Permissions - {stream_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream_name": stream_name,
                "permissions": permissions,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_key_items(
        self, chain: Any, stream_name: str, key: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List items for a specific key in a stream."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get items for key - service.rpc() returns result directly
        try:
            count_items = service.rpc("liststreamkeyitems", [stream_name, key, False, 1, 0])
            total_count = len(count_items) if count_items else 0
        except Exception as e:
            logger.error(f"Error getting key item count: {e}")
            total_count = 0

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=total_count,
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        items = []
        if total_count > 0:
            try:
                items = service.rpc(
                    "liststreamkeyitems",
                    [stream_name, key, True, page_info["count"], page_info["start"]],
                )
            except Exception as e:
                logger.error(f"Error fetching key items: {e}")
                items = []

        html = render_template(
            "pages/stream_key_items.html",
            {
                "title": f"Key Items - {stream_name} - {key}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream_name": stream_name,
                "key": key,
                "items": items,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/stream/{stream_name}/key/{key}/items"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_publisher_items(
        self, chain: Any, stream_name: str, publisher: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List items from a specific publisher in a stream."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get items from publisher - service.rpc() returns result directly
        try:
            count_items = service.rpc(
                "liststreampublisheritems", [stream_name, publisher, False, 1, 0]
            )
            total_count = len(count_items) if count_items else 0
        except Exception as e:
            logger.error(f"Error getting publisher item count: {e}")
            total_count = 0

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=total_count,
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        items = []
        if total_count > 0:
            try:
                items = service.rpc(
                    "liststreampublisheritems",
                    [stream_name, publisher, True, page_info["count"], page_info["start"]],
                )
            except Exception as e:
                logger.error(f"Error fetching publisher items: {e}")
                items = []

        html = render_template(
            "pages/stream_publisher_items.html",
            {
                "title": f"Publisher Items - {stream_name} - {publisher[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "stream_name": stream_name,
                "publisher": publisher,
                "items": items,
                **self.unpack_pagination(
                    page_info,
                    f"/{chain.config['path-name']}/stream/{stream_name}/publisher/{publisher}/items",
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
