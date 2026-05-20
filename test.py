###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import supybot.test as supybot_test

try:
    from . import plugin as imdb_plugin
except ImportError:
    import plugin as imdb_plugin


class IMDbTestCase(supybot_test.PluginTestCase):
    __test__ = False
    plugins = ("IMDb",)


class TestIMDbSecurity(unittest.TestCase):
    def setUp(self):
        self.plugin = imdb_plugin.IMDb(MagicMock())

    def test_plugin_module_exports_class(self):
        self.assertTrue(hasattr(imdb_plugin, "Class"))

    def test_clean_text_removes_control_characters_and_truncates(self):
        text = "Title\x02\nwith\tcontrol characters"
        cleaned = imdb_plugin._clean_text(text, limit=12)

        self.assertEqual(cleaned, "Title wit...")

    def test_sanitise_details_normalises_untrusted_values(self):
        details = imdb_plugin._sanitise_details(
            {
                "Title": "The\x02 Matrix\nReloaded",
                "Year": "2003",
                "Plot": "Plot\twith\nweird spacing",
                "Genre": "Action\x03",
                "Main Actors": "Keanu Reeves\nCarrie-Anne Moss",
            }
        )

        self.assertEqual(details["Title"], "The Matrix Reloaded")
        self.assertEqual(details["Plot"], "Plot with weird spacing")
        self.assertEqual(details["Genre"], "Action")
        self.assertEqual(
            details["Main Actors"], "Keanu Reeves Carrie-Anne Moss"
        )

    def test_search_omdb_title_rejects_unexpected_content_type(self):
        response = MagicMock()
        response.headers = {"Content-Type": "text/html"}
        response.content = b"<html></html>"
        response.raise_for_status.return_value = None

        with patch.object(imdb_plugin.requests, "get", return_value=response):
            with patch.object(imdb_plugin.log, "warning") as mock_warning:
                result = imdb_plugin.search_omdb_title("abc123", "the matrix")

        self.assertIsNone(result)
        mock_warning.assert_called_once()

    def test_get_movie_details_by_id_returns_fallback_for_oversized_json(self):
        response = MagicMock()
        response.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(imdb_plugin.MAX_JSON_RESPONSE_BYTES + 1),
        }
        response.content = b"x"
        response.raise_for_status.return_value = None

        fallback = {
            "Title": "Known Title",
            "Year": "1999",
            "Plot": "Known Plot",
            "Genre": "Known Genre",
            "Main Actors": "Known Actors",
        }

        with patch.object(imdb_plugin.requests, "get", return_value=response):
            result = imdb_plugin.get_movie_details_by_id(
                "abc123", "tt0133093", fallback_details=fallback
            )

        self.assertEqual(result, fallback)

    def test_request_failure_logging_does_not_include_api_key_url(self):
        response = MagicMock()
        response.status_code = 401
        error = imdb_plugin.requests.HTTPError(
            "401 Client Error: Unauthorized for url: "
            "https://www.omdbapi.com/?apikey=secret&s=matrix",
            response=response,
        )

        with (
            patch.object(imdb_plugin.requests, "get", side_effect=error),
            patch.object(imdb_plugin.log, "error") as mock_error,
        ):
            result = imdb_plugin.search_omdb_title("secret", "matrix")

        self.assertIsNone(result)
        logged = mock_error.call_args.args[0]
        self.assertIn("HTTP status 401", logged)
        self.assertNotIn("secret", logged)
        self.assertNotIn("apikey", logged)

    def test_get_movie_details_by_id_sanitises_parsed_values(self):
        long_plot = "A" * (imdb_plugin.DETAIL_LIMITS["Plot"] + 50)
        response = MagicMock()
        response.headers = {"Content-Type": "application/json; charset=utf-8"}
        response.content = b"ok"
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "Title": "The\x02 Matrix\nReloaded",
            "Year": "2003",
            "Plot": long_plot,
            "Genre": "Action, Sci-Fi",
            "Actors": "Keanu\nReeves, Carrie-Anne Moss",
            "Response": "True",
        }

        with patch.object(imdb_plugin.requests, "get", return_value=response):
            result = imdb_plugin.get_movie_details_by_id("abc123", "tt0234215")

        self.assertEqual(result["Title"], "The Matrix Reloaded")
        self.assertEqual(result["Year"], "2003")
        self.assertEqual(result["Genre"], "Action, Sci-Fi")
        self.assertEqual(
            result["Main Actors"], "Keanu Reeves, Carrie-Anne Moss"
        )
        self.assertLessEqual(
            len(result["Plot"]), imdb_plugin.DETAIL_LIMITS["Plot"]
        )
        self.assertTrue(result["Plot"].endswith("..."))

    def test_lookup_movie_details_uses_cache(self):
        suggestion = {
            "imdbID": "tt0133093",
            "Title": "The Matrix",
            "Year": "1999",
            "Type": "movie",
        }
        details = {
            "Title": "The Matrix",
            "Year": "1999",
            "Plot": "A computer hacker learns the world is a simulation.",
            "Genre": "Action, Sci-Fi",
            "Main Actors": "Keanu Reeves, Carrie-Anne Moss",
        }

        with patch.object(
            imdb_plugin, "search_omdb_title", return_value=suggestion
        ) as mock_search:
            with patch.object(
                imdb_plugin, "get_movie_details_by_id", return_value=details
            ) as mock_details:
                first = self.plugin._lookup_movie_details(
                    "The Matrix", "abc123"
                )
                second = self.plugin._lookup_movie_details(
                    "The Matrix", "abc123"
                )

        self.assertEqual(first, details)
        self.assertEqual(second, details)
        mock_search.assert_called_once_with("abc123", "The Matrix")
        mock_details.assert_called_once_with(
            "abc123",
            "tt0133093",
            fallback_details={
                "Title": "The Matrix",
                "Year": "1999",
                "Plot": "Plot unavailable (OMDb detail lookup failed).",
                "Genre": "Movie",
                "Main Actors": "Unknown Actors",
            },
        )

    def test_validate_movie_name_rejects_overlong_title(self):
        with self.assertRaises(ValueError) as context:
            imdb_plugin._validate_movie_name(
                "x" * (imdb_plugin.MAX_TITLE_LENGTH + 1)
            )

        self.assertEqual(str(context.exception), "Movie title is too long.")

    def test_cache_evicts_oldest_entry_when_full(self):
        self.plugin._cache = {
            f"title-{index}": (
                imdb_plugin.DETAIL_DEFAULTS,
                float(index),
            )
            for index in range(imdb_plugin.MAX_CACHE_ENTRIES)
        }

        with patch.object(imdb_plugin.time, "monotonic", return_value=100.0):
            self.plugin._set_cached_details(
                "new title", imdb_plugin.DETAIL_DEFAULTS
            )

        self.assertEqual(
            len(self.plugin._cache), imdb_plugin.MAX_CACHE_ENTRIES
        )
        self.assertNotIn("title-0", self.plugin._cache)
        self.assertIn("new title", self.plugin._cache)

    def test_cooldown_is_per_user(self):
        self.plugin.registryValue = lambda name, *args: 5
        irc = SimpleNamespace(network="testnet")
        msg = SimpleNamespace(
            channel="#test", prefix="nick!user@example", args=["#test"]
        )

        self.assertEqual(self.plugin._cooldown_remaining(irc, msg), 0)
        self.assertGreaterEqual(self.plugin._cooldown_remaining(irc, msg), 1)


if __name__ == "__main__":
    unittest.main()


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
