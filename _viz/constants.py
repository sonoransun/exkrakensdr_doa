import enum

MAX_VFOS = 16

# Matches VFO_COLORS from _ui/_web_interface/kraken_web_multi_doa.py
VFO_COLORS = [
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
]

# SDR#-compatible waterfall colorscale (from _ui/_web_interface/waterfall.py)
WATERFALL_COLORMAP = [
    (0.0, "#000020"),
    (0.2, "#000060"),
    (0.3, "#0000A0"),
    (0.4, "#0040FF"),
    (0.5, "#00C0FF"),
    (0.55, "#00FF80"),
    (0.6, "#80FF00"),
    (0.7, "#FFFF00"),
    (0.8, "#FF8000"),
    (0.9, "#FF2000"),
    (1.0, "#4A0000"),
]

DOA_ARRAY_SIZE = 360
DEFAULT_WS_HOST = "127.0.0.1"
DEFAULT_WS_PORT = 8021
DEFAULT_SETTINGS_PATH = "_share/settings.json"
WATERFALL_HISTORY_ROWS = 50


class SourceKind(enum.Enum):
    LIVE_WS = "live_ws"
    FILE_CSV = "file_csv"
    FILE_IQ = "file_iq"
    FILE_WAV = "file_wav"
    SYNTHETIC = "synthetic"


class SourceState(enum.Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    FINISHED = "finished"
