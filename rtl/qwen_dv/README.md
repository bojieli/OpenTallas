# Q-DV slice (`qfd_dv_slice`) — port and function contract, step 1

This is the distributed-vector slice of the Qwen3-8B TP8 ROM compute die. The owner approved it on 2026-10-16. The spec is `results/arch/qwen_dv_1016/SPEC.md` on branch `claude/qdv-1016`, with placement dv2r/dv2r8.

The slice is one master, hardened once and replicated 12 times. It has:
- one regional clock root `ck`;
- a regional reset `rst_n`, synchronised inside (asynchronous assert, two-flop release);
- a pin register on every input and a register on every output.

Everything runs to a static schedule: no ready, no credits, no backpressure. A schedule violation sets a sticky fault (`st`).

## Sources reused (arithmetic is not re-implemented)

| function | reused RTL | golden |
|---|---|---|
| SU lanes (8) | `ot_hdc_vstream_static_entries #(SW 8, LV 4, WR 16, NW 18, ML 1)` → `ot_hdc_vstream_lane`. This is the Qwen ROM die's SU core (the `qfd_sp_su64_sfu` body at SW 64): `ot_hdc_qadd`/`qmul` (`ot_hdc_fastfp`), `ot_hdc_exp_q`/`recip_q`/`rsqrt_q` (`ot_hdc_sfu_q`) | `tools/hdc_isa.py` element pipeline, `hdc_golden` add/mul/exp/reciprocal/rsqrt |
| block sums | `ot_hdc_vreduce` (R-ARITH csum8, SW 8, segments ≤ 128) | `hdc_golden.reduce_chunked` |
| tree levels 7/8/9 | `ot_hdc_fp32_add_lat #(LAT 7, DRST 0)` × 16 per level (the `qfd_slab_pair_add` adder) | `hdc_golden.matvec` split order |
| row scale | `ot_hdc_fp32_mul_lat #(LAT 6)` × 16, `b = {scale_bf16, 16'h0}` or 1.0 (wsrc). This is the `ot_qwen_me_spport_w12` soft post-scale (bit-identical to `ot_hdc_fmul`) | `mul(t, s)` |
| root combine | one `ot_hdc_qadd`: pairwise over the 32 block sums, padded with +0 | `reduce_chunked` top levels |
| memories | `ot_sram_1r1w_1024x256_m2_r2c2` (the VM macro), `ot_sram_1r1w_128x256_m1_r2c2`, `ot_sram_1r1w_256x256_m2_r2c2` | — |

The Qwen ROM die golden is `hdc_golden` / `hdc_isa`, not the HBM r25 `hgi_sim.lib`:
- **rsqrt:** Newton (seed `0x5F3759DF`, 3 steps).
- **SiLU:** `g × recip(exp(−g) + 1)`, with recip Newton (seed `0x7EF311C7`, 3 steps), then `× u`.

This is **not an IEEE divide**. The brief's "IEEE divide" is the r25 HBM contract. Bench (e) reports how many values differ between the two forms.

## Arithmetic order (bit-exact; class A)

- **RMSNorm, global.**
  1. Each slice runs its own rows in 128-row blocks. Each block sum is `csum8(x·x)`: 16 chunks of 8, each summed in sequence from +0, then a 16-leaf pairwise tree. That is an aligned subtree of the 512-chunk tree.
  2. A PSUM word carries each block sum to the root.
  3. The root does the pairwise top 5 levels, then the SU computes `rsqrt(S·fp32(1/4096) + fp32(eps))`.
  4. `r` is broadcast as an RB word.
  5. Each slice computes `h = (x·r)·g`, where `g` is the FP32 value of the BF16 gain from CROM lo.
  6. `h` is converted to BF16 by RNE, `(b + 0x7FFF + b[16]) >> 16`, and sent as 64-element stream words.
- **Residual.** `x ← x + t`, where `t` is the all-reduce result landed from the AR port. The add chases the sum of squares (`red_sq`). It is replicated identically on each side's replica.
- **Matvec levels.**
  - Level 7 is `cw0 + cw1` (left + right sibling).
  - Level 8 is `L7(lower pair, held 8 words) + L7(upper pair)`.
  - Level 9 is `L8(own, even g) + L8(neighbour, odd g)`.
  - The result is then multiplied by `bf16 scale[sbase + j]`.
