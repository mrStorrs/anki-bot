"""anki-bot — AI-powered Anki deck workspace."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("anki-bot")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
