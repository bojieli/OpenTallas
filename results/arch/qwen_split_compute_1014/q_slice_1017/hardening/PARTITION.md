# qfd_dv_slice2 partition spec (S-QSLICE, 10-18)

Masters: `qfd_dv_slice2_w` x6 and `qfd_dv_slice2_e` x6 (MY). Both wrap `qfd_dv_slice2`. The RTL is on `claude/q-die11b-1018` af607c367; this branch is `claude/qslice2-hard-1018`.

Slot (dv2f14bn `elements.lef`):
- size 2462.376 x 2591.976 um;
- 17,341 pins;
- W/E faces on M4 at 5.2 pins/um, only over y 40-1217 um (47 % of each face);
- N/S faces on M5 at 3.0 pins/um, in 4 groups of {cw, rs}.

The die abstract is `OT_SPLIT_DV_SLICE_OBS_TOP=5`: the slice owns M1-M5 and 9.6-um pin windows.

## 1. Reached children (default RTL)

| child | count/slice | reached in the default RTL | closed view | reusable as a hard child? |
|---|---|---|---|---|
| `qfd_dv_su8_entries` (SU) | 1 | yes, LT 0 (8 flat `ot_hdc_vstream_lane`, ML 1, TLS 1) + `ot_hdc_vreduce` SW 8 | - | - |
| `ot_hdc_vstream_lane_h` | 0 (8 with SU_LT) | only under LT 1 | qfd_su_lane_h (sp1) | **NO**: the view is ML 15 RD 2. The slice is ML 1 (alignment 14 edges shorter). New leaf: `qfd_dv_lane_h` |
| `ot_hdc_sfu_{exp,rcp,rsq}_t` | 0 (24 with SU_LT) | only under LT 1 | yes (LA4/LM5 = slice config) | yes |
| `qfd_su_vred_entries64` / `ot_hdc_vreduce_tail64` / `_region8` | **0** | NOT reached: `RED_ENTRIES=0`, and the branch needs SW 64 / LV 7 | yes | n/a (the slice reducer is ot_hdc_vreduce SW 8) |
| `qfd_dv_heads` | 1 | yes | - | - |
| `ot_qfd_xs_leaf` | 32 | yes, NCH 4 at defaults | qfd_xs_leaf_w130 | **NO** as built: the view is READ_PIN_PIPE 1 / FILL_PIPE 1, and the slice is 0/0 (HD_W130 opt-in fixes that). Also an M6 leaf (pins M6, RLAYERS M2-M6): child_lint (c) FAILs under any M6-strap cluster, and it is incompatible with an M5 slice |
| `ot_qfd_xs_tap` / `ot_qfd_xhead` x4 | 1 / 4 | yes | qfd_xs_tap (xt10) wraps a different port set (`aw` used, own reset edge) | flat |
| `qfd_dv_vm` | 1 | yes: 10 x 1024x256, 8 x 128x256, 4 x 256x256 SRAM | - | flat + macros |
| `qfd_dv_redstn2`, `qfd_dv_scalar2`, `qfd_dv_stream`, glue | 1 | yes | - | flat |

The element table's "CLOSED children of qfd_dv_slice2" rows (vreduce_tail64/region8, vstream_lane_h, xs_leaf) are **name matches**, not configuration matches. None of these views binds to the current slice RTL.

## 2. Decision needed (coordinator / die lead): slice layer contract

A hardened slice with hard children needs this stack:
- children capped at M5;
- parent straps on M6;
- cluster PG on M7.

That is the ref_tile cluster contract, and the closed lane_t_io cluster even has RLAYERS M2-M7 with pins on M4/M6. The die's `OBS_TOP=5` (die signals on M6/M7 over the slice) forbids it. The two options:
- **(A) Flat M5 slice** (current contract): one leaf, 30 SRAM macros, no hard children, one clock root over 2.46 x 2.59 mm. This is gated now as pathfinding (`qfd_dv_slice2_w`, sw0).
- **(B) Hierarchical slice, OBS M1-M7**: hard children are 8 x `qfd_dv_su_lane` (lane_h + 3 closed SFU) and the heads (32 M5 x-leaves, re-kit owed). The die then routes over slices only on M8/M9; the dv2f14 feedthrough over slices (17 edges) must move to channels.

Recommendation: (B), if the die GRT shows that the seams carry the feedthrough. The flat (A) slice keeps 270k+ flops on one root and puts every chain register 2.4 mm from its face.

## 3. Physical findings that need RTL (both options)

- **Pass-through chains cross the slice in one edge.** `st` (2 x 1088 b), `ch` (1095/1038), `hr` 453, `cmd` 116, `sc`, `ag` and `l9` run from pin register to pin register across 2,462 um (W->E). That is far past the 405-um plan reach, and past the measured repeated 600-750 um.
  - Each chain needs about 4 registered relay stages per slice hop, or the W/E pin groups must be placed so that the in and out ports of a chain sit side by side.
  - The die abstract already stacks them in y 40-1217 on both faces, so the remaining length is the 2.46-mm width.
  - Cost: about +3 edges per slice hop per chain. It is compiler-visible (cycles_dv.py), and the owner must price it.
