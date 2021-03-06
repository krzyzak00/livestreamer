from .cache import Cache
from .exceptions import NoStreamsError
from .options import Options

import re

SpecialQualityWeights = {
    "live": 1080,
    "hd": 1080,
    "ehq": 720,
    "hq": 576,
    "sd": 576,
    "sq": 360,
    "mobile_high": 330,
    "mobile_medium": 260,
    "mobile_low": 170,
}


def qualityweight(quality):
    if quality in SpecialQualityWeights:
        return SpecialQualityWeights[quality]

    match = re.match("^(\d+)([k]|[p])?([\+])?$", quality)

    if match:
        if match.group(2) == "k":
            bitrate = int(match.group(1))

            # These calculations are very rough
            if bitrate > 2000:
                return bitrate / 3.4
            elif bitrate > 1000:
                return bitrate / 2.6
            else:
                return bitrate / 1.7

        elif match.group(2) == "p":
            weight = int(match.group(1))

            if match.group(3) == "+":
                weight += 1

            return weight

    return 0


class Plugin(object):
    """
    A plugin can retrieve stream information from the URL specified.

    :param url: URL that the plugin will operate on
    """

    cache = None
    logger = None
    module = "unknown"
    options = Options()
    session = None

    @classmethod
    def bind(cls, session, module):
        cls.cache = Cache(filename="plugin-cache.json",
                          key_prefix=module)
        cls.logger = session.logger.new_module("plugin." + module)
        cls.module = module
        cls.session = session

    def __init__(self, url):
        self.url = url

    @classmethod
    def can_handle_url(cls, url):
        raise NotImplementedError

    @classmethod
    def set_option(cls, key, value):
        cls.options.set(key, value)

    @classmethod
    def get_option(cls, key):
        return cls.options.get(key)

    def get_streams(self, stream_types=["rtmp", "hls", "hds", "http", "akamaihd"],
                    sorting_excludes=None):
        """Attempts to retrieve available streams.

        Returns a :class:`dict` containing the streams, where the key is the
        name of the stream, most commonly the quality and the value is a
        :class:`Stream` object.

        The result can contain the synonyms **best** and **worst** which points
        to the streams which are likely to be of highest and lowest quality
        respectively.

        If multiple streams with the same name are found, the order of streams
        specified in *stream_types* will determine which stream gets to keep the
        name while the rest will be renamed to "<name>_<stream type>".

        :param stream_types: a list of stream types to return.
        :param sorting_excludes: a list of streams to exclude when sorting to
                                 decide best/worst synonyms.

        .. versionchanged:: 1.4.2
           Added *priority* parameter.

        .. versionchanged:: 1.5
           Renamed *priority* to *stream_types* and changed behaviour slightly.

        .. versionchanged:: 1.5
           Added *sorting_excludes* parameter.

        """

        try:
            ostreams = self._get_streams()
        except NoStreamsError:
            return {}

        streams = {}

        def sort_priority(s):
            n = type(s).shortname()
            try:
                p = stream_types.index(n)
            except ValueError:
                p = 99

            return p

        for name, stream in ostreams.items():
            if isinstance(stream, list):
                sstream = sorted(stream, key=sort_priority)

                for i, stream in enumerate(sstream):
                    if i == 0:
                        sname = name
                    else:
                        sname = type(stream).shortname()
                        sname = "{0}_{1}".format(name, sname)

                    streams[sname] = stream
            else:
                if type(stream).shortname() in stream_types:
                    streams[name] = stream

        stream_names = filter(qualityweight, streams.keys())
        sorted_streams = sorted(stream_names, key=qualityweight)

        if sorting_excludes:
            sorted_streams = list(filter(lambda s: s not in sorting_excludes,
                                  sorted_streams))

        if len(sorted_streams) > 0:
            best = sorted_streams[-1]
            worst = sorted_streams[0]
            streams["best"] = streams[best]
            streams["worst"] = streams[worst]

        return streams

    def _get_streams(self):
        raise NotImplementedError


__all__ = ["Plugin"]
