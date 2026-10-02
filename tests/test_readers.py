"""The readers, against real files, and against one another.

Every real file is named by a hash of its file name (`conftest.hashed_name`)
and found through `tests/local_testdata.txt`; without them these skip.

The instrument's own software exported the same measurements three ways -
the `.sp` it saves, a JCAMP-DX `.DX` and a two-column `.csv` - so each
reader is checked against the others: a mistake in one would have to be
made identically in an unrelated format to pass.
"""

import numpy as np
import pytest

from irpanel.core import loader, readers, units

from conftest import real

#: A transmittance spectrum as `.sp` (%T), JCAMP (fraction) and `.csv`
#: (fraction, the unit not said).
T_SP, T_DX, T_CSV = "sha:724d4dd5efb0", "sha:09a1b955a2ef", "sha:0ed78409b793"
#: An absorbance spectrum as `.sp` (A), JCAMP (A) and `.csv` (the SAME
#: measurement exported as fractional T).
A_SP, A_DX, A_CSV = "sha:ff905a6afc9f", "sha:a230ed3953f3", "sha:603a6f8e198b"
#: An OMNIC `.spa` in absorbance, and one single-beam background.
SPA_A, SPA_SB = "sha:17f6596e7fc9", "sha:da4908f1abc6"
#: A wizard `.csv`: `;` between the columns and decimal commas.
CSV_SEMICOLON = "sha:49ed7ae8c33a"
#: A JCAMP file that says YUNITS=A.
DX_A = "sha:d3ebf0d1d1a5"


def test_a_sp_says_percent_transmittance():
    spectrum = readers.read(real(T_SP))
    assert spectrum.kind == "sp"
    assert spectrum.unit == readers.UNIT_T_PERCENT
    assert spectrum.x[0] < spectrum.x[-1]                 # turned ascending
    assert spectrum.x[0] == pytest.approx(400.0)
    assert spectrum.x[-1] == pytest.approx(4000.0)
    assert 40.0 < np.median(spectrum.y) < 100.0


def test_the_sp_equals_its_jcamp_and_csv_exports():
    sp = readers.read(real(T_SP))
    dx = readers.read(real(T_DX))
    csv = readers.read(real(T_CSV))
    assert dx.unit == readers.UNIT_T_FRACTION
    assert csv.unit is None                               # it says nothing
    assert np.array_equal(sp.x, dx.x)
    # the JCAMP table is quantised by its YFACTOR (1.2e-7)
    assert np.max(np.abs(sp.y / 100.0 - dx.y)) < 2e-7
    assert np.max(np.abs(sp.y / 100.0 - csv.y)) < 1e-6


def test_an_absorbance_sp_equals_its_exports():
    sp = readers.read(real(A_SP))
    dx = readers.read(real(A_DX))
    csv = readers.read(real(A_CSV))
    assert sp.unit == readers.UNIT_A
    assert dx.unit == readers.UNIT_A          # YUNITS=A is absorbance
    assert np.max(np.abs(sp.y - dx.y)) < 2e-7
    # the csv holds the same spectrum as fractional transmittance
    assert np.max(np.abs(sp.y + np.log10(csv.y))) < 1e-6


def test_a_jcamp_absorbance_is_read_as_absorbance():
    """The plotter this came from missed `##YUNITS= A` and guessed."""
    assert readers.read(real(DX_A)).unit == readers.UNIT_A


def test_the_guess_for_a_csv_is_right_both_ways():
    t_csv = loader.read_sample(real(T_CSV))
    assert t_csv.unit_guessed
    assert t_csv.recorded_unit == readers.UNIT_T_FRACTION
    assert "guessed" in t_csv.unit_source
    a_csv = loader.read_sample(real(A_CSV))      # fractional T, too
    assert a_csv.recorded_unit == readers.UNIT_T_FRACTION
    # ...and the whole chain gives the file's own absorbance back
    sp = loader.read_sample(real(A_SP))
    shown, _missing = units.to_display(a_csv.y, a_csv.recorded_unit,
                                       units.UNIT_A)
    assert np.max(np.abs(shown - sp.y)) < 1e-6


