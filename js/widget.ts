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

	el.classList.add("pyviewarr");
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

	// Listen for data changes from Python
	model.on("change:data", updateImage);
	model.on("change:image_width", updateImage);
	model.on("change:image_height", updateImage);
	model.on("change:dtype", updateImage);

	// Listen for widget dimension changes
	model.on("change:widget_width", updateDimensions);
	model.on("change:widget_height", updateDimensions);

	// Cleanup when widget is removed
	return () => {
		isDisposed = true;
		if (viewerReady) {
			destroyViewer(viewerId);
		}
	};
}

export default { render };
