"""The data layer without a window: units, normalisation, the stack, the
analyses, the session."""

import json

import numpy as np
import pytest

from irpanel.core import (arrange, export, labels, measure, model, readers,
                          session, undo, units)

from conftest import BANDS, make_sample, make_spectrum


# ------------------------------------------------------------------ units
def test_transmittance_and_absorbance_convert_honestly():
    a = np.array([0.0, 1.0, 2.0])
    t, missing = units.to_display(a, readers.UNIT_A, units.UNIT_T)
    assert missing is None
    assert t == pytest.approx([100.0, 10.0, 1.0])
    back, _ = units.to_display(t, readers.UNIT_T_PERCENT, units.UNIT_A)
    assert back == pytest.approx(a)
    frac, _ = units.to_display(np.array([0.5]), readers.UNIT_T_FRACTION,
                               units.UNIT_T)
    assert frac == pytest.approx([50.0])


def test_no_transmittance_at_or_below_zero_is_made_up():
    shown, _ = units.to_display(np.array([50.0, 0.0, -1.0]),
                                readers.UNIT_T_PERCENT, units.UNIT_A)
    assert np.isfinite(shown[0]) and np.isnan(shown[1]) and np.isnan(shown[2])


def test_something_that_is_neither_says_so():
    assert units.to_display(np.ones(3), "SB", units.UNIT_T) == (
        None, units.MISSING_UNIT)


def test_the_guess_reads_the_shape_not_the_scale():
    x = np.linspace(400, 4000, 3601)
    a = make_spectrum(readers.UNIT_A).y
    assert units.guess(a) == readers.UNIT_A
    assert units.guess(a * 50.0) == readers.UNIT_A          # any scale
    assert units.guess(make_spectrum().y) == readers.UNIT_T_PERCENT
    assert units.guess(make_spectrum(readers.UNIT_T_FRACTION).y) == \
        readers.UNIT_T_FRACTION
    assert x.size


def test_a_file_that_does_not_say_is_guessed_and_says_so():
    sample = make_sample(said=False)
    assert sample.unit_guessed
    assert sample.recorded_unit == readers.UNIT_T_PERCENT
    assert "guessed" in sample.unit_text()
    sample.unit_override = readers.UNIT_A
    assert sample.recorded_unit == readers.UNIT_A
    assert sample.unit_source == "set by hand"


def test_a_typed_wavenumber():
    for text, value in (("1562", 1562.0), ("1562,3 cm-1", 1562.3),
                        ("1600-38", 1562.0), ("1500 cm^{-1}", 1500.0),
                        ("2000 1/cm", 2000.0)):
        assert units.parse_wavenumber(text) == pytest.approx(value)
    assert units.parse_wavenumber("cm-1") is None
    assert units.parse_wavenumber("abc") is None


# ---------------------------------------------------------- normalisation
def test_normalising_is_said_on_the_axis(document):
    axis = document.axes["y"]
    assert document.norm == units.NORM_GLOBAL         # where a figure starts
    assert axis.caption(document) == "Transmittance (normalised)"
    document.norm = units.NORM_NONE
    assert axis.caption(document) == "Transmittance  /  %"
    document.norm = units.NORM_RANGE
    assert "normalised" in axis.caption(document)
    document.y_unit = units.UNIT_A
    assert axis.caption(document) == "Absorbance (normalised)"


def test_range_normalises_each_spectrum_zero_to_one(document):
    document.norm = units.NORM_RANGE
    _x, y = document.scans[0].curve(document)
    assert np.nanmin(y) == pytest.approx(0.0)
    assert np.nanmax(y) == pytest.approx(1.0)


def test_a_band_is_the_yardstick(document):
    """Normalised to the 1560 band, that band's tip is 0 in transmittance
    (it points down) and 1 in absorbance, in every spectrum."""
    doc = document
    doc.add_sample(make_sample("TEST-2", scale=0.3))
    doc.norm, doc.norm_band = units.NORM_BAND, [1540.0, 1580.0]
    for unit, tip in ((units.UNIT_T, 0.0), (units.UNIT_A, 1.0)):
        doc.y_unit = unit
        for scan in doc.scans:
            scan._cache_key = None
            x, y = scan.curve(doc)
            inside = (x >= 1540) & (x <= 1580)
            extreme = y[inside].min() if unit == units.UNIT_T else \
                y[inside].max()
            assert extreme == pytest.approx(tip)


