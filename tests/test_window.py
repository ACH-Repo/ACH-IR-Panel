"""The window, driven the way a hand drives it: through Qt's own mouse and
key pipeline (`QTest` on the window's handle) where the gesture is the
point, and through the operators where it is not.

Picking reads the LAST PAINT, so a test grabs the plot before it clicks.
"""

import os

import numpy as np
import pytest

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest

from irpanel.core import measure, model, profile, session, units
from irpanel.ui.window import MainWindow

from conftest import make_sample


def curve_point(win, scan, wavenumber):
    """Where the drawn curve of `scan` is at `wavenumber`, in pane pixels."""
    plot = win.plot
    rect = plot.plot_rect()
    trace = plot._trace_of(scan)
    k = int(np.argmin(abs(trace.x - wavenumber)))
    return plot.to_widget(QPointF(plot.x_to_px(trace.x[k], rect),
                                  plot.sy_to_px(scan, trace.y[k], rect)))


def drag(win, start, end, steps=12):
    """A press, a drag and a release, through the window's handle."""
    handle = win.windowHandle()
    plot = win.plot
    QTest.mousePress(handle, Qt.LeftButton, Qt.NoModifier,
                     plot.mapTo(win, start.toPoint()))
    for i in range(1, steps + 1):
        point = start + (end - start) * (i / float(steps))
        QTest.mouseMove(handle, plot.mapTo(win, point.toPoint()))
    QTest.mouseRelease(handle, Qt.LeftButton, Qt.NoModifier,
                       plot.mapTo(win, end.toPoint()))


def drag_along(win, scan, x0, x1, answer):
    """Drag along a curve from x0 to x1 (cm-1), answering the list."""
    asked = []
    win.ask_analysis = lambda a, b: asked.append((a, b)) or answer
    win.ask_factor = lambda default=3.0: 5.0
    win.show()
    win.plot.grab()
    drag(win, curve_point(win, scan, x0), curve_point(win, scan, x1))
    win.plot.grab()
    return asked


# ------------------------------------------------------------- the stack
def test_files_open_as_a_cascade(window):
    offsets = [s.offset for s in window.doc.scans]
    assert profile.STACK_NEW
    assert offsets[0] == 0.0
    assert offsets == sorted(offsets, reverse=True)          # first on top
    assert all(step < 0 for step in np.diff(offsets))


def test_the_x_axis_runs_from_high_to_low(window):
    plot = window.plot
    rect = plot.plot_rect()
    assert plot.view_x() == (400.0, 4000.0)          # rounded to the grid
    assert plot.x_to_px(4000.0, rect) == pytest.approx(rect.left())
    assert plot.x_to_px(400.0, rect) == pytest.approx(rect.right())
    assert plot.px_to_x(rect.left() + 0.25 * rect.width(), rect) == \
        pytest.approx(3100.0)
    caption = window.doc.axes["x"].caption(window.doc)
    assert "\\tilde{\\nu}" in caption and "cm^{-1}" in caption


def test_a_stack_has_no_y_numbers_or_ticks(window):
    y = window.doc.axes["y"]
    assert not y.show_numbers and not y.show_ticks
    assert window.plot.numbered_ticks(y) == []


def test_f_frames_x_first_then_y(window):
    plot = window.plot
    plot.set_view_x(1000.0, 2000.0)
    plot.set_view_y(-5.0, 5.0)
    assert plot.reset_view()
    assert plot.view_x() == (400.0, 4000.0)
    assert plot.view_y() == (-5.0, 5.0)              # staged: y waits
    assert plot.reset_view()
    assert plot.view_y() != (-5.0, 5.0)


def test_a_pan_follows_the_hand_on_a_reversed_axis(window):
    plot = window.plot
    rect = plot.plot_rect()
    before = plot.view_x()
    # content moved to the right: lower wavenumbers come in from the left?
    # No - on a reversed axis the HIGHER ones do.
    plot.pan_by(-rect.width() * 0.1, 0.0)
    lo, hi = plot.view_x()
    assert hi > before[1] and lo > before[0]


def test_zoom_keeps_the_wavenumber_under_the_pointer(window):
    plot = window.plot
    rect = plot.plot_rect()
    pos = QPointF(rect.left() + 0.3 * rect.width(), rect.center().y())
    under = plot.px_to_x(pos.x())
    plot.zoom_at(pos, 2.0, both=True)
    assert plot.px_to_x(pos.x()) == pytest.approx(under)
    assert plot.view_x()[1] - plot.view_x()[0] == pytest.approx(1800.0)


