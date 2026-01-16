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

    # Whether the frontend needs to update its viewer state
    # (used to prevent errors from the fact that different
    # traitlets update independently, leading to temporary buffer / shape
    # mismatches while the changes apply)
    _needs_repaint = traitlets.Bool(True).tag(sync=True)

    # Data type string for viewarr (e.g., "f32", "u16")
    dtype = traitlets.Unicode("f64").tag(sync=True)

    # Widget display dimensions (CSS pixels)
    widget_width = traitlets.Int(800).tag(sync=True)
    widget_height = traitlets.Int(600).tag(sync=True)

    # Array shape (list of dimensions)
    shape = traitlets.List(traitlets.Int()).tag(sync=True)

    # Current slice indices for leading axes (empty for 2D arrays)
    current_slice_indices = traitlets.List(traitlets.Int()).tag(sync=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._array = None
        self.observe(self._on_slice_indices_changed, names=['current_slice_indices'])

    def _on_slice_indices_changed(self, change):
        """Update the displayed slice when slice indices change."""
        self._update_slice()

    def _update_slice(self):
        """Compute the current 2D slice and update traits."""
        if self._array is None:
            return

        arr = self._array
        indices = self.current_slice_indices

        # Slice the array: leading axes use indices, last two are full slices
        if len(indices) > 0:
            slice_obj = tuple(indices) + (slice(None), slice(None))
            slice_arr = arr[slice_obj]
        else:
            slice_arr = arr

        # Ensure slice is contiguous and little-endian
        slice_arr = np.ascontiguousarray(slice_arr)
        slice_arr = slice_arr.astype(slice_arr.dtype.newbyteorder('<'))

        self.dtype = _numpy_dtype_to_viewarr(slice_arr.dtype)
        self.image_height, self.image_width = slice_arr.shape
        self.data = slice_arr.tobytes()
        self._needs_repaint = True

    def set_array(self, arr: np.ndarray) -> None:
        """Set the array data to display.

        Args:
            arr: A numpy array to display. Last two axes are treated as (y, x).
                 Leading axes can be navigated with slice controls.
        """
        if arr.ndim < 2:
            raise ValueError(f"Expected array with at least 2 dimensions, got {arr.ndim}D")

        # Store the full array
        self._array = arr

        # Set shape
        self.shape = list(arr.shape)

        # Initialize slice indices for leading axes
        num_leading_axes = arr.ndim - 2
        self.current_slice_indices = [0] * num_leading_axes

        # Update the displayed slice
        self._update_slice()


def show(
    arr: np.ndarray,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Widget:
    """Display a numpy array in an interactive viewer.

    Args:
        arr: A numpy array to display. Last two axes are treated as (y, x).
             Leading axes can be navigated with slice controls.
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
