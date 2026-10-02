"""Reading infrared spectra: one file, one spectrum.

UI-free. Four kinds of file are read, each by its own function, and every
one of them returns the same thing - a `Spectrum`: the wavenumbers, the
values, what the FILE says the values are, and whatever else it states
about the measurement.

* **PerkinElmer `.sp`** ("PEPE2D constant interval DataSet file"): a tree of
  `(uint16 id, uint32 size)` blocks; ids below 0x8000 are containers. The
  x range is block 0x8b72 (two float64), the values block 0x8b7c (a two-byte
  tag, a uint32 byte length, float64s), the y label block 0x8b78 ("%T" or
  "A").
* **Thermo OMNIC `.spa`**: a section table at byte 304, 16-byte entries
  (uint16 key, uint32 offset, uint32 size). Key 2 is the spectral header
  (point count at +4, y data-type code at +12, first and last wavenumber as
  float32 at +16 and +20), key 3 the float32 values.
* **JCAMP-DX** (`.dx`, `.jdx`, `.jcm`), in the plain `(X++(Y..Y))` form a
  PerkinElmer export writes: FIRSTX, LASTX and NPOINTS give the grid, the
  table the values times YFACTOR, YUNITS what they are.
* **Two-column text** (`.csv`, `.txt`, `.dat`, `.asc`): `;`, tab, `,` or
  spaces between the columns, decimal points or commas, header lines
  skipped.

Checked against one another on real measurements: a `.sp` in %T equals its
PerkinElmer `.DX` export (fractional T) times 100 to 1.2e-7, and its `.csv`
export to 6e-7; a `.sp` in absorbance equals its `.DX` to 1.2e-7 and
-log10 of its `.csv` (fractional T) to 7.5e-7 (`tests/test_readers.py`).

**What the values are is read, not assumed.** A `.sp` and a `.spa` state
it in their headers, a JCAMP file in YUNITS. A bare two-column file states
nothing; there the unit is left None here and the loader GUESSES it from
the data - and says so (`core/loader.py`).
"""

import os
import re
import struct

import numpy as np

#: What the values of a spectrum are. Absorbance, and transmittance as a
#: PERCENT or as a FRACTION: the same quantity on two scales, and a file
#: says which (a `.sp` writes %T, its JCAMP export fractions).
UNIT_A = "A"
UNIT_T_PERCENT = "%T"
UNIT_T_FRACTION = "T"
#: What the program can draw a spectrum as (`core/units.py`).
CONVERTIBLE = (UNIT_A, UNIT_T_PERCENT, UNIT_T_FRACTION)

#: Words for them, as the program says them.
UNIT_WORDS = {
    UNIT_A: "absorbance",
    UNIT_T_PERCENT: "transmittance in %",
    UNIT_T_FRACTION: "transmittance as a fraction",
    "R%": "reflectance",
    "logR": "log(1/R)",
    "SB": "single-beam intensity",
    "KM": "Kubelka-Munk",
    "IFG": "interferogram",
    "PA": "photoacoustic",
    "Raman": "Raman intensity",
}

#: OMNIC's y data-type code, as spectrochempy reads it.
OMNIC_YCODE = {
    17: UNIT_A,
    16: UNIT_T_PERCENT,
    11: "R%",
    12: "logR",
    15: "SB",
    20: "KM",
    21: "R%",
    22: "IFG",
    26: "PA",
    31: "Raman",
}

#: A PerkinElmer `.sp`'s y-axis label.
PE_YUNIT = {
    "%T": UNIT_T_PERCENT, "%TRANSMITTANCE": UNIT_T_PERCENT,
    "T": UNIT_T_FRACTION, "TRANSMITTANCE": UNIT_T_FRACTION,
    "A": UNIT_A, "ABS": UNIT_A, "ABSORBANCE": UNIT_A,
    "%R": "R%", "R": "R%", "REFLECTANCE": "R%",
    "LOG(1/R)": "logR", "KM": "KM", "K-M": "KM", "KUBELKA-MUNK": "KM",
}

#: A PerkinElmer `.sp`'s block ids (uint16) inside its DataSet container.
_PE_XRANGE, _PE_NPOINTS, _PE_XLABEL, _PE_YLABEL, _PE_DATA = (
    0x8b72, 0x8b75, 0x8b77, 0x8b78, 0x8b7c)

