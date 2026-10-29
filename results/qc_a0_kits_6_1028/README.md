# QC-A0-KITS-6 (2026-10-28): A0 parent kit generator + child collect + estimate

Goal: signed views for qfd_tile_nk_a0c (720 die taps) and qfd_tile_nl_a0c (48 taps). A0 flat is 677.7k cells, above the 400k OpenROAD cap. So the A0 kit is a COMPOSITION: parent glue plus hard children (NK: 10 romleaf + 8 rawleaf + 1 node; NL: 10 + 8).

## 1. Child collect (CHECKED: autopilot records, signoff.json, log mtimes on intel2)

| child (master) | AP | submit | signoff.json | verdict | TT setup | FF hold | insertion TT / FF (frame 250 / 202.5 +-40) | routed LEC | rebuild owner |
|---|---|---|---|---|---|---|---|---|---|
| romleaf a0k5 (ot_qwen_tile_romleaf) | 1662a1bff39e | 08:53 | 09:05 (fresh) | NOT SIGNED, NEAR-MISS: DRV TT slew 23 / FF 5 | +155.99 | +3.41 | 287.5 / 228.0 (in band, +37.5 / +25.5 high) | not run (run data deleted by the autopilot) | QC-A0-KITS lane: slew root cause first (ROM rd_out[126..265] E-edge nets, GEOM-46), then re-kit under seam_hold |
| rawleaf a0k3 (ot_qwen_tile_lsl_rawfault_m3) | 70e33ab64fa5 | 07:53 | 15:32 (fresh) | NOT SIGNED, NEAR-MISS: FF hold -19.04 / 392 ep (vclk overlay in_min -40; kit SDC +8.09) | +95.6 | -19.04 | 253.0 / 197.8 | not run (data deleted) | QC-A0-KITS lane: re-kit under the seam_hold IO contract (sender 25 / seam 25) once die-qc22 --seam-hold is on main |
| node a0k6 (ot_qwen_tile_node, pin interleave) | db14fa47fb37 | -- | 16:00 | NOT SIGNED, NEAR-MISS: FF hold -24.56 / 896 ep (input-port seam hold) | +25.65 | -24.56 | 255.5 / 205.3 | not run | DIE-QC-23: a0k6s AP 7d28e91ad84d (seam_hold) SUBMITTED 19:23, running |
| node a0k3 / a0k6m | 0a4950716786 / afe7e72b8696 | -- | -- | STRUCTURAL (superseded by a0k6 / a0k6s) | | | | | -- |

So 0 of 3 child masters are signed. The parent kit cannot be built for real yet: the generator refuses it (section 3).

## 2. Estimate before build (one page)

All numbers are CHECKED (my own script on the inputs named here) unless marked UNCHECKED.

* **Parent kit size.** Parent synthesis with the children blackboxed is 64,205 cells / 16,592 FF (NK) and 61,550 (NL), from the QC-CORES CHECKED count. After default CTS it is 86,912 / 79,429 (QC-A0-KITS-3 trial). That is 4.6x below the 400k cap. The largest child is the rawleaf at 58,386 cells.
* **Child placement in the A0 outline (457.92 x 1157.76 = 530,161 um2).** These are the Codex fixture at_exact sites (the same sites as the QC-A0-KITS-3 trial and the DIE-QC-14..17 trunks).
  * NK: 19 children, 340,440 um2 (64.2 %), 0 overlaps, all inside the outline. The romleaf is 172.8 x 110.16 (two columns of 5, at x 22.464 MY / 262.656 R0). The rawleaf is 115.344 x 140.4 (3 columns, y 673.9 / 834.4 / 994.9). The node is 47.52 x 432, MY at (394.416, 688.656).
  * NL: 18 children, 319,911 um2 (60.3 %).
  * Glue gets 189.7k um2 (NK). The glue cell area is about 64k x ~0.12 um2, roughly 7.7k um2 or 4 % of the free area (UNCHECKED). Area is not the risk; wire length and the trunk are.
* **Child boundary pins.** From the fixture LEFs: NK has 11,933 (romleaf 530 x 10, rawleaf 508 x 8, node 2,569) and NL has 9,364.
  * Track supply on one 140.4-um rawleaf edge is about 2,900 M4 tracks per layer, against 508 pins (UNCHECKED). The parent routes M2-M7 over the children, whose OBS is <= M5, as in the trial.
* **Trunk.** These are the DIE-QC-17 routed trunks that the COORD 14:21 ruling accepted at the die gate.
  * NK t5: OCV-incl spread 62.3 TT / 62.0 FF, insertion 716 TT / 623 FF.
  * NL b5: 60.8 / 58.9, insertion 711 / 622.
  * Both assume every child at the 250 / 202.5 contract. Measured child insertion is romleaf 287.5 / 228.0, rawleaf 253.0 / 197.8, node 255.5 / 205.3. So with today's children the romleaf sits about +34 TT / +30 FF late against the rawleaf. That is inside +-40 per child, but it is skew at the parent.
  * Per 12.3 v5.0 the trunk taps each child early by its own signed insertion, so the trunk is re-balanced with the SIGNED child views, not with the contract.
