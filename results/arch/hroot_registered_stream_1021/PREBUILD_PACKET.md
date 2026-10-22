# HROOT six-slot registered stream (SPIPE6): pre-build review packet

Status: SOURCE/MODEL ONLY. Owner review requested. Nothing has been mapped, built, census-run, cold-run or gated.
The only tool run was a Verilator `--lint-only` syntax parse: engine SPIPE6=0 and 1 give 0 errors, with one
UNOPTFLAT note on the `sp_ready` bit chain, which is a per-bit chain and not a loop. The cdc shell with
IKEY_GUARD=0 and 1 gives only missing-submodule errors. This parse does not qualify anything.

Owner decisions this packet answers (DECISIONS_FOR_CLAUDE.md):
- 16:43:07: ONE six-slot architecture 33ce59d2f for source/model work, with a concrete diff, equations, proof plan,
  per-stage FF/enable/reset/native-contact budgets, ready timing and a consumer audit before any map/build.
  No APIPE2 alias, no competing fix, no native/cold/gate.
- 16:58:23: an explicit fail-closed first/nkeys-multiple-of-16/final-group-padding descriptor contract, grounded in
  the actual producer (lines 213-216). The packet must give the exact fault/drain/acceptance behaviour and a producer
  proof. The malformed 1-key/2-beat AP0 ready-dependent extra-operation counterexample and the AP1 difference stay
  preserved. No silent legacy fix and no universal-equivalence claim.

Branch: claude/qe3-hroot-sixslot-1021, base 539e8df61 (engine b491, the selected source).
- Commit 1 adopts Codex's uncommitted WIP from codex-hroot-registered-stream-1021 (hand-back 17:03) without changes.
  It also fixes the generator so that it reproduces the engine byte-for-byte.
- Commit 2 adds the guard and the wrapper plumbing.

The old architectures are unchanged. Every new behaviour is opt-in, and every default stays 0:

| Parameter | Default | Default behaviour |
|---|---|---|
| SPIPE6 | 0 | The engine is legacy 539/b491. |
| IKEY_GUARD | 0 | The shell is legacy 6a295b47. |
| qm/eng/shell SPIPE6 | 0 | The selected assembly is unchanged. |

## 1. Concrete diff (source.diff, 5 files, +217/-27 vs 539e8df61)

| File | SHA256 (539) to SHA256 (this) | Change |
|---|---|---|
| rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv | b49162d8 to 999bf9c2 | SPIPE6 P0..P5 + prep, ready chain, drain/done, dispatch interlock, busy; refusal of any other parameter shape |
| rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_ingest_cdc_shell.sv | 6a295b47 to b56ae297 | IKEY_GUARD: bad_ikey, take_d/hx_pop gating, sticky fault code 8 |
| ingest_split_1021/qkd_hr_ingest_shell.v | f25c4438 to fcf1b1ca | parameter SPIPE6, passed as .IKEY_GUARD(SPIPE6) |
| ingest_split_1021/qkd_hr_ingest_eng.v | 636336c7 to c5face92 | parameter SPIPE6, passed to the behavioural engine; the native32 (old 539) netlist branch REFUSES SPIPE6!=0 (no old-view alias) |
| ingest_split_1021/qkd_hr_ingest_qm.v | 29b36e20 to cdb4fd30 | `parameter SPIPE6 = 0` drives both children together, so the engine contract and the guard cannot be split |

Generator: tools/qwen_kv_die/hroot_registered_stream_1021/prepare_source.py. It asserts base b491 and regenerates
the engine exactly (999bf9c2).

## 2. Equations

### Descriptor preparation

Let D be the edge at which `s_disp` takes the descriptor; after D, `st_d` holds it. All arithmetic is unsigned
modulo 2^32.

| Edge | Registered values |
|---|---|
| D+1 (`sp_prep==1`) | `ring_lo = add16(st_d[127:112], 0xFFFF, 0)` (17 b, with carry). `ring_nz = (st_d[143:112] != 0)`. `ns_mask = (1 << st_d[233:232]) - 1` (3 b). |
| D+2 (`sp_prep==2`) | `ring_mask = {add16(st_d[143:128], 0xFFFF, ring_lo[16])[15:0], ring_lo[15:0]}`, which equals `st_d[143:112] - 1`. `const_valid = 1`. |

`const_valid` is cleared by `s_disp` and by `!st_act`. P0 accepts nothing until `const_valid` is set. This is
uniform across RAW, ROWS and IKEY; there is no RAW bypass.

### P0 snapshot and terms

