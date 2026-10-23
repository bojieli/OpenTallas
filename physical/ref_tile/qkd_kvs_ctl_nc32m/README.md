# qkd_kvs_ctl_nc32m (KDIE5-RTL 10-22) -- native-census release KV die qkd_kvs_ctl at the relm frame

KDIE5-RTL 10-22 (MAIN): die-bindable native-census kit of the release KV die qkd_kvs_ctl at the relm frame 1123.176 x 172.776: body = rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_ctl_nc32.sv (KV-CTL10 c32 members + DSTG = c32i body + kept E-face copies of the 967 W/E-shared output registers, 0 edges; die knob OT_KV_CTL_NC32=1 with OT_KV_CTL_C32=2).  Pin plan / M6 pin-only grant = ctl_r1 (KDIE5-TV decision b).  6 ctl_sram_1r1w_64x128_p192 in one centre row; pin registers ON (c32k: every port except the o_hroot member output flops, +1 in / +1 out edge, the die schedule must charge them).  Schedule deltas of the body: own leave guard +2, boot setup_ready +2, +1 boot-write edge (DSTG).

SAFE checklist (pre-gate):
1 Pins: frame faces / bit order (ctl_r1 plan, M4 + pin-only M6 on W/E, 2166 M6 contacts); pin registers
  ON except o_hroot_* (member output flops): +1 in / +1 out edge per port;
  reset rst_n / por_n land in 2 stages + kept copies (c32k reset_landing / reset_relay_split max 32).
2 Reach: 1123-um strip; gate textbook wire_reach decides (no waiver).
3 Fanout: c32 members (census PASS max 32 at c32k); the gate re-runs the native census on this kit.
4 Depth: c32i body unchanged (DSTG boot stage separates accept and held mux).
5 Storage: 6 ctl_sram_1r1w_64x128_p192 (layer rows a/b, writer rows); no indexed flop table > 2 kb.
6 Floorplan: macros on the 43.2 lattice, >= 34 um channels, none at a pin face; 6.5:1 frame is the die slot (frozen).
7 Clock: spine (c32k settings, 16 leaves); spread <= 80 TT+FF at the gate.
8 Schedule: body deltas own leave +2, setup_ready +2, boot write +1; pin regs +1/+1.
Benches: run_kv_ctl_c32.sh tile_n (lockstep vs the release ctl + declared deltas), kb_n (real 471-word MU boot), kb_n_m_tl (mutant).
