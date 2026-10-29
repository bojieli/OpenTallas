# DIE-QC-16 ICG: A0 tile-root clock gate enable (opt-in, ICG=0 default) -- 2026-10-28 12:20 PDT

Scope: qfd_tile_nk_a0c / qfd_tile_nl_a0c (rtl/physical/a0_core), the QC-PG-4 tile-root ICGx8DC.  Pinned body files
(a0_rc14/rc15 selected sources, qfd_tile_n?_rp2_45) untouched.

## RTL (parameter ICG, default 0 = previous elaboration)
ICG=1: body clock ck_g = ICG(ck, en) on every body entry except the input faces (ck_fa4 tap/tile_id; NK also ck_fa0/ck_fa1
n_a/n_b); the enable state is on the ungated ck.  Output faces (ck_fa2/ck_fa3) are gated (they hold).
    act = !rst_n | go_f | (|go_h) | !me_idle | nv_act          en = act | (dr != 0)
- go_f = copy of tap_q[0] (go face, edge t) -> clocks edge t+1, the first gated capture (IREG go_q): the 1-cycle lead.
- go_h = go_f held ICG_GOH=3 cycles (redundant with dr, see mutant 6).
- me_idle = ot_qwen_w12_matvec_part.idle (existing registered "engine drained" flag: OR of every valid stage, cleared on
  the accepting edge).  In the pinned body it is an UNCONNECTED port (.idle() in ot_qwen_rom_tile_logic_w12), so the
  sim model reads it hierarchically; under SYNTHESIS me_idle = 0 => en = 1 (gate OPEN, safe, no saving) until an
  idle output is threaded through logic_w12 -> rom_tile_w12 -> rom_tile_nk -> rp2_45 (1 port each, pinned files ->
  needs COORD re-pin).
- nv_act (NK) = copies of n_a/n_b face bits [512] valid and [513] fault (node pipe, mis_q, fy_q).
- dr = 8-bit drain counter, loaded with ICG_DRAIN=64 on any act and during reset (reset relays, tree/node drain, output faces).
Cost: ~1 ICG + 1+3+4 flops + 8-bit counter + ~20 gates per tile.

## Bench (tools/qwen_romleaf/a0core/icg/tb_a0_icg.sv; Verilator 5.050, intel2, capped user units) -- CHECKED
ICG=0 vs ICG=1 instances of the same kit sources (a0cv6 SRCS + behavioural children, REGROOT_MODE 9, ROM tile 48),
12,000 cycles: 11 go (5 banks, incl. 2 back-to-back while busy), x line + n data toggling every cycle, n valid
windows while busy and while idle, a fault bit, a misaligned leg, reset pulse idle (7000) and busy (8700).
Gate criterion = valid-qualified (valid/fault bits every cycle, data words under their valid bit, tie pins);
strict all-bit compare reported separately.
| case | NK qualified | NL qualified | gated cycles NK/NL | strict mismatch cycles NK/NL |
|---|---|---|---|---|
| 0 (design) | **PASS 0** | **PASS 0** | 6073 (50%) / 6647 (55%) | 6908 / 6651 |
| 9 control (en=1) | 0 | 0 | 0 | **0 / 0** (no sim race) |
| 1 no lead (go_f dropped, go_h only => 1 cycle late) | CAUGHT 4156 | CAUGHT 4156 | | |
| 2 ~me_idle dropped | CAUGHT 9847 | CAUGHT 10463 | | |
| 3 drain dropped | CAUGHT 5285 | CAUGHT 6054 | | |
| 4 n valid/fault dropped (NK) | CAUGHT 733 (n_y) | n/a | | |
| 5 reset term dropped | CAUGHT 5000 | CAUGHT 801 | | |
| 6 go hold dropped | PASS (equivalent mutant: dr reload on go_f covers it) | PASS | | |
Engine busy 4,626 of 12,000 cycles; 10-11 wake-ups.
STRICT trace_identical does NOT hold (and cannot for any closing gate under this stimulus): with the ungated clock the
x line / n data free-run through the datapath into the INVALID t_out / n_y data words (first strict diff NK cyc 64 =
right after the reset drain, n_y data, valid 0).  Control 9 shows strict 0 when never gated.

## LEC (yosys 0.68, strap_lec.py recipe; pinned body read -lib as a black box; tools/qwen_romleaf/a0core/icg/lec.sh) -- CHECKED
| | NK | NL |
|---|---|---|
| main a0c vs branch ICG=0 | EQUIVALENT (1030 $equiv) | EQUIVALENT (516) |
| main a0c vs branch ICG=1 SYNTHESIS (ICGx8DC = CLK&(ENA|SE); en const 1) | EQUIVALENT | EQUIVALENT |
| mutant .tile_id(~tile_id) | NOT EQUIVALENT (16 unproven) | NOT EQUIVALENT (16) |
ON-vs-OFF sequential equivalence of the closing gate = the bench above (valid-qualified), not a yosys proof.

## Open
1. idle port threading through the 4 pinned body modules (else synthesis keeps en=1).  2. Owner/COORD: accept
valid-qualified (not strict) equivalence at the tile pins.  3. face Q -> ICG.E timing (~550 ps budget, UNCHECKED);
ICG insertion in the kit/trunk not done.  4. ICG_DRAIN=64 is bench-passing, not a proved bound (dr-mutant 0 fails);
minimum not swept.  5. Bench idle stimulus = gen_tb pattern; die schedule traffic not replayed.