P0 captures at the edge where `st_go = st_adv && sp_ready[0]`. It snapshots:
- base = d[47:16], stride = d[79:48], mask = ring_mask, row = st_row, rnz, pitch = d[84:80], sec = st_sec,
  ldie = d[217:216], lns = d[233:232], mode, nsm, ph;
- data = st_wd, write = st_wv, poison = knownness(st_wa).

From the snapshot, define:
- `gd = (row >> 4) >> ldie`
- `gs = gd >> lns`
- `stk = gd[2:0] & nsm`
- `local = rnz ? (row & mask) : ((gs << 4) | (row & 15))`
- `sb = gs >> 6`
- `qgroup = 1 + gs[5:2]`

The term vector `T[0..9]` (unused terms are 0) is:

| Mode | T |
|---|---|
| RAW | base, row |
| ROWS | base; `rnz ? 0 : (stride << i) & stk[i]` for i = 0..2; `(local << i) & pitch[i]` for i = 0..4; sec |
| IKEY ph 0/1 | base; 3 stride partials as ROWS; `sb << 11`; `sb << 7`; `qgroup << 7`; `gs[1:0] << 5`; `(row & 15) << 1`; ph |
| IKEY ph 2 | all zero (a no-write token) |
| IKEY ph 3/4 | base; 3 stride partials; `sb << 11`; `sb << 7`; `gs[5:0] << 1`; `(ph == 4)` |

### Equivalence to the legacy source, term by term

| Legacy expression (539) | Equals | Reason |
|---|---|---|
| ROWS `s_raddr + st_sec` | `base + (rnz ? 0 : stride*stk) + local*pitch + sec` | `af_mul3` and `af_mul5` are exactly the masked shift partial sums. |
| IKEY `k_code + ph` | `k_blk + ((1 + q[5:2]) << 7) + (q[1:0] << 5) + ((row & 15) << 1) + ph`, where `k_blk = rbase + (sb << 11) + (sb << 7)` and `q = gs[5:0]` | Expansion of the legacy formula. |
| IKEY `k_scal + (ph == 4)` | `k_blk + (q << 1) + (ph == 4)` | Expansion of the legacy formula. |

### P1 to P5

| Stage | Captures |
|---|---|
| P1 | `sum1 = reduce10(T)`: two 3:2 CSA layers, 10 to 7 to 5 operands (160 b). |
| P2 | `sum2 = reduce5(sum1)`: three CSA layers, 5 to 4 to 3 to 2 (64 b). |
| P3 | `{c3, low3} = add16(sum2[15:0], sum2[47:32], 0)`; `hx3 = sum2[31:16]`; `hy3 = sum2[63:48]`. |
| P4 | `addr4 = {add16(hx3, hy3, c3)[15:0], low3} ^ {32{poison3}}`. |
| P5 | `addr5 = addr4`, plus data and write. The output registers are `w_addr = addr5`, `w_data = data5` and `w_v = v5 & write5`, each gated by the existing QKV mux. |

The CSA invariant gives `sum(T) ≡ a + b (mod 2^32)` at every layer, because each 3:2 layer conserves the sum and
the carry shift-out is modulo 2^32. The two 16-bit adds with a registered carry give the full 32-bit sum.

### Ready, valid and acceptance

```
ready5 = !v5 || !write5 || w_rdy                   // a no-write token never waits for w_rdy
ready_j = !v_j || ready_{j+1}   (j = 0..4)
v0 <= st_go          when ready0
v_j <= v_{j-1}       when ready_j
data/address stage j captures only when ready_j && v_{j-1}   (frozen otherwise; stable while blocked)
st_go = st_adv && ready0        (source state, ra pointers and sc_acc advance on P0 acceptance)
drain_edge = !(|v[4:0]) && (!v5 || ready5)
```

`nsec` counts `w_fire = w_v && w_rdy` only, which is external retirement. The segment ends at an st_pad edge with
`(st_beats == 0 || (pad_take && st_beats == 1)) && drain_edge`. That edge sets `done_pending`, and the next edge
pulses `done_r` with tag `st_d[15:8]` if fence `st_d[7]` is set.

`busy |= (!sp_empty || done_pending)`. Both `s_disp` and `q_disp` require `sp_empty && !done_pending`, so:
- no QKV descriptor, new stream descriptor or BOOT_END marker can overtake an unretired stream operation;
- the shell's `mark_go` already needs `!e_busy && !e_wv`.

## 3. Ages and programme price (stall-free)

