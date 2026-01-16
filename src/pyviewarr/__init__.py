import importlib.metadata
import pathlib
from typing import Optional

import anywidget
import numpy as np
import traitlets

try:
    __version__ = importlib.metadata.version("pyviewarr")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

__all__ = (
    'Widget',
    'show',
)

# Mapping from numpy dtype to viewarr type string
_DTYPE_MAP = {
    np.dtype('int8'): 'i8',
    np.dtype('uint8'): 'u8',
    np.dtype('int16'): 'i16',
    np.dtype('uint16'): 'u16',
    np.dtype('int32'): 'i32',
    np.dtype('uint32'): 'u32',
    np.dtype('int64'): 'i64',
    np.dtype('uint64'): 'u64',
    np.dtype('float32'): 'f32',
    np.dtype('float64'): 'f64',
}


def _numpy_dtype_to_viewarr(dtype: np.dtype) -> str:
    """Convert numpy dtype to viewarr type string."""
    if dtype in _DTYPE_MAP:
        return _DTYPE_MAP[dtype]
    raise ValueError(f"Unsupported dtype: {dtype}. Supported: {list(_DTYPE_MAP.keys())}")


class Widget(anywidget.AnyWidget):
    """Anywidget for displaying 2D arrays using the viewarr WASM viewer."""
    _esm = pathlib.Path(__file__).parent / "static" / "widget.js"
    _css = pathlib.Path(__file__).parent / "static" / "widget.css"

    # Binary image data (synced as DataView in JavaScript)
    data = traitlets.Bytes(b"").tag(sync=True)

    # Image dimensions
    image_width = traitlets.Int(0).tag(sync=True)
    image_height = traitlets.Int(0).tag(sync=True)

    # Data type string for viewarr (e.g., "f32", "u16")
    dtype = traitlets.Unicode("f64").tag(sync=True)

    # Widget display dimensions (CSS pixels)
    widget_width = traitlets.Int(800).tag(sync=True)
    widget_height = traitlets.Int(600).tag(sync=True)

    def set_array(self, arr: np.ndarray) -> None:
        """Set the array data to display.

        Args:
            arr: A 2D numpy array to display.
        """
        if arr.ndim != 2:
            raise ValueError(f"Expected 2D array, got {arr.ndim}D")

        # Ensure array is contiguous in memory
        arr = np.ascontiguousarray(arr)

        # Ensure array is in little-endian byte order
        arr = arr.astype(arr.dtype.newbyteorder('<'))

        self.dtype = _numpy_dtype_to_viewarr(arr.dtype)
        self.image_height, self.image_width = arr.shape
        self.data = arr.tobytes()


def show(
    arr: np.ndarray,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Widget:
    """Display a 2D numpy array in an interactive viewer.

    Args:
        arr: A 2D numpy array to display.
        width: Widget width in pixels (default: 800).
        height: Widget height in pixels (default: 600).

    Returns:
        A Widget instance displaying the array.
    """
    widget = Widget()
    if width is not None:
        widget.widget_width = width
    if height is not None:
        widget.widget_height = height
    widget.set_array(arr)
    return widget
