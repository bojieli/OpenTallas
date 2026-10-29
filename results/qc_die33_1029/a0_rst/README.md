# DIE-QC-33 A0: ICG enable state off raw rst_n (opt-in `ICG_RRST`), 2026-10-29 PDT

COORD ruling (~09:5x): the 73 FFs on raw `rst_n` in NK, plus the same set in NL (64/62 B-hop `h[*]` + 8 `g_icg.dr`), move to the existing synchronized reset relay `rtl/lib/ot_rst_relay.sv`. Assert stays async; release is sync. There is no data-cycle change.

## RTL change (base 68204ac61dc = Codex native B-hop source; files `rtl/physical/a0_core/qfd_tile_{nk,nl}_a0c.sv`)
- New parameter `ICG_RRST` (default **0** = unchanged elaboration).
- With `ICG_RRST > 0`, `g_icg` instantiates `ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(ICG_RRST)) u_rr` on `ck`. The `dr` async reset, every `ot_a0_icg_hop` `.rst_n` (36 NK / 34 NL) and the `!rst_n` term of `act` then use its output.
- The `rst_n` port then drives only the 3 relay flops (2 sync + 1 relay, ASR) plus the native reset sample `g_rst_native.q`. All 4 can sit at the E-face pin.
- NL has the same structure (same g_icg/hops on raw rst_n), so it gets the same opt-in. NL default is unchanged.
- **Release +k = SYNC_STAGES + TREE_STAGES = 2 + 1 = 3 cycles** (ICG_RRST = 1). This applies to the gate-enable state only: dr reload and the hops stay set 3 edges longer, so the gates stay open >= 64 + 3 cycles after release instead of >= 64. Gates being open longer only adds clock edges.
  - The body reset (`reset_q` sample) and every data edge are unchanged. Boot budget: +3 cycles before the first possible gate closure, inside the >= 64-cycle rst_n hold.
- Bench-only mutants (non-SYNTHESIS `mut`): 10 = hop tx3 left on raw rst_n; 11 = relay depth k-1.
- **Kit note:** a kit that sets `ICG_RRST 1` must add `rtl/lib/ot_rst_relay.sv` to VERILOG_FILES / kit SRCS. The kit placement must then put `u_rr` at the rst_n pin (keep its flops <= 150 um, p90 30).

## Proof
- **LEC** (`lec_rrst.sh`, the yosys recipe of `qc_a0_kits_13_1029/bhop/lec_main.sh`; hop keep_hierarchy unset so hops are flattened; body black box). Summary in `lec_summary.txt`, per-case status in `lec_{nk,nl}/`.

  | case | NK | NL | expected |
  |---|---|---|---|
  | off (ICG 0, default) | EQUIVALENT (1031 cells) | EQUIVALENT (517) | EQ |
  | icg2_rr0 (ICG 2, default RRST 0) | EQUIVALENT (1148) | EQUIVALENT (632) | EQ |
  | **icg2_cut** (ICG 2, RRST 1, relay modelled as a wire) | **EQUIVALENT (1148)** | **EQUIVALENT (632)** | EQ: reset timing is the only difference |
  | icg2_rr1 (real relay) | NOT EQ, 73 unproven | NOT EQ, 75 unproven | NOT EQ by design (release +3) |
  | mut (cut + body tile_id inverted) | NOT EQ | NOT EQ | negative control, same form as lec_main.sh `mut` |

- **Reset sim** (`tools/qwen_romleaf/a0core/icg/tb_a0_rrst.sv`, small vehicle: the real NK a0c ICG=2 wrapper with real hops and the real relay, body = port stub `rrst_body_stub_nk.sv`, engine idle).
  - The bench has an independent model: exp = rst_n delayed 3 edges, with async assert. Every cycle it checks all 36 hop reset pins against exp and dr against its model. Stimulus: boot, a 3-cycle pulse, and a 1-cycle pulse.
  - Results (`sim_results.txt`, intel2):
    - mut0 **PASS** (400 checks)
    - mut10 (hop on raw rst_n) **CAUGHT** (6 hop errors)
    - mut11 (depth k-1) **CAUGHT** (3 hop + 192 dr errors)
