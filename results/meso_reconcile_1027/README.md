# MESO-RECONCILE-1: one count-aligned crossing package (start convention, bind, wrapper, die STA rows, TOK)

Lane MESO-RECONCILE-1 (COORD 10-27 21:55 ruling (1)-(4) on MESO-COUNT-2 / MESO-INTEG-1).
Base: main 1a2aa908a6 + claude/meso-integ-1027@4526d42d70 + claude/meso-count-2-1027@0af33ccde0.
The count-aligned form stays OPT-IN. The old ring stays the default.

## 1. Start-offset conventions: the same quantity, counted from different reference edges

Origin a_v = the first edge at which region v's readers see their start high. The child origin
`ot_dp_landing_origin` syncs the parent's start. That start is a REGISTERED signal, forwarded beside the tree port's bus.

| lane | step a_child - a_parent | reference edge |
|---|---|---|
| MESO-COUNT-2 | PAD + 2 + J(d), J = -floor((d - off)/T), off = 0 rise / T/2 fall | 3 sync flops + PAD + J from the parent's start LAUNCH edge a_p - 1 |
| MESO-INTEG-1 | m + 1 + PAD, m = min integer with d + mT >= s, s = T rise / 1.5T fall | from the parent ORIGIN a_p (LAUNCH = 1) |

Proof: m = ceil((T + off - d)/T) = 1 + ceil((off - d)/T) = 1 - floor((d - off)/T) = 1 + J(d). This uses ceil(-x) = -floor(x)
for every real x. So m + 1 + PAD = PAD + 2 + J(d) identically, at every phase and both edges.

- **Unit test:** `test_two_start_conventions_are_one_quantity` checks the identity at T/64 steps over +-4T, exact
  boundaries included, rise and fall, PAD 0..3.
- **Per die:** `count_align_bind.bind()` re-derives every tree step from both formulas and from the plan's
  `origin_cycles`. It refuses any difference. HEAD3 has 325 tree edges and KV 159; all are equal.
- **What did differ:** only the tree crossing's RTL K, which is a free choice.
  - MESO-INTEG-1 fixed K_tree = -1 - PAD + q, which puts the lag in [s, s+T) + qT.
  - MESO-COUNT-2 takes K = K_eff - n0, where K_eff is the smallest count that keeps the derated lag >= 0.5T + ap. This
    is the same rule as for every other crossing.
  - With the same origins, the plan's K is equal to MESO-INTEG-1's or one count lower, never higher:
    - HEAD3: 283 equal / 42 lower.
    - KV: 48 equal / 111 lower.
  - Where it is lower, that tree crossing gets one cycle less latency, and its lag stays inside the window.
- **ONE convention adopted:** MESO-COUNT-2's plan (directed start tree, PAD+2+J, K from the derated lag). Its emitted
  fields are the only source:
  - `crossings[].rtl{K, DEPTH}` and `lat_cycles`
  - `regions[].origin_cycles` and `start_from{parent, port, edge, rtl{PAD, EDGE_FALL}}`
  - `count_align_bind.py` (schema v2) consumes the plan document and never re-derives K.

### Evidence (CHECKED-own runs)

**RTL loop bench** (`results/meso_integ_1027/bench`, MESO-INTEG-1 die wiring: root, origins, registered forwarded start,
CA rings):
- Setup: 5 regions, 11 crossings, 7 fundamental loops. One FALL-edge origin (region e) is now exercised.
- Each run: 200 chips with random region phases inside the derated d and random raw-reset release.
- All four runs below: lint clean, 0 bad chips.

| variant | PAD 0 | PAD 2 |
|---|---|---|
| plan params (the adopted convention; tree ae K = -2, latency 2) | 782,383 word checks | 776,383 word checks |
| MESO-INTEG-1 fixed tree K (ae K = -1, latency 3) | 782,383 word checks | 776,383 word checks |

Logs: `loop_bench_{plan,integ}_pad{0,2}.log`.

**Monte-Carlo** on the emitted HEAD3/KV parameters:
- MESO-COUNT-2's `mc_check` (3000 chips): 0 violations on both dies.
- `count_align_bind.verify` (2000 chips; MESO-INTEG-1 sync physics with a metastable sample resolved both ways inside
  +-26.5 ps): 0 violations. It gives the same worst margins as the plan:

| die | low | high |
|---|---|---|
| HEAD3 | 126.2 ps | 885.1 ps |
| KV | 105.1 ps | 162.9 ps |

