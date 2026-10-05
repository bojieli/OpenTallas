# Qwen3-8B ROM: full-bandwidth KV path (4 HBM3E stacks a die, STREAM4)

Owner rule: every HBM load reaches >= 90 % of the attached stacks' peak.  Qwen ROM weights are on-die ROM; the only
HBM load is the KV window (FP8, 2 KV heads a die, 4 MiB a layer at P = 8191).

Peak a die: 4 stacks x 32 PCs x 32 B / 1.024 ns (controller CK/2) = 4.000 TB/s = 104.2 sectors a 1.2 GHz core cycle.

## Standalone service bench (standalone/, final RTL with the hardened per-tile landing merge)

`rtl/test/qwen_rom_runtime/realmem/tb_qwen_rt_kv_stream4.{sv,cpp}`: ot_qwen_rt_kv_stream4_service +
ot_qwen_hbm_stream4_ack (4 x ot_hbm_r14_stream_stack RTL, WR_EN=1, picosecond DRAM checker, 0 violations), every
slice word of the 1,536 tiles and the written-back token K/V checked against an independent map.  15/15 PASS.

| case | fill cycles | sectors/cycle | TB/s | % of 4.000 TB/s peak |
|---|---|---|---|---|
| ISO P8191 (whole window, first-sector latency included) | 1,353 | 96.88 | 3.720 | 93.0 % |
| ISO P4095 | 715 | 91.66 | 3.520 | 88.0 % (latency share larger) |
| before (REAL_MEM, 1 stack, realmem-ctx8k P8191 L0) | 9,893 | 13.25 | 0.509 | 12.7 % |