| Event | Edge |
|---|---|
| Descriptor take | D |
| First possible P0 acceptance | D+3 |
| Captures P1..P5 for an op accepted at E | E+1..E+5 |
| First external write accepted | E+6 = D+9 (versus D+1 for APIPE0 and D+2 for APIPE1: +8 and +7 edges) |
| N ops issued | D+3 .. D+N+2 |
| Last write retired | D+N+8 |
| done visible | after D+N+9 (sampled by the shell at D+N+10) |
| Steady state | 1 op issued and 1 op retired per edge; no per-row or per-key refill bubble, unlike APIPE1/2 |

At 1666.667 ps the startup cost is 13.333 ns versus APIPE0, or 11.667 ns versus APIPE1. Each segment pays it once,
and so does the drain before the next dispatch. ROWS segments pay the same +8 edges per descriptor.

Programme ages must be recomputed from the actual operation sequence, including phase-2 and non-owned no-write
tokens and the padding beats. Old calendar rows are NOT adopted.

The six slots buffer up to six operations beyond a `w_rdy` stall. The shell's ox FIFO (2^OFA = 16) and its credits
(OCRED/o_cr) are unchanged. An inflight maximum of 6 is added in front of them, so static credit schedules must
include it.

## 4. Per-stage FF / enable / reset / native-contact budget (logical_load_budget.json)

| Stage | Unreset FF | ASR FF | Data enable | Enable groups at 32 loads (min / at 30) | Reset contacts |
|---|---|---|---|---|---|
| prep (lo17, mask32, nz, poison, nsm3) | 54 | 0 | sp_prep==1 / ==2 | 2 / 2 | 0 |
| P0 (151 addr + 256 data + write + poison) | 409 | 1 (v0) | st_go | 13 / 14 | 1 |
| P1 (sum1 160 + 256 + 2) | 418 | 1 | ready1 && v0 | 14 / 14 | 1 |
| P2 (sum2 64 + 256 + 2) | 322 | 1 | ready2 && v1 | 11 / 11 | 1 |
| P3 (low16, hx16, hy16, c + 256 + 2) | 307 | 1 | ready3 && v2 | 10 / 11 | 1 |
| P4 (addr32 + 256 + write) | 289 | 1 | ready4 && v3 | 10 / 10 | 1 |
| P5 (addr32 + 256 + write) | 289 | 1 | ready5 && v4 | 10 / 10 | 1 |
| prep phase (2) + const_valid | 0 | 3 | dispatch | 0 | 3 |
| done_pending | 0 | 1 | pad && drain | 0 | 1 |
| **Total** | **2088** | **10** | | **70 / 72 enable copies** | **10** |

I recounted every row against the RTL; all of them match. The P0..P5 data enables are copy trees at 32 loads or
fewer. The ready-chain fan-out (`sp_ready[j]` into 10..14 groups each) is the dominant new native contact. All 10
ASR controls sit on the engine's existing `rst_n` reset leaves; there is no new reset domain or release age.

The old 35-leaf reset copy certificate and the old native32 netlist are NOT carried over: the netlist branch
refuses SPIPE6. A strict selected-wrapper native census at 32 or fewer per driver must be measured on a regenerated
netlist after approval.

The guard adds no FF. It is one 17-bit add (`(g << 4) + g`), a 17-bit equality and two 4-bit zero tests on the
host-FIFO head. These run in parallel with the existing bad_native 32-bit add-compare on the same head, so take_d
gets no deeper than the existing bad_native depth.

## 5. Ready timing (engine clock 1666.667 ps)

| Path | Logic depth | Notes |
|---|---|---|
| `w_rdy` pin to `st_go` | about 8 levels | ready5 (1 level), ready4..ready0 (5 levels, one OR/AND each), st_go (1), the existing `st_adv` merge (1). Legacy had 2 levels: `!st_wv \|\| w_rdy`, then `st_adv`. |
| `st_go` to the P0 enable trees and the source-state enables | about 2 levels | log32 trees over 13-14 groups, plus the existing st_row/st_ph/ra_rp/sc_acc enables. |
| `ready_j` to each stage enable tree | 1 AND + about 2 levels of tree | |

- `w_rdy = !ox_full` is a registered async-FIFO flag in the shell. It arrives through the engine-face pin, which is
  not pin-registered, because it is the ready signal. An estimate of 12 levels at about 30 ps each is about 360 ps
  of logic, plus the face wire. This is an estimate, not an STA result.
- The address stages are cut at these points: the 2-layer CSA (P1), the 3-layer CSA (P2), and two 16-bit
  Kogge-Stone carries (P3/P4). Each targets about 600 ps or less as a scalar. This is plausible but unmeasured.
- Measured context, retained for comparison:
  - legacy -810.5 ps at real 1666.667 (TT 1238.6 ps/37 levels);
  - late-ring 1085.2/34;
  - APIPE1 output 1051.9/32 and internal 1183.6.
