# S81/H23 (2026-10-24): COORD H2 (attn.idx.newkey, IK_ROW) + H3 (on-die SEL_IDS producer)

Branch `claude/s81-h23-1024r` (from `claude/s81-1024r@1e44e77664` + origin/main). COORD ruling 2026-10-24 22:00
(lanes/S81.md), source `claude/tok-ds-hwmtp-1024@d6dec66d5` results/token_pass/tokds_s81hw_mtp_1024/README.md H2/H3.
No partition pin added anywhere. Benches: Verilator 5.050 (daemon pin) via ot-run, epyc1 run dirs
`/srv/opentallas-scratch2/claude/s81-h23/j_*`.

## H2: svc_att q frame IK_ROW (type 15)

`rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv`. Header word (SVC FRAME PROTOCOL v1.1 q header) + 1 payload word:

| field | bits | meaning |
|---|---|---|
| type | [511:508] | 15 IK_ROW (was free) |
| END / mask / tag | [507] / [506:503] / [502:495] | as every frame (mask bit 0 = svc attention) |
| len | [491:480] | 1 (else fault_code[16]) |
| p | [479:459] | 21-b compressed position of the new key |
| user | [458:449] | user (carried; region base KB is per user) |
| scales | [63:32] | the key's 4 UE8M0 block scales |
| KB | [29:0] | index-key region base (HBM word address) |
| payload | [511:0] | 128 E2M1 codes of the key |

Address = **rg3's index-key layout** (as dsdv_idx_rg3 reads it and tb_dsdv_idx_rg3 preloads it): j = p >> 4,
i = p & 15, owner slice rg = i ^ j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12], PC = p[8], n = p >> 9, c = p[7:4],
a = KB + 34 n: codes[255:0] -> a + 2c, codes[511:256] -> a + 2c + 1, scales -> sector a + 32 + c[3], bytes 4 c[2:0] .. +3
(byte strobe).  Exactly one slice (sid == rg) writes; the 15 others drop the frame.  The writes use the OWN_ROW write
path (same wpush stage, same PC request ports), 3 writes per key.
**Note:** the README's PC formula ((s>>2)^(s>>7)^(s>>12)) mod 32 is svc_att's *host sector interleave*, not rg3's key
layout; rg3 reads keys at the layout above, so IK_ROW writes there.

Bench `svc_rs/test/tb_dsdv_svc_att_ik.sv` + `run_svc_att_ik.sh`: one dsdv_svc_att run as each of the 16 slices on the same q
stream (96 IK_ROW keys, p over [0, 2^20) with half >= 2^16 so the j[15:12] term matters, random KB / codes / scales,
interleaved with 24 OWN_ROW frames, random gaps; PC model credit +3 / write-done +5).  Golden = rg3 layout (TB model,
independent of the RTL); exact multiset of {slice, PC, addr, strobe, data}; every key written by exactly one slice;
negative: IK_ROW len 2 -> fault_code[16].

Result **SVCIK_GATE PASS** (logs/h2_ik.log): base seeds 1-3 PASS (1,056 golden writes, 0 extra / 0 missing, 0 faults,
every key by one slice, len-2 frame -> fault 16; the 3 extra writes in the count are the negative frame's, issued after
the check); mutants caught on every seed: mut4 (region hash without j[15:12]) 276-282 wrong writes, mut5 (scale byte of
c ^ 1) 96, mut1 (OWN_ROW regression mutant) 384.

Cells (yosys 0.68 ASAP7 RVT TT, engine blackboxed, PFIFO 8): dsdv_svc_att 50,557 -> 51,575 (**+1,018 / slice**, +70 flops;
budget < 3k).

## H3: on-die SEL_IDS producer (bk_sel -> seqhost -> svc entries 5 / 11)

