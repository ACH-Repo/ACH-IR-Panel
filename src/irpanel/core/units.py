"""What the y axis means, and what a spectrum needs before it can say so.

UI-free on purpose: everything here is arithmetic and naming, so it can be
tested without a window.

**Two quantities, converted honestly.** A spectrum is drawn as
transmittance in percent or as absorbance, whichever it was recorded in:
A = -log10(T), T = 10^-A. A transmittance at or below zero (detector noise
in a saturated band) has no absorbance; that sample is left out of the
curve (NaN), never clipped to a made-up value.

**What a file does not say is guessed, and the guess is said.** A `.sp`, a
`.spa` and a JCAMP file state their unit; a two-column text file does not.
There `guess` decides from the shape of the data - absorbance lies on a low
baseline with its bands UP, transmittance on a high one with its bands DOWN
- and the loader records that it was a guess. The file's settings can
overrule it.

**Normalisation is allowed, and it is written on the axis.** Scaling
spectra is defensible for IR - the question is where the bands are and how
they compare, not how thick the pellet was - so it exists, but never
silently: a normalised axis's caption says "normalised", and its numbers
are 0 to 1, not per cent. Three ways:

* `global` (where a figure starts): ALL the spectra on show together - the
  lowest value of any is 0, the highest of any 1 - so their depths keep
  their proportions. A spectrum opened, hidden or cut changes the scale,
  and every curve follows (`Document.norm_extent`).
* `range`: each spectrum from its own lowest to its own highest value is 0
  to 1.
* `band`: a chosen band is the yardstick. Its strongest point is 1 (0 for
  transmittance, whose bands point down) and the spectrum's baseline end
  0 (1): the bands of different samples compared at equal strength of that
  one.
"""

import re

import numpy as np

from . import readers

#: The two things a spectrum is drawn as.
UNIT_T = readers.UNIT_T_PERCENT
UNIT_A = readers.UNIT_A
#: In menu order; transmittance first, the default.
UNITS = (UNIT_T, UNIT_A)

UNIT_TITLES = {UNIT_T: "Transmittance (%)", UNIT_A: "Absorbance"}

#: The y caption, by unit, and normalised.
AXIS_LABEL = {
    UNIT_T: "Transmittance  /  %",
    UNIT_A: "Absorbance  /  arb. units",
}
AXIS_LABEL_NORMALISED = {
    UNIT_T: "Transmittance (normalised)",
    UNIT_A: "Absorbance (normalised)",
}

#: The x caption: the wavenumber, tilde nu, in reciprocal centimetres.
X_LABEL = "$\\tilde{\\nu}$  /  cm^{-1}"
#: How a wavenumber is written after a number.
WAVENUMBER_UNIT = "cm^{-1}"
#: The same, as plain text (status line, CSV headers).
WAVENUMBER_TEXT = "cm-1"

#: The normalisations.
NORM_NONE = "none"
NORM_GLOBAL = "global"
NORM_RANGE = "range"
NORM_BAND = "band"
NORMS = (NORM_NONE, NORM_GLOBAL, NORM_RANGE, NORM_BAND)
NORM_TITLES = {NORM_NONE: "not normalised",
               NORM_GLOBAL: "all spectra together, 0 to 1",
               NORM_RANGE: "each spectrum 0 to 1",
               NORM_BAND: "each spectrum to one band"}

#: What a spectrum needs to be drawn, when it cannot be.
MISSING_UNIT = "absorbance or transmittance"
MISSING_BAND = "normalisation band"


def caption(unit, norm=NORM_NONE):
    """The y axis's caption for `unit`, normalised or not."""
    table = AXIS_LABEL if norm == NORM_NONE else AXIS_LABEL_NORMALISED
    return table.get(unit, "Intensity")


def to_display(values, recorded, unit):
    """`(values, missing)`: the stored `values`, recorded in `recorded`
    (`readers.UNIT_*`), as `unit` (`UNIT_T` or `UNIT_A`).

    `missing` is None, or what stops the conversion - a spectrum recorded
    as something that is neither (a single beam, a reflectance) cannot be
    drawn as either, and says so instead of being drawn wrong."""
    if recorded not in readers.CONVERTIBLE:
        return None, MISSING_UNIT
    values = np.asarray(values, dtype=float)
    if recorded == unit:
        return values, None
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        if unit == UNIT_T:
            if recorded == readers.UNIT_T_FRACTION:
                return values * 100.0, None
            return 100.0 * np.power(10.0, -values), None      # from A
        if recorded == readers.UNIT_T_FRACTION:
            fraction = values
        else:
            fraction = values / 100.0
        out = np.where(fraction > 0.0, -np.log10(np.where(
            fraction > 0.0, fraction, 1.0)), np.nan)
        return out, None


