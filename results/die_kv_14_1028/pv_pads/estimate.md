# DIE-KV-14d: PV column equalisation, estimate before build (METHODOLOGY 12.14b)

2026-10-28, sub-lane DIE-KV-14d of DIE-KV-14. Input: DIE-KV-13 step-5 bind5
(`intel1:/srv/opentallas-scratch2/claude/die-kv-13-1028/bind5`, recipe `recipe_kv13_s5wb.json`). The problem:
`regen_constants` MISMATCH. The bound RTL has TRUNK_D 54 and FLAG_D 58 (as-built); the law gives 62 and 77.

## 1. What the law is (main `tools/die_plan/regen_constants.py` `kv_pv_trunk`)

Per pair side (S = pvw_0, N = pvw_1) and column s (32 per side):
* `dcmd_s = landed - as-built` of `pvw_k__u_ctl.cmd -> pvw_k__u_s<s>_j.join_go`
* `tot_s = landed cmd_s + landed flag_s`, where the flag is `u_s<s>_j.y_valid/fault -> ctl col_valid/col_fault`
* `TRUNK_D = TRUNK_D_asb + max_s dcmd_s`
* `FLAG_D = max_s tot_s - k0 - TRUNK_D`, with `k0 = (cmd + flag)_asb(col 0) - FLAG_D_asb - TRUNK_D_asb` (S 2, N 1)
* The law describes the die only if `dcmd` is uniform, `tot` is uniform, and S == N. Otherwise regen_constants
  reports "PV pads must equalise first".

Why it must hold, from the RTL (`rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tbf.sv`):
* The ctl registers all 32 column flags (`cv_r`) and faults the start when they are not all equal (`cbad`) or when
  `cv_r[0] != out_slot`, where `out_slot = JOIN && wage == COL_CHK + 1` and `COL_CHK = COL_LAT + TRUNK_D + FLAG_D`.
  So every column's flag must arrive in the same cycle, which means `tot` is uniform.
* Each column's banks (`bc`) and its join (`join_go`) take the one command word from the same trunk station. In bind5
  each bank's bc has the same landed depth as its join_go on 512/512 banks [CHECKED]. Uniform `dcmd` keeps the as-built
  command stagger. TRUNK_D also moves the static output age: `k_oa = ... + COL_LAT + TRUNK_D`.

## 2. bind5 measured [CHECKED, probes on bind5 bus_groups]

* dcmd per trunk station: S +7 +6 +3 0 -1 -5 -8 -10 (s0..s7), +8 +7 +4 +1 0 -4 -7 -9 (s8..s15); N the same pattern.
* The landed flag returns collapsed: as-built 58..100 stages, landed 78..5. For example s7 is as-built 100, landed 5.
  So `tot` ranges from 9 to 141.
* The law on bind5 gives TRUNK_D 62 and FLAG_D 77 (the image). With these values only column 0 meets the single check
  slot. Any start would fault: the cv_r all-equal check fails.

## 3. Decision: pads (i), plus the RTL parameters regenerated from the padded bind (ii). (ii) alone is wrong.

* **(ii) alone (only set TRUNK_D/FLAG_D 62/77) is not a fix.** The parameters are one check slot and one trunk depth for
  32 columns. With non-uniform column depths no single value is right: 31 of 32 columns miss COL_CHK.
* **Padding toward the as-built 54/58 is infeasible.** The law needs dcmd = 0 everywhere, but s0/s8 already land
  +7/+8 above as-built, and pads only add stages.
* **Principled fix:** pad the shorter column paths up to the slowest one, using minimum pads that satisfy the law
  exactly:
  * C = max dcmd = **+8**. Every column command (join_go and the 8 bank bc words of that column) lands at as-built + 8.
  * Flag target per side: every column's cmd + flag total equals the largest total after the command pads.
    That is S 142 / N 141, which is the same FLAG_D on both sides.
  * Then the RTL parameters come from the padded bind through the param hook. The hook uses the same law and fails
    closed when the bind is not equalised. The image is regenerated from that same bind, so image and RTL agree by
    construction.
* **Result: TRUNK_D 62, FLAG_D 78 (not 77)** [CHECKED: generator plus regen_constants kv_pv_trunk on bind5 with the table
  applied; status OK, cmd_delta_uniform and flag_uniform true on S and N]. The +1 against the image's 77: column 0
  (dcmd +7) needs one command stage to reach the uniform +8, which adds 1 to the largest total. The current image value
  77 came from an inconsistent bind and is replaced when the image is re-emitted from the padded bind.
  TRUNK_D + FLAG_D = 140 = 112 + 28.