#: The file types read, by extension.
SPA = (".spa",)
SP = (".sp",)
JCAMP = (".dx", ".jdx", ".jcm")
TEXT = (".csv", ".txt", ".dat", ".asc")
READABLE = SPA + SP + JCAMP + TEXT

#: What the open dialog offers.
FILTER = ("IR spectra (*.sp *.spa *.dx *.jdx *.jcm *.csv *.txt *.dat *.asc);;"
          "All files (*)")


class ReadError(Exception):
    """A file that cannot be read as a spectrum, with the reason."""


class Spectrum(object):
    """What a reader found in a file.

    `x` is the wavenumber in cm-1, ASCENDING (every reader turns a
    descending file round, so nothing downstream has to ask). `y` is the
    values as stored, one per wavenumber. `unit` is what the file SAYS they
    are (`UNIT_A`, `UNIT_T_PERCENT`, `UNIT_T_FRACTION`, or one of
    `UNIT_WORDS`'s others), or None when it says nothing. `head` is what
    else it states: `title`, `date`, `instrument`, `resolution`, as text.
    """

    def __init__(self, x, y, unit=None, head=None, kind=""):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if len(x) != len(y):
            raise ReadError("{} wavenumbers for {} values".format(len(x),
                                                                  len(y)))
        if len(x) < 2:
            raise ReadError("fewer than two points")
        if x[0] > x[-1]:
            x, y = x[::-1].copy(), y[::-1].copy()
        self.x = x
        self.y = y
        self.unit = unit
        self.head = dict(head or {})
        #: Which reader made it: "sp", "spa", "jcamp", "text".
        self.kind = kind


def read(path):
    """The spectrum in `path`, by its extension. Raises `ReadError`."""
    path = str(path)
    if not os.path.isfile(path):
        raise ReadError("no such file: {}".format(os.path.basename(path)))
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in SPA:
            return read_spa(path)
        if ext in SP:
            return read_sp(path)
        if ext in JCAMP:
            return read_jcamp(path)
        if ext in TEXT:
            return read_text(path)
    except ReadError:
        raise
    except (OSError, ValueError, struct.error, IndexError) as exc:
        raise ReadError("{}: {}".format(type(exc).__name__, exc))
    raise ReadError("not a spectrum this program reads: {}".format(
        os.path.basename(path)))


# ------------------------------------------------------------- PerkinElmer
def read_sp(path):
    """A PerkinElmer `.sp`: walk the block tree for the x range, the
    float64 values and the y-axis label."""
    with open(path, "rb") as fh:
        raw = fh.read()
    if not raw.startswith(b"PEPE"):
        raise ReadError("not a PerkinElmer .sp file (no PEPE signature)")
    n = len(raw)
    blocks = {}

    def walk(start, end):
        pos = start
        while pos + 6 <= end:
            bid = struct.unpack_from("<H", raw, pos)[0]
            size = struct.unpack_from("<I", raw, pos + 2)[0]
            content = pos + 6
            if bid == 0 and size == 0:
                break
            if content + size > end:
                break
            if bid < 0x8000:             # a container: go inside
                walk(content, content + size)
            else:
                blocks[bid] = raw[content:content + size]
            pos = content + size

    # The signature is a zero-terminated description; the block tree
    # follows its zero padding, the DataSet container first.
    i = raw.index(b"\x00", 4)
    while i < n and raw[i] == 0:
        i += 1
    if i + 6 > n:
        raise ReadError("a PerkinElmer .sp file with no data blocks")
    size = struct.unpack_from("<I", raw, i + 2)[0]
    walk(i + 6, min(i + 6 + size, n))
    if _PE_DATA not in blocks or _PE_XRANGE not in blocks:
        raise ReadError("a PerkinElmer .sp file without its data")
    data = blocks[_PE_DATA]
    length = struct.unpack_from("<I", data, 2)[0]
    y = np.frombuffer(data[6:6 + length], dtype="<f8").astype(float)
    first, last = struct.unpack_from("<dd", blocks[_PE_XRANGE], 2)
    x = np.linspace(first, last, len(y))
    unit = None
    head = {}
    if _PE_YLABEL in blocks:
        label = _pe_text(blocks[_PE_YLABEL])
        head["y label"] = label
        unit = PE_YUNIT.get(label.upper().replace(" ", ""))
    if _PE_XLABEL in blocks:
        head["x label"] = _pe_text(blocks[_PE_XLABEL])
    _check_wavenumbers(head.get("x label", ""), path)
    return Spectrum(x, y, unit, head, "sp")


