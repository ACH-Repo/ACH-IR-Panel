# IR-Panel

An interactive panel for stacked infrared spectra. Drop spectra on it,
stack them into the arrangement you want, mark the bands, measure them, and
export the figure as a PNG or SVG (or the curves as CSV).

It reads PerkinElmer `.sp`, Thermo OMNIC `.spa`, JCAMP-DX (`.dx`, `.jdx`,
`.jcm`) and two-column text (`.csv`, `.txt`, `.dat`, `.asc`), each with its
own reader, checked against the other exports of the same measurement
value by value (`tests/test_readers.py`).

```bash
pip install -e <checkout>    # from a checkout (not on PyPI)
ir-panel                     # start it
ir-panel sample.sp           # straight into a file
ir-panel register            # put it in the Start Menu (optional)
```

Python 3.10 or newer; PySide6 (the Essentials only), numpy and RDKit come
with it. Version 0.2.0; "IR-Panel" is a working title. What changed is in
`CHANGELOG.md`.

## What it does

- **Every spectrum is an object** you can select, move, hide, colour and
  right-click. New files arrive stacked under the ones already open.
- **The wavenumber axis runs from high to low** (4000 to 400 cm-1), with
  round numbers at its ends, and can be **broken**: a stretch where
  nothing happens (2200 to 1800 cm-1, say) squeezed to a seam marked by
  slashes, the width given to the fingerprint region instead.
- **Transmittance or absorbance**, converted (A = -log10 T) whichever the
  file holds. A file that does not say which it holds - a bare two-column
  text - is guessed from its data, and the guess is said as one wherever
  the unit is shown; tell it otherwise in the file's settings.
- **Normalisation, said on the axis.** All the spectra together 0 to 1
  (where a figure starts: the lowest value of any is 0, the highest of any
  1, so their depths keep their proportions, and a spectrum opened or
  hidden rescales the rest), each spectrum 0 to 1, each spectrum's chosen
  band to the same strength, or none - F3, or a tick on the plot's
  right-click menu for "all together". The y caption says "(normalised)"
  whenever it is on. Changing the unit or the normalisation keeps the
  stack's arrangement.
- **The stack is continuous.** Spectra go wherever you put them (`G`, or
  type a number); `S` spreads the selection evenly. A stack has no y
  numbers or ticks - its offsets make them meaningless - but the y axis's
  settings (double-click it) switch them on.
- **Three themes**: `blender-default` (dark), `light`, `boombox`. Exports
  are always light, whichever is on screen.

## Marking and measuring

Press on a curve and drag along it: the stretch between the two crosshairs
is the interval. Let go, and a short list opens under the pointer:

| Entry | What it does |
| :-- | :-- |
| Peak position | the strongest absorbance in the stretch (the deepest transmittance), refined by a parabola through its neighbours |
| Band area | absorbance over wavenumber above a straight baseline between the stretch's ends, in A cm-1 |
| Band width (FWHM) | the full width at half height above that same baseline |
| Highlight | shade the stretch across the figure |
| Magnify... | this spectrum magnified in the stretch, about its own chord, the factor written over it |
| Normalise to this band | every spectrum's band here at the same strength |
| Break the x axis here | cut the stretch out of the axis |

The three measurements are made **on absorbance, always**, whatever the
axis shows and never on the normalised or magnified curve: absorbance is
proportional to how much absorbs, and it is the same number however the
figure is drawn. A peak at the very edge of its stretch is refused (widen
the stretch). To give the bounds as numbers, select one spectrum, press
`C`, type two wavenumbers and `Enter`.

Double-clicking an analysis brings its cursors back as gizmos, with its
settings beside them; drag a gizmo and it is recomputed. Its caption -
`{}`, `Area = {}`, `FWHM = {}` by default - is editable text; `{}` is the
result in the house number format.

## On the figure

- **Band markers** (`Ctrl+B`, or right-click the plot): a dashed line
  across the axes at a wavenumber, with an upright assignment label on it,
  `\nu_{a}(COO^{-})` or `$\nu_{a}$(COO$^-$)`. The line runs under the
  curves and breaks round its text. `{}` in the text writes the marker's
  wavenumber.
- **Distance arrows**: select two band markers and "Measure the distance
  between them" draws a double arrow labelled
  `\Delta\tilde{\nu} = 182 cm^{-1}`. Its ends follow the markers.
