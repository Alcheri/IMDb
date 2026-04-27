###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###
import builtins
import json
import re
import threading
import time
from urllib.parse import quote

import requests

# XXX: Install the following packages before running the script:
try:
    from bs4 import BeautifulSoup
except ImportError as ie:
    raise ImportError(f"Cannot import module: {ie}")

import supybot.ircutils as ircutils
import supybot.log as log
from supybot import callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization

_ = PluginInternationalization("IMDb")

HEADERS = {"User-Agent": "Limnoria-IMDb/1.0 (+https://github.com/Alcheri/IMDb)"}
REQUEST_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 600
MAX_JSON_RESPONSE_BYTES = 256 * 1024
MAX_HTML_RESPONSE_BYTES = 512 * 1024
MAX_LOG_TEXT_LENGTH = 120
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
WHITESPACE_RE = re.compile(r"\s+")
JSON_CONTENT_TYPES = ("application/json", "text/json")
HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
PREFERRED_TYPES = {"movie", "feature", "tvSeries", "tvMiniSeries", "tvMovie"}
DETAIL_DEFAULTS = {
    "Title": "Unknown Title",
    "Year": "Unknown Year",
    "Plot": "Unknown Plot",
    "Genre": "Unknown Genre",
    "Main Actors": "Unknown Actors",
}
DETAIL_LIMITS = {
    "Title": 160,
    "Year": 16,
    "Plot": 320,
    "Genre": 120,
    "Main Actors": 200,
}


def _clean_text(value, limit=None):
    text = ircutils.stripFormatting(str(value or ""))
    text = CONTROL_CHARS_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if limit is not None and len(text) > limit:
        return f"{text[: max(0, limit - 3)].rstrip()}..."
    return text


def _log_safe_text(value):
    cleaned = _clean_text(value, limit=MAX_LOG_TEXT_LENGTH)
    return cleaned or "<empty>"


def _sanitise_details(details):
    safe_details = {}
    source = details or {}
    for key, default in DETAIL_DEFAULTS.items():
        cleaned = _clean_text(source.get(key, default), limit=DETAIL_LIMITS[key])
        safe_details[key] = cleaned or default
    return safe_details


def _content_type_allowed(response, allowed_types):
    content_type = response.headers.get("Content-Type", "")
    content_type = content_type.split(";", 1)[0].strip().lower()
    return builtins.any(
        content_type.startswith(allowed_type) for allowed_type in allowed_types
    )


def _response_within_size_limit(response, max_bytes):
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return False
        except ValueError:
            pass
    return len(response.content) <= max_bytes


def _details_from_suggestion(suggestion_item):
    title = suggestion_item.get("l", DETAIL_DEFAULTS["Title"])
    year = suggestion_item.get("y", DETAIL_DEFAULTS["Year"])
    cast = suggestion_item.get("s", DETAIL_DEFAULTS["Main Actors"])
    kind = (
        suggestion_item.get("q")
        or suggestion_item.get("qid")
        or DETAIL_DEFAULTS["Genre"]
    )

    return _sanitise_details(
        {
            "Title": title,
            "Year": str(year),
            "Plot": "Plot unavailable (IMDb blocked detailed page lookup).",
            "Genre": kind,
            "Main Actors": cast,
        }
    )


def search_imdb_title(movie_name):
    """Return top IMDb suggestion entry for a title search."""
    if not movie_name or not movie_name.strip():
        return None

    query = movie_name.strip()
    first_char = next((ch.lower() for ch in query if ch.isalnum()), "x")
    encoded_query = quote(query)
    suggestion_url = (
        f"https://v3.sg.media-imdb.com/suggestion/{first_char}/{encoded_query}.json"
    )

    log.info(f"Fetching IMDb suggestions for {_log_safe_text(query)}")
    try:
        response = requests.get(
            suggestion_url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"IMDb suggestion request failed: {e}")
        return None

    if not _content_type_allowed(response, JSON_CONTENT_TYPES):
        log.warning("IMDb suggestion response had unexpected content type.")
        return None

    if not _response_within_size_limit(response, MAX_JSON_RESPONSE_BYTES):
        log.warning("IMDb suggestion response exceeded the size limit.")
        return None

    try:
        payload = response.json()
    except ValueError as e:
        log.error(f"IMDb suggestion JSON parse failed: {e}")
        return None

    results = payload.get("d", [])
    if not results:
        return None

    tt_results = [item for item in results if str(item.get("id", "")).startswith("tt")]
    if not tt_results:
        return None

    for item in tt_results:
        if item.get("qid") in PREFERRED_TYPES or item.get("q") in PREFERRED_TYPES:
            return item

    return tt_results[0]


