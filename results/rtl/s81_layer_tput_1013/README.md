# S81 per-layer throughput record, 2026-10-13 (second pass)

Owner rule 10-13: DeepSeek S81 ROM throughput is qualified per layer; a structurally safe unit over 1.10x may be
accepted when its measured end-to-end loss is at most 5 % (15 % per design). Prices are the token-path nodes of
`results/arch/token_path_20261009/ds_rom*.json` and are never changed here.

Vehicle: `tb_s81_die_layer` (one DeepSeek-V4.1 layer on the die control plane, real controller, gather / capture,
HC master and a 4-die TP4 collective; SU, svc, select, HC coefficient producers and Engram behavioural at program
duration), Verilator 5.050, 1M token. Regenerate: `run_die_layer.sh`, then `bash results/rtl/s81_layer_tput_1013/regen.sh`
(`tools/s81_ctrl/die_layer_tput.py --run ... --primary phier --split shier`).

## What changed since the first pass

The first pass (main a61d735f9) ran the bench at its default shape: NG 16 and the flat HC engine, with injected link
errors. That is not the production shape. This pass adds, all bit-exact at the layer output:

- `NG=256` (1,024 HC lanes, 20 y beats a block). The bench's collective-to-HC glue only worked at NG 16 and was repaired.
- `HCH=1`: the hierarchical HC slab at the tuple of `hc_gate.py --hier 3` (HIER 1, HALF 1, CSPLIT 1, TAIL_SPLIT 2,
  CNL_PIN 1, CHAIN_STEP 6), which is the slab that is being routed.
- `nom`: no injected link errors, so the collective has a nominal latency.
- L14, an Engram layer (HC chain fixture rebuilt from the released checkpoint, bit-exact against the 1M shard).
- `--coef-split`: two COEF jobs a block instead of one (see below).

## Runs

| Run | Shape | L0 | L2 | L14 | Verdict |
|---|---|---:|---:|---:|---|
| `phier` | NG 256, hierarchical HC, nominal link (production) | 11,574 | 20,492 | 21,617 | PASS |
| `shier` | production with `--coef-split` | 8,823 | 17,737 | 18,861 | PASS |
| `pflat` | NG 256, flat HC engine | 9,836 | 18,758 | 19,880 | PASS |
| `phier_base` | production with link errors | 12,886 | | | PASS |
| `phier_mhc`, `phier_mcoll` | production mutants | | | | FAIL as required (H_STORE 0 / 640; 544 / 640) |
| `n16` / `s16` | NG 16 flat, nominal / with `--coef-split` | 10,263 / 7,522 | 19,192 / 16,430 | 20,311 / 17,554 | PASS |
| `h16` | NG 16 hierarchical | 10,432 | | | PASS |
| `base16`, `base16_L14` | first pass (NG 16 flat, link errors) | 11,168 | 20,360 | 21,511 | PASS, 2 mutants fail each |

Bench layer cycles are not a price ratio by themselves: field phases have synthetic shapes and the bench link has no
PHY or board leg. The qualifying figures are the measured HC jobs put on the priced layer.

## HC master at production shape

| Job | Hierarchical slab | Flat engine, NG 256 | Price | Ratio (hierarchical) |
|---|---:|---:|---:|---:|
| NORM (hc_pre + RMSNorm + act-quant) | 713 | 235 to 237 | 327.0 to 333.9 | 2.16 |
| POST, cycles after the all-reduce ends | 248 | 22 | 112.9 | 2.20 |
| H_LOAD (stage entry) | 336 | 333 | none | |
| H_STORE (stage exit) | 387 | 81 | none | |
| COEF | 17 | 14 | none | |
| GAIN (boot) | 176 | 173 | none | |

The flat engine meets its price at production width. The hierarchical slab does not: the excess is its serial
forward and return chains, the same cause the HC stream traced for POST. The hc_gate unit bench agrees (NORM 727,
POST 287, H_LOAD 349).

Layer with only the HC at its measured cycles, everything else at price:

| Program | L0 | L2 | L14 |
|---|---:|---:|---:|
| production, one COEF a block | 1.088 | 1.052 | 1.050 |
| production, `--coef-split` (the priced dataflow) | 1.127 | 1.070 | 1.067 |
| flat engine NG 256 | 0.984 | 0.991 | 0.991 |

## End-to-end

| Item | Cycles | AR loss | MTP loss | Status |
|---|---:|---:|---:|---|
| NORM 713 vs 329.9, 80 a token | +383 each | 3.56 % | 2.72 % | ledger row PROPOSED, replaces the 1.178 % row measured on the reduced flat shape |
| POST (accepted row, unit bench 287) | +174 each | 1.65 % | | accepted earlier; the layer shows +135 |
| H_STORE + H_LOAD per h transfer (41 a token) | 723 | 3.45 % | 2.46 % | unpriced and serial: decision needed |
| COEF before every NORM | 17 | 0.16 % | 0.12 % | unpriced and serial |
| SU classes QB / SW / SO (slab unit bench) | | 1.47 % | | proposed by the SU owner |

s81 ledger with the new NORM row: accepted 1.812 % + proposed 5.04 % = 6.85 % of 15 %. The unpriced HC jobs are not
in the ledger (they have no price to hold a ratio against); with them the design is at about 10.5 % AR.

## Unpriced HC jobs: serial or overlapped

From the per-op dump (`OPT` lines):

- H_LOAD starts only when all 640 hidden rows have landed and the NORM cannot start before it ends. H_STORE runs
  after the last POST and before the hop. Both are serial with the layer, once per h transfer. Structural overlap:
  stream H_LOAD on the rows as the hop delivers them (the link takes 652 cycles for the payload, H_LOAD reads two rows
  a cycle) and cut H_STORE through to the link.