- Risk: if the measured `w_rdy` to enable path dominates, the structural remedy is a registered-ready skid at P5.
  That would be a separate owner decision and is not proposed here.

## 6. Exact IKEY fail-closed contract (shell IKEY_GUARD, OWNER 16:58:23)

```
bad_ikey = IKEY_GUARD && mode == 3 && ( n0[3:0] != 0 || n2[3:0] != 0 || {1'b0, nb} != 17 * n2[15:4] )
           where n0 = d[167:144], n2 = d[199:184], nb = d[255:240]
```

Behaviour when bad_ikey is set:
- `take_d = 0`, so the engine never sees the descriptor.
- `hx_pop = 1`, so the descriptor is popped and dropped.
- `f_code <= 8` if no earlier fault is set. Priority after 1/2/7 is the same "first fault wins" rule.

Once a fault is set:
- the shell's existing fail-closed path pops every host word (`hx_pop = 1` when `f_any`), so all later payload is
  drained and dropped;
- the completion stream sends `{8'hFF, 48'b0, 8'd8}` once;
- `service_faults` is raised through the existing `fs`/`fault_c` synchronisers.

There is no new opcode, port or epoch.

Acceptance: a legal IKEY descriptor (all three conditions hold) is accepted exactly as before. `nkeys = 0, nb = 0`
is legal and is the existing empty segment. When `nkeys > 61680`, the count needs 17 × groups > 65535 beats, which
the 16-bit nb field cannot hold. Such a descriptor is rejected by the 17-bit compare, which is fail-closed.

Producer proof. Sources: tools/rtl_hdc_kv_ingest_campaign.py `case_ikey` lines 213-216 (sha 184f63ac) and
tools/kv_ingest_ref.py (sha 9cc66372).
1. The producer asserts `first % 16 == 0` and `nkeys % 16 == 0`, and pads the short final group.
2. It sets `nb = len(beats_of(68 × nkeys bytes)) = ceil(68 × nkeys / 64)`. Because `nkeys = 16g`, this equals
   `68g/4 = 17g` exactly.
3. So every descriptor this producer emits passes the guard.

Engine invariant under the guard. At dispatch `row[3:0] = 0` and `left = 16g`, so `(row[3:0] + left) mod 16 = 0`.
Every key advance does `row++` and `left--` together, which preserves the invariant. Therefore:
- `left == 1` if and only if `row[3:0] == 15`.
- Phase 2 at `left == 1` always moves to phase 3, and phase 4 sets st_pad at `left == 1` (line 829).
- The one-edge window `left == 0 && !st_pad` (phase 2 with `row[3:0] != 15`) cannot be reached. That window is what
  creates the AP0 extra operation.
- `nb` equals the exact payload, so the engine never waits for beats that will not arrive (an `nb` that is too
  small would hang), and no beats are left over.

The rtl_rom_host_ingest_bench caller (1024/4096 keys) and the existing campaigns (4096 keys, and a cross-superblock
case of 1008 keys with first = 16000) all satisfy the contract.

Not claimed:
- The generic `kv_ingest_ref.desc` and the host-link class 1 can still carry arbitrary descriptors. The guard makes
  the selected SPIPE6 assembly fail closed on them; it does not make other producers correct.
- The legacy assemblies (IKEY_GUARD = 0) are unchanged.

## 7. Preserved counterexamples (not fixed and not hidden)

- **C1 (legacy AP0, IKEY_GUARD = 0):** IKEY with first = 0, count = 1, and a 68 B record padded to 2 × 64 B beats.
  After phase 2, `st_left = 0` and `st_ph = 0`, but `st_pad` is set only on the next edge (line 835). If 32 B or
  more of padding remains and ready = 1, AP0 issues an extra code operation on that edge. With ready = 0 it does
  not. The behaviour depends on ready.
- **C2 (AP1):** the APIPE1 refill bubble can suppress that extra edge, so AP0 and AP1 differ on C1.
- **C3 (six-slot without the guard):** lookahead can accept that operation while external ready is 0.
  - With IKEY_GUARD = 1 it is unreachable through the selected shell.
  - The standalone engine with SPIPE6 = 1 and an unguarded caller still has C3. It is recorded, not waived, and there
    is no transaction-equivalence claim for malformed groups.
- **ASR witnesses (separate quiescent-reset architecture, untouched here):** late o_cr OCR 8 to 9, TCRED 4 to 5, and
  coincident NBA. raw6, die boot and quiescence remain OPEN.
- **Timing (retained):** -810.5 ps, 1238.6/37, late-ring 1085.2/34 (+12.4%), APIPE1 1051.9/1183.6.

