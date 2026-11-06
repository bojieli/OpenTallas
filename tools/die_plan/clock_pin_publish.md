# Publish existing connected clock metal

Run clock_pin_publish.py with OpenROAD Python on a fresh private final ODB copy:

    openroad -python -exit clock_pin_publish.py IN.odb OUT.odb --pin clk --layer M6 --report report.json

The helper requires a root CLOCK input with no internal driver, native physical
connectivity to every load, actual target-layer regular wire and native via
enclosures. It exposes only legal-width real wire within the original pin XY
footprint. Missing metal or disconnected loads refuse before any output is
written. Original wire/via/cell geometry and all existing pin shapes remain.

This does not create a new wire or clearance window. If no actual connected M6
clock metal exists, use a real physical landing construction/new factory form.
A successful publication still needs ordinary abstract export, actual parent
pin access/DRC, and the clock timing/interface record for the resulting view.
It never upgrades a signoff result or assumes an old view has been qualified.

Actual h9b/bank canaries and the viewed image are in
results/geom_review/clock_pin_publish_1106. No production hook calls this helper.

If native upper-layer via enclosure cannot fit the default footprint, a reviewed
explicit --access-margin-um window can expose more already-connected clock metal.
It never extends a wire or clears an obstruction. The window is anchored to
unchanged lower-layer PIN geometry, so reimport cannot grow it repeatedly.
Added shapes stay in the original physical PORT. Fresh parent PA and timing
remain mandatory; a legal-width rectangle is not automatically a legal via site.