- **Regions**: a highlighted stretch, a magnified one, or both, with its
  own text (several lines). Drag either edge to move that limit alone.
- **Name labels**: `Ctrl+T` on selected spectra hangs each one's name
  from its curve, in its colour - above its high-wavenumber end in
  transmittance, below it in absorbance - with nothing to type first;
  "Label every spectrum on show by its name" does all of them. The labels
  move with their curves; a double-click retypes one.
- Captions (`Ctrl+T` with nothing selected), notes with an arrow
  (`Ctrl+Shift+T`), a legend,
  pasted pictures and skeletal structures from a SMILES.

Every text takes the same markup: `*T*` for italic, `_{a}` and `^{-}` for
sub- and superscripts, a backslash name for a Greek letter (`\nu`,
`\Delta`), `\tilde{\nu}` for the wavenumber, and LaTeX between dollars as
matplotlib's mathtext takes it.

## Keys

| Key | What it does |
| :-- | :-- |
| click | select what is under the pointer (`Shift` adds) |
| drag from a curve | **mark an interval**; let go and pick from the list |
| drag from an artist | move it: a label, a marker, a region, an arrow, the legend |
| drag from empty space | box select: curves, labels, markers, any artist |
| double-click | settings for what is under the pointer |
| wheel, two-finger swipe, middle drag | every spectrum taller or flatter about its own baseline, each in its place |
| `Shift` + swipe or middle drag | pan |
| pinch, `Ctrl` + wheel | zoom about the pointer |
| `F` / `Home` | fit the view: the x range first, then y |
| `M` | type the x range |
| `G` | grab the selection: move it, or type a number, `Enter` |
| `S` | with spectra selected, spread them evenly, the lowest held still; `T`, `B`, `M` hold the top, the bottom or the middle instead; `P` keeps the stack's own gaps in proportion |
| `R` | reset the selected offsets |
| `C` | measure by typing two wavenumbers |
| `Ctrl+T` | label the selected spectra with their names (nothing selected: a free label) |
| `Ctrl+B` | add a band marker |
| `H` / `Alt+H` | hide the selection / show everything |
| `N` | show or hide the outliner |
| `F3` | **operator search**: everything, filtered by what is selected |
| `Ctrl+Z` / `Ctrl+Y` | undo / redo, including zoom, pan and fit |
| `Ctrl+S` / `Ctrl+E` | save the session / export the figure |
| `Ctrl+,` | settings: the house style, for every figure and for this one |

A drag acts on what it starts near: start close to a curve and it marks an
interval, close to a label or a marker and it moves that, anywhere else it
draws a box. A spectrum moves with `G` and nothing else. Every operator,
its key and when it is allowed is in `docs/OPERATORS.md`.

## House style, figure size, exports

`Ctrl+,` sets the sizes (axis captions, numbers, labels, band markers,
regions, distance arrows) and the number formats, in two columns: your
default, kept on this computer, and this figure, saved in its session.

Edit > **Figure size and margins** gives the figure an exact size in
centimetres or inches with four margins, so two figures with the same
settings have identical axes boxes.

| Export | What it is for |
| :-- | :-- |
| PNG / SVG | the figure in the light palette; at an exact size, exactly that size |
| CSV | the curves as drawn, one x/y column pair per spectrum |

Sessions (`.irpanel`) keep the files' paths and a compressed copy of each
file, the arrangement and every decorator: a file that was moved is looked
for beside the session, and failing that its copy is read. Style presets
(`.irstyle`) keep a figure's look.

## The Start Menu and aliases

Opt-in and reversible, and it writes down what it created:

```bash
ir-panel register                # Start Menu entry (add --desktop for one there too)
ir-panel register --list         # what is registered
ir-panel register --remove       # take it away again
ir-panel alias irp               # your own name for it
```

## Project layout

```
src/irpanel/
  branding.py        every place the program says its own name
  register.py        Start Menu entry, aliases, and the manifest of both
  core/              UI-free: readers, units, model, analyses, undo, session, export
  ui/                the painted plot, the outliner, the F3 palette, dialogs
docs/OPERATORS.md    every operator, its key and when it lights up
```

## Development

```bash
python -m pytest -q
```

Measurements are not committed. The tests that need real files look for
paths in `IR_TESTDATA` or in an uncommitted `tests/local_testdata.txt`, and
skip when there are none. They name a real file by a hash of its file name
(`tests/conftest.py`, `hashed_name`).