def test_a_band_a_spectrum_does_not_reach_says_so(document):
    document.norm, document.norm_band = units.NORM_BAND, [5000.0, 5100.0]
    assert document.scans[0].missing_for(document) == units.MISSING_BAND
    assert document.scans_missing()
    assert any("NORMALISATION BAND" in line
               for line in export.warnings_for(document))


def test_a_typed_caption_on_a_normalised_axis_is_never_stamped(document):
    """A caption the user typed is theirs: nothing is stamped on the
    figure about what it says (Christian, 2026-10-05). It used to be
    "NORMALISED, and the y caption does not say so"."""
    document.norm = units.NORM_RANGE
    document.axes["y"].label = "Transmittance  /  %"
    assert not export.warnings_for(document)
    assert document.axes["y"].caption(document) == "Transmittance  /  %"


def test_a_change_of_unit_keeps_the_stack_in_order(document):
    doc = document
    for k, scale in enumerate((0.2, 2.0, 1.0)):
        doc.add_sample(make_sample("TEST-{}".format(k + 2), scale=scale))
    for k, scan in enumerate(doc.scans):
        scan.offset = -40.0 * k
    for change in (dict(unit=units.UNIT_A), dict(norm=units.NORM_RANGE)):
        changes = doc.set_display(**change)
        for obj, name, value in changes:
            setattr(obj, name, value)
        offsets = [s.offset for s in doc.scans]
        assert offsets == sorted(offsets, reverse=True)       # same order
        steps = np.diff(offsets)
        assert steps == pytest.approx([steps[0]] * len(steps))  # even still
    assert doc.y_unit == units.UNIT_A and doc.norm == units.NORM_RANGE


# ----------------------------------------------------------- magnifying
def test_a_magnified_stretch_stays_joined_to_the_curve(document):
    doc = document
    scan = doc.scans[0]
    x, before = [np.array(v) for v in scan.curve(doc)]
    region = model.Region(1, 600.0, 900.0)
    region.scans, region.factor = [scan], 3.0
    doc.regions.append(region)
    _x, after = scan.curve(doc)
    outside = (x < 600) | (x > 900)
    assert np.array_equal(before[outside], after[outside])
    inside = np.flatnonzero((x >= 600) & (x <= 900))
    # the ends of the stretch do not move: no step in the curve
    assert after[inside[0]] == pytest.approx(before[inside[0]])
    assert after[inside[-1]] == pytest.approx(before[inside[-1]])
    # the band at 700 cm-1, three times as deep below its baseline
    tip = inside[np.argmin(before[inside])]
    chord = np.interp(x[tip], [x[inside[0]], x[inside[-1]]],
                      [before[inside[0]], before[inside[-1]]])
    assert chord - after[tip] == pytest.approx(3.0 * (chord - before[tip]))
    region.visible = False
    assert np.array_equal(scan.curve(doc)[1], before)


# ------------------------------------------------------------- analyses
def test_analyses_are_the_same_whatever_the_file_is_in():
    """Measured on absorbance, always: a %T, an A and a fractional-T file
    of one spectrum give the same numbers."""
    found = []
    for unit in (readers.UNIT_T_PERCENT, readers.UNIT_A,
                 readers.UNIT_T_FRACTION):
        doc = model.Document()
        scan = doc.add_sample(make_sample(unit=unit))
        position = measure.compute("Peak position", scan, 1520.0, 1600.0)
        width = measure.compute("Band width", scan, 1660.0, 1740.0)
        area = measure.compute("Band area", scan, 1650.0, 1750.0)
        found.append([model.number(position["Position"]),
                      model.number(width["FWHM"]),
                      model.number(area["Area"])])
    for other in found[1:]:
        assert other == pytest.approx(found[0], rel=1e-6)
    position, fwhm, area = found[0]
    assert position == pytest.approx(1560.0, abs=0.05)
    # A Lorentzian of half width 12 is 24 wide at half height; above a
    # baseline drawn between the interval's ends, which its own tails lift
    # by 0.074 A at +-40 cm-1, it is 22.05 (worked out by hand).
    assert fwhm == pytest.approx(22.05, abs=0.1)
    assert area > 0


def test_a_peak_at_the_edge_of_the_interval_is_no_peak(document):
    scan = document.scans[0]
    assert measure.compute("Peak position", scan, 1600.0, 1650.0) is None