- **QK-norm + RoPE (per 128 head).** These are the `hdc_program` non-fold ops:
  - `SS = csum8(q·q)`;
  - `RS = rsqrt(SS/128 + eps)`;
  - `QN = (q·RS)·g`;
  - `lo = a·cos + b·(−sin)`, `hi = b·cos + a·sin`. K takes FP8 E4M3 in the lane (`DST_KV`).
- **SiLU·up.** `MA_AIMM(−1)` → SIGM → `×g` (MC) → `×u` (MD).

## Ports

| port | dir | bits | format |
|---|---|---:|---|
| `cmd` | in | 116 | `[0]` go, `[3:1]` kind. The kinds are below this table. |
| `cw0`, `cw1` | in | 514 each | `{fault, valid, 16×FP32}`: left/right cluster word of one level-7 pair, same edge |
| `nb9_i` / `nb9_o` | in/out | 514 | neighbour level-8 word (L9 receiver in / L9 sender out) |
| `sw_i`/`so_e`, `se_i`/`so_w` | in/out | 1,088 each way | `[1023:0]` payload, `[1087]` v, `[1086:1084]` kind (0 X: 64 BF16; 1 CROM; 2 BTAB; 3 PROG), `[1083:1080]` dst (15 = all), `[1079:1076]` src, `[1075:1052]` eaddr, `[1051:1024]` tag. Relayed one slice per edge; table words with a matching dst are tapped. |
| `sc_i` / `sc_o` | in/out | 96 | `[95]` v, `[94:92]` kind (1 PSUM, 2 RB), `[91:88]` src, `[87:64]` idx, `[31:0]` value. Ring semantics: pass + insert + tap; the root absorbs PSUMs; an RB is absorbed at its source. |
| `ar_o` | out | 546 | `{valid, tag 32 (row element address), last, data 512}`: station results routed to the AR |
| `ar_i` | in | 518 | `{valid, err, rank 3, last, data 512}` (the `qfd_seq_su_static` `cc` format), landed at `ar_base + 16k` |
| `dd_o` | out | 548 | `{valid, kind 2 (0 q/act, 1 K, 2 V), mask 8, 8 × addr 24, 8 × FP32, 89 × 0}` to native59 |
| `dd_i` | in | 520 | `{valid, group, beat 6, data 512}` (the native59 `vm_ar` format), landed at `dd_base + 16·{group, beat}` |
| `sid` | in | 4 | slice-id strap |
| `st` | out | 45 | `{any, su, vm, stn, sc, stm, port faults, su_idle, root_busy, su_progress 16, su_rows 16, ar_rank 3, ar_last}` |

The `cmd` kinds:

| kind | name | fields |
|---:|---|---|
| 1 | SU | `pidx [12:4]`. The 457-b SU issue word, in the `qfd_seq_su` `su[456:0]` layout, comes from the program store. Go reaches the SU 2 edges after the pin register. |
| 2 | STN | mode `[5:4]` (0 L7, 1 L8, 2 L9 receiver, 3 L9 sender), wsrc `[6]`, nwords `[14:7]`, sbase `[23:15]`, dst `[25:24]` (bit 0 VM, bit 1 AR), dbase `[49:26]` |
| 3 | ROOT | root `[4]`, nb `[10:5]`, ss `[34:11]` |
| 4 | PORTS | ar_base `[27:4]`, dd_base `[51:28]` |
| 5 | STREAM | dirs `[5:4]`, tag `[33:6]` |

SU write windows are set by address bits `[23:22]`:

| window | destination |
|---|---|
| 00 | VM |
| 01 | stream x packer (BF16) |
| 10 | D2D out |
| 11 | VM, plus a scalar RB broadcast |

The reducer uses two windows: 00 (VM) and 11 (PSUM).

## Local memories (`qfd_dv_vm`)

| memory | organisation | macros |
|---|---|---|
| VM | 3 operand replicas × 2 banks × 1024 × 8 FP32 = 16,384 FP32 | 6 × 1024x256 |
| CROM | 16,384 (lo, hi) FP32 pairs | 4 × 1024x256 |
| BTAB | 2 copies × 512 words × 16 BF16 | 8 × 128x256 |
| PROG | 512 SU instructions | 4 × 256x256 |

