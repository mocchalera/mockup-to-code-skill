"""_imgcompat: core image I/O that works with OpenCV OR Pillow+numpy.

OpenCV is preferred (faster, and the measurement tools snap_bbox/profile/
pixel_diff still require it), but normalize_image / sample_color / crop_asset
must at minimum run on Pillow + numpy so a missing cv2 never blocks the
basic normalize -> sample colors -> crop workflow.

All images are numpy BGR uint8 arrays (cv2 convention) regardless of backend.
"""
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False

BACKEND = "cv2" if HAS_CV2 else ("pillow" if HAS_PIL else None)


def require_backend():
    if BACKEND is None:
        raise SystemExit(
            "no image backend: install opencv-python (preferred) or Pillow\n"
            "  pip install opencv-python numpy   # full functionality\n"
            "  pip install Pillow numpy          # minimal fallback"
        )


def imread(path):
    """Read image as BGR uint8 ndarray, or None on failure."""
    require_backend()
    if HAS_CV2:
        return cv2.imread(path, cv2.IMREAD_COLOR)
    try:
        img = Image.open(path).convert("RGB")
    except Exception:
        return None
    return np.asarray(img)[:, :, ::-1].copy()  # RGB -> BGR


def imwrite(path, img):
    require_backend()
    if HAS_CV2:
        return cv2.imwrite(path, img)
    Image.fromarray(img[:, :, ::-1]).save(path)  # BGR -> RGB
    return True


def resize(img, width, height):
    """Resize BGR ndarray. Area-average for downscale, cubic/Lanczos for upscale."""
    require_backend()
    if HAS_CV2:
        interp = cv2.INTER_AREA if width < img.shape[1] else cv2.INTER_CUBIC
        return cv2.resize(img, (width, height), interpolation=interp)
    pil = Image.fromarray(img[:, :, ::-1])
    pil = pil.resize((width, height), Image.LANCZOS)
    return np.asarray(pil)[:, :, ::-1].copy()


def kmeans(pixels, k, seed=0, iters=30):
    """K-means over float32 (N,3) pixels -> (labels (N,), centers (k,3)).

    Uses cv2.kmeans when available; otherwise a plain numpy Lloyd's
    implementation with kmeans++ init (adequate for <=40k color samples).
    """
    pixels = np.asarray(pixels, dtype=np.float32)
    if HAS_CV2:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, iters, 0.5)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
        return labels.ravel(), centers

    rng = np.random.default_rng(seed)
    # kmeans++ init
    centers = np.empty((k, pixels.shape[1]), dtype=np.float32)
    centers[0] = pixels[rng.integers(len(pixels))]
    d2 = np.sum((pixels - centers[0]) ** 2, axis=1)
    for i in range(1, k):
        probs = d2 / (d2.sum() + 1e-12)
        centers[i] = pixels[rng.choice(len(pixels), p=probs)]
        d2 = np.minimum(d2, np.sum((pixels - centers[i]) ** 2, axis=1))

    labels = np.zeros(len(pixels), dtype=np.int32)
    for _ in range(iters):
        dists = np.linalg.norm(pixels[:, None, :] - centers[None, :, :], axis=2)
        new_labels = dists.argmin(axis=1).astype(np.int32)
        if np.array_equal(new_labels, labels) and _ > 0:
            break
        labels = new_labels
        for i in range(k):
            member = pixels[labels == i]
            if len(member):
                centers[i] = member.mean(axis=0)
    return labels, centers
