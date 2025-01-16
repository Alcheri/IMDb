###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###

"""
IMDb: Fetch movie details from IMDB.
"""

import sys
import supybot
from supybot import world

__version__ = "15012025"

__author__ = supybot.Author("Barry Suridge", "Alcheri", "barry.suridge@gmail.com")

__contributors__ = {}

__url__ = "https://github.com/Alcheri/IMDb"

from . import config
from . import plugin
from importlib import reload

# In case we're being reloaded.
reload(config)
reload(plugin)
# Add more reloads here if you add third-party modules and want them to be
# reloaded when this plugin is reloaded.  Don't forget to import them as well!

if world.testing:
    from . import test

Class = plugin.Class
configure = config.configure


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
