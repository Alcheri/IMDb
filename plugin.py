###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###
import requests
import json

# XXX: Install the following packages before running the script:
try:
    from bs4 import BeautifulSoup
except ImportError as ie:
    raise ImportError(f"Cannot import module: {ie}")

import supybot.log as log
from supybot import callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization


_ = PluginInternationalization('IMDb')


def get_imdb_id(imdb_url, movie_name):
    log.info(f"Fetching movie details for {movie_name}")
    try:
        # Set headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
                Chrome/91.0.4472.124 Safari/537.36"
        }

        # Fetch the IMDb search page
        response = requests.get(imdb_url, headers=headers)
        response.raise_for_status()

        # Parse the page content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the script with ID "__NEXT_DATA__"
        script_tag = soup.find("script", id="__NEXT_DATA__", type="application/json")
        if not script_tag:
            raise ValueError("NEXT_DATA script not found.")

        # Load the JSON content from the script
        next_data = json.loads(script_tag.string)

        # Navigate to the `titleResults` -> `results` section
        title_results = (
            next_data.get("props", {})
            .get("pageProps", {})
            .get("titleResults", {})
            .get("results", [])
        )

        # Check if results are present
        if not title_results:
            raise ValueError("No title results found in NEXT_DATA.")

        # Extract the first `tt` ID
        tt_id = title_results[0].get("id")
        return tt_id

    except Exception as e:
        log.error(f"Error: {e}")
        return None


def get_movie_details_by_id(imdb_id):
    movie_url = f"https://www.imdb.com/title/{imdb_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
            Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(movie_url, headers=headers)

    if response.status_code != 200:
        log.error(
            f"Debug: Failed to fetch movie details. HTTP Status: {response.status_code}"
        )
        return {
            "Title": "Unknown Title",
            "Year": "Unknown Year",
            "Plot": "Unknown Plot",
            "Genre": "Unknown Genre",
            "Main Actors": "Unknown Actors",
        }

    soup = BeautifulSoup(response.text, "html.parser")

    # Find JSON-LD data
    json_ld = soup.find("script", type="application/ld+json")
    if not json_ld:
        print("Debug: JSON-LD data not found.")
        return {
            "Title": "Unknown Title",
            "Year": "Unknown Year",
            "Plot": "Unknown Plot",
            "Genre": "Unknown Genre",
            "Main Actors": "Unknown Actors",
        }

    # Parse JSON-LD data
    data = json.loads(json_ld.string)

    # Extract movie details
    title = data.get("name", "Unknown Title")
    year = data.get("datePublished", "Unknown Year")
    if year != "Unknown Year":
        year = year.split("-")[0]  # Extract just the year
    plot = data.get("description", "Unknown Plot")
    genres = ", ".join(data.get("genre", ["Unknown Genre"]))
    actors = ", ".join([actor.get("name", "") for actor in data.get("actor", [])[:5]])

    return {
        "Title": title,
        "Year": year,
        "Plot": plot,
        "Genre": genres,
        "Main Actors": actors,
    }


class IMDb(callbacks.Plugin):
    """
    Add the help for "@plugin help IMDb" here
    This should describe *how* to use this plugin.
    """
    threaded = True

    def __init__(self, irc):
        super().__init__(irc)

    @wrap(["text"])
    def imdb(self, irc, msg, args, movie_name):
        """<movie_name>

        Fetch details of the given movie from IMDb.
        """
        if not self.registryValue("enabled", msg.channel, irc.network):
            return
        search_url = f"https://www.imdb.com/find?q={movie_name}&s=tt"

        imdb_id = get_imdb_id(search_url, movie_name)

        if imdb_id:
            details = get_movie_details_by_id(imdb_id)
            irc.reply("Movie Details:", prefixNick=False)
            for key, value in details.items():
                irc.reply(f"{key}: {value}", prefixNick=False)
        else:
            irc.error(
                "Movie not found on IMDb! Ensure correct spelling or try a different title.",
                prefixNick=False,
            )

Class = IMDb


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