Cross-layer prefetch (early_go: next layer's stream released at kv_free) + posted write-back:
CHAIN_P8191_early_posted B fill exposed after start = 0 (kv_ok 65 cycles after start vs 1,740 without the straps);
with only 400 MLP cycles the exposure is 912 = 1,312 - 400.

Landing: per-tile merge `rtl/hdc/kv/ot_qwen_kv_land_merge.sv` (<= 12 sources a tile under the striped map); lockstep
vs the service's rule: 200,000 random cycles, 0 mismatches (standalone/land_merge_lockstep.log).

## Runtime, one layer at P8191 (runtime_P8191/, exact vs the GPU golden realmem-ctx8k/gold/P8191)

TP4 REAL_MEM runtime with the STREAM4 die (tools/qwen_rom_rt_token_stream4_w12.py, AR256, WBW 4), X of all 4 dies and
the token K/V written back to HBM bit-exact.  The whole 8K history (8,191 positions, 131,072 sectors a die) is read with
no fault (the one-stack HBM_STREAM path faulted at P >= 2048; P1023/P4095/P8191 bench cases and this run cover it).

| L0 isolated, P8191 | cycles | fill cycles | sectors/cycle | TB/s | % of 4-stack peak |
|---|---|---|---|---|---|
| REAL_MEM one stack (before) | 14,574 | 9,893 | 13.25 | 0.509 | 12.7 % |
| STREAM4 (this) | 6,468 | 1,348 | 97.23 | 3.734 | 93.4 % |
| KV_IDEAL (compute bound) | 5,290 | - | - | - | - |

## Tagged near-row read port on the SAME controllers / array (tagged/; for the combined STREAM4 die)

Additive successor backend `rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv` (top `ot_qwen_hbm_stream4_tagged`; the
`ot_qwen_hbm_stream4_ack` port list unchanged plus `t_*`), served by the same 4 x `ot_hbm_r14_stream_stack`
(new default-off `AQ_RD=1`: tagged reads enter each pseudo-channel's write-back queue = access queue, in order;
background to the stream with a 64-cycle starvation bound) and the same `mem`. Native hook
`tools/runtime/qwen_combined/stream4_tagged_rows_hook.cpp` (`bool qwen_stream4_wire_native_tagged_rows(Vdie&,Vhbm&)`,
pin wiring only; compile/link checked against the real Vhbm: tagged/hook_check.log).

Bench (`tb_qwen_rt_kv_stream4_tagged.sv` + `tb_qwen_rt_kv_stream4.cpp -DTAGGED`, t_clk 1.0 GHz beside the
1.2 GHz core, 4 clients, 16-sector reads of the current layer's history, every beat checked against `mem`):

| case | stream fill | stream % of 4.000 TB/s | tagged during fill | total % | tagged beats exact | DRAM violations |
|---|---|---|---|---|---|---|
| TAG_ISO_P8191_r5  | 1,387 cyc | 90.7 % | 0.072 TB/s | 92.5 % | 3,488 / 3,488 | 0 |
| TAG_ISO_P8191_r15 | 1,394 cyc | 90.3 % | 0.091 TB/s | 92.5 % | 5,520 / 5,520 | 0 |
| TAG_ISO_P8191_r30 | 1,393 cyc | 90.3 % | 0.092 TB/s | 92.6 % | 5,392 / 5,392 | 0 |

Slices and token write-backs exact in all; TAG_NEG_write (read-only port) and TAG_NEG_other_layer (not the current
descriptor row) fault as required.

## Stream-aware refresh pull-in (pullin/)

The prefetched (early_go) fill depended on the refresh phase: 1,310 .. 2,064 cycles (63 .. 100 % of peak) with the
strict REFpb schedule (forced REFpb of banks the stream needs). `ot_hbm_r14_stream_pc PULLIN=N` (default 0, lockstep
identical to main on 3 x 200k cycles) refreshes up to N REFpb ahead while not reading and skips that many slots
while reading. Phase sweep (pullin/phase_sweep.txt): worst B fill 2,064 -> 1,464 (N=8) -> 1,398 (N=16, 90.0 %),
typical 1,307 (96.3 %); 0 DRAM violations; full regression with N=16 15/15 PASS (pullin/).

## 8K token on STREAM4 (compose_P8191_token.json; runtime_P8191/*_p16; PULLIN 16)

Exact vs the GPU golden (X of 4 dies, token K/V of every layer). L0 isolated 6,489; chained with early_go +
posted write-back L0/L1/L2 = 6,044 / 5,282 / 5,282 (L1/L2 fill 1,311 cycles, exposed 0; KV_IDEAL 5,283).
Token = 7 + E + (L0 - 1) + 35 x 5,282 + (head - 1) + 37 = 194,498 cycles = 162.1 us = 6,170 tok/s per user
(REAL_MEM one stack, same formula: 580,968 = 2,066 tok/s; 2.99x). E (98) and head (2,999) from the P255 record.
Note: the chained record says status=fail only because the run tree's ack/pc/stack sources were overwritten by the
(default-off) AQ_RD successor after the binary was built; all numeric checks are 0 mismatches.

## DSpark verify on STREAM4 (dspark_verify_P8187/, dspark_step_stream4.json)

ot_qwen_rt_kv_stream4_mp_service + die ot_qwen_rom_rt_die_w12_vprm_stream4 + tools/qwen_rom_rt_vprm_stream4_w12.py,
the record's plan: step 1 P8187..8190 (np 4), commit 1 (rollback 8188..8190), step 2 P8188..8191 over the HBM the
RTL left: PASS exact (all X, kv blocks, tokens, accept). Verify layer 17,197 / 17,188 cycles (REAL_MEM 24,320 /
25,252), fill 1,362 cycles. Composed step (draft 169,925 from the record, tau 3.0375): 801,075 cycles =
4,550 tok/s per user = 0.737x AR-with-prefetch (6,170) on the same path; free-draft bound 0.936x.
VERDICT: at 8K on the full-bandwidth path the verify layer is compute bound; DSpark does not beat AR there.

## Physical (physical/)

ot_hbm_r14_stream_stack NCH=1 slice, 1.024 ns, WC setup / WC+BC hold: PULLIN=16 PASS (setup +18.7 ps, hold +5.3 ps);
PULLIN=16 + AQ_RD=1 (tagged reads) PASS (pc_aq3). The per-tile landing merge does not close yet (setup -0.75 ns
grant path at 0.833 ns, CTS hold repair exhausts buffers): OPEN item; the landing network remains modelled.

### DSpark update: third-party tau and the weight-reuse check

tau = 3.1445 (tools/third_party_tau.py, Qwen3-8B, 3 drafts): 4,710 tok/s per user = 0.763x AR with prefetch (free-draft
bound 0.969x). Per-cycle trace of the verify layer (dspark_verify_P8187/s1_trace): ME-busy 1.47x (attention) and 2.09x
(MLP) of AR for 4 positions, i.e. the ROM verify path does NOT apply each weight word to all 4 positions in one pass.
Lever: single-pass weight reuse, measured bound 2,144 ME cycles a layer (9.6% of the step); the bigger excess is
non-ME per-position work (8,564 cycles a layer). Detail in dspark_step_stream4.json verify_segment_breakdown.

## DSpark KV closure element (multi-position commit / rollback / visibility)

rtl/hdc/kv/ot_qwen_kv_mp_commit.sv: the synthesizable token-side control of ot_qwen_rt_kv_stream4_mp_service
(E4M3 encode, block visibility of K lanes / V rows, K tile select, V block row, open-tile mask, commit_n / ack-debt /
restart checks, committed_len). Lockstep vs the service's expressions (tb_qwen_kv_mp_commit.sv): 4 seeds x 100k cycles,
0 mismatches; mutation (committed_len off by one) FAILS as required. Route at 0.833 ns WC / WC+BC hold: see physical/.

DSpark KV closure: ot_qwen_kv_mp_commit (lane path registered at the boundary, decode stage 2; lockstep 4 seeds 0
mismatches with the 2-edge lane latency) routed at 0.833 ns (1.2 GHz) WC setup with 60 ps uncertainty / WC+BC hold
with 25 ps: PASS, setup +24.9 ps, hold +4.9 ps, 0 DRC, 3,043 um2 (physical/mp_commit_180_ss_ff.json; every IO
registered, IO paths false-pathed so the screen is the element's register-to-register timing).

## DSpark verdict at 8K on STREAM4: AR_MODE (dspark_verdict.json)

Verify levers, measured exact at P8187: MERGE_SU (one stream op for the positions where there is no DYN term) cuts
the np4 verify layer 17,197 -> 15,971 (-7.1%); np3 13,104; np2 9,942. Shared K/V passes give no gain (the KV op's time is
query slots x K steps; each position already fills the 8 slots; the attention time is the 1,023-cycle-per-position
softmax on the 64-lane stream unit). With the measured ingest/Markov (75,000) and third-party tau (1.84/2.54/3.14/3.66
for 1-4 drafts), the best DSpark configuration reaches 0.742x AR (np4, MERGE_SU); break-even verify layer 10,069
(np4) / 8,372 (np3). A true single-pass 4-position verify needs +103..165 mm2 vs the 46 mm2 margin.
