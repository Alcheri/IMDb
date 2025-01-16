###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###

from supybot.setup import plugin_setup

plugin_setup(
    "IMDb",
    install_requires=[
        "beautifulsoup4",
    ],
)
