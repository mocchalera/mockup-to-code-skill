#!/usr/bin/env python3
"""Small stdlib-only PNG surface inspector for the pre-CSS asset gate.

The main skill intentionally runs its contract doctor with the system Python.
This module therefore avoids Pillow/OpenCV and reads the common 8-bit,
non-interlaced RGB/RGBA PNGs emitted by image generators directly.
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _read_png(path: Path) -> tuple[int, int, int, list[bytearray]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("surface pixel inspection currently requires PNG")
    offset = len(PNG_SIGNATURE)
    width = height = color_type = bit_depth = interlace = None
    compressed = bytearray()
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if not width or not height or bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
        raise ValueError("only non-interlaced 8-bit RGB/RGBA PNG is supported")
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError("unexpected PNG scanline size")
    rows: list[bytearray] = []
    cursor = 0
    prior = bytearray(stride)
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        source = raw[cursor : cursor + stride]
        cursor += stride
        row = bytearray(stride)
        for index, value in enumerate(source):
            left = row[index - channels] if index >= channels else 0
            up = prior[index]
            upper_left = prior[index - channels] if index >= channels else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = value + left
            elif filter_type == 2:
                decoded = value + up
            elif filter_type == 3:
                decoded = value + ((left + up) // 2)
            elif filter_type == 4:
                decoded = value + _paeth(left, up, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
            row[index] = decoded & 255
        rows.append(row)
        prior = row
    return width, height, channels, rows


def _pixel(rows: list[bytearray], channels: int, x: int, y: int) -> tuple[int, int, int, int]:
    start = x * channels
    row = rows[y]
    alpha = row[start + 3] if channels == 4 else 255
    return row[start], row[start + 1], row[start + 2], alpha


def _mean_and_deviation(values: list[tuple[int, int, int]]) -> tuple[list[float], float]:
    count = max(1, len(values))
    mean = [sum(value[channel] for value in values) / count for channel in range(3)]
    deviation = sum(
        sum(abs(value[channel] - mean[channel]) for channel in range(3)) / 3
        for value in values
    ) / count
    return mean, deviation


def _color_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


def inspect_png_surface(path: Path) -> dict:
    width, height, channels, rows = _read_png(path)
    step = max(1, int(math.sqrt((width * height) / 120000)))
    transparent = sampled = 0
    for y in range(0, height, step):
        for x in range(0, width, step):
            sampled += 1
            if _pixel(rows, channels, x, y)[3] < 250:
                transparent += 1

    band_x = max(1, round(width * 0.02))
    band_y = max(1, round(height * 0.02))
    edge_pixels: list[tuple[int, int, int]] = []
    edge_stride = max(1, step)
    for y in range(0, height, edge_stride):
        for x in range(0, band_x):
            edge_pixels.append(_pixel(rows, channels, x, y)[:3])
        for x in range(width - band_x, width):
            edge_pixels.append(_pixel(rows, channels, x, y)[:3])
    for x in range(0, width, edge_stride):
        for y in range(0, band_y):
            edge_pixels.append(_pixel(rows, channels, x, y)[:3])
        for y in range(height - band_y, height):
            edge_pixels.append(_pixel(rows, channels, x, y)[:3])
    edge_mean, edge_deviation = _mean_and_deviation(edge_pixels)

    def line_distance(axis: str, position: int) -> float:
        values = []
        if axis == "row":
            values = [_pixel(rows, channels, x, position)[:3] for x in range(0, width, edge_stride)]
        else:
            values = [_pixel(rows, channels, position, y)[:3] for y in range(0, height, edge_stride)]
        mean, deviation = _mean_and_deviation(values)
        return _color_distance(mean, edge_mean) + deviation

    threshold = 18.0
    max_y = max(1, round(height * 0.25))
    max_x = max(1, round(width * 0.25))

    def depth(axis: str, positions) -> int:
        count = 0
        for position in positions:
            if line_distance(axis, position) > threshold:
                break
            count += 1
        return count

    top = depth("row", range(max_y))
    bottom = depth("row", range(height - 1, height - max_y - 1, -1))
    left = depth("col", range(max_x))
    right = depth("col", range(width - 1, width - max_x - 1, -1))
    border_fraction = min(top / height, bottom / height, left / width, right / width)

    content_x: list[int] = []
    content_y: list[int] = []
    for y in range(0, height, step):
        for x in range(0, width, step):
            r, g, b, a = _pixel(rows, channels, x, y)
            if a >= 16 and _color_distance([r, g, b], edge_mean) > 24:
                content_x.append(x)
                content_y.append(y)
    content_bounds = None
    if content_x and content_y:
        content_bounds = {
            "x": min(content_x),
            "y": min(content_y),
            "w": max(content_x) - min(content_x) + step,
            "h": max(content_y) - min(content_y) + step,
        }
    return {
        "width": width,
        "height": height,
        "hasAlphaChannel": channels == 4,
        "transparentPixelFraction": transparent / max(1, sampled),
        "edgeMeanRgb": [round(value, 2) for value in edge_mean],
        "edgeMeanHex": "#" + "".join(f"{round(value):02x}" for value in edge_mean),
        "edgeMeanDeviation": round(edge_deviation, 3),
        "uniformOuterBandFraction": round(border_fraction, 5),
        "uniformOuterBandPx": {"top": top, "right": right, "bottom": bottom, "left": left},
        "estimatedContentBounds": content_bounds,
        "sampleStride": step,
    }


def parse_hex_color(value: str) -> list[int]:
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        raise ValueError("expected #RRGGBB color")
    return [int(text[index : index + 2], 16) for index in (0, 2, 4)]


def rgb_distance(a: list[float], b: list[float]) -> float:
    return _color_distance(a, b)