def _pe_text(body):
    """A `.sp` text block: a two-byte tag, a uint16 length, the text."""
    length = struct.unpack_from("<H", body, 2)[0]
    return body[4:4 + length].decode("latin-1", "replace").strip()


# ------------------------------------------------------------------- OMNIC
def read_spa(path):
    """A Thermo OMNIC `.spa`: the spectral header (key 2) and the values
    (key 3) through the section table at byte 304."""
    with open(path, "rb") as fh:
        raw = fh.read()
    n = len(raw)
    count = first = last = None
    code = None
    data_at = data_size = None
    pos = 304
    for _entry in range(64):
        if pos + 10 > n:
            break
        key = struct.unpack_from("<H", raw, pos)[0]
        offset = struct.unpack_from("<I", raw, pos + 2)[0]
        size = struct.unpack_from("<I", raw, pos + 6)[0]
        if key == 0 and offset == 0:
            break
        if key == 2 and 0 < offset < n:
            count = struct.unpack_from("<I", raw, offset + 4)[0]
            code = raw[offset + 12]
            first = struct.unpack_from("<f", raw, offset + 16)[0]
            last = struct.unpack_from("<f", raw, offset + 20)[0]
        elif key == 3 and 0 < offset < n:
            data_at, data_size = offset, size
        pos += 16
    if data_at is None or first is None:
        raise ReadError("not an OMNIC .spa file (no spectral header or "
                        "values)")
    y = np.frombuffer(raw, dtype="<f4", count=data_size // 4,
                      offset=data_at).astype(float)
    if count and count != len(y):
        raise ReadError("an OMNIC .spa file whose header says {} points and "
                        "holds {}".format(count, len(y)))
    x = np.linspace(first, last, len(y))
    unit = OMNIC_YCODE.get(code) if code is not None else None
    return Spectrum(x, y, unit, {"y code": str(code)}, "spa")


# ------------------------------------------------------------------- JCAMP
_JCAMP_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
#: The characters of JCAMP's compressed forms (SQZ, DIF, DUP): a table
#: holding any of these is not a plain one.
_JCAMP_COMPRESSED = re.compile(r"[@A-IJ-Ra-ij-rs-z%]")


def read_jcamp(path):
    """A JCAMP-DX file in the plain `(X++(Y..Y))` form: the grid from
    FIRSTX, LASTX and NPOINTS, the values from the table times YFACTOR.

    FIRSTX and LASTX are the ACTUAL first and last wavenumbers (the
    standard's definition), so XFACTOR - which scales the numbers in the
    table - is not applied to them. A compressed table (SQZ, DIF) is
    refused with a reason rather than misread."""
    with open(path, "r", encoding="latin-1", errors="replace") as fh:
        text = fh.read()
    fields = {}
    for chunk in text.split("##")[1:]:
        key, _sep, value = chunk.partition("=")
        key = key.strip().upper()
        if key and key not in fields:
            fields[key] = value.strip()
    match = re.search(r"##XYDATA\s*=\s*\(\s*X\+\+\s*\(\s*Y\.\.Y\s*\)\s*\)",
                      text, re.I)
    if not match:
        raise ReadError("a JCAMP-DX file without an (X++(Y..Y)) table")
    body = text[match.end():].split("##", 1)[0]
    values = []
    for line in body.splitlines():
        line = line.split("$$", 1)[0].strip()
        if not line:
            continue
        if _JCAMP_COMPRESSED.search(line.replace("e", "").replace("E", "")):
            raise ReadError("a compressed JCAMP-DX table (SQZ/DIF): export "
                            "it uncompressed (AFFN)")
        numbers = _JCAMP_NUMBER.findall(line)
        values.extend(float(v) for v in numbers[1:])     # [0] is its x
    y = np.array(values, dtype=float) * _number(fields.get("YFACTOR"), 1.0)
    first = _number(fields.get("FIRSTX"))
    last = _number(fields.get("LASTX"))
    if first is None or last is None:
        raise ReadError("a JCAMP-DX file without FIRSTX and LASTX")
    declared = _number(fields.get("NPOINTS"))
    if declared is not None and int(declared) != len(y):
        raise ReadError("a JCAMP-DX file whose NPOINTS says {} and whose "
                        "table holds {}".format(int(declared), len(y)))
    x = np.linspace(first, last, len(y))
    units = fields.get("XUNITS", "").strip().upper()
    if units and units not in ("1/CM", "CM-1", "CM^-1", "WAVENUMBERS"):
        raise ReadError("x in {}: only wavenumbers (1/CM) are read".format(
            fields.get("XUNITS").strip()))
    unit = _jcamp_unit(fields.get("YUNITS", ""), y)
    head = {}
    for key, name in (("TITLE", "title"), ("DATE", "date"),
                      ("TIME", "time"),
                      ("SPECTROMETER/DATA SYSTEM", "instrument"),
                      ("RESOLUTION", "resolution"),
                      ("YUNITS", "y label")):
        if fields.get(key):
            head[name] = " ".join(fields[key].split())
    return Spectrum(x, y, unit, head, "jcamp")


