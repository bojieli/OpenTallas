# Forwarded capture-edge replacement kits

The existing `v17_negcap/dsfd_hend.sv` generated source is retained. The eight
selected masters capture lane data on the falling forwarded edge, before the
original rising FIFO write edge. The kit outlines and individual pin positions
come directly from `physical/s81_die_pins/v17/<master>.json`.

The reference flow's original single-domain boundary switches are followed by
`boundary_tcl`: `di0` is timed against virtual launch clock `vw`, its receiving
register uses falling `w_fi0`, and `o` is referenced to virtual `vclk` associated
with the local `core_clk` insertion. Every input/output max and min delay is
reapplied after CTS, global route, detail route and fill boundary switches.
The mesochronous FIFO crossings retain the proven 1190 ps max and zero min
constraints; the 3:4 ratio FIFO crossings retain ordinary related-clock timing
with no crossing exceptions. No same-domain capture paths are excluded.

Route uncertainty is the established 123 ps, signoff uncertainty 60 ps; hold
uncertainty is 25 ps. Both real clocks propagate at signoff. Virtual IO clocks
use the measured corresponding clock tree insertion through the original
`post_cts_hend.tcl` logic, included in the standalone extra SDC and boundary hook.

`bench_hend.sh pass|mut TOP KIND RUN` drives lane words on rising `fi0` and
independently records expected falling-edge captures. It checks FIFO accepted
transactions against every output word in order, including repeated data and
absence of duplicate outputs. Five static phases cover launch/receive ordering, including phase 0. The clocks use
1 fs precision: meso 833.333 ps, ratio 833.331:1111.108 ps (exact 3:4), so
the ratio phase-0 run includes repeated coincident divider edges.
Raw masters continuously accept words; their live run retains at most 16 words
in flight at the terminal sample. VR/ratio runs drain every accepted word.
The mutant flips a data bit in the input capture register; compilation failures
return 2 and cannot be mistaken for its expected transaction mismatch exit 1.
Every submitted job reruns the positive and mutant with its exact top master.