- Identity K + 1 + a_dst - a_src = sched_lat: 0 errors.
- Every fundamental loop sum(sched_lat) = sum(K+1): 0 errors (HEAD 102 loops, KV 3756 loops).
- The emitted RTL K/DEPTH/latency are byte-identical to MESO-COUNT-2's committed `results/meso_count_1027/*_ca2_w0.05.json`
  (compared on all 427 / 3915 crossings).

## 2. Wrapper: GUARD_HI = DEPTH default, ready-timeout fault

`rtl/common/ot_dp_clk_landing_ca.sv` (wrapper only; the ring is unchanged):
- **GUARD_HI:** the default is now `DEPTH`. It was 4, which is wrong at D8 (MESO-COUNT-2 finding).
- **TIMEOUT (new parameter):** if the crossing is not armed TIMEOUT receiver cycles after `rst_n` release, it raises
  the sticky fault on the same fault port. TIMEOUT = 0 turns this off.
- **TIMEOUT default:** max(K,0) + ARM + 2*DEPTH + 8. That is 30 cycles at D4/K2 and 46 at D8/K2.
  - Why it is safe: in the window, word 0 is consumed at receiver count max(K,0) and the crossing is armed by
    max(K,0) + ARM + 2. That leaves 2*DEPTH + 6 counts of slack.
  - Elaboration stops with `$fatal` if 0 < TIMEOUT < max(K,0) + ARM + 3.
- **Effect:** a lag below the window used to stay silently !ready. It now faults.
- **Mutant:** `OT_MESO_CA_MUTANT_NO_TIMEOUT`.
- `clock_landings.py` emits `#(.W, .DEPTH, .K)`, so every die instance gets GUARD_HI = DEPTH and the default TIMEOUT.

**Formal** (`rtl/test/meso/formal_ca/fv_ca2*`, `fv_ca2_results.txt` MESO-RECONCILE-1 section, logs in
`logs_reconcile/`): same abc k-induction flow, W=1, K=2.

| proof | D4 | D8 |
|---|---|---|
| A_ALL (safe + no-fault incl. timeout + closed + 21 helpers, 3 of them new on the timeout counter, proven not assumed): PROVEN unbounded | 120/120 | 184/184 |
| new A_TMO (outside the window, fault IS raised by TIMEOUT+3): PROVEN unbounded | 48/48 | 48/48 |

Mutants caught (failing frame, D4 / D8):
- K: 3 / 3
- FREERUN: 8 / 8
- NO_GUARD: 138 / 202
- NO_TAG: 195 / 323
- NO_TIMEOUT: 267 / 395

Simulation:
- Verilator 1-ps lag sweep (K {-2,1,2,5} x D {4,8}): clean window [0.502, DEPTH-0.499]T is unchanged.
  - 0 silent-wrong.
  - 0 out-of-window lags without a fault. The NO_TIMEOUT mutant leaves 7,498 at D4/K2.
- Lint -Wall is clean.
- Loop bench re-run on the new RTL (PAD 0/2): 0 bad chips (`loop_bench_plan_pad*_tmo.log`).

Not re-run: the full-anyconst BMC and the tag-range samples. K != 2 and W > 1 are still covered only by the
symmetry / data-independence argument (UNCHECKED, as COORD 21:55).

## 3. die_sta_related --count-align rows (main shared model, opt-in; unit tests only, no die proof run yet)

The bind's L_lo/L_hi are the plan's TRUE derated lag bounds: wander included, no aperture. The STA re-derives d from its
own derated arrivals and shifts L by (d_sta - d_plan). Clean tree crossings are shifted too, because their J is
invariant. Ambiguous tree crossings keep the plan sync window. A crossing without taps fails closed.

| row | rule | where the limit comes from |
|---|---|---|
| lag | margin to the ring guards 0.5T / (DEPTH-0.5)T >= 100 ps on both sides | COORD 20:35/20:48; the plan keeps ap = T/8 |
| slot->read | L_lo - T/2 >= 0. The ring SDC max_delay T/2 - setup on slot -> dsel -> RDREG/r_v_q/r_lap_q then suffices. | fv_ca2 abstraction: a read < T/2 after the write is arbitrary |
| guard | margin_hi >= T/8. The high guard is late by up to the s_w/s_lap -> glo0/ghi0 path, ring SDC max_delay T/8. | NUMBER-CHECK 20:47 |
| start skew | per tree edge, skew = clk->Q(parent origin reg) + start wire - fclk wire, with \|skew\| <= the plan's `start_skew_limit_ps` | plan, per die |