# ---------------------------------------------------------------- break
def test_a_break_squeezes_its_stretch_and_is_undone(window):
    plot = window.plot
    rect = plot.plot_rect()
    width_before = plot.x_to_px(1800.0, rect) - plot.x_to_px(2200.0, rect)
    window.set_break({"lo": 1800.0, "hi": 2200.0})
    width_after = plot.x_to_px(1800.0, rect) - plot.x_to_px(2200.0, rect)
    assert width_after == pytest.approx(0.02 * width_before * 3600.0
                                        / (3600.0 - 400.0 * 0.98), rel=0.01)
    # the mapping still goes both ways, across the seam too
    for value in (3000.0, 2000.0, 1500.0):
        assert plot.px_to_x(plot.x_to_px(value, rect), rect) == \
            pytest.approx(value)
    # no tick or number inside, and the curves are cut at the seam
    ticks = [v for v, _at, _t in plot.numbered_ticks(window.doc.axes["x"])]
    assert 2000.0 not in ticks and 2500.0 in ticks and 1500.0 in ticks
    plot.grab()
    trace = plot.traces[0]
    px = plot.x_to_px(np.array([1800.5, 2199.5]), rect)
    assert not np.any((trace.px > px[1] + 0.01) & (trace.px < px[0] - 0.01))
    assert plot.break_seam(rect) is not None
    window.undo_step()
    assert window.doc.x_break is None


def test_the_break_comes_from_a_drag_along_a_curve(window):
    scan = window.doc.scans[0]
    drag_along(window, scan, 2300.0, 1900.0, measure.BREAK)
    cut = window.doc.x_break
    assert cut is not None
    assert cut["lo"] == pytest.approx(1900.0, abs=5.0)
    assert cut["hi"] == pytest.approx(2300.0, abs=5.0)


# ------------------------------------------------------------- analyses
def test_a_drag_along_a_curve_measures_a_peak(window):
    scan = window.doc.scans[1]
    asked = drag_along(window, scan, 1610.0, 1515.0, "Peak position")
    assert asked, "the list was not asked"
    [analysis] = scan.analysis_objects
    assert analysis.value() == pytest.approx(1560.0, abs=0.5)
    assert analysis.span is not None
    assert analysis.summary(window.doc) == "1560 cm^{-1}"
    assert window.plot._analysis_boxes          # it was drawn
    window.undo_step()
    assert not scan.analysis_objects


def test_an_analysis_label_points_from_beyond_the_band(window):
    """A band points down in transmittance: its label hangs BELOW it, and
    above it once the axis shows absorbance."""
    scan = window.doc.scans[0]
    analysis = measure.run("Peak position", scan, 1520.0, 1600.0)
    trace = window.plot._trace_of(scan)
    assert window.plot.label_offset(analysis, trace,
                                    window.plot.plot_rect()) > 0
    window.set_display(unit=units.UNIT_A)
    trace = window.plot._trace_of(scan)
    assert window.plot.label_offset(analysis, trace,
                                    window.plot.plot_rect()) < 0


def test_a_band_area_is_shaded_above_its_absorbance_baseline(window):
    scan = window.doc.scans[0]
    analysis = measure.run("Band area", scan, 1340.0, 1420.0)
    trace = window.plot._trace_of(scan)
    xs, top, base = window.plot.area_baseline(trace, analysis)
    # on a transmittance axis the baseline (straight in A) is not straight
    middle = len(xs) // 2
    straight = base[0] + (base[-1] - base[0]) * (xs[middle] - xs[0]) / (
        xs[-1] - xs[0])
    assert base[middle] != pytest.approx(straight, abs=1e-9)
    # ...and the curve dips below it (bands point down in %T)
    assert np.all(top <= base + 1e-9)
    assert base[0] == pytest.approx(top[0]) and base[-1] == pytest.approx(
        top[-1])


def test_a_width_is_drawn_at_half_height(window):
    scan = window.doc.scans[0]
    analysis = measure.run("Band width", scan, 1660.0, 1740.0)
    ends = window.plot.width_line(window.plot._trace_of(scan), analysis)
    assert ends is not None
    left, right = ends
    fwhm = model.number(analysis.fields["FWHM"])
    assert abs(window.plot.px_to_x(left.x()) - window.plot.px_to_x(
        right.x())) == pytest.approx(fwhm, rel=1e-3)