def test_omnic_spa_says_what_it_is():
    spectrum = readers.read(real(SPA_A))
    assert spectrum.kind == "spa"
    assert spectrum.unit == readers.UNIT_A
    assert 390.0 < spectrum.x[0] < 410.0 and 3990.0 < spectrum.x[-1] < 4010.0
    background = readers.read(real(SPA_SB))
    assert background.unit == "SB"


def test_a_single_beam_is_not_drawn_as_either(qapp):
    from irpanel.core import model
    sample = loader.read_sample(real(SPA_SB))
    doc = model.Document()
    scan = doc.add_sample(sample)
    assert scan.missing_for(doc) == units.MISSING_UNIT
    assert scan.curve(doc) == (None, None)
    assert "NOT DRAWN" in loader.summary(sample)


def test_a_semicolon_csv_with_decimal_commas():
    spectrum = readers.read(real(CSV_SEMICOLON))
    assert spectrum.kind == "text"
    assert len(spectrum.x) > 10000
    assert np.all(np.diff(spectrum.x) > 0)
    assert units.guess(spectrum.y) == readers.UNIT_A


def test_what_is_not_a_spectrum_is_refused(tmp_path):
    notes = tmp_path / "info.txt"
    notes.write_text("- several measurements\n- ground again\n")
    with pytest.raises(readers.ReadError):
        readers.read(str(notes))
    zigzag = tmp_path / "zigzag.csv"
    zigzag.write_text("1,5\n3,6\n2,7\n")
    with pytest.raises(readers.ReadError):
        readers.read(str(zigzag))
    with pytest.raises(readers.ReadError):
        readers.read(str(tmp_path / "gone.sp"))


def test_a_compressed_jcamp_is_refused_not_misread(tmp_path):
    path = tmp_path / "squeezed.dx"
    path.write_text("##TITLE= x\n##XUNITS= 1/CM\n##YUNITS= ABSORBANCE\n"
                    "##FIRSTX= 4000\n##LASTX= 3996\n##NPOINTS= 5\n"
                    "##XYDATA= (X++(Y..Y))\n4000 A1B2C3D4E5\n##END=\n")
    with pytest.raises(readers.ReadError, match="compressed"):
        readers.read(str(path))


def test_a_plain_jcamp_by_the_standard(tmp_path):
    """FIRSTX is the ACTUAL first wavenumber: XFACTOR scales the table's
    numbers, never FIRSTX (the plotter multiplied it in)."""
    path = tmp_path / "plain.jdx"
    path.write_text("##TITLE= made here\n##XUNITS= 1/CM\n##YUNITS= "
                    "TRANSMITTANCE\n##XFACTOR= 2.0\n##YFACTOR= 0.001\n"
                    "##FIRSTX= 4000\n##LASTX= 3992\n##NPOINTS= 5\n"
                    "##XYDATA= (X++(Y..Y))\n2000 900 910 920\n1998 930 "
                    "940\n##END=\n")
    spectrum = readers.read(str(path))
    assert list(spectrum.x) == [3992.0, 3994.0, 3996.0, 3998.0, 4000.0]
    assert list(spectrum.y) == pytest.approx([0.94, 0.93, 0.92, 0.91, 0.9])
    assert spectrum.unit == readers.UNIT_T_FRACTION
    assert spectrum.head["title"] == "made here"


def test_a_text_header_that_names_the_values(tmp_path):
    path = tmp_path / "named.csv"
    path.write_text("Wavenumber;Absorbance\n400,0;0,10\n401,0;0,12\n"
                    "402,0;0,11\n")
    spectrum = readers.read(str(path))
    assert spectrum.unit == readers.UNIT_A
    assert list(spectrum.y) == pytest.approx([0.10, 0.12, 0.11])
