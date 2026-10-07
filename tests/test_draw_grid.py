"""draw_grid: paint pixel art from rows of characters plus a palette."""
from conftest import BASE, ok, run

from aseprite_mcp.tools import canvas, drawing, pixel_read


def _rgba(pixel_result: str) -> tuple[int, int, int, int]:
    s = str(pixel_result)
    return (int(s.split("r=")[1].split(",")[0]),
            int(s.split("g=")[1].split(",")[0]),
            int(s.split("b=")[1].split(",")[0]),
            int(s.split("a=")[1].split(")")[0]))


def _canvas(name: str, w: int = 8, h: int = 8) -> str:
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(w, h, path)))
    return path


def test_grid_paints_palette_and_skips_dots():
    path = _canvas("grid_basic")
    ok(run(drawing.draw_grid(path, ["R.G", ".B."],
                             {"R": "#FF0000", "G": "#00FF00", "B": "#0000FF"})))
    assert _rgba(run(pixel_read.get_pixel_color(path, 0, 0))) == (255, 0, 0, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 2, 0))) == (0, 255, 0, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 1, 1))) == (0, 0, 255, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 1, 0)))[3] == 0  # "." stays empty


def test_grid_offset_and_layer():
    path = _canvas("grid_layer")
    ok(run(canvas.add_layer(path, "sprite")))
    ok(run(drawing.draw_grid(path, ["K"], {"K": "#111111"}, x=5, y=6,
                             layer_name="sprite")))
    assert _rgba(run(pixel_read.get_pixel_color(path, 5, 6, "sprite", 1))) == (17, 17, 17, 255)


def test_grid_does_not_erase_existing_pixels():
    path = _canvas("grid_keep")
    ok(run(drawing.draw_circle(path, 4, 4, 2, "#3366FF", True)))
    ok(run(drawing.draw_grid(path, ["R"], {"R": "#FF0000"})))
    assert _rgba(run(pixel_read.get_pixel_color(path, 0, 0))) == (255, 0, 0, 255)
    assert _rgba(run(pixel_read.get_pixel_color(path, 4, 4))) == (51, 102, 255, 255)


def test_grid_reports_unknown_characters():
    path = _canvas("grid_unknown")
    res = run(drawing.draw_grid(path, ["RX"], {"R": "#FF0000"}))
    assert res.startswith("Invalid") and "X" in res, res


def test_grid_rejects_bad_palette_color():
    path = _canvas("grid_badcolor")
    res = run(drawing.draw_grid(path, ["R"], {"R": "#GG0000"}))
    assert res.startswith("Invalid"), res


def test_grid_rejects_all_transparent():
    path = _canvas("grid_empty")
    res = run(drawing.draw_grid(path, ["....", "...."], {"K": "#000000"}))
    assert res.startswith("Invalid"), res
