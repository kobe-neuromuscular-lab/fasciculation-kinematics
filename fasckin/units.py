"""Unit conversion.

Pixel size depends on the scanner's depth / field-of-view setting. In the
paper's data it was read from the on-screen 1-cm scale of each export
(pixels per cm) and happened to be tied to the frame rate:

    fps   px per cm   um per px
    39    109         91.74
    41    125         80.00
    43    146         68.49
    45    165         60.61
    50    109         91.74

Measure your own scale bar and pass ``um_per_px``; the table is only a record.
"""

PAPER_UM_PER_PX_BY_FPS = {39: 10000 / 109, 41: 10000 / 125, 43: 10000 / 146,
                          45: 10000 / 165, 50: 10000 / 109}


def px_per_frame_to_um_per_ms(value, um_per_px, fps):
    """Per-frame displacement (px/frame) -> velocity (um/ms)."""
    return value * um_per_px * fps / 1000.0


def frames_to_ms(value, fps):
    return value * 1000.0 / fps
