"""Procedural generation of tileable ground-plane textures."""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _tileable_noise(size: int, rng: np.random.Generator, frequency: int) -> np.ndarray:
    """Create smooth tileable value noise in [0, 1]."""
    grid = rng.random((frequency, frequency))
    y = np.linspace(0.0, frequency, size, endpoint=False)
    x = np.linspace(0.0, frequency, size, endpoint=False)
    x0 = np.floor(x).astype(int) % frequency
    y0 = np.floor(y).astype(int) % frequency
    x1 = (x0 + 1) % frequency
    y1 = (y0 + 1) % frequency
    tx = x - np.floor(x)
    ty = y - np.floor(y)

    # Smoothstep interpolation avoids blocky transitions.
    sx = tx * tx * (3.0 - 2.0 * tx)
    sy = ty * ty * (3.0 - 2.0 * ty)

    n00 = grid[np.ix_(y0, x0)]
    n10 = grid[np.ix_(y0, x1)]
    n01 = grid[np.ix_(y1, x0)]
    n11 = grid[np.ix_(y1, x1)]

    nx0 = n00 * (1.0 - sx)[None, :] + n10 * sx[None, :]
    nx1 = n01 * (1.0 - sx)[None, :] + n11 * sx[None, :]
    return nx0 * (1.0 - sy)[:, None] + nx1 * sy[:, None]


def _draw_wrapped_line(
    draw: ImageDraw.ImageDraw,
    size: int,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    fill: tuple[int, int, int],
    width: int,
) -> None:
    """Draw a short line with wrapped copies so edge-crossing fragments tile."""
    for dx in (-size, 0, size):
        for dy in (-size, 0, size):
            draw.line(
                [(start[0] + dx, start[1] + dy), (end[0] + dx, end[1] + dy)],
                fill=fill,
                width=width,
            )


def generate_ground_texture(
    output_path: Path,
    *,
    size: int = 1024,
    seed: int = 42,
) -> Path:
    """Generate a tileable dry soil and mowed-grass albedo texture."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    noise_low = _tileable_noise(size, rng, 5)
    noise_mid = _tileable_noise(size, rng, 17)
    noise_hi = _tileable_noise(size, rng, 59)

    base = np.array([126, 101, 63], dtype=np.float32)
    tan = np.array([174, 151, 96], dtype=np.float32)
    brown = np.array([84, 67, 44], dtype=np.float32)
    gray = np.array([126, 124, 105], dtype=np.float32)

    blotches = noise_low[..., None]
    sandy = noise_mid[..., None]
    fine = noise_hi[..., None]
    rgb = base * (0.72 + 0.28 * sandy) + tan * (0.18 * blotches)
    rgb = rgb * (0.92 + 0.16 * fine)
    rgb = rgb * (0.84 + 0.24 * blotches) + brown * (0.14 * (1.0 - blotches))

    gray_mask = (_tileable_noise(size, rng, 9) > 0.68)[..., None].astype(np.float32)
    rgb = rgb * (1.0 - 0.10 * gray_mask) + gray * (0.10 * gray_mask)

    # Sparse small dark flecks and pebbles.
    flecks = rng.random((size, size))
    rgb[flecks > 0.996] *= 0.45
    rgb[(flecks > 0.992) & (flecks <= 0.996)] *= 0.70

    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image)
    py_rng = random.Random(seed)

    # Dry straw fragments, intentionally sparse and muted.
    for _ in range(10500):
        length = py_rng.uniform(9.0, 42.0)
        angle = py_rng.uniform(0.0, math.tau)
        cx = py_rng.uniform(0.0, size)
        cy = py_rng.uniform(0.0, size)
        dx = math.cos(angle) * length * 0.5
        dy = math.sin(angle) * length * 0.5
        color_base = py_rng.randint(142, 192)
        fill = (
            color_base,
            max(0, color_base - py_rng.randint(18, 42)),
            max(0, color_base - py_rng.randint(70, 100)),
        )
        _draw_wrapped_line(
            draw,
            size,
            (cx - dx, cy - dy),
            (cx + dx, cy + dy),
            fill=fill,
            width=py_rng.choice((1, 1, 1, 2)),
        )

    # Occasional subtle green-gray fragments.
    for _ in range(130):
        length = py_rng.uniform(6.0, 20.0)
        angle = py_rng.uniform(0.0, math.tau)
        cx = py_rng.uniform(0.0, size)
        cy = py_rng.uniform(0.0, size)
        dx = math.cos(angle) * length * 0.5
        dy = math.sin(angle) * length * 0.5
        _draw_wrapped_line(
            draw,
            size,
            (cx - dx, cy - dy),
            (cx + dx, cy + dy),
            fill=(95, 111, 69),
            width=1,
        )

    image = image.filter(ImageFilter.GaussianBlur(0.25))
    image.save(output_path)
    return output_path
