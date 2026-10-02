"""What an analysis label SAYS: the words are the user's, the number is not.

A label is a TEMPLATE. `{}` is the measured value, filled in by the program
every time the label is drawn; everything else is the user's text, with the
figure markup (`*A*` italic, `_{a}` subscript, `^{-1}` superscript,
`\\nu`, `$\\tilde{\\nu}$`). The default templates are `{}` for a peak
position, `Area = {}` for a band area and `FWHM = {}` for a width.

The rules, and why each one is where the program takes control away:

1. **The number is never typed.** It reaches a label only through `{}`, so
   re-measuring can never leave a stale number on the figure.
2. **A unit the quantity is not in is refused.** Every IR result here is in
   cm-1 (a band area of absorbance over wavenumber is A cm-1, and absorbance
   has no unit); `{} nm` is drawn in cm-1, and the settings say why. A
   number is never drawn beside a unit it is not in.
3. **The digits are the user's** (`core/numbers.py`): rounding changes how
   exact a number looks, never what it is.
4. **Free text is free.** A number typed by hand ("lit. 1560 cm-1") is
   allowed, because it may be a reference value; but one beside a unit is
   flagged in the settings as not the measurement.

UI-free, like the rest of `core/`.
"""

import re

from . import numbers
from . import units

WAVENUMBER = "wavenumber"
AREA = "area"

#: The template an analysis carries until somebody writes their own, by
#: model.
DEFAULTS = (
    ("Peak position", "{}"),
    ("Band area", "Area = {}"),
    ("Band width", "FWHM = {}"),
)

#: The one unit of every result, and how it may be written.
UNIT = units.WAVENUMBER_UNIT
_SPELLINGS = ("cm^{-1}", "cm^-1", "cm-1", "1/cm", "/cm")
_UNIT = "(?:{})".format("|".join(re.escape(u) for u in _SPELLINGS))

#: `{}`, and the unit right after it if one was written. Not `_{}` or
#: `^{}`, which are markup (an empty subscript).
_PLACEHOLDER = re.compile(r"(?<![_^])\{\}(?:(\s*)([A-Za-z][\w^{}/-]*))?")
_TYPED = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?\s*(" + _UNIT + ")",
                    re.I)


def canonical_unit(text):
    """A unit as the program writes it (`cm^{-1}`), or None for anything
    it does not know."""
    token = str(text or "").strip().replace(" ", "").lower()
    if token in [s.lower() for s in _SPELLINGS]:
        return UNIT
    return None


def normalise_format(spec):
    """A number format that may carry a unit (`%.1f cm-1`), canonical."""
    return numbers.normalise(spec, canonical_unit)


class Rendered(object):
    """A label as drawn: its text and what is wrong with it.

    `problems` is `[(kind, message), ...]`: "unit" (a unit the quantity
    cannot be put in) and "typed" (a number written by hand beside a unit:
    not the measurement). "missing" is kept for the family's exports and is
    never produced here."""

    def __init__(self, text, problems=(), value_text=""):
        self.text = text
        self.problems = list(problems)
        self.value_text = value_text

    def missing(self):
        return [m for kind, m in self.problems if kind == "missing"]


def quantity_of(model_name):
    """What an analysis of this model reports: a wavenumber (a position, a
    width) or an area."""
    return AREA if "area" in str(model_name).lower() else WAVENUMBER


def default_template(analysis):
    for word, template in DEFAULTS:
        if word in analysis.model_name:
            return template
    return "%s = {}" % analysis.model_name


def template_of(analysis):
    return (analysis.label if analysis.label is not None
            else default_template(analysis))


def result(analysis):
    """`(value, quantity)`: the number a label shows, in cm-1."""
    from .model import number
    name = analysis.model_name
    fields = analysis.fields
    quantity = quantity_of(name)
    if quantity == AREA:
        return number(fields.get("Area")), quantity
    if "width" in name.lower():
        return number(fields.get("FWHM")), quantity
    return number(fields.get("Position")), quantity


def units_of(quantity):
    """The units a result can be shown in."""
    return [UNIT]


def natural_unit(_quantity=None, _doc=None):
    return UNIT


def number_format(analysis, doc):
    from . import style
    return style.value(doc, analysis, "number_format")


def render(analysis, doc=None):
    """The label's text, with every `{}` filled in, and its problems."""
    template = template_of(analysis)
    value, quantity = result(analysis)
    spec = number_format(analysis, doc)
    problems = []
    fallback = numbers.WAVENUMBER if quantity == WAVENUMBER else numbers.VALUE
    shown = []

    def fill(match):
        typed = match.group(2)
        if typed and canonical_unit(typed) is None:
            problems.append(("unit", "'{}' is not a unit of the {}: shown "
                                     "in cm-1".format(typed, quantity)))
        text = ("? " + UNIT if value is None else "{} {}".format(
            numbers.write(value, spec, fallback), UNIT))
        shown.append(text)
        return text

    text = _PLACEHOLDER.sub(fill, template)
    if analysis.label is not None:
        for match in _TYPED.finditer(_PLACEHOLDER.sub("", template)):
            problems.append(("typed", "'{}' is typed by hand, not the "
                                      "measurement; {{}} shows the measured "
                                      "value".format(match.group(0).strip())))
    return Rendered(text, problems, shown[0] if shown else "")


def wavenumber_text(value, doc=None, spec=None):
    """A wavenumber written with the house format and its unit: what a
    band marker's `{}` and a distance arrow's say."""
    from . import style
    if spec is None:
        spec = (style.figure_value(doc, "wavenumber_format")
                if doc is not None else style.preference("wavenumber_format"))
    return "{} {}".format(numbers.write(value, spec, numbers.WAVENUMBER),
                          UNIT)


def fill_wavenumber(template, value, doc=None, spec=None):
    """`template` with every `{}` (not `_{}` or `^{}`) as `value` in cm-1."""
    return re.sub(r"(?<![_^])\{\}",
                  lambda _m: wavenumber_text(value, doc, spec),
                  str(template))


_NAMES = ("Position", "FWHM", "Area", "Height")


def results(analysis, doc=None):
    """`[(name, text), ...]`: every result an analysis carries beyond its
    cursors, written in the figure's formats - what its settings list."""
    from .model import number
    from . import style
    out = []
    for key in _NAMES:
        if key not in analysis.fields:
            continue
        value = number(analysis.fields.get(key))
        if value is None:
            continue
        if key == "Height":
            out.append(("Height (A)", numbers.write(
                value, style.figure_value(doc, "value_format"),
                numbers.VALUE)))
            continue
        spec = style.figure_value(doc, "wavenumber_format" if key != "Area"
                                  else "value_format")
        out.append((key, "{} cm-1".format(numbers.write(
            value, spec, numbers.WAVENUMBER if key != "Area"
            else numbers.VALUE))))
    return out