def _jcamp_unit(text, y):
    """What JCAMP's YUNITS says. ABSORBANCE (or a bare A) is absorbance;
    TRANSMITTANCE the standard's fraction - unless the values run past 1.5,
    which no fraction does, when the file's writer meant percent; "%T" or a
    PERCENT in it is percent."""
    word = " ".join(str(text).upper().split())
    if not word:
        return None
    if word in ("A", "ABS") or "ABSORB" in word:
        return UNIT_A
    if "%" in word or "PERCENT" in word:
        return UNIT_T_PERCENT
    if word == "T" or "TRANSMIT" in word:
        finite = y[np.isfinite(y)]
        if len(finite) and float(np.max(finite)) > 1.5:
            return UNIT_T_PERCENT
        return UNIT_T_FRACTION
    if "KUBELKA" in word:
        return "KM"
    if "REFLECT" in word:
        return "R%"
    return None


def _number(text, default=None):
    if text is None:
        return default
    found = _JCAMP_NUMBER.search(str(text))
    return float(found.group(0)) if found else default


# -------------------------------------------------------------------- text
def read_text(path):
    """Two columns, wavenumber and value. The separator is found from the
    first line that holds numbers (`;` and a tab are separators whatever
    the decimals; a lone `,` only when the decimals are points); decimal
    commas are read; lines that are not two numbers are skipped. A header
    that names the values ("Absorbance", "%T") says what they are."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        text = fh.read()
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ReadError("an empty file")
    probe = next((line for line in lines if any(c.isdigit() for c in line)),
                 lines[0])
    separator = None
    if ";" in probe:
        separator = ";"
    elif "\t" in probe:
        separator = "\t"
    elif probe.count(",") == 1 and "." in probe:
        separator = ","
    rows, headers = [], []
    for line in lines:
        parts = line.split(separator) if separator else line.split()
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            headers.append(line)
            continue
        try:
            a = float(parts[0].replace(",", "."))
            b = float(parts[1].replace(",", "."))
        except ValueError:
            headers.append(line)
            continue
        rows.append((a, b))
    if len(rows) < 2:
        raise ReadError("no two columns of numbers")
    array = np.array(rows, dtype=float)
    x, y = array[:, 0], array[:, 1]
    if not np.all(np.diff(x) > 0) and not np.all(np.diff(x) < 0):
        raise ReadError("the first column is not a wavenumber axis (it does "
                        "not run one way)")
    unit = _header_unit(headers, y)
    head = {"header": headers[0].strip()[:120]} if headers else {}
    return Spectrum(x, y, unit, head, "text")


def _header_unit(headers, y):
    """What a text file's header lines say the values are, or None."""
    words = " ".join(headers).upper()
    if not words:
        return None
    if "ABSORB" in words:
        return UNIT_A
    if "%T" in words or "TRANSMITTANCE" in words:
        finite = y[np.isfinite(y)]
        if "%" in words or (len(finite) and float(np.max(finite)) > 1.5):
            return UNIT_T_PERCENT
        return UNIT_T_FRACTION
    return None


def _check_wavenumbers(label, path):
    """A `.sp` whose x label names something other than a wavenumber."""
    word = str(label).strip().lower()
    if word and "cm" not in word and "wavenumber" not in word:
        raise ReadError("x in {}: only wavenumbers (cm-1) are read".format(
            label))
