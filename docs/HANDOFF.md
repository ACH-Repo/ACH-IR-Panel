# Handoff: the chat that built IR-Panel (2026-09-30)

Everything a new session needs to pick this up cold. Read this, then
`CLAUDE.md` (the rules and the traps) and `docs/PLAN.md` (the log and
what is next). `docs/OPERATORS.md` is generated from the code.

## 0. State

- Version 0.2.0 (2026-10-02). A git repository since 2026-10-02, on
  GitHub as ACH-Repo/ACH-IR-Panel (see PLAN.md). Not on PyPI: the
  family name is to be settled first (Christian, 2026-10-02).
- `python -m pytest -q`: 125 passed, none skipped, with the real files
  listed in `tests/local_testdata.txt` (gitignored) on disk.
- The end-to-end check: his Hbc figure (ten `.sp` files, the driver's
  ladder, colours, labels, break at 2200-1800, four band markers and the
  carboxylate splitting) rebuilt with the panel's own operators and
  exported at 7 x 4 in. It matches his matplotlib figure; the two
  deliberate differences are in section 4.

## 1. What was asked

Christian: build the FTIR equivalent of Triplot (ACH-DSC-Panel) in this
folder; carry over everything that is abstract and works for any plotted
data type; take his stacked-IR script (`plot_IR.py`, the matplotlib
figure for the carboxylate paper) as the model, and add its IR-specific
features. His answers to the questions put first:

| Question | Answer |
| :-- | :-- |
| Share code with Triplot how? | **Copy** into this repo (recommended option). The shared core is drawn out later. |
| Name? | **IR-Panel, provisional** (`ir-panel`, import `irpanel`). |
| Which analyses? | Peak position, band area, band width (FWHM) - and **"not just analyses: highlighting an interval should be part of the draggable ergonomics"**. |
| A driver export (a script that redraws the figure)? | **No**: SVG/PNG (and CSV) only. |

Note the copy departs from `ACH-DSC-Panel/docs/FAMILY.md`, which
suggested building IR against Triplot's code and moving pieces into a
core as they were needed. Christian chose the copy; FAMILY.md's table of
what belongs in the core still stands.

## 2. What was built

The whole of Triplot's handling came across (plot widget, gestures,
picking, undo, operators and F3, outliner, sessions, house style,
presets, figure size, themes, exports, registration, structures from
SMILES). Removed: the TRIOS readers and analyses, DTG, molar masses, the
exotherm arrow, the driver export, segments.

New for IR (details in `CLAUDE.md` and the module docstrings):

- `core/readers.py`: `.sp` (PerkinElmer block tree), `.spa` (OMNIC
  section table), JCAMP-DX (AFFN only; compressed forms refused), and
  two-column text. Validated against the other exports of the same
  measurement (a `.sp` against its `.DX` and `.csv`, in %T and in A) and
  bit-identical with his script's readers where those were right; fixed
  where they were not (`##YUNITS= A` missed, XFACTOR multiplied into
  FIRSTX, compressed JCAMP misread).
- `core/units.py`: %T / A with the conversion, the unit guess for files
  that do not say (said as a guess), normalisation none / 0-1 / band,
  said on the y caption.
- The reversed x axis (4000 to 400, rounded ends) and the **broken** x
  axis (`warp_x`), with the seam's slashes, set from a drag or typed.
- `core/measure.py`: peak position (parabolic vertex; an edge maximum
  refused), band area (trapezoid above a straight A baseline), band width
  (FWHM, interpolated). On absorbance always. The drag list also holds
  Highlight, Magnify, Normalise to this band, Break the x axis here.
- Decorators: `Region` (highlight and / or magnify, the script's
  `mark_area` + `magnify`), `SpanArrow` (the script's `mark_delta`, ends
  tied to band markers), band markers (`TextLabel.vline`, the script's
  `mark_mode`, `{}` = the wavenumber), edge labels (`label_edges`, the
  script's `add_labels`), offset markers (`add_yoffset_markers`).
- `core/profile.py`: F staged (x then y), x reversed, rounded ends, new
  files stacked under the open ones.
- The script's colours are the colour picker's basic colours; its
  `shades` is the F3 gradient.

## 3. Open for Christian

- **Git**: initialise, and push to `ACH-Repo/ACH-IR-Panel`? (Not done.)
- **The name** (with the family's: `docs/FAMILY.md` in ACH-DSC-Panel
  suggests `stackline-ir`).
- **Spread labels**: his script has `spread_labels` (push overlapping edge
  labels apart). Here labels are placed by hand (drag, or the align
  operators). An operator "arrange the selected labels as a block under
  their curves" would replace the script's hand-tuned `label_dy` lists.
- **VT colouring** (a series coloured by temperature, with a colour bar):
  FAMILY.md's round 6, not built.
- **More formats**: Bruker OPUS, compressed JCAMP-DX - real files first.
- **The shared core**: diff `src/irpanel` against `src/dscpanel` and move
  what is identical into a package both depend on. Best done once PXRD
  starts, per FAMILY.md.
- **Neutral source before any public release**: about 40 comments and
  three tooltips cite "the plotter's `mark_mode`" etc. (his IR script, as
  Triplot's cite ACH-DSC-Plotter). Harmless in a private repo; reword
  before PyPI.

## 4. Deliberate differences from his script

- **The y caption on normalised data says "(normalised)"**, not
  "Transmittance / %": the script labels 0-1 normalised values in per
  cent, which the panel's rule 4 does not allow.
- **A band marker's label has no white box.** The line breaks round the
  text instead; a box (the script's `bbox`) cut the curves that ran under
  it once the text was drawn over them.

## 5. Where the real files are

Listed in `tests/local_testdata.txt` (gitignored, on this machine): seven
folders - the Hbc stack and the paper's other stacked-IR folders,
measurements exported as `.sp`, `.DX` and `.csv` in %T and in A, and
ACH-VT-IR-Plotter's example `.spa` files. `tests/test_readers.py` names
each file it uses by a hash of its file name.