- **Corridor words.** `cw_n0..3` / `cw_s0..3` (8 x 516 b) leave the xhead output flops directly on the N and S faces, which are 2.59 mm apart. With one head row, at least one of the two needs relay stages (+2-3 edges per x delivery).
- **Slot fill.** Content is about 1.5-2 mm² (macros 0.21, lane tiles 8 x 0.135, x-leaves 0.29, std cells) in a 6.38-mm² slot. The slot is set by the die pitch, not by the content, and the empty area lengthens every chain (owner rule "no empty area on link paths").

## 4. Pin-register wrappers / opt-in RTL (this branch, default off = the benched RTL)

- `qfd_dv_slice2 #(SU_LT, HD_W130)`.
- `SU_LT=1`: su8 `LT=LOFF=RTREE=LTD=1`. Each lane is `qfd_dv_su_lane`, the qfd_su_lane_t_io structure:
  - IREG 1 / OREG 1, one clock, own reset register;
  - children `qfd_dv_lane_h` (ML 1 RD 2 head) and the closed `ot_hdc_sfu_*_t` leaves.
  - The su8 relays follow the ot_hdc_vstream LIREG/LOREG arrangement: answers and read requests take RD-1 stages, so the head's ML + 2 + 2 RD alignment holds.
  - Cost against the flat lanes: read round trip +6 edges, issue +4 / results +4 edges, SFU +4 / sigmoid +8.
- `HD_W130=1`: `qfd_dv_heads_w130` (no parameters; sw_m internal). The leaves take the w130 configuration and the xheads use LEAF_READ_PIN_PIPE 1, FILL_LEAD 5, DX 14, which adds +4 edges per x delivery.
- Hard-child defines: `OT_DV_SLICE_HARD`, `OT_DV_SU_LANE_HARD`, `OT_DV_HEADS_HARD`.

## 5. Kits

| kit | kind | state |
|---|---|---|
| `qfd_dv_lane_h` | leaf M5 | gate `--cts` launched (non-critical, submit if PASS/WARN after the benches) |
| `qfd_dv_su_lane` | cluster (lane_h + 3 closed SFU) | spec only; gate after lane_h closes; needs (B) |
| `qfd_dv_heads_w130` | cluster (32 w130 leaves) | kit generated; the local gate FAILs child_lint (c) on the M6 leaf. Needs an M5 x-leaf re-kit first; not gated |
| `qfd_dv_slice2_w` | flat M5 leaf (A), pins = the die abstract | gate `--cts` launched (CRITICAL: no REVIEW.json, no submit) |

## 6. Benches

`bench_h1.sh` covers:
- lint of both configurations;
- the heads bench at HD_W130 = 1, plus mutants 8 and 9;
- slice2 a..j at SU_LT = 1 / HD_W130 = 1, plus the lane mutants LOFF / TLS / LOREG / IREG.

The fleet logs land at `ot-epyc4:/srv/opentallas-scratch/claude/qslice2-hard/bench_h1/`. Once they finish, commit them as the fail witnesses under `bench_h1/`.

## 7. Hierarchical slice kit (QK-SLICE 10-18, coordinator 0gs(c))

The coordinator chose (B): the slice is a hardened cluster, and the die grants M1-M7 inside its region. The flat-M5 gate is reference only; it hit the 4 h synthesis cap (REMOTE_INCOMPLETE).

`qfd_dv_slice2_wh` (`tools/qwen_dv/slice2_wh_spec.py`) has **one cluster level**: children M5, straps M6, PG M7. The su_lane and heads cluster levels fold into the slice, because a nested cluster would need its own PG on M7, and the M1-M7 grant has no room for that.
- **Hard children:**
  - 8 x (`qfd_dv_lane_h` + closed `ot_hdc_sfu_exp/rcp/rsq_t`), each group 324 x 324 on the 43.2 lattice;
  - 32 x `ot_qfd_xs_leaf` at the heads_w130 relative positions.
- **Macros and soft logic:** 22 VM SRAMs sit in two rows between the lane rows. The glue is soft.
- **Stand-ins (never bindable, `tools/qwen_dv/slice_standin.py`):**
  - lane_h, built from its kit with the measured gate insertion (254 / 209 / 330);
  - xs_leaf, an M5 re-layer of the closed w130 view: the 791 M6 E/W pins move to the nearest M4 track at the same y.
- **Real M5 leaf kit:** `qfd_xs_leaf_w130m5`, the same RTL with E/W pins on M4. `ref_tile.py` now admits literal pin plans that have no M6 pin without an M6 grant.

**Owed:** landed regions. The slice RTL still has one clock port `ck`, so this gate runs one balanced tree over 2.46 mm. The landed form needs:
- per-region `ck_<r>` ports;
- landed crossings (`tools/landed_parent/lp.py`).

lp.py takes only a wires-only parent, so qfd_dv_slice2 must first be split into one core tile (stream, scalar2, redstn2, VM control, su8 glue) plus the lane groups and the heads. That is an RTL restructure. It costs +E+1 edges on every landed net, and the compiler (cycles_dv.py) must price it.

**Bench h3** (Verilator 5.050, with the redstn2 idle fix):
- slice2 SU_LT=1 HD_W130=1: a..j PASS;
- mutants LOFF / TLS / LOREG / IREG: FAIL (committed witnesses in `bench_h3/`);
- lints: PASS;
- **open:** the `run_heads.sh` HD_W130=1 positive bench FAILs 192 / 397,440 checks, all at ref cycle 1623, with identical data words (`go 0/0`). This looks like the bench's end window not extended by the +4-edge w130 delivery offset. It is unverified.
