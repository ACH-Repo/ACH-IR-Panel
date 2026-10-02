"""What is particular to THIS plotter's data: infrared spectra.

This program is one of a family of stacked-trace plotters on one handling.
The handling is shared; what a kind of data wants differently - how F frames
it, which way the x axis runs, what a new file does to the stack - is
gathered here, so a sibling changes this module rather than the handling
code.

UI-free: plain values.
"""

#: F frames in two steps, x first and then y, as a spectrum viewer does:
#: for spectra the x range is the question, and the y range follows it.
FIT_STAGED = True

#: The x axis runs from high to low: wavenumbers are written 4000 to 400
#: cm-1, left to right. The view is still kept as (low, high); only the
#: mapping onto the page turns it round (`PlotWidget.x_to_px`).
X_REVERSED = True

#: The fitted x range is rounded to a whole grid at each end (4000, 400)
#: rather than stopping at the first and last sample (3999.88, 399.92).
#: An end within `X_SNAP` of the axis span of a grid line is put on it.
X_ROUND = True
X_SNAP = 0.01

#: A file opened into a figure goes BELOW the lowest spectrum on show, one
#: step down, so a folder opens as a cascade rather than a heap of curves on
#: top of one another. The step is `arrange.suggested_step`'s.
STACK_NEW = True


#: Where a spectrum IS, for the swipe that makes every curve taller in its
#: place (`PlotWidget.scale_intensity`): its baseline, which is what the eye
#: follows. Transmittance hangs its bands down from a baseline near the
#: top; absorbance stands them up from one near the bottom. A percentile
#: rather than the extreme, so a spike or a noisy baseline does not decide.
BASELINE_PERCENTILE = {"T": 90.0, "A": 10.0}


def baseline(values, doc):
    """The baseline of a curve's `values` as drawn (no offset), in the
    axis's unit."""
    import numpy as np
    from . import units
    kind = "T" if getattr(doc, "y_unit", None) == units.UNIT_T else "A"
    return float(np.percentile(values, BASELINE_PERCENTILE[kind]))


#: A session keeps a COPY of every file it uses (compressed, inside it), so
#: a figure opens even after its files were moved or deleted; a moved file
#: is looked for beside the session first. Spectra are small: ten .sp
#: files add ~0.75 MB to a session of 15 kB.
EMBED_SOURCES = True


def name_label_corner(doc=None):
    """Where a label naming a curve sits (Ctrl+T on selected curves,
    `MainWindow.name_labels`): at the high-wavenumber (left) end, on the
    side the bands do not point to - above a transmittance, whose bands
    hang down, and below an absorbance, whose bands stand up."""
    from . import units
    if getattr(doc, "y_unit", units.UNIT_T) == units.UNIT_T:
        return "upper left"
    return "lower left"
