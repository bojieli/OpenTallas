# Generated clock physical family census

This tool change measures generated descendants under their actual primary
physical source. It does not authorize a clock phase, change a period, relax an
uncertainty, or qualify LAND timing.

OpenSTA 3.1.0 exposes `Clock.is_generated` but no master-clock accessor. The
helper reads OpenSTA's canonical `write_sdc` declarations in a safe interpreter;
only generated-clock declarations execute, through recorder aliases. It checks
the source pin's actual clock owner against the exported master, rejects
ambiguous sources/sinks and ancestry cycles, and visits each sink once under
its actual timing clock. Names select declared entries, never infer ancestry.

A full native timing search must initialize generated source insertion before
iterating clock paths. In the toy circuit, without that search the generated
sink incorrectly appears to have only 3 ps of insertion. The complete path is
6 ps of master distribution plus 3 ps of bank distribution. After the native
search, the tag contains 9 ps. The measurement subtracts the actual generated
source waveform phase (110 or 310 ps in the probes), retaining those 9 ps.
No synthetic source insertion is added.

The same Tcl implementation supplies CE, native insertion calibration, and
routed IO references. The routed file embeds an identical copy so archived and
flat helper layouts remain self-contained; a test compares the exact bytes.
The helper plan ships the standalone Tcl beside flat `ck_insertion.py` copies.
Native insertion JSON includes each corner's per-clock family counts.
Cross-family CE reservations project onto every generated descendant: 150 ps
setup (210 for a deep reference) and 100 ps hold. Same-family clocks retain their
explicit existing base/scenario uncertainties. Generated-clock owners must
supply at least the ordinary 60/25 ps base themselves before CE applies.

## Evidence

`evidence/focused.log`: 24 focused tests PASS, including real OpenSTA ownership,
large phase, source compensation, CE/native/routed-reference equality, the
150/210 + 100 ps reservations, multiple-master rejection, and existing path and
boundary census tests. `evidence/final_family.log`: eight final family tests
PASS, adding flat shipped-helper import coverage. The expected rogue-master
rejection appears as an OpenSTA error in the successful negative-test log.

All native executions used `ot-run`, Docker `openroad/orfs:latest`, pinned
OpenSTA 3.1.0 / OpenROAD 26Q3-1510-g6cb3f2b704 on the fleet.

Actual LAND mapped/floorplan topology was also exercised, using the immutable
artifact on ot-epyc8:

```
/srv/opentallas-scratch/claude/ref_gate/qfwd_landh0_180_en_48x48_g4-20261019-085926/routes/gate/work/orfs/results/asap7/opentallas_qfd_landh0_180_EN_48x48_asap7_ref_gate/base
2_floorplan.odb sha256 5323f426c15d3c08de5489a1ad16ba1296fd3a4a152e86d9abcda32f634b188c
2_floorplan.sdc sha256 73c4586df40542f5ea0a8406982dca79febb83dd480df79de59e405d022fee11
```

`land_floorplan_probe.tcl` adds eight generated-bank declarations at the actual
ICG GCLK pins. Its `{1 2 9}` edges are deliberately a diagnostic topology case,
not a compiled phase contract. TT and FF both find 992 read-family clock pins
(260 direct plus four banks of 183) and 745 write-family pins (13 direct plus
four banks of 183), each with a unique actual owner. The FF log is retained.
The first TT sample was approximately 351 ps/read bank and 431 ps/write bank;
FF is approximately 255/311 ps. These are unbuffered floorplan diagnostics,
not routed/native R records or acceptable boundary spread.

LAND still requires its joined compiled K/E/reset/physical-root-phase scenario
certificate, every timed write/read/root/control/reset path, and actual routed
TT setup / FF hold with native family measurements and the existing reserves.
The standalone 256-case functional certificate does not establish that physical
phase contract. No LAND gate or CLOSED record is issued by this work.