Start-skew details:
- **Clean edges:** the limit is sync_dist - 26.5 ps. The minimum over clean edges is 116.0 ps on HEAD3 and 78.9 ps on
  KV, matching COORD's 116 / 79. The STA's own d (minus the skew) must also stay >= 26.5 ps from the sampling boundary.
- **Ambiguous edges (KV 7):** the limit is the tree crossing's margin - 100 ps. The KV minimum is **52.5 ps**.
- **Wire mismatch:** taken from `--count-align-start-wire {port: [lo, hi]}` on a routed die. Otherwise the model is 0,
  because the start pin sits at the bus point (`model-coroute`).
- **Margin definition:** COORD 20:35 can be read as ">= 100 ps inside the ap-inset window". MESO-INTEG-1's first STA
  version used that reading, which is 204 ps from the guard. This version gates at 100 ps to the guard, as the plan,
  MC, NUMBER-CHECK and COORD 20:48 do (HEAD 126.2/173.6, KV worst 105.1 accepted as 0 FAIL).

## 4. HEAD3 / KV crossing cycles and TOK with the reconciled params (UNCHECKED, own tools)

Crossing cycles:

| | HEAD3 (LAND-HEAD-3 sfbR) | KV (lpo 304c20fb8d) |
|---|---|---|
| crossings D4 / D8 / FAIL | 427 / 0 / 0 | 3392 / 523 / 0 |
| sched_lat hist | {2:256, 3:171} | {2:2676, 3:763, 4:382, 5:94} |
| total crossing cycles: reconciled / MESO-INTEG-1 / old ring | **1025** / 1064 / 1281 | **9639** / 9956 / 11745 |
| tree edges clean / fall, max tree depth | 325 of 325 / 43, 27 | 152 of 159 / 138, 14 |
| K range, max origin count | [-2, 63], 70 | [-25, 28], 41 |
| worst margin low / high (to the guards) | 126.2 / 885.1 ps | 105.1 / 162.9 ps |

TOK:
- **HEAD** (`head_tok.json`, shared `fallback_land.head_pass`, plan fb1_lat, part granularity):
  - Per head pass: +171 (old ring) -> +139 (MESO-INTEG-1) -> **+136** (reconciled).
  - Head pass 37 crossings: 111 -> 88 cycles. Gather round trip: 60 -> 48.
  - 9,418 cycles/token against the 10,357 window, slack 939. The base 9,282 is from LAND-HEAD 10-27.
- **KV** (`kv_tok.json`, MESO-INTEG-1 `kv_ca_price.py` on the LAND-KV-1 v39r lane-class record):
  - Added cycles: 2499 -> **2089** (MESO-INTEG-1: 2344).
  - Per request: 66 -> 55. Embed: 123 -> 109.
  - Throughput: **4763.2 -> 4771.0 tok/s** (MESO-INTEG-1: 4766.2).
  - 185 lanes are above 3 cycles per crossing (up to 5).
  - The interior families (vport/pv/ahub/seq/acal) are unpriced, as in the source.

## Files
- `tools/die_plan/count_align_plan.py`: MESO-COUNT-2, plus `start_skew_limit_ps` per tree edge, plus `DSU` kept for
  locality.py.
- `tools/die_plan/count_align_bind.py`: v2, plus 9 tests.
- `tools/die_plan/die_sta_related.py`: rows, plus 2 tests replacing MESO-INTEG-1's.
- `tools/die_plan/test_locality.py`: HEAD pin updated from MESO-COUNT-1's 104.1 / {2:349, 3:78} to MESO-COUNT-2's
  126.2 / {2:256, 3:171}. The `results/locality_1027` v3 numbers were made with the MESO-COUNT-1 plan; re-run them.
- `results/meso_reconcile_1027/{head3,kv}_{plan,bind}.json`, `*.summary.txt`, `*_cases.tsv`, `head_tok.{py,json}`,
  `kv_tok.json`, `loop_bench_*.log`.
- MESO-INTEG-1's `results/meso_integ_1027/bind/*` are kept as history (fixed tree K). They are superseded.

## MESO-RECONCILE-2 (2026-10-27 23:xx PDT): per-edge PAD, KV ca-origin relay, SS row, spice clock cal, main RM86

Base: this branch (MESO-RECONCILE-1 cc2a507386) + main 810b714798 (RM86) + DIE-KV-3 ca-origin 69d1ba8933.