## 4. Cost

| item | value | status |
|---|---|---|
| padded members | 660 (512 bc + 64 join_go + 64 col_valid + 64 col_fault, minus members with 0 pad) | CHECKED |
| command pad stages per column | 0..18 (sum 544 over 64 columns) | CHECKED |
| flag pad stages per column | 0..116 (sum 3,674) | CHECKED |
| pad flops, command (bc is 23 b per bank) | 100,640, in pv_S_k / pv_N_k; largest pv_S_7 / pv_N_7 12,950 each | CHECKED (count) |
| pad flops, flag (2 b per column, in hub_C) | 7,348 | CHECKED (count) |
| total | **107,988 FF** (about 0.03 mm2 at about 0.29 um2/DFF) | count CHECKED, area UNCHECKED |
| shared-entry variant (one tapped line per partition input bit, about 32 b x pad) | about 5k FF | UNCHECKED; bind.py `land_pad_tree` is skipped when `plan_cells` is set (KV), so it needs a shared-tool change |

Notes on the cost:
* The pads are reset-less ot_dp_dly stages on control bits (command / valid / fault). Activity is low; the 23-b bc
  word toggles once per PV step.
* Per-instance pad differences on one partition type go through the OWNER 10-28 KV R8 strap pads
  (`land_r8_strap_pads`, already on in the recipe).
* For comparison, the 10-23 v3.6 PV entry table was 236k FF, and the recipe's pv_calendar_restore candidate was
  +115.6k FF.

## 5. Cycles and token latency

All numbers in this section are UNCHECKED.

* **Output age.** `k_oa` moves with TRUNK_D only: 62 against the as-built 54, so +8 cycles per PV pass. The image
  already carries 62 (KV-13 step-5 image), so the change against the image is 0. Against as-built, 36 layers x 8 = 288
  cycles, about 0.24 us per token, about -0.1 % at 4051 tok/s. This term was already in the image KV-13 estimated.
* **FLAG_D 78 against the image's 77.** This moves only the ctl check slot and the JOIN-to-IDLE return (COL_CHK + 1),
  not the output age. Token effect: 0, as long as the next PV start comes more than COL_CHK + 1 = 140 + COL_LAT cycles
  after JOIN. The compiler's static schedule checks this.
* No added schedule cycles on the V request / return (RL, FIRST_INPUT_AGE, vport RT/DQ are untouched).

## 6. OPEN (not covered by this table; reported to the die owner)

**V words to the banks.** In the as-built design, `V(vport -> bank pv2) - cmd(ctl -> bank bc)` is ONE constant per
vport on every bank it feeds. For example vport_EN_0 is +31 on pvw_0 and +32 on pvw_1 [CHECKED]; that offset is what
the vport DQ/RT absorb.

On bind5 the V landed deltas vary per bank within one vport. After the command pads above, the per-vport spread of
(V landed - as-built - 8) is up to 48 stages for pv2 (32 vport sources, 1,048 members), and up to 11 for the ASTK
response -> bank pe2 (4 sources, 1,030 members) [CHECKED].

Equalising those by sink pads would cost about 1.19M FF (pv2) plus 74k FF (pe2) [CHECKED count], which is not viable
as pads. The regen_constants laws and the kv_boot_v36 prep do not model the V-to-bank leg: pvst / pvp are
INTRA_OR_UNMAPPED in depth_map. Whether the vport output taps (vo_d1..d3) or the bank take logic absorb the per-bank
skew is UNCHECKED. It needs the pair bench (tools/qwen_kv_die/pv_floor_bench.sh on the bound pair) before the B48 token
sim.

## 7. Build check (bind6pv, 2026-10-28 17:28 PDT) [CHECKED]
`intel1:/srv/opentallas-scratch2/claude/die-kv-14-1028/bind6pv` (recipe_kv14_s6, ot-run --mem 48 on intel1): BIND_RC 0,
160 partitions, 2545 crossings, 0 errors; param hook applied TRUNK_D 54->62, FLAG_D 58->78 on pvw_0/pvw_1 __u_ctl (hook did
not raise = every column equalised); regen_constants qwen_kvsys (--peer qc_fresh_v3): TRUNK_D 62 OK, FLAG_D 78 OK,
REGEN_CONSTANTS PASS {OK 40, WARN 2} (the 2 WARN = VPORT_DQ / CFG_FIA, unchanged from bind5). Pair image not re-emitted
here (needs a claude/kv-image-13-1028 worktree; run_bind14d.sh IMG_WT=...).
