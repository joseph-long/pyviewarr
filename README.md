# pyviewarr

A faster, more intuitive way to explore 2D data (i.e. monochromatic images) in Python notebooks.

- Server-side slicing — view 1 MB of a 100 GB data cube without downloading 100 GB of data
- Interactive re-stretching by right-clicking and dragging in X and Y (inspired by [ds9](https://sites.google.com/cfa.harvard.edu/saoimageds9))
- Stepper buttons for moving along the leading axes of N-D data where N > 2
- Linear, log, and symmetric linear (i.e. centered at zero with `vmin == -vmax`) scales
- Panning and zooming (`0` key resets, `-` zooms out, `=` zooms in)
- A few good colormaps

_Clanker code disclaimer: written in collaboration with Anthropic's Claude LLM. Use at your own risk._

## Installation

```sh
pip install pyviewarr
```

or with [uv](https://github.com/astral-sh/uv):

```sh
uv add pyviewarr
```

## Development

Be sure to clone with `git clone --recurse-submodules` (or, if you cloned first and **then** read this, `git submodule update --init --recursive` to initialize an existing clone). 

The frontend part of the widget (i.e. `viewarr` itself) is written in Rust with egui, requiring a Rust compiler toolchain for `wasm32-unknown-unknown` and the [`wasm-pack`](https://drager.github.io/wasm-pack/installer/) tool installed.

Install rust with rustup: https://rustup.rs/

Now that you have `cargo`, install wasm-pack with `cargo install wasm-pack`.

Using [uv](https://github.com/astral-sh/uv) for development will automatically manage virtual environments and dependencies for you.

```sh
uv run jupyter lab example.ipynb
```

Alternatively, create and manage your own virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
jupyter lab example.ipynb
```

The widget front-end code bundles it's JavaScript dependencies. After setting up Python,
make sure to install these dependencies locally:

```sh
npm install
```

While developing, you can run the following in a separate terminal to automatically
rebuild JavaScript as you make changes:

```sh
npm run dev
```

Open `example.ipynb` in JupyterLab, VS Code, or your favorite editor
to start developing. Changes made in `js/` will be reflected
in the notebook.