**Per-start-tree-edge PAD** (COORD 22:53 HEAD (b)): `count_align_plan.py --edge-pad PORT_OR_REGION=N` (N >= --pad).
The child origin (and its subtree) moves N - PAD counts later. The tree crossing's RTL K is held, so its lag grows by
(N - PAD) T and its latency by N - PAD. Every other crossing's K is re-chosen against the new origins; the plan emits
`start_from.rtl.PAD` per edge and the bind consumes it. The identity PAD_e + 2 + J == m + 1 + PAD_e is checked per edge.
- HEAD part map (DIE-HEAD-3 sfb250c landed_ocv, x1.05, `head_part/`): 6 chW*_t__2 tree edges (child regions tW{0..5}b10) PAD 1.
  chW*_t__2 margin_lo 208.1 -> 1041.1 ps, latency 2 -> 3 (+6 cycles total, 1025 -> 1027 sched_lat with the part map's
  re-chosen K). Die worst lo/hi 134.3 / 967.3 ps (sp_b3__0), unchanged. NOTE: with MESO-COUNT-2 K (derated lag) these
  edges already have 208.1 ps at PAD 0 (the 104.1 was the MESO-COUNT-1 d150 number), so PAD 1 is margin, not a fix.
- MC (count_align_plan mc_check, 3000 chips): 0 violations. Bind verify (2000 chips, metastable both ways): 0
  violations, 0 identity/loop errors (102 loops). The bind re-run after the merges is byte-identical (report excluded).
- Loop bench (RTL, 200 chips, lint clean, 0 bad chips): single PAD0 782,383 checks; single EDGE_PAD b=1,e=2 780,783;
  PAD2+edge 774,983 (MESO-RECONCILE-1 worktree log).

**DIE-KV-3 ca-origin (69d1ba8933) ported onto the plan-param bind v2**: `bind(plan, parts=)` / `--parts table|ocv`:
one origin partition per region, relay partitions start origin + 2 (ot_dp_landing_relay x2), tree K = plan K, non-tree
K in partition frames, sched_lat unchanged; loops over the partition tree; relay-aware start-up sim; annotate_table
writes parts/roles; clock_landing_plan keeps main's intra-region monitor AND the relay pins/ports.
- Loop bench multi graph (17 crossings, 3 relays): 200 chips 1,203,619 checks 0 bad; with EDGE_PAD c=1 1,201,419, 0 bad;
  mutant_noshift 20/20 chips bad (caught). Unit mutant: identity + loop errors (a 2-count K error can stay inside the
  D4 window, so the sim window alone does not catch it; the RTL bench does).
- KV L128 (DIE-KV-3 inputs, sha b37d5307/3ea38080; `kv_l128/`): x1.05: 3595 crossings D4/D8 3442/153, 32 relays,
  3468 loops 0 errors, 2000 chips 0 violations, worst 107.1 / 141.0 ps; x1.00: D4/D8 3490/105, 109.0 / 127.5 ps.
  sched_lat total 9399 (x1.05) / 9259 (x1.00). (UNCHECKED, own run.) Supersedes `results/meso_integ_1027/caorigin/kv_l128_bind.json` (v1 bind).

**die_sta_related**:
- `--count-align` SS INFO row (`count_aligned_info.SS`, gate `ss_INFO`, never gates per METHODOLOGY 6.1): no die proof
  has tap_arrivals_SS.json, so TT taps and clk->Q x `--count-align-ss-scale` (1.27, ASAP7 logic SS/TT from uarch_model;
  clock scaling alike UNCHECKED). A proof with real SS taps runs `--corner SS`.
- `--clock-cal spice` (METHODOLOGY 12.15 b): clock arrivals and CPPR node ranges x1.0485 TT / x1.0552 FF (SS uses TT)
  before every class and the --count-align rows. Opt-in here; flipping the default is a ROOT-MERGE/COORD call.

**Not done: 12.15 a count straps (K/PAD as strap_* pins).** Estimate (before build): RTL ring `strap_kr[TW-1:0]` input
replacing the K localparam (KSTRAP param; TIMEOUT from a per-type KMAX), origin `strap_pad`/`strap_efall` with a PAD_MAX
shift chain + mux after the 3rd sync flop (no mux before the first flop); clock_landings signature without K/PAD/EDGE_FALL,
DEPTH = per-type max, per-instance strap values (KM = K mod 2^TW at the type DEPTH) in the bind manifest; straps.py
declaration + kit false_path + TIEHI/TIELO; fv_ca2 re-run with the strap tied (same proof) + LEC per used constant set.
~3-4 h for one lane; RTL first (it is a blocker for the kits, not for die STA).