1. **Encoder** `dsdv_bk_selids` (`idx/dsdv_idx_l20s.sv`, in `dsdv_bk_sel_vmtx`, same vo_s tap as the closed tree tx
   `dsdv_idx_tx_n32`, which is unchanged).  Job = CTL beat on vo_s: kind 0, p[7:0] = 0x5C, p[10:8] = **3** (SEL job; tx
   jobs are op 2), K = p[40:31] (1..512 ranks), OT = p[68:61] (the egress tag), mask = p[72:69].  Every IDX egress word
   (kind 5, part 0 + part 1, type 3, tag OT) -> 2 relay beats north, back to back:
   `[0] 1, [3:1] 0, [8:4] 0, [12:9] 0xB, [20:13] 0xA5 (relay marker), [21+21e +: 21] id of rank s_first+8·part+e (0 past
   s_cnt), [189] part, [199:190] s_first, [204:200] s_cnt = popcount(lv), [208:205] mask`.  Ids = the 20-b positions
   zero-extended (svc_att SEL_IDS ids are the compressed positions).  Faults (sticky): lv not a prefix, ranks > K, a SEL
   job CTL while one is open.  No SRAM.
   vmtx: relay beats join u_sel.vo_n in **one output register** (vo_n now leaves a flop: **+1 edge for every northbound
   bk_sel beat** on xtier__bk_sel__seqhost); a relay beat on a non-idle vo_n slot = sticky fault; fault output registered.
   Parameter SELE (default 1; 0 = pre-H23 master).
2. **Seqhost relay** `dsdv_sh_selr` (`unit/dsdv_seq_host.sv`, L0 dsdv_sh_lk, param SELR; `dsdv_seq_host_mux` (die master)
   SELR = 1, `dsdv_seq_host` / `dsdv_seq_host_mu` default 0): a landed relay beat (marker) is sunk from the north rung
   (never forwarded) and becomes one host-write word of **class 3** `{cls 3, we 0, addr {12'0, beat[208:189]}, d 8 × {11'0,
   id}, v}` on BOTH s_hw_w and s_hw_e (unit__seqhost__svc_5 / __svc_11, existing lanes) through one merge register;
   a relay word on a cycle with a host write = sticky fault (folded into the L0 status).  Cost: **host-write path +1
   edge** (s_hw_w/e leave the new merge register) in the die master.
3. **Entry** `dsdv_svc_selq` (`svc_rs/dsdv_svc_rs.sv`, ENTRY g_host of rsv_05 / rsv_11): class-3 words are kept off the hw
   stream; part 0 -> SEL_IDS header q word `{type 7, END 0, mask, tag 0, len 1, [19:10] s_cnt, [9:0] s_first}`, part 1
   (next edge) -> payload q word (16 × 32-b ids, rank s_first+e at [32e +: 32]); injected on the q part of the entry's
   r1 register after the svc job gate.  Sticky faults (into the slice fault): a job-gate q word in a relay cycle, part 1
   not on the next edge / meta mismatch, s_cnt 0 or > 16.

Bench `unit/test/tb_dsdv_selchain.sv` + `run_selchain.sh` (exact chain: real encoder -> +1 merge + 65-edge plan lane
-> real `dsdv_seq_host` SELR 1 -> 7 / 11-edge unit lanes -> entry pin flop -> real `dsdv_svc_selq` W and E).  Stimulus: 4
jobs (K 512, 7, random) of ascending random 20-b positions, partial last word, decoy words of another tag, a decoy tx
job (op 2), random gaps; plus non-relay northbound beats on the rung (must leave the seqhost north unchanged, relay
beats must not).  Golden = TB model of the SEL_IDS frames.  Negative: a job-gate q word on a relay word -> selq fault.

Result **SELCHAIN_GATE PASS** (logs/h3_chain.log): base seeds 1-3 PASS (110 / 162 / 138 golden q words at both
entries, exact, header->payload pairing 0 errors, 9-11 rung beats crossed the seqhost unchanged, 0 relay beats leaked
north, negative -> selq fault); mutants caught on every seed: selmut1 (encoder s_first frozen), sqmut1 (entry payload
halves swapped).

Cells (same flow; children blackboxed):

