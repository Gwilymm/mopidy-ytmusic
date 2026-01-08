# -*- coding: utf-8 -*-
from setuptools import setup

packages = ["mopidy_ytmusic"]
package_data = {"": ["*"]}

install_requires = [
    "Mopidy>=3,<4",
    # ytmusicapi évolue, mais 1.11.x est récent et largement utilisé
    "ytmusicapi>=1.11.4,<2.0.0",
    # extraction robuste des URLs audio YouTube
    "yt-dlp>=2025.1.1",
    # pour les requêtes HTTP si ton code l'utilise (souvent déjà présent)
    "requests>=2.31.0",
]

entry_points = {"mopidy.ext": ["ytmusic = mopidy_ytmusic:Extension"]}

setup(
    name="mopidy-ytmusic",
    version="0.3.9",
    description="Mopidy extension for playing music/managing playlists in YouTube Music",
    packages=packages,
    package_data=package_data,
    install_requires=install_requires,
    entry_points=entry_points,
    python_requires=">=3.11,<4.0",
)
