Native closed reset-repeater PDN regression
=========================================

This fixture tests `pdn_regroup.py --own-grid qfd_rst_rep=2.16,3.36
--own-grid qfd_rst_rep_p8=2.16,3.36` against the real, unchanged closed-view
LEFs. It places 32 macros: both masters, four orientations (R0, MX, MY,
R180), and four y-origin phases on the 2.16-um lattice. X origins also
vary relative to the core M9 pitch. No RTL, macro geometry, or PG pin edits
are used. The candidate keeps the 8.64-um core M8 lattice and the 9.091-um
core M9 lattice.

Run `python3 tools/qwen_split/pdn_own_fixture/prepare.py REPO OUT TECH_LEF`
from a repository containing the own-grid implementation. The actual
input paths and SHA-256 hashes are saved in OUT/inputs.json. Sync OUT onto
the fleet and use admission, for example:

```bash
ot-run --mem 2 --threads 1 --dir OUT -- bash -c \
  'docker run --rm --user $(id -u):$(id -g) -v "$PWD":/work -w /work \
  --entrypoint bash openroad/orfs:asap7lock driver.sh'
```

The driver requires native `check_power_grid` success for VDD and VSS.
It also reads the generated ODB back and checks every generated PG metal
rectangle and every via's metal/cut rectangles for cross-net geometric
intersections. There are zero intersections on M5-M9 and V5-V8. This is
an intersection check, not a complete foundry DRC deck.

The mutant applies the original per-phase 8.64-um macro grids to the same
masters and placements. It must fail with PDN-0185 (the 6.48-um macro
cannot accommodate both straps at offset 2.16). Removing own-grid support
therefore cannot silently pass this fixture.

`evidence/` contains the successful native logs, original-phase mutant
failure, shape counts and input/source hashes. This is a small physical
integration regression; full-die connectivity, routing and timing still
require the actual die run.
