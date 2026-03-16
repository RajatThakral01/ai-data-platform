"""
utils/data_loader.py – Re-export of modules.data_loader for convenience.

Supports importing via either path:
    from modules.data_loader import load_data
    from utils.data_loader import load_data   # alias
"""

from modules.data_loader import (  # noqa: F401
    DataLoaderError,
    EmptyFileError,
    FileNotFoundError_,
    FileParsingError,
    UnsupportedFileTypeError,
    load_data,
)
