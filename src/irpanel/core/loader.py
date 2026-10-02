"""Turning a path into a `Sample`: the reader, plus what it does not say.

UI-free. The threading that keeps a folder-sized drop from freezing the
window lives in `ui/loading.py`; everything here is a plain function, so it
can be tested against a real file without a window.

**What the values are is read where the file says it and guessed where it
does not - and a guess is reported.** A `.sp`, a `.spa` and a JCAMP file
state absorbance or transmittance; a two-column text file does not, and
there `units.guess` decides from the data (`Sample.unit_source` says
"guessed from the data" wherever the unit is shown, and the file's
settings can overrule it).
"""

import os

from . import model
from . import profile
from . import readers

#: What the open dialog and a drop will accept.
READABLE = readers.READABLE

ReadError = readers.ReadError


def reader_origin():
    """Which reader is in use, for the About box: the program's own
    (`core/readers.py`)."""
    return "this program's own (.sp, .spa, JCAMP-DX, text)"


def looks_readable(path):
    """Could this path be a spectrum? Extension only, deliberately loose:
    the reader is the only thing that can really tell, and refuses with a
    reason."""
    return (os.path.isfile(str(path))
            and os.path.splitext(str(path))[1].lower() in READABLE)


def read_sample(path):
    """Read one file into a `Sample`. Raises `ReadError` with the reason."""
    spectrum = readers.read(path)
    sample = model.Sample(path, spectrum)
    if profile.EMBED_SOURCES:
        # The file itself, for the copy a session keeps of it.
        try:
            with open(path, "rb") as fh:
                sample.source_bytes = fh.read()
        except OSError:
            sample.source_bytes = None
    if sample.unit_guessed:
        sample.note = ("{}: the file does not say what its values are; "
                       "taken as {} from their shape".format(
                           sample.name,
                           readers.UNIT_WORDS.get(sample.recorded_unit,
                                                  sample.recorded_unit)))
    return sample


def summary(sample):
    """One line about a file that was just opened, for the note line."""
    x = sample.x
    bits = ["{}: {} points, {:.0f} to {:.0f} cm-1".format(
        sample.name, len(x), float(x[-1]), float(x[0])), sample.unit_text()]
    if sample.recorded_unit not in readers.CONVERTIBLE:
        bits.append("NOT DRAWN: neither transmittance nor absorbance")
    return ", ".join(bits)