def test_the_position_is_not_tied_to_the_grid():
    doc = model.Document()
    sample = model.Sample("C:/nowhere/coarse.sp", readers.Spectrum(
        np.arange(1500.0, 1620.0, 4.0),
        100.0 * 10 ** -(0.8 / (1 + ((np.arange(1500.0, 1620.0, 4.0)
                                     - 1561.3) / 10.0) ** 2)),
        readers.UNIT_T_PERCENT))
    scan = doc.add_sample(sample)
    found = model.number(measure.compute("Peak position", scan, 1510.0,
                                         1610.0)["Position"])
    assert found == pytest.approx(1561.3, abs=0.8)
    assert found % 4.0 != 0.0


def test_labels_are_templates_of_the_measurement(document):
    analysis = measure.run("Peak position", document.scans[0], 1520.0,
                           1600.0)
    assert labels.render(analysis, document).text == "1560 cm^{-1}"
    analysis.label = "\\nu_{a}(COO^{-}) {}"
    assert labels.render(analysis, document).text.endswith("1560 cm^{-1}")
    analysis.label = "{} nm"
    problems = labels.render(analysis, document).problems
    assert problems and problems[0][0] == "unit"
    analysis.label = "lit. 1562 cm-1"
    assert labels.render(analysis, document).problems[0][0] == "typed"


def test_band_marker_text_fills_in_its_wavenumber():
    assert labels.fill_wavenumber("\\nu(C=O) {}", 1708.44) == \
        "\\nu(C=O) 1708 cm^{-1}"
    assert labels.fill_wavenumber("x_{}", 1.0) == "x_{}"


# --------------------------------------------------------------- arrange
def test_align_puts_curves_on_top_of_one_another(document):
    doc = document
    other = doc.add_sample(make_sample("TEST-2"))
    other.offset = -30.0
    changes = arrange.align_to(doc.scans[0], [other],
                               lambda s: s.kept_curve(doc))
    assert changes[0][2] == pytest.approx(0.0, abs=1e-6)


def test_a_drag_is_one_undo_step(document):
    stack = undo.UndoStack()
    scan = document.scans[0]
    stack.begin_group("drag")
    for value in (1.0, 2.0, 3.0):
        stack.set_props([(scan, "offset", value)], "move")
    stack.end_group()
    assert scan.offset == 3.0
    stack.undo()
    assert scan.offset == 0.0


# --------------------------------------------------------------- session
def test_session_round_trip(tmp_path):
    doc = model.Document()
    first = doc.add_sample(make_sample("TEST-1"))
    second = doc.add_sample(make_sample("TEST-2", said=False))
    second.sample.unit_override = readers.UNIT_T_PERCENT
    second.offset = -35.5
    doc.y_unit, doc.norm, doc.norm_band = (units.UNIT_A, units.NORM_BAND,
                                           [1540.0, 1580.0])
    doc.x_break = {"lo": 1900.0, "hi": 2300.0, "compress": 0.05, "gap": 6.0}
    made = measure.run("Band area", first, 1650.0, 1750.0)
    made.label = "C=O {}"
    marker_a = doc.add_label("\\nu_{a}", 0.4, 0.2)
    marker_a.vline = 1560.0
    marker_b = doc.add_label("\\nu_{s}", 0.6, 0.2)
    marker_b.vline = 1380.0
    span = model.SpanArrow(9, 1560.0, 1380.0, 0.35)
    span.ends = [marker_a, marker_b]
    doc.spans.append(span)
    region = model.Region(8, 600.0, 900.0)
    region.scans, region.factor, region.shade = [second], 4.0, False
    doc.regions.append(region)
    owned = doc.add_label("TEST-2", 0.1, 0.5, second)
    owned.at, owned.dx, owned.dy = ("i", 3500), 4.0, 4.0
    samples = {s.path: s for s in doc.samples}
    path = tmp_path / "figure.irpanel"
    session.save(doc, str(path))
    with open(str(path), encoding="utf-8") as fh:
        assert json.load(fh)["format"] == "irpanel-session"
    back, problems = session.load(
        str(path), lambda p: model.Sample(p, samples[p].spectrum))
    assert problems == []
    assert [s.sample.path for s in back.scans] == [s.sample.path
                                                   for s in doc.scans]
    assert back.scans[1].offset == -35.5
    assert back.samples[1].unit_override == readers.UNIT_T_PERCENT
    assert (back.y_unit, back.norm, back.norm_band) == (
        units.UNIT_A, units.NORM_BAND, [1540.0, 1580.0])
    assert back.x_break == doc.x_break
    again = back.scans[0].analysis_objects[0]
    assert again.label == "C=O {}"
    assert model.number(again.fields["Area"]) == pytest.approx(
        model.number(made.fields["Area"]))
    assert back.spans[0].ends[0] is back.labels[0]
    assert back.spans[0].end_values() == (1560.0, 1380.0)
    assert back.regions[0].scans == [back.scans[1]]
    assert back.regions[0].factor == 4.0 and not back.regions[0].shade
    label = [lb for lb in back.labels if lb.scan is not None][0]
    assert label.scan is back.scans[1] and label.at == ("i", 3500)


