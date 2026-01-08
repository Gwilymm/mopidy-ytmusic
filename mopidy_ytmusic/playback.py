import yt_dlp
from mopidy import backend

from mopidy_ytmusic import logger


class YTMusicPlaybackProvider(backend.PlaybackProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_id = None

    def change_track(self, track):
        """
        This is dumb.  This is an exact copy of the original method
        with the addition of the call to set_metadata.  Why doesn't
        mopidy just do this?
        """
        uri = self.translate_uri(track.uri)
        if uri != track.uri:
            logger.debug("Backend translated URI from %s to %s", track.uri, uri)
        if not uri:
            return False
        self.audio.set_uri(
            uri,
            live_stream=self.is_live(uri),
            download=self.should_download(uri),
        ).get()
        self.audio.set_metadata(track)
        return True

    def translate_uri(self, uri):
        logger.debug('YTMusic PlaybackProvider.translate_uri "%s"', uri)

        if "ytmusic:track:" not in uri:
            return None

        try:
            bId = uri.split(":")[2]
            self.last_id = bId
            return self._get_track(bId)
        except Exception as e:
            logger.error('translate_uri error "%s"', str(e))
            return None

    def _get_track(self, bId):
        # Use yt-dlp to extract stream URLs - it handles signature decoding internally
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'cookiefile': None,
        }
        
        url = f"https://music.youtube.com/watch?v={bId}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info or 'formats' not in info:
                    logger.error("YTMusic: No formats found for %s", bId)
                    return None
                
                # Build a dict of available formats by itag
                formats_by_itag = {}
                for fmt in info['formats']:
                    if 'format_id' in fmt and fmt.get('acodec') != 'none':
                        formats_by_itag[fmt['format_id']] = fmt
                
                # Try to find preferred stream by itag
                selected_format = None
                if self.backend.stream_preference:
                    for pref in self.backend.stream_preference:
                        if str(pref) in formats_by_itag:
                            selected_format = formats_by_itag[str(pref)]
                            logger.debug("YTMusic: Found preference stream %s", pref)
                            break
                
                # Fallback: find best audio-only format
                if not selected_format:
                    audio_formats = [
                        f for f in info['formats']
                        if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
                    ]
                    if audio_formats:
                        # Sort by bitrate (abr) descending
                        audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
                        selected_format = audio_formats[0]
                    elif info.get('formats'):
                        # Last resort: any format with audio
                        selected_format = info['formats'][0]
                
                if not selected_format or 'url' not in selected_format:
                    logger.error("YTMusic: No suitable format found for %s", bId)
                    return None
                
                stream_url = selected_format['url']
                quality = selected_format.get('format_note', 'unknown')
                bitrate = selected_format.get('abr', 0) or selected_format.get('tbr', 0)
                
                logger.info(
                    "YTMusic: Found %s stream with %.0f kbps for %s",
                    quality,
                    bitrate,
                    bId
                )
                
                # Verify URL if configured
                if self.backend.verify_track_url:
                    import requests
                    try:
                        resp = requests.head(stream_url, timeout=5)
                        if resp.status_code == 403:
                            logger.error("YTMusic: URL forbidden for %s", bId)
                            return None
                    except Exception as e:
                        logger.warning("YTMusic: Failed to verify URL: %s", e)
                
                return stream_url
                
        except Exception as e:
            logger.exception("YTMusic: yt-dlp extraction failed for %s", bId)
            return None
