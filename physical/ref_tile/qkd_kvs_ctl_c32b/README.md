# qkd_kvs_ctl_c32b — KV-CTL10 10-20 (K.STA.CTL exact successor of the die's control tile)

Why: the strict die (GEN9 d22bu, tile file qkd_kvs_tiles_hroot_ff_k_mu_ba.sv) keeps qkd_kvs_ctl ASSUMED (placeholder
0.194 mm2): kv_tile_views REFUSES every closed ctl view (mu2-9105d74ed: "tile RTL differs", its tile is
qkd_kvs_tiles_hroot_ff_k.sv; mu2 also fails the native clock audit, spread TT 121.8 / FF 109.3) and the KV-CTL3 successor
qkd_kvs_ctl_s32 (45 ports: no dcfg__age_* outputs, o_attn 77 b vs 109 b) is not the die's tile.

What: `OT_KV_CTL_C32=2` makes tools/qwen_kv_die/kv_static_die.py emit the die tile file
rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32b.sv: qkd_kvs_ctl with the SAME 62 ports, wiring and assigns as
the boot-ages tile, members = native-census successors (tools/qwen_kv_die/kv_ctl_c32.py): KV-CTL3 b5d750822 S32 members
(boot, fanr, lprg, own, wprg, wrn) + NEW qkd_kv_die_cfg_a_c32 (boot-age words) + qkd_kv_ownership_obs_c32 (reset copies).
CTLSRAM 2 (6 x ctl_sram_1r1w_64x128_p192). Kit top = qkd_kvs_ctl, tile file = the die's file, so kv_tile_views identity can PASS.

Schedule deltas vs the BA tile (die / compiler must take them; INBOX KV-GEN9): u_own PIPE 1 + SAFE 1 = enter / leave drain
guards sample the group drain 2 edges earlier (QUIET / drain window +2 ck before enter / leave); u_boot SRQ 2 =
boot__setup_ready +2 boot edges.  Every token-path port edge unchanged.  Die slot: OT_KV_CTL_PORTRAIT=1 (345.6 x 475.2).

## SAFE-DESIGN checklist (pre-gate)
1 Pins: pin registers OFF (owner 10-20 09:05: pin regs only at region crossings / > 405 um; the die lands the ctl links in
  its relays and charges 0 tile pin edges, kv_tile_views requires 0/0); reset rst_n / por_n land in 2 registered stages.
2 Reach: 345.6 x 475.2 outline, longest internal span < 405 um except corner-to-corner (gate measures).
3 Fanout: members are the native32 successors (KV-CTL3 rev3 mapped census PASS max 32 on s32a/b); dcfg_a_c32 new (kept
  field leaves, 10 kept sealed copies, kept data copies): census runs in the gate (--native-census) BEFORE CTS.
4 Depth: unchanged member logic vs s32 (native PASS); no comb in->out (members land their inputs).
5 Storage: layer / writer root tables in SRAM macros (CTLSRAM 2); no runtime-indexed flop table > 2 kb.
6 Floorplan: macros on the 43.2 lattice (as s32b), halo 5.4, W/E 2524 b at 5.31/um, N 1647 b at 4.77/um, S ck centre +
  rst_n / lp / o_attn / 17 age words (402 b, 1.2/um); one std-cell band; aspect 1.38.
7 Clock: spine (centre ck on S, 16 leaves); spread <= 80 TT/FF measured by the --cts gate; io_hold_margin 0.03.
8 Schedule: static; deltas above handed to the die schedule.
Census / gate results: (pending: gate run)
