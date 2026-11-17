#!/usr/bin/env python3
"""End-to-end test of /api/queue "tags" against the simulator.

Starts the simulator (run_sim.sh) on a fresh config, drives it over HTTP and
checks every answer, then stops it and scans the sanitizer log. Everything has
to finish inside SonixLink's 60 s boot grace: the simulator host has no wlan0,
so SonixLink switches itself off a minute after start.
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

SCRATCH = os.environ.get("SONIX_TEST_DIR", os.getcwd())
SIM = SCRATCH + "/sim"
BIN = sys.argv[1] if len(sys.argv) > 1 else "sonix_tags_asan"
LOG = SIM + "/run-queue-test.log"
BASE = "http://127.0.0.1:7800"
CARD = "/mnt/sd_0"
TIDAL = CARD + "/.local/tidal-cache"
QOBUZ = CARD + "/.local/qobuz-cache"
LIB1 = CARD + "/Music/Test Artist/Test Album/01 Library Song.flac"
LIB2 = CARD + "/Music/Test Artist/Test Album/02 Second Song.flac"
KEPT = CARD + "/Podcast/My Show/2026-10-05 Episode.flac"
SIDECAR_333 = SIM + "/card/.local/tidal-cache/333333333.flac.tags"

failures = []


def check(cond, what):
    print(("  ok    " if cond else "  FAIL  ") + what)
    if not cond:
        failures.append(what)


def http(path, data=None, timeout=5):
    req = urllib.request.Request(BASE + path, data=data, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def command(query, body=None):
    return http("/api/command?" + query, data=body if body is not None else b"")


def queue(frm=None):
    """A window that is ready: retries while the player answers pending."""
    path = "/api/queue" + ("" if frm is None else "?from=%d" % frm)
    for _ in range(20):
        d = json.loads(http(path).decode("utf-8"))  # strict UTF-8 and JSON
        if not d["pending"]:
            return d
        time.sleep(0.2)
    raise RuntimeError("queue stays pending")


def wait_queue_count(n):
    for _ in range(30):
        if json.loads(http("/api/state"))["queue_count"] == n:
            return
        time.sleep(0.2)
    raise RuntimeError("queue never reached %d entries" % n)


def start():
    with open(SIM + "/config/device_config.ini", "w") as f:
        f.write("[ui]\nlanguage = English\n\n[clock]\nconfigured = true\n\n[wireless]\nsonixlink = 1\n")
    proc = subprocess.Popen(["sh", SCRATCH + "/run_sim.sh", BIN, LOG])
    for _ in range(80):
        try:
            if http("/api/ping", timeout=1) == b"ok":
                return proc
        except OSError:
            pass
        time.sleep(0.25)
    raise RuntimeError("simulator did not come up")


def stop(proc):
    subprocess.run(["pkill", "-x", BIN[:15]])
    proc.wait(timeout=10)


def main():
    os.makedirs(os.path.dirname(SIDECAR_333), exist_ok=True)
    if os.path.exists(SIDECAR_333):
        os.remove(SIDECAR_333)
    proc = start()
    t0 = time.monotonic()
    try:
        print("library scan")
        command("do=scan")
        for _ in range(50):
            st = json.loads(http("/api/state"))
            if not st["scanning"] and st["tracks"] == 2:
                break
            time.sleep(0.2)
        check(st["tracks"] == 2, "the index holds the 2 library tracks and none of the cached files")

        print("library-only queue: answers exactly as before")
        command("do=play_path&list=album&value=Test%20Album&path=" + urllib.parse.quote(LIB1))
        wait_queue_count(2)
        d = queue()
        check("tags" not in d, "no \"tags\" key when no entry is streamed")
        check(d["paths"] == [LIB1, LIB2], "paths unchanged")

        print("mixed queue: library track playing, streamed tracks queued next")
        streamed = [TIDAL + "/111111111.flac", TIDAL + "/222222222.flac", TIDAL + "/333333333.flac",
                    QOBUZ + "/444444444.flac", KEPT]
        command("do=queue_next", ("\n".join(streamed) + "\n").encode())
        wait_queue_count(7)
        d = queue(0)
        check(d["paths"] == [LIB1] + streamed + [LIB2], "paths in queue order")
        check(len(d["tags"]) == len(d["paths"]), "one tags entry per path")
        t = d["tags"]
        check(t[0] is None and t[6] is None, "library entries are null")
        check(t[1] == {"title": 'Bohemian "Rhapsody" \\ Live', "artist": "Queen", "album": "A Night at the Opera"},
              "Tidal sidecar with quotes and a backslash round-trips")
        check(t[2] == {"title": "Ελληνικά — 日本語 ✓", "artist": "Σωκράτης", "album": "Ünïcödé"},
              "Tidal sidecar in Greek, Japanese and accents round-trips")
        check(t[3] is None, "Tidal file without a sidecar is null")
        check(t[4] == {"title": "Qobuz Track", "artist": "Qobuz Artist", "album": "Qobuz Album"}, "Qobuz sidecar")
        check(t[5] == {"title": "Episode 12: Tests", "artist": "My Show", "album": "My Show"},
              "kept podcast episode (Podcast folder, not in the index)")

        print("paging: ?from=N keeps tags aligned with paths")
        d = queue(2)
        check(d["first"] == 2 and len(d["tags"]) == len(d["paths"]) == 5, "window from 2 has 5 entries, 5 tags")
        check(d["tags"][0]["title"].startswith("Ελληνικά") and d["tags"][1] is None and d["tags"][4] is None,
              "the tags belong to the paths beside them")
        d = queue(6)
        check(d["paths"] == [LIB2] and "tags" not in d, "a window holding only library entries has no tags")

        print("malformed sidecars (re-read on every request)")
        cases = [
            ("300-character title", "title=" + "A" * 300 + "\nartist=Long\n",
             lambda x: x["title"] == "A" * 255 and x["artist"] == "Long"),
            ("CRLF line endings", "title=Windows Line\r\nartist=CRLF Artist\r\n",
             lambda x: x["title"] == "Windows Line" and x["artist"] == "CRLF Artist"),
            ("no final newline", "title=No Newline\nartist=At End",
             lambda x: x["artist"] == "At End"),
            ("'=' inside a value", "title=a=b=c\n", lambda x: x["title"] == "a=b=c"),
            ("control characters", "title=Tab\there\x01x\n", lambda x: "\x01" not in x["title"]),
            ("invalid UTF-8", b"title=Bad \xff\xfe \xc3\n", lambda x: x["title"].startswith("Bad")),
            ("empty title", "title=\nartist=Only Artist\n", lambda x: x["title"] == "" and x["artist"] == "Only Artist"),
            ("empty file", "", lambda x: x == {"title": "", "artist": "", "album": ""}),
            ("binary garbage", bytes(range(256)) * 8, lambda x: isinstance(x["title"], str)),
        ]
        for name, content, ok in cases:
            with open(SIDECAR_333, "wb") as f:
                f.write(content if isinstance(content, bytes) else content.encode())
            d = queue(0)  # json.loads above is strict: invalid JSON or UTF-8 raises
            check(d["tags"][3] is not None and ok(d["tags"][3]), name + ": valid JSON, sane value")
        os.remove(SIDECAR_333)

        print("stress: parallel readers while the queue is reordered and skipped")
        stop_at = time.monotonic() + 12
        bad = []
        counts = {"reads": 0, "writes": 0}

        def reader(path):
            while time.monotonic() < stop_at:
                try:
                    d = json.loads(http(path).decode("utf-8"))
                    if path.startswith("/api/queue") and not d["pending"] and "tags" in d \
                            and len(d["tags"]) != len(d["paths"]):
                        bad.append("length mismatch")
                    counts["reads"] += 1
                except Exception as e:  # noqa: BLE001 - any failure is a finding
                    bad.append(repr(e))

        def writer():
            i = 0
            while time.monotonic() < stop_at:
                try:
                    rev = json.loads(http("/api/state"))["queue_revision"]
                    command("do=queue_move&from=%d&to=%d&rev=%d" % (1 + i % 4, 1 + (i + 2) % 4, rev))
                    if i % 7 == 6:
                        command("do=queue_index&value=0")
                    counts["writes"] += 1
                except Exception as e:  # noqa: BLE001
                    bad.append(repr(e))
                i += 1
                time.sleep(0.02)

        threads = [threading.Thread(target=reader, args=(p,)) for p in
                   ("/api/queue", "/api/queue?from=1", "/api/queue?from=3", "/api/state")]
        threads.append(threading.Thread(target=writer))
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        check(not bad, "%d reads, %d queue changes, no errors%s" % (counts["reads"], counts["writes"],
                                                                     "" if not bad else ": " + bad[0]))
        check(http("/api/ping") == b"ok", "still answering afterwards")
        print("  (all of the above took %.1f s of the 60 s grace)" % (time.monotonic() - t0))
    finally:
        stop(proc)

    print("sanitizers")
    log = open(LOG, errors="replace").read()
    reports = [b for b in log.split("\n\n") if "AddressSanitizer" in b or "runtime error" in b]
    ours = [r for r in reports if any(s in r for s in ("sonixlink.c", "metadata.c", "gui/wireless"))]
    print("  %d report(s) in the whole run; in the changed files: %d" % (len(reports), len(ours)))
    for r in reports:
        first = next((l for l in r.splitlines() if "runtime error" in l or "ERROR:" in l), r.splitlines()[0])
        print("    " + first.split("/sonix-player/")[-1][:150])
    check(not ours, "no sanitizer report from the changed code")

    print("\n%s: %d failure(s)" % ("PASS" if not failures else "FAIL", len(failures)))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
