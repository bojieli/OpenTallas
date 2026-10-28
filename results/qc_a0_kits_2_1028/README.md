# QC-A0-KITS-2 (2026-10-28) -- A0 NK/NL parent: estimate before build + child route continuation

## Parent centre-entry clock ESTIMATE (12.14, UNCHECKED model; est.json)
Inputs: outline 457.92 x 1157.76 um, one centre entry (228.96, 578.88); child records = Codex fixture
parent_{nk,nl}_children.json (census b5e8528af8, NK 8 raw + 10 ROM + 1 node, NL 8 raw + 10 ROM); every child
clock pin is its centre entry. Child insertion = trial CTS placement-RC (rawleaf 157.98/126.28, romleaf 170.29/139.94,
node 222.31/178.41 TT/FF). Parent trunk = Manhattan centre->child pin x 199..334 ps/mm (CORELAT-SQ-1 range), FF = 0.8 x TT wire.

| type | farthest child pin | balanced insertion TT (199 / 334 ps/mm) | FF | critical child | early tap vs 250 TT |
|---|---|---|---|---|---|
| NK | 641.6 um | 324.8 / 394.3 | 260.4 / 316.0 | node (515 um, 222 ps internal) | +75 .. +144 |
| NL | 641.6 um | 294.0 / 377.9 | 238.9 / 306.1 | romleaf (621.7 um) | +44 .. +128 |

- 250 +-20 with a centre entry is NOT reachable (node alone 222; the 0.64 mm trunk alone is 128-214 ps). The centre
  entry fits with an EARLY TAP of ~75-145 ps (NK) / ~45-130 ps (NL) per 12.3 v5.0, below the ~250 ps last-mile limit
  (CORELAT ruling 3). Consistent with the CORELAT placeholder 390/312 (upper end).
- NK is set by the node: a 12.8b in-core structured trunk in the node (two plan-fixed N/S branch nodes, local leaves
  <= ~115 um) would bring NK to about the NL value (UNCHECKED, ~20-40 ps).
- Cells: parent glue NK 64,205 / NL 61,550 std (historical, UNCHECKED) + CTS + hold buffers -> < 80k << 400k cap.
- A0 boundary FF hold: CORELAT est -15.8 ps (UNCHECKED) after the early tap -> data hold buffers (12 v4.6) in the parent.
- The real number is the parent kit CTS on the child fixtures; it replaces this estimate.

## Child continuation
- rawleaf: rawleaf_resume_finish.sh = route + sign-off continuation of the GEOM-PASS rst145 placement (CODEX-PV 10-27 14:58,
  3_place sha 0a1428ef...), make -o on the reviewed 3_place so it is never redone.
