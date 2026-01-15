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

	/**
	 * Update the image data in the viewer.
	 */
	function updateImage(): void {
		if (!viewerReady) return;

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
		container.style.width = `${model.get("widget_width")}px`;
		container.style.height = `${model.get("widget_height")}px`;
	}

	// Initialize the viewer
	createViewer(viewerId)
		.then(() => {
			viewerReady = true;
			updateImage();
		})
		.catch((err) => {
			console.error("Failed to create viewarr viewer:", err);
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
		destroyViewer(viewerId);
	};
}

export default { render };
