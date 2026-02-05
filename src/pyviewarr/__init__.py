import importlib.metadata
import pathlib
from typing import Optional, Tuple, TYPE_CHECKING

import anywidget
import numpy as np
import traitlets

if TYPE_CHECKING:
    from matplotlib.axes import Axes

try:
    __version__ = importlib.metadata.version("pyviewarr")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

__all__ = (
    'Widget',
    'show',
    'ViewarrNormalize',
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


# =========================================================================
# ViewarrNormalize: Matplotlib-compatible normalization class
# =========================================================================

# Try to import matplotlib's Normalize base class, but don't require it
try:
    from matplotlib.colors import Normalize as _NormalizeBase
    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False
    _NormalizeBase = object  # Fall back to plain object


class ViewarrNormalize(_NormalizeBase):
    """Matplotlib-compatible normalization with DS9-style contrast/bias and optional log stretch.

    This class replicates the normalization pipeline used by the viewarr WASM viewer,
    allowing you to render images with matplotlib using the same stretch settings
    you've dialed in interactively.

    The normalization pipeline is:
    1. Normalize to 0-1 range based on vmin/vmax (or symmetric around zero)
    2. Optionally apply log stretch: log10(1000*x + 1) / log10(1000)
    3. Apply DS9 contrast/bias: (x - bias) * contrast + 0.5

    Parameters
    ----------
    vmin : float, optional
        Minimum data value. If None, will be set from data.
    vmax : float, optional
        Maximum data value. If None, will be set from data.
    contrast : float, default=1.0
        Contrast value (0.0 to 10.0). Higher values increase contrast.
    bias : float, default=0.5
        Bias value (0.0 to 1.0). Controls the midpoint of the stretch.
    log : bool, default=False
        If True, apply flexible log stretch before contrast/bias.
    symmetric : bool, default=False
        If True, scale symmetrically around zero (for diverging colormaps).
        In symmetric mode, bias is locked to 0.5.
    clip : bool, default=True
        If True, clip output to [0, 1] range.

    Examples
    --------
    >>> norm = ViewarrNormalize(vmin=0, vmax=100, contrast=2.0, bias=0.4)
    >>> ax.imshow(data, norm=norm, cmap='gray')

    >>> # Using log stretch
    >>> norm = ViewarrNormalize(vmin=1, vmax=1000, log=True)
    >>> ax.imshow(data, norm=norm, cmap='inferno')

    >>> # Symmetric mode for diverging data
    >>> norm = ViewarrNormalize(symmetric=True, contrast=1.5)
    >>> ax.imshow(data, norm=norm, cmap='RdBu_r')
    """

    # Log stretch exponent (DS9 default for optical images)
    LOG_EXPONENT = 1000.0

    def __init__(
        self,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        contrast: float = 1.0,
        bias: float = 0.5,
        log: bool = False,
        symmetric: bool = False,
        clip: bool = True,
    ):
        # Initialize matplotlib base class if available
        if _HAS_MATPLOTLIB:
            super().__init__(vmin=vmin, vmax=vmax, clip=clip)
        else:
            self.vmin = vmin
            self.vmax = vmax
            self.clip = clip

        self.contrast = contrast
        self.bias = bias
        self.log = log
        self.symmetric = symmetric

    def __call__(self, value, clip=None):
        """Normalize value(s) to 0-1 range.

        Parameters
        ----------
        value : array-like
            Data to normalize.
        clip : bool, optional
            Override instance clip setting.

        Returns
        -------
        np.ma.MaskedArray
            Normalized values in [0, 1] range.
        """
        if clip is None:
            clip = self.clip

        # Convert to masked array to handle NaN/Inf
        result = np.ma.asarray(value)

        # Determine vmin/vmax if not set
        vmin = self.vmin
        vmax = self.vmax
        if vmin is None:
            vmin = float(np.nanmin(result))
        if vmax is None:
            vmax = float(np.nanmax(result))

        # Step 1: Determine scaling range
        if self.symmetric:
            abs_max = max(abs(vmin), abs(vmax))
            scale_min, scale_max = -abs_max, abs_max
        else:
            scale_min, scale_max = vmin, vmax

        # Step 2: Normalize to 0-1
        range_val = scale_max - scale_min
        if abs(range_val) < 1e-15:
            normalized = np.zeros_like(result)
        else:
            normalized = (result - scale_min) / range_val

        if clip:
            normalized = np.clip(normalized, 0, 1)

        # Step 3: Apply log stretch if enabled
        if self.log:
            stretched = np.log10(self.LOG_EXPONENT * normalized + 1) / np.log10(self.LOG_EXPONENT)
        else:
            stretched = normalized

        # Step 4: Apply contrast/bias (DS9 formula)
        # In symmetric mode, bias is locked to 0.5 to keep zero at center
        bias = 0.5 if self.symmetric else self.bias
        output = (stretched - bias) * self.contrast + 0.5

        if clip:
            output = np.clip(output, 0, 1)

        return np.ma.array(output, mask=np.ma.getmask(result))

    def inverse(self, value):
        """Inverse transform (not fully implemented for log stretch)."""
        # This is a simplified inverse that ignores log stretch
        bias = 0.5 if self.symmetric else self.bias
        x = (value - 0.5) / self.contrast + bias

        vmin = self.vmin if self.vmin is not None else 0
        vmax = self.vmax if self.vmax is not None else 1

        if self.symmetric:
            abs_max = max(abs(vmin), abs(vmax))
            scale_min, scale_max = -abs_max, abs_max
        else:
            scale_min, scale_max = vmin, vmax

        return x * (scale_max - scale_min) + scale_min

    def autoscale(self, A):
        """Set vmin/vmax from data."""
        self.vmin = float(np.nanmin(A))
        self.vmax = float(np.nanmax(A))

    def autoscale_None(self, A):
        """Set vmin/vmax from data only if not already set."""
        if self.vmin is None:
            self.vmin = float(np.nanmin(A))
        if self.vmax is None:
            self.vmax = float(np.nanmax(A))

    def scaled(self):
        """Return whether vmin and vmax are set."""
        return self.vmin is not None and self.vmax is not None


# Colormap name mapping from viewarr to matplotlib
_COLORMAP_MAP = {
    'Gray': 'gray',
    'Grayscale': 'gray',
    'Inferno': 'inferno',
    'Magma': 'magma',
    'RdBu': 'RdBu_r',  # Reversed to match matplotlib convention
    'RdYlBu': 'RdYlBu_r',
}


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

    # =========================================================================
    # Viewer state properties (bidirectional sync with frontend)
    # =========================================================================

    # Contrast value (0.0 to 10.0, default 1.0)
    contrast = traitlets.Float(1.0).tag(sync=True)

    # Bias value (0.0 to 1.0, default 0.5)
    bias = traitlets.Float(0.5).tag(sync=True)

    # Stretch mode: "linear", "log", or "symmetric"
    stretch_mode = traitlets.Unicode("linear").tag(sync=True)

    # Viewport bounds in pixel coordinates
    xlim = traitlets.Tuple(traitlets.Float(), traitlets.Float(), default_value=(0.0, 0.0)).tag(sync=True)
    ylim = traitlets.Tuple(traitlets.Float(), traitlets.Float(), default_value=(0.0, 0.0)).tag(sync=True)

    # Colormap name (read from viewer)
    colormap = traitlets.Unicode("Gray").tag(sync=True)

    # Whether colormap is reversed (read from viewer)
    colormap_reversed = traitlets.Bool(False).tag(sync=True)

    # Data value range (read from viewer after image load)
    vmin = traitlets.Float(0.0).tag(sync=True)
    vmax = traitlets.Float(1.0).tag(sync=True)

    # Internal flag to prevent feedback loops during sync
    _sync_from_viewer = traitlets.Bool(False).tag(sync=True)

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

    def get_current_slice(self) -> np.ndarray:
        """Get the current 2D slice being displayed.

        Returns
        -------
        np.ndarray
            The 2D array currently being displayed.
        """
        if self._array is None:
            raise ValueError("No array has been set")

        indices = self.current_slice_indices
        if len(indices) > 0:
            slice_obj = tuple(indices) + (slice(None), slice(None))
            return self._array[slice_obj]
        return self._array

    def get_normalization(self) -> ViewarrNormalize:
        """Get a ViewarrNormalize object matching the current viewer settings.

        Returns a normalization object that can be used with matplotlib to
        reproduce the same stretch settings you've dialed in interactively.

        Returns
        -------
        ViewarrNormalize
            Normalization object with current contrast, bias, and stretch settings.
        """
        return ViewarrNormalize(
            vmin=self.vmin,
            vmax=self.vmax,
            contrast=self.contrast,
            bias=self.bias,
            log=(self.stretch_mode == "log"),
            symmetric=(self.stretch_mode == "symmetric"),
        )

    def plot_to_matplotlib(
        self,
        ax: "Axes",
        cmap: Optional[str] = None,
        **imshow_kwargs
    ) -> "Axes":
        """Plot the current view to a matplotlib axes.

        Renders the current 2D slice with the same normalization settings
        (contrast, bias, stretch) that are currently applied in the interactive
        viewer. Sets xlim/ylim to match the current viewport.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to plot on.
        cmap : str, optional
            Colormap name. If None, uses the viewer's current colormap.
        **imshow_kwargs
            Additional keyword arguments passed to ax.imshow().

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the plotted image.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> widget.plot_to_matplotlib(ax)
        >>> plt.show()
        """
        # Get the current slice data
        data = self.get_current_slice()

        # Create normalization matching viewer settings
        norm = self.get_normalization()

        # Determine colormap
        if cmap is None:
            viewer_cmap = self.colormap
            cmap = _COLORMAP_MAP.get(viewer_cmap, 'gray')
            if self.colormap_reversed:
                # Append _r if not already reversed, or remove it if it is
                if cmap.endswith('_r'):
                    cmap = cmap[:-2]
                else:
                    cmap = cmap + '_r'

        # Set default imshow parameters
        imshow_defaults = {
            'origin': 'lower',  # FITS convention: Y=0 at bottom
            'aspect': 'equal',
        }
        imshow_defaults.update(imshow_kwargs)

        # Plot the image
        ax.imshow(data, norm=norm, cmap=cmap, **imshow_defaults)

        # Set viewport limits if they've been set (non-zero)
        xlim = self.xlim
        ylim = self.ylim
        if xlim[0] != xlim[1]:
            ax.set_xlim(xlim)
        if ylim[0] != ylim[1]:
            ax.set_ylim(ylim)

        return ax


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
