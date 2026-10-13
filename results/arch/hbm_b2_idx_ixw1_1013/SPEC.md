# B2 IDX.INDEX native control and physical plan

Source adapter: 0d8f55c19, unchanged arithmetic, reduction order, selector tags and mutant points. Integration base ade0e472cb38c5c9cb30479cf4ef41e7fed0b220. Historical packet results and the 29,447-flop / 929-ps adapter gate are not physical or throughput qualification.

## Native ownership and service budget

SW slice sid=0, wide client slot=5 (SW KE=6), 8 lanes, sector low three bits select bank. Read request native8x17, read credits8, reply8x257; write request8x281, credit8, commit8; independent registered request/grant handshakes. RRS=WRS=3 gives LQ=10. Query A 4096 words, weights B32 words and optional C IDs plus values belong to REPL [262144,294912). Outputs O/R and optional D IDs plus values belong to SW [0,65536). All full 40-bit bases and extents are validated before dispatch. The legacy18-bit core sees validated offsets; read translation adds native sec16 mirror bit, writes add SW ownership. A/B/C are all mirrored, so no per-request mirror owner switch is necessary. O/R/D are all owned SW. Owner remains fixed until completion after every write-done.

L24 price remains1080 streaming cycles, allowed maximum1188. L20 and L2 must also be exact. Scorer remains64 keys/cycle, four stacks16 each; adapter must accept four read sectors/cycle and issue one sector/lane/cycle subject to credits, query32 words/cycle, output8 survivors/half beat plus two candidates/beat. One record dispatch register adds one exposed streaming edge, to be measured rather than repriced. LQ10 is finite; read landing DL2 additionally bounds issue reservations. No whole-array bench.

## Physical cuts before structural RTL

No flat route is eligible: current29447 sinks exceed15000 for a new root. Candidate hierarchy has two four-lane landing tiles (pin captures,2x256-bit landing per lane, pointers, read reservations/credits, write pin launch), four unchanged output packer tiles, and one bounded core containing issue/log, gather, query ring, keep stages and selector ingress. A synthesis census must determine whether core itself needs a keep tile and a selector FIFO tile; estimated split is not acceptance. Root per leaf <=15000, no datapath reset, control reset fanout measured.

Candidate cluster envelope640x480um: two lane tiles on W/E, core centre, packers at output faces. Registered reach <=500um; external SW lane station is approximately1886um away vertically from IDX site and therefore requires at least3 intermediate registered stations (actual Manhattan and legal positions must be measured in native die placement). Each seam uses an ordered finite-credit link; credits cover registered round-trip and every captured pending beat. Arbitrary delay-only flops on valid/ready are prohibited.

Conservative major-cut demand: read half4x(17+1+257)=1100bits/cycle; write half4x(281+1+1)=1132, combined2232. At480um span, M5 horizontal pitch0.064um, reserve25% power/access/spare, capacity5625 tracks, ratio0.397. Orthogonal selector cut: fs90+qb1048+kin345+to612+co72+qbr1+toc1+coc1+ev2=2172bits/cycle; M4 vertical0.064um over640um with25% reserve=7500 tracks, ratio0.2896. These are planning upper bounds, not routed evidence; actual PG/OBS must be deducted and no M6 child signal is allowed. Leaf M5 signal/PG default; cluster layer grant must come from die lead if M6 inter-child routes are needed. Pins belong to registered faces; avoid a pin-driven outline increase.

## Required evidence

Pinned existing source0d8f55c19 BASE/MUT2 incremental production build is owned by throughput agent on EPYC4; no duplicate. New native mapping gates need exact address/data/mask/credit/done propagation and invalid full40-bit/extent negative controls. Structural hierarchy requires a source-matched composition exact+mutant and production rate gate before route submission through ref_tile. TT/FF/SS, DRC0 and child_lint cap are required. No closure, native production qualification or die assembly is established by this plan.