- COEF is serial in front of each NORM (17 cycles).
- The bench program gave each block ONE COEF that reads the pre, post and combine rows. The post and combine rows come
  from the block's own coefficient chain (fn / sumsq, rsqrt, pre_post, sinkhorn: 1,529 cycles), so the NORM waited for
  the whole chain: 1,555 to 1,560 cycles in front of each NORM. The priced token path starts hc_pre from the PREVIOUS
  block's pre_post. If the die program were written like the bench, that would cost 11.7 % AR / 9.1 % MTP.
  `--coef-split` removes it with the same RTL and the same golden: COEF-a (previous block's pre row) before the NORM,
  COEF-b (this block's post and combine rows) after it. Measured saving 2,751 to 2,756 cycles a layer. The die program
  and the coefficient producers' row map must be written this way.

## Collective and gathers at nominal link

With `nom` every all-reduce takes 452 or 453 cycles and the gathers 30 to 123, against prices of 827 and 422 to
1,033. These are not price ratios: the price includes the PHY, the board leg with RS FEC and the routed wire stages,
which the bench channel (60 / 12 cycles) does not model. The price-shape bench of the collective is
`tb_s81ph_coll_sys` with production FIFOs; the split lane slices measured 3,021 against 3,014 cycles for the flat
(priced) design, 1.002x. With injected errors the all-reduce varies from 637 to 1,185.

## Hand-offs folded in (`record.json` `handoffs`)

- VM read latency: the bgq28 leaf split adds 40 cycles to a read round trip (41 to 81), the front-end hierarchy 4
  (41 to 45). Read streams are pipelined, but each VM-fed op opens its stream only after its producer's rows are
  complete, so the latency is serial once per op. Critical field phases plus SU ops: about 22 a layer, 886 a token:
  4.10 % AR at +40, 2.09 % at +20, 4.49 % at +44. Field phases alone: 1.38 % at +40, 0.70 % at +20. Modelled on the
  token path from the measured unit delta; the layer bench has no VM master.
- SU slab classes: QN 1.045, KV 1.261 (off the critical path), QB 2.075, SW 1.843, SO 1.237: 1.51 % AR if all stand.
- Collective split 1.002x; core insertion 353 to 358 ps with about 100 ps spread.
- Engram 508.7 against 500 (1.017), off the critical path.
- Gather root storage: not built, bound at most 0.07 % / 0.7 % of a layer.

## Families without a measured production throughput (`families.json`)

Field (55 entries), svc / hbm (18), head (9) and select (8) have exactness gates only, or a price-source bench that
predates the hardened tiles; none prints cycles against its token-path nodes at production shape. The table names the
cheapest vehicle for each. The cheapest common step is to replace the behavioural engines of `tb_s81_die_layer` on
ports 1 (SU slab), 4 (svc) and 5 / 6 (select, collector) with the real masters, and to drive the field port with the
stage program's phase shapes.

## Round 5 (10-13 evening): ledger decisions and the measured VM read latency

Runs added (ot-epyc1tb, `ot-run`, main 2974cb067 + the `LVM` bench parameter; `runs/lvm10`, `lvm30`, `lvm54`,
`lvm54_mhc`; `record.json` `vm_read_measured`): the production shape with `--coef-split` at three read latencies of the
bench's behavioural VM.

| Run | VM read latency | L0 | L2 | Delta | Verdict |
|---|---:|---:|---:|---:|---|
| `lvm10` | 10 (bench default) | 8,823 | 17,737 | | PASS, reproduces `shier` on current main |
| `lvm30` | +20 (bgq28 leaf hop 1) | 8,883 | 17,797 | +60 / +60 | PASS |
| `lvm54` | +44 (leaf hop 2 with the front-end hierarchy) | 8,962 | 17,874 | +139 / +137 | PASS |
| `lvm54_mhc` | +44, HC mutant | | | | FAIL as required |

Three VM read round trips of the HC master are serial in a layer: H_LOAD at the layer entry and the COEF-a in front of
each NORM. COEF-b and the boot GAIN loads take the latency too but are off the critical chain. On every layer of the
token that is 0.29 % AR at +20 and 0.67 % AR at +44 (0.22 % / 0.51 % MTP). This is the HC share only: the SU slab, svc
and select engines are behavioural in this bench and the field has its own capture path, so the field and SU share of
the VM read cost (4.49 % at +44, 2.50 % at +24) is still a model on the token path.

The SU slab gate was re-run at main 2974cb067 under Verilator (`results/rtl/ref_tile/s81su_full_gate_2974cb067`):
positive exact at 3,149 cycles, mutant 5 fails, job cycles identical to the 9e37b21b2 record.

| Unit | Priced | Measured | Ratio | End-to-end loss | Ledger |
|---|---:|---:|---:|---:|---|
| MTP p2.core_transaction | 5,467 | 6,092 | 1.114 | 0.159 % MTP | accepted |
| SU.HC_POST | 112.9 | 287 | 2.542 | 1.653 % | accepted |
| SU.HC_PRE_NORM (hierarchical slab) | 329.9 | 713 | 2.161 | 3.566 % | proposed |
| SU.QB | 80 | 167 | 2.088 | 0.418 % | accepted (coordinator 10-13) |
| SU.SW | 191 | 353 | 1.848 | 0.776 % | accepted (coordinator 10-13) |
| SU.SO | 244.9 | 303 | 1.237 | 0.280 % | accepted (coordinator 10-13) |
| HC.H_XFER (H_STORE + H_LOAD per h transfer) | none | 723 | | 3.453 % at 41 transfers | proposed, removal named |
| HC.COEF (before each NORM) | none | 17 | | 0.164 % | proposed |
| SU.KV | 283 | 357 | 1.261 | 0 (off the critical path, slack 512.7) | no row |
| SU.QN | 288 | 301 | 1.045 | | qualifies |
| SU.SE (max + exp + den nodes, mapping to confirm) | 495.2 | 387 and 466 | 0.94 | | under price |
| Collective, split lane slices | 3,014 | 3,021 | 1.002 | | qualifies |
| Field X broadcast, +1 column relay (hop gate) | 183.6 | 184.6 | 1.005 | 0.034 % | qualifies, no row |
| VM read, leaf hop 2 + front end (+44) | 41 | 85 | 2.07 | 0.67 % HC share measured; 4.49 % with field + SU, 6.02 % every VM-fed class (model) | NOT entered |

Ledger total: accepted 3.286 % + proposed 7.183 % = 10.469 % of 15 %.

What is not entered and why:

- VM read at leaf hop 2. The all-class reading is over the 5 % unit limit and, with it, the design would stand at about
  15 %. Structural fix: the bgq28 leaf hop goes 2 to 1 (+24: 2.50 %), and the VM issues the next op's operand stream on
  the producer's row-completion event, which hides the read round trip behind the producer's tail.
- HC.H_XFER is entered at the 41 layer-boundary transfers the layer run measures. Every stage hop carries the
  40,976-byte h payload; if the 17 placed mid-layer hops also store and load, the cost is 4.82 %, and on all 120 stage
  hops of the mapping about 9.5 %. The structural removal makes the count irrelevant: stream H_LOAD on the rows as the
  hop delivers them and cut H_STORE through to the link.
- The die's v16 plan lengthens the field round trip at the farthest frame from 183 to 188 cycles: at most 0.17 % on the
  290 critical field phases, inside 1.10 as a ratio. The hub command and done buses (sequencer to SU 31, SU done 32 in
  v16) have no priced stage count to compare against; they are unmeasured.
- The front-end S3 change is cycle-exact (0 cycles, not +1). The done flag relay adds one stream cycle a done and did
  not show at the stream-clock done output of the production case (94 = 94).

Still without a production-shape measurement: the SU nodes attn.sink, attn.q_rope, ffn.bias and ffn.softplus_sqrt
(616.8 priced cycles a layer, 2.98 % of the token), and the field, svc, head and select families listed below.

Order of the structural fixes by what they return: H_LOAD / H_STORE streaming (3.45 %, and the hop-count exposure),
the hierarchical NORM chains (3.57 %: the flat engine meets the price at 0.71x), VM read prefetch with leaf hop 1
(2.5 to 4.5 %), SU job overlap in the slab control (1.47 %).

## Round 6 candidate scope (Codex takeover, 10-13 evening)

The exact source and raw measurements are preserved in `runs/r6_*` and `r6_scope.json`.
These measurements establish HC candidate exactness, output flit checks, and cycle
deltas at production HC width NG256. They do not qualify the complete production
die layer: the VM and SU/service/select/coefficient engines are behavioural, the
Engram path is behavioural, and production PHY/FEC/board and die relay stages are
not present. Any token-path replay using these durations is a modelled share,
not measured end-to-end tok/s. No accepted-cost row is added by this record.

PIPE-only saves 419/421 layer cycles. PIPE plus landing stream and watermark
hand-off saves 942/938 cycles to the final flit at L0/L2, with 640/640 exact flits,
zero early reads and at least 19 rows of writer lead. At LVM54 and PGAP600 the
stream path passes at adjusted xfer8569/17475; the PGAP400 run fell back to VM
and is excluded from streaming latency comparisons. Engram L14 never enters the
landing stream and remains a separate VM-path observation. The original PIPE
parameter defaults are zero; production default-on and pin-safe landing changes
are separate candidates requiring fresh gates and physical adoption.

The `r6_pD` batch contains only negative controls: its aggregate gate prints FAIL
because the harness requires a positive case. Both individual actual mutant
cases fail as expected. The aggregate FAIL is retained and classified, never
promoted to a full positive gate. The NG64 PD0 mutant is reduced-shape evidence;
a fresh NG256 PD0 mutation is running before default-on adoption.

The immutable AR graph has 80 HC POST nodes in 41 changed-h groups, while the
MTP graph has 86 in 44 groups. This establishes the graph/program requirement
for changed-h transfers, not a measured deployed H_LOAD/H_STORE count: native
stage schedules for the full 120-stage allocation are still owed. Hop-only stages
can forward landing rows without an HC copy; gratuitous H_LOAD/H_STORE jobs
there would create extra serial work that is absent from the price.
