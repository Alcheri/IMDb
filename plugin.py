###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###
import builtins
import re
import threading
import time

import requests

import supybot.ircutils as ircutils
import supybot.log as log
from supybot import callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization

_ = PluginInternationalization("IMDb")

HEADERS = {"User-Agent": "Limnoria-IMDb/1.1 (+https://github.com/Alcheri/IMDb)"}
OMDB_API_URL = "https://www.omdbapi.com/"
REQUEST_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 600
MAX_JSON_RESPONSE_BYTES = 256 * 1024
MAX_LOG_TEXT_LENGTH = 120
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
WHITESPACE_RE = re.compile(r"\s+")
JSON_CONTENT_TYPES = ("application/json", "text/json")
PREFERRED_TYPES = {"movie", "series", "episode"}
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


def _coalesce_omdb_value(value, default):
    cleaned = _clean_text(value)
    if not cleaned or cleaned.upper() == "N/A":
        return default
    return cleaned


def _request_omdb(params):
    try:
        response = requests.get(
            OMDB_API_URL,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"OMDb request failed: {e}")
        return None

    if not _content_type_allowed(response, JSON_CONTENT_TYPES):
        log.warning("OMDb response had unexpected content type.")
        return None

    if not _response_within_size_limit(response, MAX_JSON_RESPONSE_BYTES):
        log.warning("OMDb response exceeded the size limit.")
        return None

    try:
        return response.json()
    except ValueError as e:
        log.error(f"OMDb JSON parse failed: {e}")
        return None


def _details_from_search_result(search_item):
    title = search_item.get("Title", DETAIL_DEFAULTS["Title"])
    year = search_item.get("Year", DETAIL_DEFAULTS["Year"])
    kind = search_item.get("Type", DETAIL_DEFAULTS["Genre"]).title()

    return _sanitise_details(
        {
            "Title": title,
            "Year": str(year),
            "Plot": "Plot unavailable (OMDb detail lookup failed).",
            "Genre": kind,
            "Main Actors": DETAIL_DEFAULTS["Main Actors"],
        }
    )


def search_omdb_title(api_key, movie_name):
    """Return the top OMDb search entry for a title search."""
    if not movie_name or not movie_name.strip():
        return None

    query = movie_name.strip()
    params = {"apikey": api_key, "s": query}

    log.info(f"Fetching OMDb search results for {_log_safe_text(query)}")
    payload = _request_omdb(params)
    if not payload:
        return None

    if payload.get("Response") != "True":
        log.warning(f"OMDb search did not return a match for {_log_safe_text(query)}.")
        return None

    results = payload.get("Search", [])
    if not results:
        return None

    tt_results = [
        item for item in results if str(item.get("imdbID", "")).startswith("tt")
    ]
    if not tt_results:
        return None

    for item in tt_results:
        if item.get("Type") in PREFERRED_TYPES:
            return item

    return tt_results[0]


def get_movie_details_by_id(api_key, imdb_id, fallback_details=None):
    fallback_details = _sanitise_details(fallback_details or DETAIL_DEFAULTS)
    payload = _request_omdb({"apikey": api_key, "i": imdb_id, "plot": "short"})
    if not payload:
        return fallback_details

    if payload.get("Response") != "True":
        error = payload.get("Error", "Unknown OMDb error")
        log.warning(f"OMDb detail lookup failed for {imdb_id}: {error}")
        return fallback_details

    title = _coalesce_omdb_value(payload.get("Title"), fallback_details["Title"])
    year = _coalesce_omdb_value(payload.get("Year"), fallback_details["Year"])
    plot = _coalesce_omdb_value(payload.get("Plot"), fallback_details["Plot"])
    genres = _coalesce_omdb_value(payload.get("Genre"), fallback_details["Genre"])
    actors = _coalesce_omdb_value(payload.get("Actors"), fallback_details["Main Actors"])

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
    A simple plugin to fetch title details from OMDb while keeping the IMDb command
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

    def _lookup_movie_details(self, movie_name, api_key):
        cached_details = self._get_cached_details(movie_name)
        if cached_details is not None:
            return cached_details

        search_result = search_omdb_title(api_key, movie_name)
        if not search_result:
            return None

        imdb_id = search_result.get("imdbID")
        if not imdb_id:
            return {}

        fallback_details = _details_from_search_result(search_result)
        details = get_movie_details_by_id(
            api_key, imdb_id, fallback_details=fallback_details
        )
        self._set_cached_details(movie_name, details)
        return details

    @wrap(["text"])
    def imdb(self, irc, msg, args, movie_name):
        """<movie_name>

        Fetch details of the given title from OMDb.
        """
        channel = self._channel_from_msg(msg)
        if not self.registryValue("enabled", channel, irc.network):
            return

        api_key = self.registryValue("apiKey").strip()
        if not api_key:
            irc.error("OMDb API key is not configured for IMDb.", prefixNick=False)
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
            details = self._lookup_movie_details(movie_name, api_key)

        if details == {}:
            irc.error(
                "Movie found, but OMDb did not provide a valid IMDb title ID.",
                prefixNick=False,
            )
            return

        if details:
            irc.reply("Top Match Details:", prefixNick=False)
            for key, value in _sanitise_details(details).items():
                irc.reply(f"{key}: {value}", prefixNick=False)
            return

        irc.error(
            "Movie not found via OMDb! Ensure correct spelling or try a different title.",
            prefixNick=False,
        )


Class = IMDb


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
