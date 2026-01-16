import type { RenderProps } from "@anywidget/types";
import { createViewer, setImageData, destroyViewer } from "viewarr";
import "./widget.css";

/* Specifies attributes defined with traitlets in ../src/pyviewarr/__init__.py */
interface WidgetModel {
	data: DataView;
	image_width: number;
	image_height: number;
	dtype: string;
	widget_width: number;
	widget_height: number;
	shape: number[];
	current_slice_indices: number[];
}

/**
 * Generate a UUID v4 for unique viewer identification.
 */
function generateUUID(): string {
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0;
		const v = c === "x" ? r : (r & 0x3) | 0x8;
		return v.toString(16);
	});
}

/**
 * Wait for an element to be connected to the document DOM.
 * Returns immediately if already connected.
 */
function waitForDOMConnection(element: HTMLElement): Promise<void> {
	return new Promise((resolve) => {
		if (element.isConnected) {
			resolve();
			return;
		}

		// Use MutationObserver to detect when the element is added to the DOM
		const observer = new MutationObserver(() => {
			if (element.isConnected) {
				observer.disconnect();
				resolve();
			}
		});

		// Observe the document body for subtree additions
		observer.observe(document.body, { childList: true, subtree: true });

		// Also use requestAnimationFrame as a fallback for the next frame
		requestAnimationFrame(function checkConnection() {
			if (element.isConnected) {
				observer.disconnect();
				resolve();
			} else {
				requestAnimationFrame(checkConnection);
			}
		});
	});
}

function render({ model, el }: RenderProps<WidgetModel>) {
	const viewerId = `pyviewarr-${generateUUID()}`;

	// Create container element
	const container = document.createElement("div");
	container.id = viewerId;
	container.classList.add("pyviewarr-container");
	container.style.width = `${model.get("widget_width")}px`;
	container.style.height = `${model.get("widget_height")}px`;

	// Create controls container
	const controlsContainer = document.createElement("div");
	controlsContainer.classList.add("pyviewarr-controls");

	el.classList.add("pyviewarr");
	el.appendChild(controlsContainer);
	el.appendChild(container);

	let viewerReady = false;
	let isDisposed = false;

	/**
	 * Update the image data in the viewer.
	 */
	function updateImage(): void {
		if (!viewerReady || isDisposed) return;

		const dataView = model.get("data");
		const imageWidth = model.get("image_width");
		const imageHeight = model.get("image_height");
		const dtype = model.get("dtype");

		if (dataView && dataView.byteLength > 0 && imageWidth > 0 && imageHeight > 0) {
			// Extract ArrayBuffer from DataView (slice creates a new ArrayBuffer, not SharedArrayBuffer)
			const buffer = dataView.buffer.slice(
				dataView.byteOffset,
				dataView.byteOffset + dataView.byteLength
			) as ArrayBuffer;
			setImageData(viewerId, buffer, imageWidth, imageHeight, dtype);
		}
	}

	/**
	 * Update the widget container dimensions.
	 */
	function updateDimensions(): void {
		if (isDisposed) return;
		container.style.width = `${model.get("widget_width")}px`;
		container.style.height = `${model.get("widget_height")}px`;
	}

	/**
	 * Render slice controls for leading axes.
	 */
	function renderControls(): void {
		if (isDisposed) return;

		const shape = model.get("shape");
		const indices = model.get("current_slice_indices");
		const numLeadingAxes = shape.length - 2;

		if (numLeadingAxes === 0) {
			controlsContainer.innerHTML = '';
			return;
		}

		let html = '';
		for (let axis = 0; axis < numLeadingAxes; axis++) {
			const axisSize = shape[axis];
			const currentIndex = indices[axis];
			const axisLabel = numLeadingAxes === 1 ? 'Slice' : `Axis ${axis}`;

			html += `
				<div class="pyviewarr-sliceControl" data-axis="${axis}">
					<button class="pyviewarr-sliceButton pyviewarr-prevButton"
							data-axis="${axis}"
							data-direction="prev">
						◀
					</button>
					<span class="pyviewarr-sliceLabel">
						${axisLabel}: <strong>${currentIndex + 1}</strong> / ${axisSize}
					</span>
					<button class="pyviewarr-sliceButton pyviewarr-nextButton"
							data-axis="${axis}"
							data-direction="next">
						▶
					</button>
				</div>
			`;
		}

		controlsContainer.innerHTML = html;

		// Attach event listeners
		const buttons = controlsContainer.querySelectorAll('.pyviewarr-sliceButton');
		buttons.forEach(btn => {
			btn.addEventListener('click', e => {
				const target = e.currentTarget as HTMLElement;
				const axis = parseInt(target.dataset.axis || '0', 10);
				const direction = target.dataset.direction;
				navigateSlice(axis, direction === 'next' ? 1 : -1);
			});
		});
	}

	/**
	 * Navigate to a different slice along a given axis.
	 */
	function navigateSlice(axis: number, delta: number): void {
		const shape = model.get("shape");
		const indices = [...model.get("current_slice_indices")];
		const axisSize = shape[axis];
		let newIndex = indices[axis] + delta;

		// Wrap around
		if (newIndex < 0) {
			newIndex = axisSize - 1;
		} else if (newIndex >= axisSize) {
			newIndex = 0;
		}

		if (newIndex !== indices[axis]) {
			indices[axis] = newIndex;
			model.set("current_slice_indices", indices);
			model.save_changes(); // Trigger sync to backend
		}
	}

	// Wait for the container to be in the DOM before initializing the viewer.
	// This is necessary because createViewer uses document.getElementById(),
	// which only works for elements attached to the document.
	waitForDOMConnection(container)
		.then(() => {
			if (isDisposed) return;
			return createViewer(viewerId);
		})
		.then(() => {
			if (isDisposed) return;
			viewerReady = true;
			updateImage();
		})
		.catch((err) => {
			if (!isDisposed) {
				console.error("Failed to create viewarr viewer:", err);
			}
		});

	// Initial render of controls
	renderControls();

	// Listen for data changes from Python
	model.on("change:data", updateImage);
	model.on("change:image_width", updateImage);
	model.on("change:image_height", updateImage);
	model.on("change:dtype", updateImage);

	// Listen for widget dimension changes
	model.on("change:widget_width", updateDimensions);
	model.on("change:widget_height", updateDimensions);

	// Listen for shape and slice index changes to update controls
	model.on("change:shape", renderControls);
	model.on("change:current_slice_indices", renderControls);

	// Cleanup when widget is removed
	return () => {
		isDisposed = true;
		if (viewerReady) {
			destroyViewer(viewerId);
		}
	};
}

export default { render };