def test_a_moved_file_costs_one_line_not_the_figure(tmp_path):
    doc = model.Document()
    doc.add_sample(make_sample("TEST-1"))
    doc.add_sample(make_sample("TEST-2"))
    path = tmp_path / "figure.irpanel"
    session.save(doc, str(path))
    keep = doc.samples[0]

    def read(p):
        if p != keep.path:
            raise readers.ReadError("no such file")
        return model.Sample(p, keep.spectrum)

    back, problems = session.load(str(path), read)
    assert len(back.scans) == 1 and len(problems) == 1


# ---------------------------------------------------------------- export
def test_the_csv_is_what_is_drawn(document, tmp_path):
    document.norm = units.NORM_NONE
    document.scans[0].offset = -10.0
    path = export.curves_csv(document, str(tmp_path / "out.csv"))
    rows = open(path, encoding="utf-8").read().splitlines()
    data = [r for r in rows if not r.startswith("#")]
    assert data[0].startswith("TEST-1 Wavenumber/cm-1,TEST-1 "
                              "Transmittance/%T")
    first = [float(v) for v in data[1].split(",")]
    assert first[0] == pytest.approx(4000.0)       # high wavenumber first
    x, y = document.scans[0].curve(document)
    assert first[1] == pytest.approx(y[-1], rel=1e-5)


def test_bands_used_by_the_fixture_are_where_it_says():
    x = np.linspace(400, 4000, 3601)
    a = make_spectrum(readers.UNIT_A).y
    for centre, _height, _half in BANDS:
        near = (x > centre - 5) & (x < centre + 5)
        assert np.argmax(a[near]) == np.argmin(abs(x[near] - centre))


# --------------------------------------------- all together, 0 to 1
def _global_doc(*scales):
    doc = model.Document()
    for k, scale in enumerate(scales):
        doc.add_sample(make_sample("TEST-{}".format(k + 1), scale=scale))
    doc.norm = units.NORM_GLOBAL
    return doc


def test_all_together_keeps_the_depths_in_proportion():
    """One scale for every spectrum on show: the lowest value of any is 0,
    the highest of any 1."""
    doc = _global_doc(1.0, 0.4)
    low, high = doc.norm_extent()
    for scan in doc.scans:
        own, _missing = units.to_display(scan.sample.y,
                                         scan.sample.recorded_unit,
                                         units.UNIT_T)
        _x, y = scan.curve(doc)
        assert y == pytest.approx((own - low) / (high - low))
    tops = [np.nanmax(s.curve(doc)[1]) for s in doc.scans]
    bottoms = [np.nanmin(s.curve(doc)[1]) for s in doc.scans]
    assert max(tops) == pytest.approx(1.0) and min(bottoms) == \
        pytest.approx(0.0)
    assert bottoms[1] > 0.1                   # the weaker one stays weaker


def test_a_spectrum_opened_or_hidden_rescales_the_rest():
    doc = _global_doc(0.4)
    scan = doc.scans[0]
    scan.offset = -0.3
    assert np.nanmin(scan.curve(doc)[1]) == pytest.approx(-0.3)
    deeper = doc.add_sample(make_sample("TEST-2", scale=2.0))
    assert np.nanmin(scan.curve(doc)[1]) > -0.3 + 0.1   # follows the new
    assert scan.offset == -0.3                            # offsets stay
    deeper.visible = False
    assert np.nanmin(scan.curve(doc)[1]) == pytest.approx(-0.3)