The tables are SRAMs, written from stream table words at boot (RoPE rows per token). This keeps one master for all 12 instances. Mask ROMs would make each instance a different master.

## Not built in step 1 (no tied ports were added for these)

- **The 4 column-corridor words (516 b).** These need the `ot_qfd_xhead` column-slice control (epochs, tile windows, x leaves). The SPEC keeps the 48 column heads and feeds them from the stream. The slice emits the X stream words; the corridor face is left to a later step.
- **The LM-head running argmax** (per slice) and the argmax scalar-tree kind.
- **The gather-exit** (`qfd_dv_gather_exit`).
- **Die-level tree topology.** The scalar port is a single in/out ring/chain; a fan-in tree would need a second input.

## Boundary timing (FLOW-HOLD, `results/arch/boundary_hold_budget_1016/RULE.md` on `claude/flowhold-1016`)

The slice is a recipe-4 tile with `"hold_budget": "die"`.
- **Inputs.** Every input pin goes straight into a flop: `cmd`, `cw0`, `cw1`, `nb9_i`, `sw_i`, `se_i`, `sc_i`, `ar_i`, `dd_i` and `sid` land in the pin registers of `qfd_dv_slice`, and `rst_n` lands in the reset synchroniser's first flop.
- **Outputs.** Every output comes straight from a flop.
- **No pads.** There are no inhold/outhold pads, and no hold buffer on input pins. Hold is budgeted on the die relay stations.
- **Sign-off.** Input min = L_min + C + U and output min = U − (L_min + C), with C = 25 ps and U = 25 ps. Setup is unchanged.
- **No opt-out.** The slice has a single clock domain and no CDC/async leaf.

## Step 2 (2026-10-17)

### Root combine (`qfd_dv_scalar`)
- **Tree.** The sequential ~70-cycle combine is replaced by a pipelined 5-level pairwise tree of `ot_hdc_qadd`, the SU's adder: 16 + 8 + 4 + 2 + 1 adders over the 32 block slots.
  - Slots past nb hold +0, and x + (+0) = x exactly, so the result equals the golden tree padded to p2ceil(nb).
  - Trigger to total takes 15 edges.
- **Fused r.** With ROOT `fuse` set, the root itself forms `r = rsqrt_q(qadd(qmul(total, 2^-k), eps))`, using the SU op's primitives and order. It then broadcasts r.
  - Measured: last block sum out of a neighbour → r out of the root = **61 cycles** (ring 2 + trigger 1 + tree 15 + 1/n 3 + eps 3 + rsqrt 37). The old path was ~70 plus an SU rsqrt op (~60).
  - The 3-step Newton rsqrt of the golden alone is 37 edges at LA = LM = 3, so the ~25-cycle target holds only for the tree to the total (15 + 3).
- **Root cmd fields.** fuse `[35]`, rx `[59:36]`, eps `[91:60]`, k `[96:92]` (1/n = 2^-k), amnb `[102:97]`; slice2 adds rdir `[103]`.

### LM-head argmax
- Station results of an op armed with STN `amax` (cmd `[50]`) feed a 16-leaf, 4-level compare tree, then the running best per slice. The order is the `ot_qwen_me_spport_w12` key order, ties to the lower index.
- AMAX cmd (kind 6): `[4]` clear, `[5]` emit the candidate.
- The root merges amnb candidates and sends a TOK word.

### Station skew
`cw0` is the far port and `cw1` the near port. The near word passes a fixed `SKEW` (14) edge line, so the far word arriving 14 edges later meets it at level 7.

### Column heads (`qfd_dv_heads`)
- One existing `ot_qfd_xs_tap`, 4 `ot_qfd_xhead` and 32 `ot_qfd_xs_leaf`, all unchanged.
- **Input.** The tap is fed from every x stream word the slice sees, as `{bf16, 0}`, plus `hr = {go, ib 379, xpf 72}`.
- **Outputs.** 8 corridor words: n_d goes to the band-2 cluster, s_d to the band-1 cluster.
- **Tile ids.** Column = 4·sid + i, using the die's TIDM-1 map.
- **Bench.** `run_heads.sh` checks against the existing `ot_qfd_xdvm_fabric` (NCOL 48, tap fed the FP32 x).

