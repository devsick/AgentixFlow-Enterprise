from typing import Literal

StreamMode = Literal[
    "live",
    "final_only",
    "status_only",
]

DEFAULT_STREAM_MODE: StreamMode = "live"