def test_the_analysis_settings_retype_the_interval(window):
    from irpanel.ui.dialogs import AnalysisSettings
    scan = window.doc.scans[0]
    analysis = measure.run("Peak position", scan, 1520.0, 1600.0)
    dialog = AnalysisSettings(window, analysis)
    dialog.start.setText("1420")
    dialog.end.setText("1340 cm-1")
    dialog._typed_interval()
    assert analysis.value() == pytest.approx(1380.0, abs=0.5)
    assert analysis.cursors() == pytest.approx([1340.0, 1420.0])
    dialog.model.setCurrentIndex(dialog.model.findData("Band width"))
    assert analysis.model_name == "Band width"
    dialog.close()


# ------------------------------------------------ what a stretch becomes
def test_highlight_and_magnify_from_the_drag(window):
    scan = window.doc.scans[0]
    drag_along(window, scan, 3300.0, 2500.0, measure.HIGHLIGHT)
    [region] = window.doc.regions
    assert region.shade and not region.magnifies
    assert region.lo == pytest.approx(2500.0, abs=5.0)
    x, before = [np.array(v) for v in scan.curve(window.doc)]
    drag_along(window, scan, 900.0, 600.0, measure.MAGNIFY)
    magnifier = window.doc.regions[-1]
    assert magnifier.magnifies and magnifier.factor == 5.0
    assert magnifier.scans == [scan] and not magnifier.shade
    assert magnifier.shown_text() == "\\times5"
    _x, after = scan.curve(window.doc)
    assert not np.allclose(before, after)
    window.undo_step()
    assert len(window.doc.regions) == 1
    window.plot.grab()


def test_normalise_to_the_band_dragged(window):
    scan = window.doc.scans[0]
    drag_along(window, scan, 1600.0, 1520.0, measure.NORMALISE)
    assert window.doc.norm == units.NORM_BAND
    lo, hi = window.doc.norm_band
    assert lo == pytest.approx(1520.0, abs=5.0)
    assert "normalised" in window.doc.axes["y"].caption(window.doc)


# ------------------------------------------------- markers and distances
def test_band_markers_and_the_distance_between_them(window):
    plot = window.plot
    rect = plot.plot_rect()
    a = window.add_marker_line(text="\\nu_{a}(COO^{-})",
                               at=QPointF(plot.x_to_px(1562.0, rect),
                                          rect.center().y()))
    b = window.add_marker_line(text="\\nu_{s}(COO^{-}) {}",
                               at=QPointF(plot.x_to_px(1380.0, rect),
                                          rect.center().y()))
    assert a.vline == pytest.approx(1562.0, abs=1.0)
    assert plot.label_text(b).endswith("cm^{-1}")
    window.doc.select_only([a, b])
    span = window.add_span_between()
    assert span.ends == [a, b]
    assert span.distance() == pytest.approx(182.0, abs=2.0)
    # moving a marker moves the arrow's end with it
    a.vline = 1600.0
    assert span.end_values()[0] == 1600.0
    assert "{:.0f} cm^{{-1}}".format(1600.0 - b.vline) in plot.span_text(span)
    # a marker taken away leaves that end where the marker was...
    window.doc.select_only([a])
    window.remove_selected()
    assert a not in window.doc.labels
    assert span.ends == [None, b] and span.x0 == 1600.0
    # ...and an undo ties it to the marker again
    window.undo_step()
    assert span.ends == [a, b]
    plot.grab()


def test_a_white_page_under_a_dark_theme(window):
    """The handling keeps the program theme's colours on a page drawn in
    the light ink. The markup's accent table once had the same module
    name as the theme's (`ACCENTS`) and replaced it: a white page under
    the default theme raised KeyError 'tilde'."""
    from irpanel.ui import plot as plot_module
    assert window.doc.theme != plot_module.THEME_LIGHT
    window.set_background("#ffffff")
    assert window.plot.page_colour().name() == "#ffffff"
    window.plot.grab()


def test_a_band_marker_line_is_under_the_curves_its_text_over(window):
    """The plotter's `zorder=-1`: the dashed line goes under the curves and
    breaks around its text. A white box behind the text once cut every
    curve that ran under it."""
    plot = window.plot
    rect = plot.plot_rect()
    window.add_marker_line(text="\\nu(C=O)", at=QPointF(
        plot.x_to_px(1700.0, rect), rect.center().y()))
    order = []
    for name in ("_paint_vline", "_paint_trace", "_paint_text_labels"):
        real = getattr(plot, name)
        setattr(plot, name, lambda *a, _n=name, _r=real, **k: (
            order.append(_n), _r(*a, **k))[1])
    plot.grab()
    curves = [i for i, name in enumerate(order) if name == "_paint_trace"]
    assert order.index("_paint_vline") < curves[0]
    assert order.index("_paint_text_labels") > curves[-1]


