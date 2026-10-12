# SM.MATVEC re-architecture, track B (el1011-hbm-smmv-b, 2026-10-12)

Measured today: 32.9x the simulator price per token (results/rtl/hgi_unit_tput_20261010/sm/report.json): FP4 81.5x,
FP8 18.4x, BF16 7.4x. The SM datapath is not the cause. ot_hbm_accel_smh issues one weight line a cycle and already
queues NOUT = 4 ops (issue_pq: op N+1 launches when op N issues its last line). The cause is the record level around it.
Every record runs x load, then start, then drain, then publication, then retire, strictly in series, with nothing
overlapped across records. x arrives at about 2.8 elements a cycle. Track B rebuilds that record level top-down, from
the budget below.

## 1. Budget (price -> per-SM rates)

Line = 1,088 b = 136 B (1,024 b codes + 64 b block exponents; INT8 transport 160 B). Clock 1.2 GHz. 32 SMs a die.

| class (DS-V4.1 1M rank-0 token) | records/token | K | rows/SM | lines/SM | price (cyc) | price basis |
|---|---|---|---|---|---|---|
| FP4 expert w1/w3, batched | 480 | 5120 | 1 | 24 | 24 | lines only (walk flush group) |
| FP4 expert w2, batched | 240 | 2304 | 2 | 32 | 32 | lines only |
| FP8 shared/slot-6 w3, w2, batched | 80 | 5120 / 2304 | 1 / 2 | 40 / 48 | 40 / 48 | lines only |
| FP8 attention projections (wq_a, wkv, slot-6 w1) | 120 | 5120 | 1 | 40 | 185 | lines + drain + first access |
| FP8 wo_b | 40 | 8192 | 2 | 128 | 273 | walk |
| FP8 indexer.wq_b / engram.wkv | 10 | 1280 / 6144 | 16 / 9 | 160 / 432 | 163 / 577 | walk |
| BF16 router / compressor | 44 | 5120 | 1 | 80 | 246 | walk |
| BF16 LM head | 1 | 5120 | 43 | 3,440 | 3,606 | walk |

What the price requires of each SM (rates sustained across back-to-back records):

| rate | requirement | binding class |
|---|---|---|
| weight lines from HBM | 1 line/cycle/SM = 136 B x 32 = 4,352 B/cycle/die = 5.22 TB/s | every batched record |
| MACs | 256 (FP4) / 128 (FP8) / 64 (BF16) a cycle per SM (one line a cycle) | met by smh today |
| x into the x store (all 32 SMs, broadcast) | K / price: w2 FP4 2,304 / 32 = 72 el/cycle; w1/w3 5,120 / 24 = 213 el/cycle without reuse, 18 el/cycle with one x a layer (12 records share it) | expert w2 (fresh x each), first record of a layer |
| x quantisation (block-dot) | 72 el/cycle = 2.25 blocks of 32 a cycle -> 4 quantisers (actquant, 1 block/edge each) | w2 |
| VM read for x (FP32) | 72 x 4 B = 288 B/cycle = 9 sectors/cycle -> one 32-lane VM read group | w2 |
| x-store write port | 2 beats (2,048 b) an address for P = 1: w2 FP4 = 16 addresses = 32 beats <= its 32-cycle price | w2 (at the limit, must overlap the previous record) |
| results into pub / VM | wo_a BF16 K512: 32 rows/SM per 256 lines = 4 rows/cycle/die; wq_b 3.2/cycle; w2 2/cycle | wo_a |
| record overhead | 0 exposed cycles a batched record: decode, per-SM fields, x load, HBM first access, drain and pub tail must all overlap the neighbouring records | every batched record |

### Bandwidth reconciliation (OWNER DECISION, price NOT changed)

- Die HBM: 4 HBM3E stacks at 1.0 TB/s = 4.0 TB/s peak. hgi_sim calibration `hbm.bytes_per_cycle` = 3,166.7 B/cycle =
  3.80 TB/s sustained (95 %, measured on vehicle A). That is 99.0 B/cycle/SM = 0.728 lines/cycle/SM, or 1 line every
  1.374 cycles. The bench HBM model (`BWX10 = 31667`) is exactly this figure: 1 line / 1.37 cycles / SM. At peak it is
  1 line / 1.306 cycles.
- The batched price charges 1 line/cycle/SM = 5.22 TB/s a die. That is 1.374x the sustained bandwidth and 1.306x the
  peak the die physically has.
