"""Fixtures: an offscreen Qt application, and synthetic spectra.

A synthetic spectrum is built in the SHAPE the readers return - a
`readers.Spectrum`: ascending wavenumbers, values, what the file says they
are - which is a different thing from inventing a file. The tests that care
about real files look for them on disk (see `local_file`) and skip when
there are none: inventing a `.sp` would be inventing the one thing in this
program that must never be guessed at.
"""

import hashlib
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from irpanel.core import model, readers            # noqa: E402

#: The bands of the synthetic spectrum: (position cm-1, absorbance at the
#: top, half width at half height cm-1).
BANDS = ((3100.0, 0.25, 60.0), (1700.0, 0.9, 12.0), (1560.0, 0.6, 15.0),
         (1380.0, 0.7, 20.0), (1080.0, 0.5, 8.0), (700.0, 0.8, 10.0))


def spectrum_values(x, scale=1.0, baseline=0.04):
    """Absorbance of the synthetic sample at wavenumbers `x`: Lorentzian
    bands on a gently sloping baseline."""
    a = baseline + 0.00001 * (4000.0 - x)
    for centre, height, half in BANDS:
        a = a + scale * height / (1.0 + ((x - centre) / half) ** 2)
    return a


def make_spectrum(unit=readers.UNIT_T_PERCENT, scale=1.0, points=3601,
                  said=True):
    """A reader-shaped spectrum, 400 to 4000 cm-1 at 1 cm-1, in `unit`;
    `said` False leaves the unit unsaid, as a text file does."""
    x = np.linspace(400.0, 4000.0, points)
    a = spectrum_values(x, scale)
    if unit == readers.UNIT_A:
        y = a
    elif unit == readers.UNIT_T_FRACTION:
        y = 10.0 ** (-a)
    else:
        y = 100.0 * 10.0 ** (-a)
    return readers.Spectrum(x, y, unit if said else None, {}, "synthetic")


def make_sample(name="TEST-1", unit=readers.UNIT_T_PERCENT, scale=1.0,
                said=True):
    return model.Sample("C:/nowhere/{}.sp".format(name),
                        make_spectrum(unit, scale, said=said))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv[:1])
    return app


@pytest.fixture(autouse=True)
def no_modal_loops(monkeypatch):
    """A modal dialog in a test FAILS it instead of hanging the run.

    `exec()` starts an event loop that nobody in a test will ever close.
    Every modal entry point answers "cancelled" here, and the test fails at
    teardown naming what it opened. Raising instead would be worse: most of
    these run inside a Qt slot, where PySide6 turns an exception into an
    abort. A test that means to reach one stubs it itself.
    """
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (QColorDialog, QDialog, QFileDialog,
                                   QInputDialog, QMenu, QMessageBox)
    opened = []

    def refused(name, answer):
        def refuse(*_args, **_kwargs):
            opened.append(name)
            return answer() if callable(answer) else answer
        return refuse

    monkeypatch.setattr(QDialog, "exec", refused("QDialog.exec", 0))
    monkeypatch.setattr(QMenu, "exec", refused("QMenu.exec", None))
    monkeypatch.setattr(QMessageBox, "about",
                        refused("QMessageBox.about", None))
    for name in ("question", "warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name,
                            refused("QMessageBox." + name,
                                    QMessageBox.Cancel))
    monkeypatch.setattr(QInputDialog, "getText",
                        refused("QInputDialog.getText", ("", False)))
    monkeypatch.setattr(QInputDialog, "getDouble",
                        refused("QInputDialog.getDouble", (0.0, False)))
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        refused("QFileDialog.getOpenFileName", ("", "")))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames",
                        refused("QFileDialog.getOpenFileNames", ([], "")))
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        refused("QFileDialog.getSaveFileName", ("", "")))
    monkeypatch.setattr(QColorDialog, "getColor",
                        refused("QColorDialog.getColor", QColor))
    yield opened
    assert not opened, "a test reached a modal dialog: {}".format(opened)



@pytest.fixture(autouse=True)
def full_drawings():
    """Every change drawn in full at once: tests read pixels, and a draft
    (`PlotWidget.SETTLE_MS`) draws its curves as hairlines. The family test
    of the drafts turns it back on."""
    from irpanel.ui.plot import PlotWidget
    saved = PlotWidget.SETTLE_MS
    PlotWidget.SETTLE_MS = 0
    yield
    PlotWidget.SETTLE_MS = saved


@pytest.fixture(autouse=True)
def own_preferences(tmp_path):
    """Every test gets the BUILT-IN house style and its own preferences
    file: the user's defaults are real state on this machine."""
    from irpanel.core import style
    saved = style.preferences()
    saved_figure = style._figure_default
    style.PATH_OVERRIDE = str(tmp_path / "preferences.json")
    style.restore_preferences({}, figure_state=None)
    yield style.PATH_OVERRIDE
    style.PATH_OVERRIDE = None
    style.restore_preferences(saved, figure_state=saved_figure)


@pytest.fixture
def sample():
    return make_sample()


@pytest.fixture
def document(sample):
    doc = model.Document()
    doc.add_sample(sample)
    return doc


@pytest.fixture
def window(qapp):
    """A window with three synthetic spectra, stacked as a folder opens."""
    from irpanel.ui.window import MainWindow
    win = MainWindow()
    win.resize(1000, 640)
    for k, scale in enumerate((1.0, 0.6, 1.4)):
        win._sample_loaded(make_sample("TEST-{}".format(k + 1), scale=scale))
    win.undo.clear()
    win.plot.grab()
    return win


@pytest.fixture
def stack_window(window):
    """A window with three curves on the plot: what `test_family.py`, the
    file every panel of the family shares, is given."""
    return window


def _local_entries():
    """The folders and files named in `IR_TESTDATA` (semicolon separated)
    and in the uncommitted `tests/local_testdata.txt`, one per line."""
    entries = []
    env = os.environ.get("IR_TESTDATA", "")
    entries.extend(part for part in env.split(";") if part.strip())
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "local_testdata.txt")
    if os.path.isfile(local):
        with open(local, "r", encoding="utf-8") as fh:
            entries.extend(line.strip() for line in fh
                           if line.strip() and not line.startswith("#"))
    return entries


def hashed_name(name):
    """How a test names a real measurement: `sha:` and the first 12 hex
    digits of the SHA-256 of its file name in lower case. A file name is a
    sample id, and a sample id does not belong in published source."""
    digest = hashlib.sha256(str(name).lower().encode("utf-8")).hexdigest()
    return "sha:" + digest[:12]


def local_file(name):
    """The real measurement `name` on this machine, or None. `name` is a
    `hashed_name`, or a plain file name, looked up in the folders the local
    list names."""
    wanted = name.lower()
    hashed = wanted.startswith("sha:")
    for entry in _local_entries():
        folder = entry if os.path.isdir(entry) else os.path.dirname(entry)
        if not os.path.isdir(folder):
            continue
        for candidate in os.listdir(folder):
            key = hashed_name(candidate) if hashed else candidate.lower()
            if key == wanted:
                return os.path.join(folder, candidate)
    return None


def real(name):
    """`local_file(name)`, or skip the test that asked."""
    path = local_file(name)
    if path is None:
        pytest.skip("real file not here (see tests/local_testdata.txt)")
    return path
