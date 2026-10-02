# Plan and log

What is built, what is next, what is undecided. The decisions behind the
repo are in `docs/HANDOFF.md`; the family plan (IR, then PXRD, on a shared
core) is `docs/FAMILY.md` in ACH-DSC-Panel.

## Round 1, 2026-09-30: the first version (0.1.0)

Built in one chat from Triplot's code and Christian's stacked-IR script:

1. The copy: Triplot's tree as `src/irpanel`, the DSC-only modules taken
   out (TRIOS reader and analyses, DTG, molar masses, exotherm arrow,
   driver export), the name in `branding.py`.
2. Readers for `.sp`, `.spa`, JCAMP-DX and text, against his real files.
3. %T / A, the unit guess, normalisation (none, 0-1, band), the offsets
   carried across a change by one common factor.
4. The reversed x axis, rounded ends, the broken x axis.
5. The drag list: peak position, band area, FWHM (on absorbance),
   highlight, magnify, normalise to the band, break.
6. Band markers, distance arrows tied to them, regions, edge labels.
7. Tests (95), the operator doc, the README, the replica of his Hbc
   figure as the end-to-end check. After the replica: band-marker lines
   moved under the curves and broken round their text.

## Round 2 (2026-10-01): what S holds still, family-wide

Christian, 2026-10-01: "the scale with S for offsetting could be improved
for all current and future plotters by allowing to change the reference
point of the scaling operation by pressing T/B/M while scale is active".
The first change made family-wide by his new standing rule (his global
notes): the same patch in Triplot and IR-Panel, and the same test file,
`tests/test_family.py`, in both.

* T, B and M during S on curves hold the top scan, the bottom one (as
  before, and where S starts) or the middle of the stack still
  (`PlotWidget.spread_anchor`). The step reached is kept; the dashed
  neutral line moves to the held place; the status line names it. R and
  Esc work as before. X, Y and C still mean nothing to a spread; on
  artists, S keeps its X / Y / M / C pivots.
* Second pass, the same day, from his screenshots: the held place is where
  the curve IS when the key is pressed (the first version took where it
  was when S began, and the stack jumped on every key), and the line runs
  through the held curve - at the offset it sat ~100 %T below a
  transmittance and looked like y = 0.
* Same day, after his question about the trackpad: the plain swipe makes
  every curve taller or flatter IN ITS PLACE (`scale_intensity`) -
  MestReNova's gesture and MoloM's PXRD window's, family-wide at his word.
  It reverses round 13 of Triplot ("scale y about y = 0") and the
  docstring that said MoloM's intensity gesture "must not exist here"
  because a W/g axis would lie: here the axis is scaled and the offsets
  follow, nothing is multiplied, so the numbers stay true. Each curve
  keeps its BASELINE in place (`profile.baseline`: a %T spectrum's near
  its top, a heat flow's median). The old proportional spread is P during
  S, his choice.
* Found the same day, his log: a white page under the default theme
  raised KeyError 'tilde' - the markup's accent table had the theme's
  table's name (`ACCENTS`) and replaced it. Renamed `MARK_ACCENTS`;
  `test_no_module_name_is_bound_twice` (both panels) guards the kind.
* Same day, a batch from his use of IR-Panel, family-wide at his word:
  the pan draws (it slid the whole page); drafts while a hand is at work
  and after every change, the full drawing when it settles (measured: the
  line width is the cost, not antialiasing, which had only ever been off
  for the frame, for crispness); numpy point lists; align shows at once
  and moves labels on curves; space artists evenly; a box selects
  artists; the hex field beside every colour; "Inherit" (a colour that
  follows another object's, saved); a label given to a curve wears its
  colour; a label on a curve placed by x and y (his choice: it still
  hangs). The page-margin blades were there all along in IR-Panel: they
  show on an exact-size figure only, and his was a fixed aspect ratio.
* Same day, more from his use: the blades on every figure, making it
  exact from the screen on first use (orange note) - and the size window
  going exact from the screen too (his: "the default size settings ...
  all sizes completely out of whack"). Sessions look for moved files
  beside themselves; IR-Panel keeps copies inside (~0.75 MB for ten .sp
  files), Triplot not (.tri files are big; his call). IR-Panel's regions: each edge dragged on its own, text in several lines. Asked, not
  built: a figure in Word that opens the panel on a double-click (a COM
  OLE server, the ChemDraw way: possible with pywin32, a large fragile
  project; the light alternative, the session inside every exported
  picture, offered and declined for now).

## Round 3 (2026-10-02): labels by name, the pick distance, normalising together

Christian, 2026-10-02: labels "spawned with default names without having
to type one first", for all selected lines at once, "across panel
plotters"; lower right of each line in PXRD, upper left in IR (if
transmission), upper right in DSC; and the default pick distance 8
"across projects". Family-wide, the same patch in the three members and
two tests in `tests/test_family.py`:

* `Ctrl+T` asks nothing: on selected curves a label each, the curve's
  name, hanging from its end at `profile.name_label_corner`
  (`MainWindow.name_labels`, `PlotWidget.end_sample`); on nothing, a free
  "Label". New labels are selected. His answer for IR in absorbance:
  lower left (the mirror of transmittance).
* The pick distance is 8 px built in (was 14).
* Not family-wide (DSC is never normalised), IR-Panel and PXRD-Panel:
  "all together, 0 to 1" (`units.NORM_GLOBAL`) - the lowest value of any
  curve on show is 0, the highest 1, recomputed as curves are opened,
  hidden or cut; the offsets stay (his choice). In F3 beside "each 0 to
  1", and a tick on the empty plot's right-click menu. IR starts with it;
  PXRD starts without normalisation (it started with each 0 to 1).
* IR-Panel and PXRD-Panel's "label at their left edge" became "Label
  every curve on show by its name", placed like `Ctrl+T` (his choice).

## Round 4 (2026-10-02): colours on a white page, family-wide

Christian: why a yellow came out olive on a white page. On a white page
(and every export) only the default screen palette is darkened now
(`paper_colour`); a picked colour is drawn as picked - his choice, for the
whole family. (The selective swipe and "xN" factors he asked for in the
same message went to PXRD-Panel only.)

## Next (suggested; Christian decides)

- Git: initialise and push (his call).
- Use it on real figures and collect requests here, as Triplot did in
  `docs/NEXT.md`.
- Spread / block the edge labels (the script's `spread_labels` and
  `label_dy`).
- VT colouring with a colour bar.
- OPUS and compressed JCAMP-DX, when there are real files.
- The shared core with Triplot, then PXRD.
