# Changelog

## Unreleased

- Settings windows in an order you can work down: the text first, then
  the colour, then what only the window can set (a marker line's
  position, a note's point and arrow, a region's stretch), then sizes and
  style; Show and Layer at the bottom.
- A band marker's (marker line's) window has no arrow rows any more: they
  belonged to notes. A label's arrow rows appear only once "Leader
  arrow" makes it a note.
- A region's list of curves to magnify shows only once it magnifies (a
  factor other than 1); a plain highlight has none to choose.

- No more "NORMALISED, and the y caption does not say so" stamped on the
  figure when you type your own y caption: what you type is yours.

- The plot's right-click menu has a Normalise submenu with all four
  choices - None, Individual (each spectrum 0 to 1), Global (all together,
  0 to 1) and To a band... - the one in force ticked. It replaces the
  single "all together" tick.
- Double-click the y caption: "Shows" changes what the axis shows
  (transmittance or absorbance), one undo step. A caption you typed yourself stays as typed,
  and the window says so.

## 0.2.0 (2026-10-02)

- On a white page (and in every export) a colour you picked is drawn
  exactly as picked; only the default screen palette is darkened to read
  on paper. A yellow used to come out olive.
- `Ctrl+T` asks nothing: on selected curves it makes a label for each,
  saying its name, hanging from the curve (above its high-wavenumber end in transmittance, below it in absorbance); with nothing
  selected, one free label "Label" to retype with a double-click. New
  labels are selected.
- The pick distance is 8 px unless you change it (it was 14).
- "Label the spectra at their left edge" is now "Label every spectrum
  on show by its name", placed as `Ctrl+T` places them.
- Normalising all the spectra together, 0 to 1 - the lowest value of any
  spectrum on show is 0, the highest 1 - is where a figure starts; a
  spectrum opened or hidden rescales the rest. In F3 beside "each spectrum
  0 to 1", and a tick on the plot's right-click menu.
- S on curves holds the lowest still, as before; T, B or M while it is live
  holds the top, the bottom or the middle of the stack still instead, where
  it is when the key is pressed. The dashed line runs through the held curve.
- The plain swipe (wheel, middle drag) makes every curve taller or flatter in
  its place; the axis rescales and the offsets follow. It used to scale the
  axis about y = 0, which spread the stack apart: P during S does that now,
  keeping the stack's own gaps in proportion.
- A white page under the default theme no longer fails to draw.
- A pan shows the data moving under a still frame (the whole page moved
  until the button was let go).
- Faster drawing: every change shows at once as a draft, the curves drawn
  thin, and in full once nothing has changed for a moment; curves are put
  together several times faster.
- Align from F3 shows at once and moves labels hanging from a curve too;
  new: space the selected artists evenly across or down.
- A box selects labels, markers and other artists, not only curves.
- Colours: the colour as #rrggbb beside every swatch, to copy and paste;
  "Inherit" makes a colour follow another object's for good; a label given
  to a curve takes the curve's colour.
- A label on a curve is placed by x and y like every other artist (no more
  "Distance" and "Sideways"), and still moves with its curve.
- The page-margin blades are there on every figure; taking one on a figure
  that is not of an exact size makes it exact as it is on screen (the
  axes box stays where it is), and says so in orange. Choosing "an exact
  size" in Figure size and margins also starts from the screen.
- A session whose files were moved looks for them beside itself (its
  folder and the folders under it) and keeps their curves.
- A session keeps a compressed copy of its files: it opens even after they
  were moved or deleted, and says when it read the copy.
- A region's two edges are dragged one at a time on the figure; its text
  takes several lines.

## 0.1.0 (2026-09-30)

The first version.

- Readers for PerkinElmer `.sp`, Thermo OMNIC `.spa`, JCAMP-DX (the plain
  `(X++(Y..Y))` form) and two-column text, each checked against the other
  exports of the same measurement. A file that does not say what its values
  are is guessed from the data, said as a guess, and can be told.
- A wavenumber axis from high to low with round ends, and a broken x axis:
  a stretch squeezed to a marked seam, set from a drag or typed.
- Transmittance or absorbance, converted; normalisation per spectrum (0 to
  1, or to a chosen band), said on the y caption; the stack's arrangement
  kept across both.
- A drag along a curve: peak position, band area and band width (FWHM),
  all on absorbance; highlight, magnify, normalise to the band, break the
  axis.
- Band markers with assignment labels and `{}` for their wavenumber;
  distance arrows tied to two markers; highlighted and magnified regions;
  labels at the spectra's left edges.
- The handling of the sibling DSC panel: stacking, `G`/`S`/`R`, the F3
  operator search, undo for everything including the view, the outliner,
  sessions, house style and presets, exact figure sizes, PNG/SVG/CSV
  exports, three themes, the Start Menu entry.