- Consequence: every line-priced (batched) record has a hard floor of 1.374x its price on this die and on the bench. That
  covers 800 of 1,095 records/token and about 22.7 k of the 104 k priced cycles. They cannot qualify at 1.10x by any SM
  architecture. Track B targets 1.374 x price x 1.10 = 1.51x for those classes, and 1.10x for every class whose price
  is not line-bound (walk-priced records: price >= 1.374 x lines + latency).
- Owner options: (a) re-price batched records at lines x 1.374 (simulator consistent with its own HBM calibration);
  (b) give the die 5.2 TB/s (5-6 HBM3E stacks or HBM4); (c) keep the price and accept the 1.37x floor as a known
  model inconsistency. Track B does not choose. It reports both ratios (vs price, vs the bandwidth floor).

## 2. Architecture (SOTA weight-streaming matvec, sized to the budget)

Batch-1 decode matvec has no weight reuse, so the weights must stream. A weight-stationary design is excluded: 1 M-context
DS-V4.1 weights do not fit on-die. That fixes the design: a streaming engine where weights flow once at the HBM rate and
everything else is decoupled from them by queues. Comparable machines are the TPU v4/v5 vector-matrix path for decode,
Groq's streaming matvec and Cerebras' weight-streaming mode: weights move, x and partial sums stay put. x is broadcast
once and reused across all rows and all SMs. The record pipeline runs N+1's setup under N's stream.

```
 sequencer --rec--> [ENGINE  ot_hgi_smmv]  (one per die, at the cmdproc)
                     D: decode pipe (1 rec/edge; exact-divide by modular inverse; products pipelined)
                     W: record window (W = 4 entries, in-order pointers x / issue / retire)
                     A: x-slot allocator (ring over the XD = 128 x-store addresses; release at retire)
                     X ----x cmd (slot base)----> x engine (wide VM read group + NQ = 4 quantisers) --xw bcast--> 32 SMs
                     I ----ONE broadcast record bus {Q, LQ, ML, M, line0, g, fmt, xb, id}----> 32 SM stations
                     P ----pub cmd queue (W)----> record-pipelined publication
 SM station (per SM, at the SM): rows_s = clamp(M - sQ, 0, Q), d_base = line0 + s LQ, d_lines = clamp(ML - s LQ, 0, LQ)
                     (s is a strap: constant multiplies) -> smh start / descriptor ports (unchanged), done counter
 smh (unchanged): 1 line/cycle, NOUT = 4 op queue, HBM requests ahead of compute (descriptor queued before start)
 pub (record-pipelined): per-SM record pointer; a row's VM address is formed at the SM front from that SM's current
                     descriptor; writes carry a record tag; per-record outstanding counters; done in record order
```

Decisions and why:

1. **Record window instead of a serial FSM.** Records are accepted while fewer than W = 4 are in flight. x load, SM
   issue, publication and retire each have their own in-order pointer, so record N+1's decode, x load, descriptors and
   start all overlap N's stream. The smh's NOUT = 4 queue already accepts the op, and its HBM requests start as soon
   as the descriptor is queued, so the 104-cycle first access and the about 60-cycle drain sit under the previous record.
   Retire is in order: every SM active in the record has completed its op (a per-SM completion counter against the
   record's target) AND the record's publication is done.
2. **x slots by hardware allocation.** A ring allocator over the 128 x-store addresses gives each record a slot of
   8 x op_g addresses (FP4 K5120: 24, FP8: 40, BF16: 80). A record's x load can never overwrite a slot that a
   not-yet-retired record reads. That is correct by construction, independent of the compiler. Compiler x reuse
   (track A's XR bit) is an optional add-on on top: a reuse hit skips the load and pins the slot.
3. **x engine sized to 72 el/cycle (not 2.8).** x is read over one 32-lane VM read group (ot_hgi_vm_wrd +
   ot_hgi_vm_lanearb, die contract r25gq v7 D19 lgE slot 0, already granted to the SM x load). It is quantised by
   NQ = 4 ot_hdc_actquant (4 blocks/edge = 128 el/cycle) into a fragment buffer, then broadcast on the existing 2,048-b
   xw port, one beat an edge. Its throughput is >= 1.8x the w2 requirement, and it runs one record ahead in the window.
4. **Per-SM fields at the SM.** One broadcast record bus (about 130 b, relayed every <= 500 um) replaces 32 x 106-b
   point-to-point command words from a central adapter. Each SM station derives its fields with constant multiplies
   (strap s), so no 32-edge serial field loop remains (that loop alone was 34 edges a record, more than the 24-cycle price).
5. **Exact divide B.base / LB by a modular inverse.** LB = 136 = 8 x 17 and 160 = 32 x 5, so line0 = ((base >> 3) x
   17^-1) mod 2^37. The 1-in-17 check is q <= (2^37 - 1) / 17. That is one pipelined multiply, against the 20-edge
   iterative divide.
6. **Record-pipelined publication.** Rows of N+1 reach the pub while N's writes drain. Every SM walks a small
   descriptor queue (pointer advances after R_s rows), and a coalescing buffer flushes on a record change. Writes carry
   the record tag, and pub_done pulses once per record in order. Rate need: 4 rows/cycle/die. That is unchanged, and
   it is met by the 8-slice hierarchical pub.

Physical (every new block hardened through tools/ref_tile): the engine sits in the cmdproc region at about
0.25 mm^2, with flop-bounded stages <= 500 um and the record bus relayed at <= 500 um. The SM station is about 1.5 k
flops, folded into the smh front strip (it already owns the SM pins). The x engine is about 4 actquant + 8 x
128x256 SRAM fragment buffer, placed at the VM lgE face, and the xw tree is unchanged. The record-pipelined pub keeps
the 8-slice hierarchy (4 SMs a slice, about 15 k sinks a clock root). No clock root exceeds 15 k sinks: the engine is
about 9 k flops, a station about 1.5 k.

## 3. Elements and contracts affected

- `ot_hgi_sm_record` -> `ot_hgi_smmv` (new; the adapter stays for LEGACY / DS lockstep). hfd_cmdproc port: the per-SM
  W_CTL/W_DESC words become one broadcast record bus + per-SM station (die net change: 32 x 106 b -> 1 x ~130 b bus +
  32 x 4 b returns, unchanged).
- `hfd_sm` / smh front strip: + SM station (rows / d_base / d_lines from the bus, strap s), smh ports unchanged.
- `ot_hgi_sm_xload` -> x engine on lgE slot 0 (contract D19, already granted; track A 3b(i) built the BF16 half).
- `ot_hgi_sm_pub` (slice / hier): + per-SM record pointer, record tag, W-deep command queue (pub_rdy = queue not full).
- Compiler: none required (hardware slot allocation). Optional XR bit (track A 3a) for reuse.

## 4. Implementation status (step B1 = engine + record-pipelined pub; step B2 = x engine)

See /home/ubuntu/claude-takeover-20261007/el1011-hbm-smmv-b.log (COLLECT) for the live state.

## 5. HBM B2 re-cut (owner, 2026-10-12): 4 clusters x 8 SMs, one HBM3E stack and one LOCAL VM slice each

- **Bandwidth per SM is unchanged by B2.** One stack per cluster = 1.0 TB/s for 8 SMs = 125 GB/s = 104.2 B/cycle/SM
  at peak, or 99.0 B/cycle/SM sustained (95 %). The batched price needs 136 B/cycle/SM, so the floor is the same
  **1.374x sustained / 1.306x peak**. The OWNER DECISION in section 1 stands as written.
- The engine becomes per cluster: one ot_hgi_smmv with NSM 8 (W 4), with stations at its 8 SMs. An MoE expert record
  is split across all 4 clusters, so each cluster engine runs its quarter of the rows. Row blocks are Q = ceil(M / 32)
  globally, and cluster c owns SMs 8c..8c+7, so the station strap is s_global = 8c + s. Retire is per cluster. Any
  cross-cluster ordering comes from the compiler-scheduled ring, with no global barrier.
- **x load (B2 step) sized against the LOCAL slice port, not lgE.** Each cluster loads the full x (K elements)
  into its 8 SMs. The rate per cluster is unchanged at 72 el/cycle for w2 FP4. Reading FP32 from the local slice
  needs 288 B/cycle = 9 sectors/cycle, then NQ 4 actquant. The provisional slice-port width must be checked when
  results/arch/hbm_b2_1012/SPEC.md lands. If the port is narrower than 9 sectors/cycle, x moves as pre-quantised FP4
  blocks: 2,304 FP4 = 36 sectors per w2 record, about 1.1 sectors/cycle.
- **Results:** 8 SMs per cluster, so 1 row/cycle/cluster at wo_a. The local pub is one slice of the 8-slice pub at
  4 SMs a slice, i.e. 2 slices a cluster.
- **Track A pieces to fold in:** credit flow (sm_cr, AD 32 arrival FIFO), the 32-deep pub slice, x reuse (header
  XR bit + xb; in B as a reuse hit that pins the allocator slot).