Native transport implementation: ot_hgi_idx_b2_station uses existing finite burst-owner/release-handshake station at K6/ID5, native REQW17 read and281 write. Upper24 padded lanes are zero at every physical boundary and synthesis must prune them. Native tap137bits read up and2249bits write up; old SPEC129/2241 counts omit mirror sec16. Station source needs its own synthesis/reset-fanout/physical gate; no physical acceptance claimed.

## Reused actual synthesis gate, source hash confirmed

The preserved PVE1 gate `idxw_b2-20261012-202510` has adapter SHA256 `5bbff6eea5bb2d5638bd8690960869a28e5dde14d741a6c7094a674d3a74bd85`, exactly the imported0d8f55c19 source. Its actual textbook receipt is `pinned_adapter_textbook.json`:184343cells,29447flops,0macros. The offending stage is `k1_q[19][0] -> k2_ord[19][11]/D`,929ps/26levels. The dominant high-fanout points are selector FIFO head `tfh[1]`4874loads and query ring pointer `rg_rp[0]`4097loads. Splitting lane pins alone cannot cure those core paths. Keep ordinal division requires an exact registered pipeline; FIFO/ring gathers require regional pointer copies at actual hard-tile boundaries or local SRAM. Added stages must be measured against immutable1188cycle maximum, with golden field ordering and candidate matching unchanged. No new synthesis was duplicated to learn this.

## Tiled redesign `ot_hgi_idx_index_wt` (el1013-idx-tiles, 2026-10-13; written BEFORE the RTL)

The flat adapter `ot_hgi_idx_index_w` stays untouched as the conservative line (route `idxw_b2-v2-c08e87086`) and as the
reference of the equivalence bench. The redesign is a wires-only wrapper `ot_hgi_idx_index_wt` (same ports and parameters;
`ot_hgi_idx_unit` selects it with IXW = 2) over six hard-leaf instances of five masters. No parent route: the die places
the leaves (two-level rule); the wrapper holds no logic.

### Leaves, census (estimate from the 29,447-flop receipt, to be replaced by the per-leaf synthesis census)

| master | inst | contents | flops (est.) | outline um (cut-bound) |
|---|---|---|---|---|
| `ot_hgi_idxw_lane` | 2 (hardened once) | 4 lanes: wrr pin capture 4x257, landing memory DL 4 x 256 a lane, local chunk log, in-order chunk assembly, registered 1,024-bit chunk beat, wrq launch, lane credit counters | 6.6k | 110 x 170 |
| `ot_hgi_idxw_qcore` | 1 | frame command registers and FSM, chunk walker / issuer, group-order log, 2:1 chunk merge, head weights, query ring, block register, qb / fs launch | 9.5k | 200 x 170 |
| `ot_hgi_idxw_keep` | 1 | held id chunk, 6-stage exact ordinal divide and rank match, result FIFO, match drain, keep bitmap, kin launch | 9.5k | 200 x 110 |
| `ot_hgi_idxw_beat` | 1 | to / co pin capture, beat FIFOs, T1 / T2 / D1 compaction | 7.5k | 140 x 110 |
| `ot_hgi_idxw_wr` | 1 | four sector packers, lane arbiter, wwq launch, write credits / done count | 5.2k | 350 x 60 |

Every leaf: one clock root <= 15,000 sinks, M5 cap (no pg_layer), own 2-flop reset synchroniser, control-only reset with
one synchroniser copy per <= 256 reset loads, no datapath reset. Cell area is about 0.75 um2 a flop of the flat receipt
(22,000 um2), so the outlines are pin / cut bound (18-30 % utilisation), not area bound; they are not grown further.
Candidate cluster 510 x 380 um (inside the 640 x 480 envelope): bottom row KEEP, middle row LANE0 | QCORE | LANE1, top
row WR | BEAT, 20 um channels. Longest registered seam (flop to flop, Manhattan) <= 400 um.

### Cut analysis (bits a cycle across each seam vs die tracks over it; die signals M6 horizontal / M7 vertical, 0.064 um pitch, 25 % reserved)