## 8. Consumer audit (CONSUMER_AND_INPUT_AUDIT.md, plus guard additions)

**Selected chain:** eng w_addr/w_data/w_v feeds eng_waddr/wdata/wv (plus 20 KW copies), then the qm wires, then the
shell engine face, then the cdc shell. Address and data are used only in
`ox_eng = {1, e_waddr, e_wdata}` and the per-chunk `ox_w = mark_c ? ox_mark : (e_wv_c ? ox_eng : ox_rd)`.

**SRAM capture:** the capture is `w_ce = ox_push = ox_wr && !ox_full`, where
`ox_wr = (e_wv && e_wrdy) || (e_rv && e_rrdy) || mark_go`. The P5 address and data that are held while invalid are
therefore never captured.

**Other consumers that ignore address/data:** markers need `!e_wv_c`, and f_code never reads e_waddr.

**Debt/outst, completion FIFO and BOOT_END mark_go:**
- debt/outst uses `rv` and `rd_v`;
- the completion FIFO uses `e_done`;
- BOOT_END `mark_go` needs `!e_busy && !e_wv`, and busy now includes every occupied slot and `done_pending`.

**QKV mutual exclusion:** w_v/w_addr are muxed by qk_wv first. A QKV and a stream write can never coexist, because
`q_disp` waits for `sp_empty && !pending` and `s_disp` waits for `!qp_busy`. If they did coexist, ready5 would take
w_rdy for the wrong source; the interlock excludes this.

**New ABI (OWNER-accepted 16:43):** while invalid, P5 holds its last captured address and data. Before the first
valid capture, the payload bits are unreset and may be X; valid is reset to 0. Invalid-cycle raw-address
observability differs from AP0, and debug traces WILL show the held values. Raw-pin harnesses that compare against
AP0 are not valid equivalence evidence; they need a held-word reference.

**Other direct-origin users:** qkd_host_native_qm, qm_debt, qkd_hr_native_qm_cdc and the SRAM-ref fork all keep
the defaults (SPIPE6 = 0), so they are unchanged.

**Guard consumers:**
- f_code 8 reaches the host fault word and `service_faults`. Host software must decode code 8 as "malformed IKEY".
  This is documented in the shell's fault-code list.
- There is no other consumer.

## 9. Proof plan (only after owner approval; bounded, reusing existing benches)

| # | Obligation | Method |
|---|---|---|
| P1 | Arithmetic: for all 32-bit operands, `reduce` + add16 pair equals legacy `s_raddr + sec`, `k_code + ph` and `k_scal + (ph == 4)` | Yosys SAT/equiv on the combinational functions (bounded, quick) |
| P2 | 4-state knownness: an X in any legacy operand gives an X address | Reuse the prior poison-witness method on the actual source |
| P3 | Transactions: the ordered `(addr, data)` write sequence, n_sectors and done tags equal the legacy APIPE0 sequence for legal descriptors, under random `w_rdy` stalls | Existing campaign cases (IKEY 4096 / 1008 cross-superblock, ROWS, RAW) on the behavioural engine |
| P4 | Elasticity: no loss, duplication or reordering; P5 stable while `v5 && write5 && !w_rdy`; a no-write token retires without `w_rdy` | Scoreboard plus assertions in the same bench |
| P5 | Drain/done: done only after the last retirement and the padding; no dispatch, QKV or marker while slots are occupied; the stall-free ages in §3 | Same bench |
| P6 | Guard | Shell bench: three malformed descriptors (first = 1; count = 1; nb off by 1) each give f_code 8, `e_dv` never pulses, there are no writes, and the stream drains. Legal descriptors are unchanged. C1 is reproduced with IKEY_GUARD = 0 (preserved witness). |
| P7 | Reset | Async reset clears v/prep/const/pending. No issue before const_valid. X-init and random-init of the unreset payload never produce `w_v` before the first valid. |
| P8 | Mutants that must FAIL | ready5 ignores `w_rdy`; carry3 dropped; done before drain; guard off with a malformed input; prep skipped (D+1 issue) |
| P9 | Then, and only then | ONE canonical unpinned map for per-stage depth; a regenerated SPIPE6 native32 netlist with a strict census at 32 or fewer and cold seeds; normal physical review before any gate |

## 10. Requested owner decision

Approve or reject this packet as written:
- the diff above, with SPIPE6 opt-in and IKEY_GUARD tied to SPIPE6;
- fault code 8;
- the +8/+7 first-write edges and the +E+7 done;
- the held-word ABI.

On approval, the next step is P1-P8 (bounded), then P9. There is no build before approval.