def get_movie_details_by_id(imdb_id, fallback_details=None):
    fallback_details = _sanitise_details(fallback_details or DETAIL_DEFAULTS)
    movie_url = f"https://www.imdb.com/title/{imdb_id}/"
    try:
        response = requests.get(
            movie_url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as e:
        log.warning(f"IMDb title request failed for {imdb_id}: {e}")
        return fallback_details

    if response.status_code != 200:
        log.warning(f"IMDb title page blocked/unavailable ({response.status_code})")
        return fallback_details

    if not _content_type_allowed(response, HTML_CONTENT_TYPES):
        log.warning(
            "IMDb title page had unexpected content type; using fallback details."
        )
        return fallback_details

    if not _response_within_size_limit(response, MAX_HTML_RESPONSE_BYTES):
        log.warning("IMDb title page exceeded the size limit; using fallback details.")
        return fallback_details

    soup = BeautifulSoup(response.text, "html.parser")
    json_ld = soup.find("script", type="application/ld+json")
    if not json_ld:
        log.warning("IMDb JSON-LD data not found; using fallback details.")
        return fallback_details

    try:
        data = json.loads(json_ld.string)
    except (TypeError, json.JSONDecodeError) as e:
        log.warning(f"IMDb JSON-LD parse failed: {e}")
        return fallback_details

    title = data.get("name", fallback_details["Title"])
    year = data.get("datePublished", fallback_details["Year"])
    if year != DETAIL_DEFAULTS["Year"]:
        year = str(year).split("-", 1)[0]
    plot = data.get("description", fallback_details["Plot"])

    genre_value = data.get("genre")
    if isinstance(genre_value, list):
        genres = ", ".join(str(genre) for genre in genre_value)
    elif isinstance(genre_value, str):
        genres = genre_value
    else:
        genres = fallback_details["Genre"]

    actor_list = data.get("actor", [])
    actors = ", ".join(
        actor.get("name", "") for actor in actor_list[:5] if isinstance(actor, dict)
    )
    if not actors:
        actors = fallback_details["Main Actors"]

    return _sanitise_details(
        {
            "Title": title,
            "Year": str(year),
            "Plot": plot,
            "Genre": genres,
            "Main Actors": actors,
        }
    )


class CooldownTracker:
    """Track per-user command cooldowns."""

    def __init__(self):
        self._seen = {}
        self._lock = threading.Lock()

    def remaining(self, key, cooldown_seconds):
        if not cooldown_seconds:
            return 0

        now = time.monotonic()
        with self._lock:
            last_seen = self._seen.get(key)
            if last_seen is None or now - last_seen >= cooldown_seconds:
                self._seen[key] = now
                return 0
            return max(1, int(cooldown_seconds - (now - last_seen)))


class IMDb(callbacks.Plugin):
    """
    A simple plugin to fetch movie details from the Internet Movie Database (IMDb)
    """

    threaded = True

    def __init__(self, irc):
        self.__parent = super(IMDb, self)
        self.__parent.__init__(irc)
        self.cooldowns = CooldownTracker()
        self._cache = {}
        self._cache_lock = threading.Lock()

    def _cache_key(self, movie_name):
        return _clean_text(movie_name).casefold()

    def _get_cached_details(self, movie_name):
        cache_key = self._cache_key(movie_name)
        if not cache_key:
            return None

        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached is None:
                return None
            details, timestamp = cached
            if now - timestamp >= CACHE_TTL_SECONDS:
                del self._cache[cache_key]
                return None
            return details

    def _set_cached_details(self, movie_name, details):
        cache_key = self._cache_key(movie_name)
        if not cache_key:
            return

        with self._cache_lock:
            self._cache[cache_key] = (_sanitise_details(details), time.monotonic())

    def _channel_from_msg(self, msg):
        return getattr(msg, "channel", None) or (
            msg.args[0] if getattr(msg, "args", None) else None
        )

    def _cooldown_remaining(self, irc, msg):
        channel = self._channel_from_msg(msg)
        cooldown = self.registryValue("cooldownSeconds", channel, irc.network)
        key = (irc.network, channel, getattr(msg, "prefix", ""))
        return self.cooldowns.remaining(key, cooldown)

    def _lookup_movie_details(self, movie_name):
        cached_details = self._get_cached_details(movie_name)
        if cached_details is not None:
            return cached_details

        suggestion = search_imdb_title(movie_name)
        if not suggestion:
            return None

        imdb_id = suggestion.get("id")
        if not imdb_id:
            return {}

        fallback_details = _details_from_suggestion(suggestion)
        details = get_movie_details_by_id(imdb_id, fallback_details=fallback_details)
        self._set_cached_details(movie_name, details)
        return details

    @wrap(["text"])
    def imdb(self, irc, msg, args, movie_name):
        """<movie_name>

        Fetch details of the given movie from IMDb.
        """
        channel = self._channel_from_msg(msg)
        if not self.registryValue("enabled", channel, irc.network):
            return

        details = self._get_cached_details(movie_name)
        if details is None:
            cooldown = self._cooldown_remaining(irc, msg)
            if cooldown:
                irc.error(
                    f"Please wait {cooldown}s before sending another IMDb request.",
                    prefixNick=False,
                )
                return
            details = self._lookup_movie_details(movie_name)

        if details == {}:
            irc.error(
                "Movie found, but IMDb did not provide a valid title ID.",
                prefixNick=False,
            )
            return

        if details:
            irc.reply("Top Match Details:", prefixNick=False)
            for key, value in _sanitise_details(details).items():
                irc.reply(f"{key}: {value}", prefixNick=False)
            return

        irc.error(
            "Movie not found on IMDb! Ensure correct spelling or try a different title.",
            prefixNick=False,
        )


Class = IMDb


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
