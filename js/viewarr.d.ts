declare module "viewarr" {
	/**
	 * Create a new viewer instance in the specified container.
	 * @param containerId - The ID of the HTML element to use as the container.
	 * @returns Promise that resolves when the viewer is ready.
	 */
	export function createViewer(containerId: string): Promise<void>;

	/**
	 * Set image data for a viewer.
	 * @param containerId - The ID of the container (viewer instance).
	 * @param buffer - The raw pixel data.
	 * @param width - Image width in pixels.
	 * @param height - Image height in pixels.
	 * @param dtype - Data type string (e.g., "f32", "f64", "i16", "u8").
	 */
	export function setImageData(
		containerId: string,
		buffer: ArrayBuffer,
		width: number,
		height: number,
		dtype: string
	): void;

	/**
	 * Destroy a viewer instance and clean up resources.
	 * @param containerId - The ID of the container (viewer instance).
	 */
	export function destroyViewer(containerId: string): void;

	/**
	 * Check if a viewer exists for a container.
	 * @param containerId - The ID of the container.
	 * @returns True if a viewer exists.
	 */
	export function viewerExists(containerId: string): boolean;
}
