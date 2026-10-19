# qkd_d2d_static_r7w (TW7-KVD2D 10-19)
KV die D2D link end re-hardened at the MU release seam TXDP_K 0x03030415 [21,4,3,3] (r7v = 0x03030418 cannot bind the MU KV die).
Only the TXDP parameter differs from r7v (CLOSED 1b609a25c, TT +13.55 / FF +7.68); geometry identical (review 83ff32c7 carried).
Benches: run_d2d_dies.sh KDLY=18 (exact + LOCK NTX3 lockstep; mutants MUT1 / LMUT1 / LMUT2, witnesses in results/closure_witness/qkd_d2d_static_r7w).
SAFE checklist (owner 10-19): 1 PASS (RTL PR=1 pin flops + kit reset_landing 2 stages + ot_rst_pipe regions); 2 PASS (475 um tile, pin flops FIRM);
3 waived: reset region rst_n[1] 321 loads, CTS/repair buffered, r7v closed with it (SAFE-AUDIT-KV: none blocking); 4 PASS (r7v closed);
5 PASS (slot store in 4 SRAM macros); 6 PASS (lattice, std-cell band, as reviewed); 7 PASS (spread 71.2/64.7 r7v, io_hold 0.030);
8 PASS (static compiled calendars, no credits/backpressure).

## Codex recovery 10-19
Both daemon attempts stopped in Yosys canonicalization before synthesis/placement.
The reset-landing wrapper's default compatibility regexp matched
`host_link_reset_req`, a registered protocol command, and the registered reset
status outputs `fwd_link_rst_n` / `phy_rst_n`. These are not sequential-reset
inputs and must retain their existing PR pin flops. The kit now explicitly sets
`OT_PIN_REGS_RESET=^(por_n|rst_n)$`; its literal reset_ports remain por_n,rst_n.
Only those two inputs get the existing two-stage landing. No RTL, schedule,
pin assignment, outline, macro position or latency changes. Failed job records
remain immutable; the source-pinned recovery is on this same kit. SAFE checklist
above still applies; inherited closed geometry is preserved rather than
misclassifying a tool refusal as a physical route failure.

## Production registered-codec2 seam
The KV die lead/root confirmed ATTN_LAND=1 uses codec2: TXDP_K
0x03030416 ([22,4,3,3]), one more capture edge than codec1. The shared
compiler emits this with --kv-codec2; compute remains0x0a010308. The same
kit now uses TXDP50529302 and pair benches KDLY19; codec1 .15 gates are
historical and cannot bind production. Additional edge is included in shared
static calendars and the KV die schedule; no unpriced padding/tie introduced.

Reset-capture hook now anchors the actual wrapper landing cells
por_n__ot_rl[01] and rst_n__ot_rl[01], two per real reset. The inherited
hook looked for unwrapped u_core.u_por_region.s[01], which became stale
once kit reset_landing added u_ot_pr_core hierarchy. Its fail-closed
expected-count check is retained; no timing path is masked.

Codec2 mutant witnesses live separately under results/closure_witness/qkd_d2d_static_r7w_codec2; codec1 witness logs remain preserved.