| block | base | new | delta |
|---|---|---|---|
| dsdv_bk_sel_vmtx glue (selector / tx / vmux blackboxed) | 3 | 3,272 | **+3,269** (encoder 2,441 incl. 914 flops + 276-b vo_n merge reg) |
| dsdv_sh_lk (L0, SELR 0 -> 1; host ingest / decode blackboxed) | 5,643 | 7,977 | **+2,334** (relay 2,138 incl. 774 flops) |
| dsdv_svc_rs_c ENTRY 1 (children blackboxed) | 49,150 | 51,042 | **+1,892** per entry (2 entries / die) |

## Cycles (measured, chain bench)

- last IDX part 1 at the bk_sel tap -> its SEL_IDS payload q word at the entry r1: **81 (svc_5) / 85 (svc_11)** edges
  = encoder 2 + vmtx merge 1 + lane 65 + seqhost 3 + unit lane 7 / 11 + entry pin flop 1 + r1 1 (+1 TB).
- one gather instance, K = 512 (32 index words): first IDX beat at the tap -> last payload at the entry = egress span
  + 80 / 84; with a back-to-back egress (64 beats) **144 (svc_5) / 148 (svc_11)** edges (README est ~140), + the entry ->
  svc_att dn tree (unchanged, already priced).
- Plan lanes used: xtier__bk_sel__seqhost 65 edges; unit__seqhost__svc_5 7, unit__seqhost__svc_11 11 (README said 13 / 18).

## Regressions

- `run_seq_host_mu_bench.sh` (die master dsdv_seq_host_mux, bench pinned SELR 0): **SEQHOST_MU_GATE PASS** (ar / mtp,
  5 fault cases, 3 mutants, MU_HOST / MU_HWIN gates, -Wall lint of dsdv_seq_host_mux at its default SELR 1 clean).
- `run_seq_host_bench.sh` (dsdv_seq_host, SELR 0): exact 4 seeds + pair + collide + stdrop PASS, mutants 1-10 detected;
  gate prints FAIL only for the lint PINMISSING `bk_uid` on u_vs (ot_dsdv_vstop gained bk_uid in 51ae2e4cef on main;
  the dsdv_seq_host instance on origin/main has no bk_uid either: pre-existing, not changed here).
- Not rerun: tb_idx_tree DIEM (needs the L20 layer fixtures); the vmtx change leaves vo_s / tl_o / tx untouched (tap
  only), the encoder is inert without an op-3 CTL (the chain bench feeds an op-2 tx job: ignored), only vo_n (unused by
  that bench) and the fault output (+1 edge, registered) change.  rs_bench (16-slice svc) not rerun: the entry change is
  inert without class-3 hw words (r1 unchanged, jf 0).

## Compiler / schedule contract (for TOK-DS)

- IK_ROW frames are counted in the svc job's q-frame count (they pass the ot_s81_svc_job gate like every q frame);
  schedule them outside rg3 reader slots of the same PC and before the next scan that must see the key.
- SEL job: CTL beat (op 3) on the bk_sel rung before the selector's egress; the egress window must leave vo_n idle on the
  2 edges after each word's part 1 (+2) at bk_sel, the seqhost host-write slots idle on the relay edges, and the entry q
  stream free (no job-gate q word) on the 2 relay edges; any collision is a sticky fault (never arbitrated).
  SEL_IDS frames bypass the job gate but svc_att needs the job open (WIN_LOAD first, fc[17]).
- Latency changes: bk_sel vo_n +1 edge (all northbound bk_sel beats), seqhost host-write path +1 edge (die master SELR 1).

## Face guard

No changed module is a kit core (core_pins kits: dsdv_bk_g, dsdv_bksel_c/q, dsdv_idx_tx_n32, ... unchanged).  The
changes sit in soft partitions; every new / changed output (vmtx vo_n, seqhost s_hw_w/e) now leaves a flop, the
entry reads the existing hw pin flop.  0 new partition pins.
