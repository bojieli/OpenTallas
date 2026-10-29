# DIE-KV-16: PV V-word landing — estimate before build (METHODOLOGY 12.14b)

Input: DIE-KV-15 bind4 (intel1:/srv/opentallas-scratch2/claude/die-kv-15-1028/bind4, recipe_kv15_b3).

## 1. The rule (from the RTL)
* `ot_qwen_tp8_pv_wide_ctl_tbf_p`: the 8 vport headers (`in_valid`/`in_t`) are checked at ONE age pa
  (`iv_r != pexp_v -> cbad`), and the ctl issues "the command word for the arrival at pa+1" to the banks.
* `ot_qwen_tp8_pv_slice_t`: registers pv2 / pe2 / bc on one edge and takes V on `c_r.take`.
* So for bank b fed by vport p: V must reach b exactly the as-built number of cycles after p's header reached the ctl plus
  the bank's command depth: `VDH(b) = dV(b) - dcmd(b) - dH(p) = 0`, `dX = landed - as-built`.
  The vport launch (boot DQ / W pads / RT) moves V and H together, so NO boot value absorbs VDH != 0.
  This is Codex's KV-P6-PV correction d218a2b989 ("V-D-H shift must be 0"); the DIE-KV-14d column table (cmd + flag
  only) dropped it.
* DIE-KV-15 `v_offset_check` (one `d = dV - dcmd` per vport SOURCE) is necessary, not sufficient: it lets every bank of
  a vport sit one constant off its command, and it treats out_v_lo / out_v_hi (one row register, one edge,
  `{out_v_hi, out_v_lo} <= row`) as two independent sources.
* ASTK response -> pe2: the astk owner launch is free in the PV schedule (KV-P6-PV: external source) -> one
  `e = dpe2 - dcmd` per astk source.

## 2. bind4 measured [CHECKED-own, kv_pv_v_pads.py check on bind4 bus_groups]
* 512 banks, 1048 V members, 1030 pe2 members; 2022 members off the rule.
* V: VDH -16 .. -114 on every vport (V lands 16..114 cycles EARLY against its command); pe2: e spread up to 11 per source.
* As-built V - cmd per vport is one value (+-1 for the walk h = l>>2), confirming the as-built satisfies the rule.

## 3. Options (FF counts CHECKED-own on bind4; area/power UNCHECKED arithmetic)
KV die = 299.5 mm2 (160 partitions, outline 11.08 x 27.04 mm); PV partitions 16 x 3.28 = 52.5 mm2.
Measured-activity power of hg + hgi + pv only (PG-ACTIVITY 10-27: 1.191 / 1.143 / 0.654 W/mm2) = 179.5 W (lower bound
for the die).  FF: 0.29 um2 (ASAP7 DFFHQNx1), ~2 uW at 1.2 GHz incl. clock pin + data toggle (UNCHECKED).

| option | FF | area % die | power % (of >=179.5 W) | notes |
|---|---|---|---|---|
| (a) V pads at the PV partition entry to VDH = 0 (+ pe2 one offset per source); bind shares one ot_dp_dly per (in-lane bit, pad) per partition | 765,784 (V 760,704 + pe2 5,080) shared; 6,159,616 if every bank member had its own | 0.074 % (0.22 mm2; 0.42 % of PV partitions) | <= ~0.85 % (~1.5 W) | max pad 114 stages; restores as-built relative timing -> 0 schedule cycles |
| (a-old) per-source single d (DIE-KV-15 criterion) | 185,344 | 0.018 % | ~0.2 % | NOT sufficient (sect. 1) |
| (b) bank-side count-aligned V buffer released by the command | >= 6.16 M storage bits at exact depth; standard set 8/16 cannot cover 114 (12.16 b(iii)); 128-deep: 512 x 256 x 128 = 16.8 M | >= 8x (a) | lower toggle per bit, but >= 8x bits | new bank RTL (shared rtl/hdc/nearhbm) + LEC |

Decision (COORD ruling 18:59 conditions): (a) <= 3 % die area and (b) is clearly larger -> build (a).
The FF count is 4.5x the DIE-KV-15 168k UNCHECKED figure because the target is VDH = 0, not one offset per source.
