"""Getting out: the curves as data, and what an export must admit to.

* `curves_csv` - what is on screen, as numbers: for a colleague, a
  spreadsheet, or a plot in something else entirely.
* `warnings_for` - what an export must not be allowed to hide. A figure drawn
  while a spectrum could not be drawn at all - recorded as something that is
  neither transmittance nor absorbance, or short of the normalisation band -
  misleads unless it says so, and so does a normalised axis whose caption
  was retyped without saying it. These lines are printed AND stamped into
  the image.
* `notes_for` - what is worth knowing and is not wrong: a unit guessed from
  the data, a label's number typed by hand. Printed, not stamped.

The figure itself goes out as PNG or SVG from the plot (`ui/window.py`),
drawn by the same code as the screen.
"""

import numpy as np

from .. import branding
from . import labels
from . import units


def warnings_for(doc):
    """Everything an export has to admit to, as short lines."""
    out = []
    for scan, missing in doc.scans_missing():
        out.append("NO {}: {} is not drawn".format(missing.upper(),
                                                   scan.display_name()))
    if doc.norm != units.NORM_NONE:
        own = doc.axes["y"].label
        if own and "normal" not in str(own).lower():
            out.append("NORMALISED, and the y caption does not say so")
    return out


def notes_for(doc):
    """What is odd without being wrong: units guessed from the data, and
    what the analysis labels say that is not the measurement."""
    out = []
    guessed = sorted(s.name for s in doc.samples if s.unit_guessed
                     and any(sc.visible for sc in s.scans))
    if guessed:
        out.append("UNIT GUESSED from the data for: " + ", ".join(guessed))
    for analysis in doc.visible_analyses():
        for kind, message in labels.render(analysis, doc).problems:
            if kind != "missing":
                out.append("{} on {}: {}".format(
                    analysis.model_name, analysis.scan.display_name(),
                    message))
    return out


def label_notes(doc):
    """The analysis-label half of `notes_for`."""
    return [line for line in notes_for(doc)
            if not line.startswith("UNIT GUESSED")]


def curves_csv(doc, path):
    """Every visible spectrum as drawn - its unit, its normalisation, its
    magnified stretches and its offset - one column pair per spectrum.

    Column PAIRS rather than one shared x column, because two spectra need
    not share their wavenumbers: interpolating them onto a common grid
    would be inventing data. A sample that cannot be drawn (NaN) is an EMPTY
    cell, never the text "nan"."""
    blocks = []
    for scan in doc.visible_scans():
        x, y = scan.kept_curve(doc)
        if x is None:
            continue
        blocks.append((scan, x, y))
    if not blocks:
        return None
    columns, headers = [], []
    y_name = "{}/{}".format(
        "Transmittance" if doc.y_unit == units.UNIT_T else "Absorbance",
        doc.y_axis_unit())
    for scan, x, y in blocks:
        name = scan.display_name().replace(",", " ")
        columns.append(x[::-1])
        headers.append("{} Wavenumber/{}".format(name,
                                                 units.WAVENUMBER_TEXT))
        columns.append(y[::-1])
        headers.append("{} {}".format(name, y_name))
    rows = max(len(c) for c in columns)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# {} export\n".format(branding.APP_NAME))
        for line in warnings_for(doc) + notes_for(doc):
            fh.write("# {}\n".format(line))
        for scan, _x, _y in blocks:
            fh.write("# {}: {}, recorded as {}, offset {:g}\n".format(
                scan.display_name(), scan.sample.path,
                scan.sample.unit_text(), float(scan.offset)))
        fh.write(",".join(headers) + "\n")
        for i in range(rows):
            cells = []
            for column in columns:
                cells.append(_cell(column[i]) if i < len(column) else "")
            fh.write(",".join(cells) + "\n")
    return path


def _cell(value):
    """A number as a CSV cell: `%.6g`, and empty for a missing sample."""
    value = float(value)
    return "{:.6g}".format(value) if np.isfinite(value) else ""


def mathtext(text):
    r"""The panel's markup as matplotlib mathtext: `*A*` -> `$\mathit{A}$`,
    `_{a}` -> `$_{\mathrm{a}}$`, `^{-1}`, `\nu` -> `$\nu$`; what is already
    between dollars is mathtext and stays as it is. For anything that hands
    a caption to matplotlib."""
    import re
    out = []
    parts = re.split(r"(?<!\\)(\$[^$]*(?<!\\)\$)", str(text))
    for part in parts:
        if part.startswith("$") and part.endswith("$") and len(part) > 1:
            out.append(part)
            continue
        part = re.sub(r"\\([A-Za-z]+)", lambda m: "$\\" + m.group(1) + "$",
                      part)
        part = re.sub(r"\*([^*]+)\*",
                      lambda m: "$\\mathit{" + m.group(1).replace(" ", "\\ ")
                      + "}$", part)
        part = re.sub(r"([_^])\{([^}]*)\}",
                      lambda m: "$" + m.group(1) + "{\\mathrm{"
                      + m.group(2).replace(" ", "\\ ") + "}}$", part)
        out.append(part)
    return "".join(out).replace("$$", "")