### SU delay line
`qfd_dv_su8_entries` is `ot_hdc_vstream_static_entries` with one pass-through parameter, TLS (default 1): the lane's tapped line moves to its existing SRAM ring.

### Benches
- `run_all.sh`: positive (a)–(g), plus mutants 1–7.
- `run_heads.sh`: the heads bench, plus mutants 8 and 9.

## qfd_dv_slice2: the dv2r8f2 die port cut (bound by Q-DIEPLAN3)

Children are the same apart from three:
- `qfd_dv_redstn2`: both level-7 pairs arrive in parallel; the up block of gate/up waits in an 8-word buffer.
- `qfd_dv_scalar2`: a 48-b scalar chain both ways, with a 2-beat argmax candidate and RB destination rx from the ROOT cfg.
- The command and return chains.

| port | bits | contract |
|---|---|---|
| `cmd_i` / `cmd_o` | 116 | Chain W5→E5, 2 edges a hop. `[115:112]` dst (15 = all). SETID (kind 7) latches id `[7:4]` and forwards id+1. |
| `hr_i` / `hr_o` | 453 | `{go, ib 379, xpf 72, hr_v}`. `hr_o` is the pin register (1 edge a hop). |
| `rs_s` / `rs_n` | 1,028 | `{far rs_o, near rs}` of the band-1 / band-2 cluster. Far words come 14 edges after near. |
| `l9_i` / `l9_o` | 514 | level-9 neighbour word |
| `st_up_*` / `st_dn_*` | 1,088 | stream toward E5 / toward W5 |
| `sc_up_*` / `sc_dn_*` | 48 | `{v, kind 3, tag 12, value 32}`. Kinds: PSUM, RB, AMI, AMV, TOK. |
| `ch_up_i` / `ch_dn_o` | 1,094 | outbound `{AR 546, D2D 548}` toward W5. At W5, AR goes to io_collective and D2D to native59. |
| `ch_dn_i` / `ch_up_o` | 1,038 | return `{AR ret 518, D2D ret 520}`, 1 edge a hop. D2D ret `[518]`: 0 = attention (dd_base + 16·beat), 1 = embedding row (em_base + 16·k). |
| `cw_n0..3` / `cw_s0..3` | 516 | corridor words |
| `st` | 74 | status: `{sid, faults, ...}` |

PORTS cmd: ar_base `[27:4]`, dd_base `[51:28]`, ar_en `[52]`, dd_en `[53]`, em_base `[77:54]`, em_en `[78]`.

**Chain-end inputs take the idle word, all zero.** These are E5's `ch_up_i`, `st_dn_i` and `sc_dn_i`, and W5's `st_up_i` and `sc_up_i`. An all-zero word means "no word" on each of these ports, as with the outermost `fault_i` termini.

**Benches.** `dv_bench2.py` runs (a)–(g) on the chain ports, plus (h): SETID enumeration of 12 slices. MUT 10, where the forward does not increment, must fail (h).

## q3h SU reference latency (item 6, 2026-10-17)

`run_q3h_lat.sh` / `tb_q3h_su_lat.sv` run the q3h SU64 core (`ot_hdc_vstream_static_entries` SW 64, LV 7, ML 15, LT 1, RED_ENTRIES 1) on a behavioural VM: residual + sum of squares over 4,096, then the r = rsqrt op. PASS (r matches hdc_golden). Verilator build ~30 GB, run on the fleet.

| path | q3h SU64 | DV slice |
|---|---:|---:|
| last vector issue -> SSX / last PSUM | 142 | <= 67 (bench g) |
| -> r | 2 + 117 (separate rsqrt op) + IS/OS 2 | 61 (fused root) |
| **last vector issue -> r** | **263** | **<= 128** |

Per RMSNorm the slice is 135 edges shorter; 2 norms a layer give -270 cycles/layer, which the dv2r8f5 ledger (-66, root compute assumed to cancel) did not count: **dv2r8f5 = -336 cycles/layer vs q3h**. Record: `results/arch/qwen_dv_slice_1017/q3h_su_lat.json`.
