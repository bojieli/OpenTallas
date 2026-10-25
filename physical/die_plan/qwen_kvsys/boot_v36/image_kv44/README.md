# image_kv44: KV boot image on the kv44 bound top (TOK-QK, 2026-10-25)

Recipe (`RECIPE`): `kv_boot_image.sh` on `claude/kv-bind-1024r@1de24d72a` `bind/bound_kv44` with the pair image of the
kv44 dcal tile (KV-R4: `results/rtl/qwen_rom_pair_candidate_1024/d2d_cal_image.svh`, MU+RoPE emb1627 R16, HEAD_PREP 12;
recompiled here bit-exact, sha256 fdd258d4). Status COMPILED_NOT_QUALIFIED (as image_kv41: LOGICAL_ONLY retirement).
`manifest.json` has the sha256 of every input and output.

Checks: DQ_CHECK PASS against the bind's `kv44/tables/vport_dq_pads_kv44.json` (RL 64, RT of all 16 vports 31/32, DQ after
the bind's 810 W pad flops; no extra W pad needed). PV_CHECK FAIL 25 is against the v36 entry table, which still carries
RL 67 / RT 30-31 (image_kv41 had FAIL 17 against it).

## Difference vs image_kv41 (13 targets, same word counts)

| target | words differ | cause |
|---|---|---|
| 0, 2, 4, 5, 12, 13 | 0 | - |
| 1 layer programme | 133 / 327 | pair profile (stage-1 roots +1030..+2247 edges: emb window 595 -> 1627, token period 258,048 -> 293,376) and bind depths (V RL 63 -> 64, D_RL 44 -> 45, V lead 25 -> 24, attention P0/P1 +1, PV_START -1) |
| 3 ownership | 2 / 4 | pair profile: quiet / token cycles 249,921 / 254,386 -> 284,638 / 290,059 |
| 6..9 controller calendars | 96 / 1024 each | bind depths: V RD reservations and V command template +1 edge (v_first 951 -> 952, RL 64) on all 128 PCs |
| 11 link cfg | 13 / 66 | pair profile: K calendar of the pair1024 image (TX entry 4; RX entries 5..11 move one slot for the HEAD_PREP kind-12 record; TX / RX admission-segment bases 9/10 -> 10/11) |

Separated with two extra compiles: kv44 depths on the kv41 ew595 profile change only targets 1 (36 words) and 6..9;
the kv41 bind on the pair profile changes only targets 1 (139 words), 3 (2) and 11 (13). No target changes for any
other reason (no code drift: the same tool reproduces image_kv41 bit-exact).

## Owner decision 14 (hbm_duty.json)

The calendars are compiled on static_kv_calendar.HBM_PS = 1024 ps (controller edge) with the core at 833.334 ps.
Per PC: 512 columns + 4 template commands a layer; RD shape K 8 on / 2 off (0.800 / edge), V 8 on / 3 off (0.727).
Per 833-ps die cycle (same wall time): shape 0.651, in-burst 0.814, RD-span mean 0.353, layer mean 0.075 -> sustained
column duty 0.651 <= 0.73 PASS. What-if with the controller on the die clock (`hbm_duty.py --hbm-ps 833.334`): the
compile STOPS in landing_cal_golden.pacing ("put offsets are not the regular paced form: p0 8 gap 3"), and the K shape
would be 0.800 / cycle > 0.73; the KV calendar compiler still models a 1024-ps hck.
