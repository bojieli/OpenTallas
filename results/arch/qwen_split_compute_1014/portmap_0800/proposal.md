# Qwen compute die: per-side port mapping (option b), priced

Helper Q-PORTMAP, stream Q-COMPUTE-DIE, 2026-10-16. No RTL built. The numbers are geometric stage estimates (`price.py`, the pm_h_cycle_price method: one stage per 490 µm plus a register hop), taken from the r2h5 bus graph (`numbers.json`). They are not qualified.

## 1. What the 6,704 b k <-> k_f1 link is

`rtl/qwen_split/qfd_port_tiles.sv`: `qfd_port_tiles_k` is the band's **slab master**. `_f1` is a plain half. Both halves run the same logic:
- `qfd_slab_word_half` adds root pairs into the level-7 word, 4 x 512 b.
- `qfd_slab_result_half` handles four result groups: scale ROM, post-scale and argmax heads.

The link does **no arithmetic** across halves. It only packs and forwards:

| bus | bits | direction | role |
|---|---|---|---|
| pfrag (cw) | 2,050 | E -> W | E level-7 word. k concatenates it as tw[4095:2048], which goes to band lanes |
| slab_rq | 2,213 | E -> W | E result slots. k packs them into rq[4415:2208], which goes to res_ser (one burst capture) |
| slab_am | 52 | E -> W | E argmax head + fault. k packs it into tf, which goes to tt_ctlm |
| slab_tc | 341 | W -> E | tree-controller scale requests, forwarded copy |
| slab_ty | 2,048 | W -> E | band-lane result words for positions 4..7 (E groups' lv_in) |

Sum per pair: 6,704 b. The only check that crosses halves is `align_fault`, an XOR of the two valids.

The real cross-half arithmetic happens in the band lanes (`ot_qfd_band_lanes`):
- Lane l takes positions k = 0..7, where k 0..3 are the W word and k 4..7 the E word.
- L8 pairs (2p, 2p+1) and L9 pairs stay inside one side.
- **L10 (W+E) is the single cross-half add**: 16 FP32 adders per band.

The band-local result frame then pulls the E-derived results at split 8 and 9 into positions 0..3, which are W groups. That is why the E port tile needs ty from the W side.

## 2. Remap (recommended b2): per-side half-band lanes + TP4-form tree top

**Ports.** Each port tile becomes one half module: its own 8 bwords, tc and ty in; cw, rq (2,213 b) and am (52 b) out. The six tiles collapse to **one variant** with BAND/HALF straps. The master registers go away: tc_copy, ty_copy, tw_q, rq_q and tf_q, 13,062 flops per band.

**Band lanes.** Each `qfd_sp_band_lanes` splits into a W half and an E half beside their port groups: 16 lanes, 4 positions each, levels L8 and L9 (`ot_qfd_band_lanes` with GI 4 / NLV 2). Each half sends one L9 word (16 x 32 + valid = 513 b) into the centre.

**Tree top.** The 4 upper leaves (`qfd_band_upper_tp8`) take 6 half-band words in the order (W0, E0, W1, E1, W2, E2):
- Change the parameters only: `ot_qfd_band_upper` NB 6, TCUT 6, LG 12, which gives NU 2. This is the existing TP4 parameterisation.
- Upper level 1 = L10 (Wb+Eb). Level 2 = L11 (band0+band1, band2 held). This is **bit-identical to today's TP8 tree order** (class A).
- FP32 adders move from the band lanes to the upper: net 0.

**Frame (BANDF 2, compiler plus the two `bframe` copies in `ot_qwen_me_spine_h_w12.sv`).**
- Half-band hb = 2b+h, position p = 4hb+k.
- At s <= 9: g = hb·2^(9-s) + k.
- At s >= 10: g = k on hb 0, which is band-0 W slots 0..2.
- The group numbers and word values are the same as BANDF 1. Only the port position of the s = 8, 9 and 10 results moves.
- The compiler regenerates the per-(b,h,g,c) scale-ROM images and the tc addresses.

**Results.** `qfd_res_ser_static` splits into W and E halves of 4 slots each. W emits at 8b+0..3 and E at 8b+4..7, so the calendar is unchanged and E of the last band carries `end`. The VM result face takes 6 sources that the static calendar keeps disjoint.

**Control.**
- tt_ctlm drives tc to both sides: +1,023 b out, from the centre, not crossing.
- It takes am per side: 52 b x 6, the same bits as tf.
- Lockstep across halves is now the upper's existing band-word valid check.

**Remaining traffic.**
- West <-> east across the centre: **0 b**.
- Into the centre from each side: 3 x (513 L9 + 551 rs + 341 tc + 52 am) = 4,371 b. The W side also gets the existing 1,538 b tt_ty return from the leaves.
- Option (a) for comparison: the 3 x 6,704 b pass through the VM/SU column, plus the same side-to-centre buses.

## 3. Cost and comparison

Stages per ME op cover the reduction path (bword -> L7 -> lanes -> tree top) plus the result path (tree top -> port -> res_ser). There are 217 ME ops per AR token and a base of 249,431 cycles per token.

| option | cross-centre bits | cross-centre kbit·mm | port-subsystem kbit·mm | stages/op | vs today | vs (a), cycles/AR token |
|---|---|---|---|---|---|---|
| today (r2h5, both tiles W of VM) | 12,336 (E bwords) | 71.1 | 368.4 | 75 | 0 | |
| (a) split each pair across centre | 20,112 | 136.0 | 408.8 | 95 | +20 | 0 |
| b0 remap only (bands 0/2 one-sided by ROM placement, band 1 still split; no RTL) | 6,704 | 45.3 | ~339 | 95 | +20 | 0 (band 1 sets the max) |
| b1 half lanes, L10 in W half (E L9 word crosses) | 1,539 | 10.2 | 303.1 | 67 | -8 | -6,076 |
| **b2 half lanes + upper NB 6** | **0** | **0** | **311.7** | **64** | **-11** | **-6,727 (-2.7%)** |

Why (a) is slow: the E level-7 word still crosses the centre, so the reduction path is no better than today's 18 mm E bwords. On top of that, the E result path adds ty out and rq back across 6.76 mm, about 2 x 14 stages.

Why b2 is fast: each side's bword maximum drops to about 12.9 mm. Only the L9 words travel into the centre, about 3.3 mm. There are no logic edges added: the same 4 adder levels; L10 just moves into the upper.

**b2 area:**
- Logic: about -30k flops, roughly -0.02 mm².
- Outline: +0.3 to +0.6 mm², from splitting the band-lane slots (1.0 mm²) and res_ser slots (0.40 mm²) into W and E halves.
- New hard-view pins: VM +1,653 (3 x 551 rs) and tt_ctlm +1,023 (tc copies).

**RTL files touched (b2):**
- `qfd_port_tiles.sv`: one half module.
- `ot_qwen_band_lanes_slots.sv` and `ot_qfd_band_lanes.sv`: 4-position, 2-level parameter; new hardened half-lane leaf.
- `qfd_band_upper_tp8.sv`: parameters only.
- `ot_qwen_me_spine_h_w12.sv`: BANDF 2 frame, used by both the controller and the port element.
- `qfd_res_ser_static.sv` / `qfd_sp_res_train_par.sv`: 4-slot half.
- VM result face: 6 sources.
- `qfd_tt_ctlm_static_s`: tc x2, am x6.
- `qfd_native_compute_join_961*.sv`.
- Generators: `tools/qwen_rom_fulldie_b3r2.py` (pfrag/slab_* out, tw/ty halved, pword -> 6 half-band words) and `tools/qwen_split/*`.
- Compiler: scale-ROM image and tc addresses.

Everything sits behind BANDF/NB parameters, off by default. The existing MUT negatives (level 9 pairing, band index) carry over.

## 4. Recommendation

Adopt **b2**. It is exact (same adders, same operand order; only the result-port positions move), and it:
- removes all west <-> east traffic;
- cuts the port-subsystem wiring by about 97 kbit·mm against (a);
- prices about -31 stages per ME op against (a) (-6.7k cycles per AR token, about 2.7%) and -11 against today;
- costs at most +0.6 mm² of outline;
- reuses the proven NB 6 / NU 2 tree top.

Do not choose (a): it is the slowest option (+20 stages per op against today) and the widest centre crossing.

Before RTL, re-price on the relay allocator's stage_of for the owner floorplan; these are geometric stages. After that, build in this order:
1. half lane and frame bench (bit-exact against BANDF 1 per split, including the negatives);
2. upper NB 6;
3. die join.