def test_a_region_and_a_span_move_along_x_with_g(window):
    window.show()
    plot = window.plot
    region = window.add_region(2500.0, 3000.0)
    window.doc.select_only([region])
    plot.setFocus()
    plot.start_grab()
    plot._move["typed"] = "-100"
    plot._move["axis"] = "x"
    plot._update_move(plot._move["start"])
    plot._finish_move()
    assert region.lo == pytest.approx(2400.0, abs=1.0)
    assert region.hi == pytest.approx(2900.0, abs=1.0)


def test_labels_at_the_left_edge(window):
    """Above the high-wavenumber end in transmittance, below it in
    absorbance: on the side the bands do not point to."""
    made = window.label_edges()
    assert len(made) == 3
    assert all(label.attached for label in made)
    plot = window.plot
    rect = plot.plot_rect()
    for label in made:
        x, _y = plot.artist_point(label, rect)
        assert x < rect.left() + 0.1 * rect.width()
        assert label.dy < 0 and label.anchor == "bottom left"
    assert window.label_edges() == []                  # not twice
    window.undo_step()
    window.set_display(unit=units.UNIT_A)
    window.plot.grab()
    made = window.label_edges()
    assert all(label.dy > 0 and label.anchor == "top left"
               for label in made)


# ------------------------------------------------------------- the y axis
def test_the_y_unit_and_normalisation_are_one_undo_step_each(window):
    offsets = [s.offset for s in window.doc.scans]
    window.set_display(unit=units.UNIT_A)
    assert window.doc.axes["y"].caption(window.doc).startswith("Absorbance")
    window.set_display(norm=units.NORM_RANGE)
    window.undo_step()
    assert window.doc.norm == units.NORM_GLOBAL
    window.undo_step()
    assert window.doc.y_unit == units.UNIT_T
    assert [s.offset for s in window.doc.scans] == pytest.approx(offsets)


def test_a_file_that_does_not_say_can_be_told(window):
    sample = make_sample("GUESSED", said=False)
    window._sample_loaded(sample)
    scan = window.doc.scans[-1]
    window.edit_object(scan)                 # what a double-click opens
    dialog = window._dialogs[-1]
    dialog.recorded.setCurrentIndex(dialog.recorded.findData("A"))
    assert sample.unit_override == "A"
    dialog.accept()
    assert sample.unit_override == "A"
    window.undo_step()
    assert sample.unit_override is None


# --------------------------------------------------------------- output
def test_export_and_reopen(window, tmp_path):
    scan = window.doc.scans[0]
    measure.run("Peak position", scan, 1520.0, 1600.0)
    window.set_break({"lo": 1800.0, "hi": 2200.0})
    png = window.export_image(str(tmp_path / "figure.png"), light=True)
    assert QImage(png).width() > 100
    svg = window.export_image(str(tmp_path / "figure.svg"), light=True)
    assert "irpanel-axes" in open(svg, encoding="utf-8").read()
    path = window.save_session(path=str(tmp_path / "figure.irpanel"))
    samples = {s.path: s for s in window.doc.samples}
    doc, problems = session.load(
        path, lambda p: model.Sample(p, samples[p].spectrum))
    assert problems == [] and doc.x_break == window.doc.x_break
    assert len(doc.scans[0].analysis_objects) == 1


def test_the_menus_and_operators_are_consistent(window):
    assert not window.ops.duplicate_keys()
    for op in window.ops.all() if hasattr(window.ops, "all") else []:
        assert op.label
    assert window.ops.get("file.open").label == "Open spectra..."
    assert window.ops.get("view.break") is not None
    assert window.ops.get("sample.molar_mass") is None
    assert window.ops.get("arrow.flip") is None


def test_a_drop_of_readable_files(qapp, tmp_path):
    from irpanel.core import loader
    win = MainWindow()
    path = tmp_path / "two.csv"
    path.write_text("400;0,1\n401;0,2\n402;0,15\n")
    assert loader.looks_readable(str(path))
    assert not loader.looks_readable(str(tmp_path / "image.png"))


