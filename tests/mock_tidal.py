#!/usr/bin/env python3
"""A stand-in for api.tidal.com/v1 with canned answers, for the simulator.

The response shapes follow the real API: the user's own playlists come flat
({"items":[<playlist>]}), favourites come wrapped ({"items":[{"created":...,
"item":<playlist>}]}). Every request is logged to mock_tidal.log.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LOG = sys.argv[2]
USER = "42"


def playlist(uuid, title, creator, tracks):
    who = {"id": 0} if creator == "TIDAL" else {"id": 7, "name": creator}
    return {"uuid": uuid, "title": title, "numberOfTracks": tracks, "creator": who,
            "type": "EDITORIAL" if creator == "TIDAL" else "USER", "squareImage": None, "image": None,
            "duration": tracks * 200, "lastUpdated": "2026-10-01T10:00:00.000+0000"}


OWN = [playlist("0000aaaa-0000-4000-8000-000000000001", "Road trip", "Bill", 2)]
FAVOURITES = [
    playlist("1111bbbb-0000-4000-8000-000000000002", "Jazz Classics", "TIDAL", 3),
    playlist("2222cccc-0000-4000-8000-000000000003", "Friday Night Mix", "Someone Else", 2),
]


def track(tid, title, artist, album, n):
    return {"id": tid, "title": title, "duration": 245, "trackNumber": n, "allowStreaming": True,
            "streamReady": True, "audioQuality": "LOSSLESS", "artist": {"id": 1, "name": artist},
            "artists": [{"id": 1, "name": artist}], "album": {"id": 900 + n, "title": album, "cover": None}}


TRACKS = {
    "1111bbbb-0000-4000-8000-000000000002": [track(501, "So What", "Miles Davis", "Kind of Blue", 1),
                                             track(502, "Take Five", "Dave Brubeck", "Time Out", 2),
                                             track(503, "Naima", "John Coltrane", "Giant Steps", 3)],
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        with open(LOG, "a") as f:
            f.write("GET %s auth=%s\n" % (self.path, self.headers.get("Authorization", "")))
        p = url.path
        if p == "/v1/users/%s/favorites/playlists" % USER:
            import os
            mode = open(LOG + ".mode").read().strip() if os.path.exists(LOG + ".mode") else ""
            if mode == "empty":
                return self.reply(200, {"limit": 50, "offset": 0, "totalNumberOfItems": 0, "items": []})
            if mode == "error":
                return self.reply(500, {"status": 500, "subStatus": 999, "userMessage": "Internal server error"})
            items = [{"created": "2026-0%d-01T10:00:00.000+0000" % (9 - i), "item": pl} for i, pl in enumerate(FAVOURITES)]
            return self.reply(200, {"limit": 50, "offset": 0, "totalNumberOfItems": len(items), "items": items})
        if p == "/v1/users/%s/playlists" % USER:
            return self.reply(200, {"limit": 50, "offset": 0, "totalNumberOfItems": len(OWN), "items": OWN})
        if p.startswith("/v1/users/%s/favorites/" % USER):
            return self.reply(200, {"limit": 50, "offset": 0, "totalNumberOfItems": 0, "items": []})
        if p.startswith("/v1/playlists/") and p.endswith(("/tracks", "/items")):
            uuid = p.split("/")[3]
            tracks = TRACKS.get(uuid, [])
            if p.endswith("/items"):
                tracks = [{"item": t, "type": "track"} for t in tracks]
            return self.reply(200, {"limit": 50, "offset": 0, "totalNumberOfItems": len(tracks), "items": tracks})
        return self.reply(404, {"status": 404, "subStatus": 2001, "userMessage": "not in the mock"})

    def do_POST(self):
        with open(LOG, "a") as f:
            f.write("POST %s\n" % self.path)
        self.reply(404, {"status": 404, "userMessage": "not in the mock"})


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
