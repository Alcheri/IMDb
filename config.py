###
# Copyright (c) 2025, Barry Suridge
# All rights reserved.
#
#
###

from supybot import conf, registry

try:
    from supybot.i18n import PluginInternationalization

    _ = PluginInternationalization("IMDb")
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn

    conf.registerPlugin("IMDb", True)


IMDb = conf.registerPlugin("IMDb")

conf.registerGlobalValue(
    IMDb,
    "apiKey",
    registry.String("", _("""Sets the API key for OMDb."""), private=True),
)

# XXX Default: False
conf.registerChannelValue(
    IMDb,
    "enabled",
    registry.Boolean(False, """Should plugin work in this channel?"""),
)

conf.registerChannelValue(
    IMDb,
    "cooldownSeconds",
    registry.NonNegativeInteger(
        5,
        _("""Sets the per-user IMDb lookup cooldown for this channel, in seconds."""),
    ),
)

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