def test_a_session_keeps_a_copy_of_its_files(qapp, tmp_path):
    """IR-Panel keeps a copy of every file inside the session
    (`profile.EMBED_SOURCES`): deleted, the file is read from the copy,
    and the copy goes on into the next save."""
    import json
    from irpanel.core import loader, profile, session
    assert profile.EMBED_SOURCES
    data = tmp_path / "data"
    data.mkdir()
    source = data / "spectrum.csv"
    xs = np.linspace(4000.0, 400.0, 400)
    ys = 90.0 - 40.0 * np.exp(-((xs - 1600.0) / 30.0) ** 2)
    source.write_text("\n".join("{:.2f};{:.4f}".format(x, y)
                                for x, y in zip(xs, ys)), encoding="utf-8")
    win = MainWindow()
    win._sample_loaded(loader.read_sample(str(source)))
    saved = tmp_path / "figure.irpanel"
    session.save(win.doc, str(saved))
    state = json.loads(saved.read_text(encoding="utf-8"))
    assert state["samples"][0].get("copy")
    source.unlink()
    doc, problems = session.load(str(saved), loader.read_sample)
    assert len(doc.samples) == 1 and doc.samples[0].from_copy
    assert doc.samples[0].path == str(source) and len(doc.scans) == 1
    spectrum = doc.samples[0].spectrum             # by wavenumber
    expected = 90.0 - 40.0 * np.exp(-((spectrum.x - 1600.0) / 30.0) ** 2)
    assert np.allclose(spectrum.y, expected, atol=0.01)   # x to 0.01
    assert any("copy inside the session" in p for p in problems)
    again = tmp_path / "again.irpanel"
    session.save(doc, str(again))
    assert json.loads(again.read_text(encoding="utf-8"))["samples"][0][
        "copy"] == state["samples"][0]["copy"]


def test_a_region_edge_is_dragged_on_its_own(window):
    """Each of a region's two limits moves by itself on the figure: the
    edge of a selected region anywhere along it. One undo step."""
    plot = window.plot
    window.add_region(1500.0, 1700.0)
    region = window.doc.regions[-1]
    window.doc.select_only([region])
    window.refresh()
    plot.grab()
    rect = plot.plot_rect()
    at = QPointF(plot.x_to_px(1700.0, rect), rect.center().y())
    assert plot.region_edge_at(at) == (region, "hi")
    plot._start_region_edge(region, "hi")
    plot._drag_region_edge(QPointF(plot.x_to_px(1800.0, rect), at.y()))
    plot._finish_region_edge()
    assert region.lo == pytest.approx(1500.0)
    assert region.hi == pytest.approx(1800.0, abs=2.0)
    window.undo_step()
    assert (region.lo, region.hi) == pytest.approx((1500.0, 1700.0))
    # dragged past the other edge, the two come back in order
    plot._start_region_edge(region, "lo")
    plot._drag_region_edge(QPointF(plot.x_to_px(1900.0, rect), at.y()))
    plot._finish_region_edge()
    assert region.lo < region.hi
    assert region.hi == pytest.approx(1900.0, abs=2.0)


def test_a_region_says_several_lines(window):
    from irpanel.ui.dialogs import RegionSettings
    window.add_region(2500.0, 3000.0)
    region = window.doc.regions[-1]
    dialog = RegionSettings(window, region)
    dialog.text.setPlainText("C-H\nstretch")
    assert region.text == "C-H\nstretch"
    window.plot.grab()
    plot = window.plot
    box = plot.region_text_box(region)              # two lines tall
    assert box.height() > 1.5 * plot.region_font(region).pointSizeF()
    dialog.close()


def test_all_together_from_the_canvas_and_f3(window):
    """A tick on the empty plot's right-click menu turns "all together,
    0 to 1" on and off; F3 has it and "each 0 to 1" beside it."""
    assert window.ops.get("view.norm_global") is not None
    assert window.ops.get("view.norm_range") is not None
    window.set_display(norm=units.NORM_NONE)
    menu = window.context_menu_for(None)
    [tick] = [a for a in menu.actions() if a.text().startswith(
        "Normalise all spectra together")]
    assert tick.isCheckable() and not tick.isChecked()
    tick.trigger()
    assert window.doc.norm == units.NORM_GLOBAL
    menu = window.context_menu_for(None)
    [tick] = [a for a in menu.actions() if a.text().startswith(
        "Normalise all spectra together")]
    assert tick.isChecked()
    tick.trigger()
    assert window.doc.norm == units.NORM_NONE
    assert window.run_op("view.norm_range")
    assert window.doc.norm == units.NORM_RANGE
