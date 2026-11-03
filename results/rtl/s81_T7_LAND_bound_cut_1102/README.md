# T7 LAND bound data cut: UNAPPLIED, structural identity proved, no manifest change

`transform.py --parent <bound.sv> --out <fresh dir>` prepares the LAND data cut. It accepts only four exact preimages of `s81p_svc_lo_dsdv_svc_rs__t7_bound.sv`, identified by hash:

| Preimage | SHA (prefix) |
|---|---|
| original | 61c902f1 |
| PMEM cut | 04a55430 |
| PVQ-only cut | a2886879 |
| PMEM+PVQ joint cut | 00bd1321 |

**What the transform does:**
- Removes the native 640x256 land helper instance (`ot_bind_native_4c805`).
- Removes the three lines of the 1060-bit `ekv_w` capture register `src_2be8…_q` (reg, Q assign, always). The `src_2be8…_Q` wire and both engine `.wr_data` readers stay as they are.
- Rewrites one line, the 2158-bit struct wire `711_Y`. It keeps the only fields still read, [3:0] (`ekv_m` capture) and [1067:1064] (`rel_bad`), and zeroes the rest. Those zeroed fields are the raw RD_DATA copies, the debug row/j words and the `kc_w` words, which only the removed capture used to read.
- Deletes the 61 wire/assign nodes that are dead only because of the cut. These are the four RD_ADDR chains and the four lane procmux/rowword chains, restricted to the backward cone of the cut. Pre-existing dead logic elsewhere stays byte-identical.
- Instantiates `ot_t7_land_capture_candidate`, byte-identical to the child proved in `s81_T7_LAND_native_candidate_1102`. The child gets:
  - the helper's own WR_ADDR/WR_DATA/WR_EN expressions, copied verbatim;
  - `driver_rc_Q`;
  - the parent's existing per-lane wires: valid 558/597/636/675, win 580/619/658/697, need 567/606/645/684 and scale 583/622/661/700.

The top header is unchanged, and every other line is identical and in the same order.

**Proof obligations the transform checks** (it refuses otherwise):
- The land port identity.
- The capture identity.
- The exact 20-field list of the struct.
- The struct has exactly three readers.
- For every lane j:
  - RD_ADDR = 4*(driver_rc_Q-1)+j;
  - the lane word is `valid ? (valid ? (win ? {0,scale,RD[256j+:256]} : need ? {1,0^120,RD[256j+:144]} : {1,0^264}) : x) : 0`;
  - valid and win compare that same row against tjob (`60_Y`) and `wcount`.

This is exactly the composition the native gate models. That gate is the unchanged helper plus verbatim rowword/kc_w, compared on all 1060 bits on every edge, with the production child also compared on every edge. The bound cut is therefore the native-gated child substituted at an identified boundary.

**Guard controls** (`test_transform.py <preimage dir>`, see `guard_controls.json`): all four preimages transform, each removing 65 lines. Five corruptions are refused:
- wrong lane RD slice;
- RD_ADDR lane offset;
- an extra struct reader;
- a win compare on tjob;
- an unapproved hash.

**Outputs:**
- `LAND_only_bound.sv.gz` (after b30a4283) and `PMEM_PVQ_LAND_joint_bound.sv.gz` (after 43dc924c).
- Their patches and transform.json files.

**Cost:** −1060 capture FF, +1280 LVT FF, +40 metadata FF, so +260 FF. Also +12 256x256 macro clocks, 0 reset loads, 0 cycles.

**Held:**
- Not applied to a manifest, kit or recipe.
- No full-T7 lockstep simulation yet (the child substitution is covered by the native gate above).
- 2-state zero-start native scope only.
- Physical macro fit, collision/CE/repair and 833 ps timing are not qualified.
- Source cohort/provider/epoch is not qualified.

**Full-T7 elaboration (ELAB.txt, `full_t7_lint.sh`):** Verilator 5.050 `--lint-only` of the whole `s81p_svc_lo_dsdv_svc_rs__t7` (kit-wave-15-s81b file list, SYNTHESIS defines) with the T7 bound swapped for LAND-only (b30a4283) and for PMEM+PVQ+LAND joint (43dc924c): both exit 0, 0 errors. The 6 warnings in each run are the same set, all in existing bind_ev2 glue / fdiv source; none are in the child or the cut lines. intel2 ot-run 96 GB unit oth-ubuntu-3336031-1793676354, peak RSS 36.5 GB.