* **Parent-glue hold under the seam_hold contract (sender 25 / seam 25).** The contract binds the CHILD kits' sign-off frame (receiver input min = sender_ps - seam_ps = 0 at the child vclk). Inside the parent kit the child seams are timed with the children's own ETMs (real arrivals), so the contract does not double count.
  * Worst parent-to-child hold, assuming early launch at the glue and late capture in the child at the routed OCV spread of 62 FF: clk->Q ~22 + min wire ~5 - 25 unc - 62 = **about -60 ps worst** (UNCHECKED).
  * Median skew is about 0-30, so most bits are positive. The repair needs about 2-4 hold buffers on the worst paths. With about 20 % of the 11.9k boundary bits needing about 2 buffers each, that is ~4.8k buffers and ~0.5k um2, under 0.3 % of the glue area (UNCHECKED). This is far below the 5 % ASK threshold.
  * Child-to-parent paths are safe by contract: the sender out-min is 25.

## 3. Generator: gen_core_kit_qc.py, opt-in recipe key `hard_children`

The kit is a macro-COMPOSED core. The key is absent from every existing recipe, so the kit bytes are unchanged (section 4).

* The existing rule stays: a child must be SIGNED first. A child view is the export_view.py / autopilot layout:
  * `<m>.lef`, `<m>_tt.lib`, `<m>_ff.lib`;
  * `provenance.json` with views_status `signoff` and a verdict that starts with SIGNED;
  * `gates.json` with view_complete true;
  * a LEF that defines `MACRO <m>`.
* Every unsigned child is named in ONE refusal (fail closed, no trial bypass).
* Children are blackboxed by their `(* blackbox *)` module in the kit sources. This is checked; a missing blackbox refuses the kit.
* Children are placed FIRM at the planned lower-left site by exact hierarchical instance name, one match required (the gen_core_kit_kv --hard-children form). A Yosys `genblkN.` scope between name segments is tolerated, because the node elaborates as `genblk5.g_ndh.u_node`.
* The plan is checked: unique instances, a view per master, R0/MY/MX/R180 only, inside the core area, no overlaps.
* PDN uses the KV hard-children form (M6 straps, children M5 -> M6).
* Recipe `max_routing_layer` (default M5) and recipe `pins_file` without `lef` (plan pin table + plan_pins_contract) are also opt-in.

New A0 parent inputs (die-local QC, built by `build_parent_inputs.py` with sha256 in `cores/a0/parent/inputs.json`):

* `cores/a0/parent/{nk,nl}/spec.json`: the a0ck sources, with lsl_fp1_bb replaced by the Codex native LSL fault-cut wrapper `rtl/ot_qwen_tile_lsl_rawcut.v`. Its sha is 1bac053a, the same as the 64,205-cell parent synth input. It equals codex/qc-a0-2157@b7da9afaa native_wrapper.v with rawleaf_bb.v inserted.
* `cores/a0/parent/{nk,nl}_children.json` (fixture sites).
* `cores/a0/parent/a0_{nk,nl}_pins_dir.json`: the plan pin geometry unchanged, with dir taken from the RTL top ports.
* `cores/a0_slices/qfd_tile_n{k,l}_a0c.json`: the ONE centre clock entry ck M5 (228.972, 578.88) of the DIE-QC-11 contract.
* recipes_a0.json keys `qfd_tile_nk_a0c` / `qfd_tile_nl_a0c`: the vclk insertion is the DIE-QC-17 routed trunk 716/623 and 711/622, M7, util 0.45.

Command: `gen_core_kit_qc.py --module qfd_tile_nk_a0c --recipes ../a0/recipes_a0.json --master-slice ../a0_slices`.

* Real views today: REFUSED, "19 of 19 hard children are not SIGNED views". It names rawfault_m3 x8 (no view at all), node x1 and romleaf x10 (old provenance-less views). NL refuses 18 of 18.
* MECHANICS TEST: a tmp dir only, never enqueued, now deleted. It uses the Codex placement-RC fixture LEF/LIB with a test provenance. Both kits generate:
  * NK: 2,584 pins, ck moved to the centre M5 by the slice, 19 children placed by name (the macro_place.tcl `OT_HARD_CHILDREN placed 19`).
  * NL: 1,042 pins, 18 children.

## 4. Tests

* test_gen_core_kit_qc_hard_children.py: 10 PASS.
* test_gen_core_kit_qc.py: 12 PASS.
* Default byte-identity, CHECKED: main's generator vs this one on every recipes.json module. 5 kits give `diff -r` empty; btab and prog give the same refusal in both.

## 5. Still open before a parent kit can go to the autopilot

1. Signed child views (section 1).
2. The plan trunk (tools/die_plan/parent_trunk_dme.py) is wired as the kit CTS hook. Today the recipe has insertion_balance off and would run default TritonCTS, which is not the accepted form.
3. A0 boundary seam_hold contract (die-qc22 --seam-hold) on main.
4. Composition LEC: the parent with blackboxed children vs the flat RTL (the nc adder / keep hook), as QC-CORES listed.
5. The OWNERS / autopilot type for qfd_tile_n{k,l}_a0c.