| seam | bits a cycle | face um | tracks usable | ratio |
|---|---|---|---|---|
| S1 LANE -> QCORE (each): chunk beat 1,024 + meta 20 + v; back: chunk descriptor 21, pop 1, ready 2 | 1,070 | 170 (M6) | 1,992 | 0.537 |
| S2 QCORE -> KEEP: chunk beat 1,045, frame command 40; back: credit, kin_sent, busy | 1,090 | 200 (M7) | 2,343 | 0.465 |
| S3 BEAT -> WR: T2 v + n 4 + o 256 + r 256, D1 v + n 4 + ids 64 + values 64; back 2 credits | 652 | 110 (M6) | 1,289 | 0.506 |
| S4 QCORE -> BEAT / WR control (go, bases 72, has_r, flush) and status back | 100 | any | - | < 0.1 |
| P1 WR wwq 8 x 281 + credits / done 16 + req / gnt | 2,266 | 350 (M7) | 4,101 | 0.553 |
| P2 LANE wrr 4 x 257 + wrq 4 x 17 + credits 4 (outer face) | 1,100 | 170 (M6) | 1,992 | 0.552 |
| P3 QCORE qb 1,048 + fs 90 + command 190 (free N/S face) | 1,330 | 200 (M7) | 2,343 | 0.568 |
| P4 BEAT to 612 + co 72 + toc / coc; KEEP kin 345 | 686 / 345 | 140 / 200 | 1,640 / 2,343 | 0.418 / 0.147 |

All <= 0.60. Leaf pin faces use M4 / M5 at 0.048 um, so pin occupancy is below the die-track ratio on every face.

### Mechanisms (each has its own mutant)

1. Exact ordinal divide, six registered stages, one <= 32-bit add or one compare a stage: K1 fields, value test, range
   test from a chunk-level base difference, q5 = q + 4q; K2 p85 = q5 + 16 q5; K3 s = 2 p85 + 512 p85; K4 ord = (s + q) >> 17;
   K5 t = 3 ord, ord < 1,368; K6 match = ok and {q - t, lo} == rank. Identity q * 43,691 = 514 * 85 q + q is checked
   exhaustively over q < 2^15. +3 walk stages against the flat adapter; latency is measured, not re-priced.
2. Free-flowing pipelines with reservations instead of stall chains: a chunk is popped from a lane leaf only when its
   consumer slot is reserved (ring room for A, K-result FIFO credit for a C value chunk), so no wide register has a
   combinational stall enable.
3. Regional gather: landing memory, chunk log and read / write pointers are local to each lane leaf; every pointer or
   load-enable that selects wide data exists as registered copies, one a <= 64-bit data slice (keep attribute), so no
   pre-buffer net other than clock has more than 128 loads. Same rule for the beat FIFO head (tfh), the query ring
   (rg_rp) and the keep bitmap write. No runtime part-select >= 64 bits.
4. Finite-credit seams: S1 pops against lane ready counts, S2 K-result credits, S3 one credit a packer slot; every
   credit return and every seam beat is registered on both sides; credits cover the registered round trip. Landing
   depth DL = 4 a lane inside the lane leaf covers the longer pop return (local memory; read reservations unchanged
   in meaning).

### Gates before any route

(a) transaction-exact equivalence bench: flat `ot_hgi_idx_index_w` and `ot_hgi_idx_index_wt` under the same randomised
VM lane / selector models: identical wrq sequence a lane, fs / qb / kin beats, wwq (sector, data, mask) sequence a lane,
done / fault, over L24 / L20 / L2-shape frames with keep_en / cand_en / has_r variants, random credit and reply delays;
(b) the golden-backed unit bench (tools/hbm_idx_die_bench.py compare) through `ot_hgi_idx_unit` IXW = 2: L24 exact and
IDX <= 1,188 cycles (price 1,080), L20 / L2 exact; (c) mutants that must FAIL: one divider stage, one regional pointer
copy, one credit seam, plus the inherited MUT 1 / 2; (d) Verilator 5.050 lint clean; (e) per-leaf generic-synthesis
census: flops <= 15,000, max non-clock fanout <= 128, reset fanout reported. None of this is closure or qualification.