def absorbance(values, recorded):
    """The values as absorbance (what band areas and widths are measured
    in), or None when they are neither transmittance nor absorbance."""
    return to_display(values, recorded, UNIT_A)[0]


def guess(values):
    """`UNIT_A`, `UNIT_T_PERCENT` or `UNIT_T_FRACTION` for values whose
    file does not say which they are.

    Scale-free: where the BASELINE sits between the lowest and the highest
    values (the 1st and 99th percentiles, so a spike does not decide).
    Absorbance has its baseline near the bottom and its bands up;
    transmittance near the top with its bands down. Transmittance above 1.5
    anywhere is per cent (no fraction gets there)."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return UNIT_A
    low, middle, high = np.percentile(values, [1, 50, 99])
    span = high - low
    if span <= 0:
        return UNIT_A
    if (middle - low) / span <= 0.55:
        return UNIT_A
    return (readers.UNIT_T_PERCENT if float(np.max(values)) > 1.5
            else readers.UNIT_T_FRACTION)


def normaliser(x, y, unit, norm, band=None, extent=None):
    """`(scale, shift, missing)` that normalise `y` (in `unit`) as
    `y * scale + shift`, or `(1, 0, None)` for none.

    Affine on purpose: the same two numbers carry a point taken off the
    curve (a band's half height, a baseline) onto the drawn curve.
    `missing` is `MISSING_BAND` when a band is asked for that the spectrum
    does not reach (or that is not given). `extent` is what `global`
    scales by: `(low, high)` of every spectrum on show, in `unit`."""
    if norm == NORM_GLOBAL:
        # One scale for every curve: the lowest value of any curve on show
        # is 0 and the highest 1, so their heights keep their proportions.
        if not extent:
            return 1.0, 0.0, None
        low, high = float(extent[0]), float(extent[1])
        if not high > low:
            return 1.0, 0.0, None
        return 1.0 / (high - low), -low / (high - low), None
    if norm not in (NORM_RANGE, NORM_BAND):
        return 1.0, 0.0, None
    y = np.asarray(y, dtype=float)
    finite = np.isfinite(y)
    if finite.sum() < 2:
        return 1.0, 0.0, MISSING_BAND if norm == NORM_BAND else None
    low, high = float(np.min(y[finite])), float(np.max(y[finite]))
    down = unit == UNIT_T
    if norm == NORM_BAND:
        if not band or len(band) != 2:
            return 1.0, 0.0, MISSING_BAND
        lo, hi = sorted(float(b) for b in band)
        x = np.asarray(x, dtype=float)
        inside = finite & (x >= lo) & (x <= hi)
        if inside.sum() < 1:
            return 1.0, 0.0, MISSING_BAND
        # The band's strongest point is the yardstick: its top for
        # absorbance, its bottom for transmittance.
        if down:
            low = float(np.min(y[inside]))
        else:
            high = float(np.max(y[inside]))
    span = high - low
    if not span > 0:
        return 1.0, 0.0, MISSING_BAND if norm == NORM_BAND else None
    # 0 to 1 either way: the band's tip (or the lowest value) at 0 for a
    # transmittance, and at 1 for an absorbance.
    return 1.0 / span, -low / span, None


def span_of(values):
    """How tall a curve is, robustly: its 1st to 99th percentile. What an
    offset is carried across a change of unit or normalisation by, so a
    stack keeps its proportions (`Document.set_display`)."""
    if values is None:
        return None
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return None
    low, high = np.percentile(values, [1, 99])
    span = float(high - low)
    return span if span > 0 else None


def convert_offset(old_factor, new_factor, offset):
    """An offset carried across a change of what the y axis shows: in
    proportion to the spectrum's own height before and after, so a stack
    keeps its shape. Each spectrum carries its OWN factor across."""
    if not old_factor or not new_factor:
        return offset
    return float(offset) * (float(new_factor) / float(old_factor))


def parse_wavenumber(text):
    """A typed wavenumber - a number or a sum, a comma as the decimal
    point, "cm-1" after it or not - or None."""
    from . import numbers
    match = _TYPED_WAVENUMBER.match(str(text or ""))
    return numbers.evaluate(match.group(1)) if match else None


_TYPED_WAVENUMBER = re.compile(
    r"^\s*(.*?)\s*(?:cm\s*\^?\s*\{?\s*-\s*1\s*\}?|1\s*/\s*cm|/\s*cm)?\s*$",
    re.I)
