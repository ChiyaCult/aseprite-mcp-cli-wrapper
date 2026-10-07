"""draw_pixels / draw_line on the active cel must not clip to the cel bounds.

After a shape tool trims the cel to its bounding box, putPixel outside that
box was silently dropped while the tool still reported success.
"""
from conftest import BASE, ok, run

from aseprite_mcp.tools import canvas, drawing, pixel_read


def _rgba(pixel_result: str) -> tuple[int, int, int, int]:
    s = str(pixel_result)
    return (int(s.split("r=")[1].split(",")[0]),
            int(s.split("g=")[1].split(",")[0]),
            int(s.split("b=")[1].split(",")[0]),
            int(s.split("a=")[1].split(")")[0]))


def _trimmed_canvas(name: str) -> str:
    # A small centred circle leaves the active cel trimmed to the circle box.
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(drawing.draw_circle(path, 8, 8, 3, "#3366FF", True)))
    return path


def test_draw_pixels_outside_trimmed_cel():
    path = _trimmed_canvas("active_pixels")
    ok(run(drawing.draw_pixels(path, [
        {"x": 0, "y": 0, "color": "#FF0000"},
        {"x": 15, "y": 15, "color": "#00FF00"},
    ])))
    assert _rgba(run(pixel_read.get_pixel_color(path, 0, 0))) == (255, 0, 0, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 15, 15))) == (0, 255, 0, 255)
    # The circle drawn before must stay where it was.
    assert _rgba(run(pixel_read.get_pixel_color(path, 8, 8))) == (51, 102, 255, 255)


def test_draw_line_outside_trimmed_cel():
    path = _trimmed_canvas("active_line")
    ok(run(drawing.draw_line(path, 0, 15, 15, 15, "#FFFFFF")))
    assert _rgba(run(pixel_read.get_pixel_color(path, 0, 15))) == (255, 255, 255, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 15, 15))) == (255, 255, 255, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 8, 8))) == (51, 102, 255, 255)


def test_draw_pixels_offcanvas_is_ignored():
    path = _trimmed_canvas("active_offcanvas")
    ok(run(drawing.draw_pixels(path, [
        {"x": -3, "y": 4, "color": "#FF0000"},
        {"x": 2, "y": 2, "color": "#FF0000"},
    ])))
    assert _rgba(run(pixel_read.get_pixel_color(path, 2, 2))) == (255, 0, 0, 255)


def test_draw_pixels_at_outside_trimmed_cel():
    path = _trimmed_canvas("at_pixels")
    ok(run(drawing.draw_pixels_at(path, "Layer 1", 1,
                                  [{"x": 0, "y": 0, "color": "#FF0000"}], True)))
    assert _rgba(run(pixel_read.get_pixel_color(path, 0, 0))) == (255, 0, 0, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 8, 8))) == (51, 102, 255, 255)
