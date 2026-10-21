# KV-PVW 10-19: qkd_pvw_die_t (PV16 pair) = DIE-PLACED parent, folded into the GEN9 die top

Decision: FOLD, do not harden. qkd_pvw_die_t is a wires-only frame of 2,790 closed leaves per pair (256 pv_slice_t, 32 pv_join_t,
1 pv_wide_ctl_tb, 1 pv_rs_hd_f, 64 rlyi_258s, 2,436 rlys_1/36/296 relays) over a 1,555 x 12,010 um slot, with 33 separate
clock entries (ck_c0..31 per column + ck_c32 ctl). A 12 mm parent cannot be one hardened tree (landed-regions-standard);
the die is its parent. COORD 0je (10-19 00:50) approved the die-placed wires-only parent row; AD3-KV-PARENTS expand trial PASS.

GEN9 already does it (no GEN9 change needed): kvs14r.sh @3923bb422 OT_KV_EXPAND includes qkd_pvw_s,qkd_pvw_n;
OT_KV_BOOT_AGES=1 binds qkd_pvw_die_tb = qkd_pvw_die_t_f_ba.sv (sha b15daa62, byte-identical to qkd_pvw_die_t_ba.sv pinned by
kv_pvw_padding / kv_pvw_residual_roles); OT_KV_RS_HD auto -> f (f2 native PASS receipt). Run kvs14r-3923bb422-gen9d expand.json:
qkd_pvw_s / qkd_pvw_n 1 inst each, 2,790 leaves, 0 undriven / multi-driver / unbound / overlaps / outside-slot.
Clocking: each ck_c<s> is its own die sink point (kvsys_clocks.py: per-child entries of a wires-only frame carry the child's
measured R); intra-region spread and cross-region LANDED pairs are judged by the die DIECLK step (kv_die_clock_regions.sh +
kv_landed_pairs.py) -> tree item K.CLK, not an element hardening.

Composition bench (this dir; Verilator 5.050, ot-epyc5, branch claude/kv-pvw-1019 @90c97d144 + runall fix):
tb_qkd_pvw_die_tb = tb_qkd_pvw_die_t with the GEN9 frame and the boot word cfg_age (FIRST_INPUT_AGE param = 127 bound).
PASS (bit-exact vs pv_pair_ref, 32 cols / 512 words, ages = static out_age + COL_D, no fault), T = 1 100 300 1000 4097 8192:
  pos_p0_rl19 (FIA 20), pos_p0_rl95 (FIA 96, die value), pos_p1_rl95 (pair 1 byte; pair 1 owns no rows at T<=256).
Mutants FAIL (witnesses committed): mut_age_m1 (cfg age-1), mut_cfg_swap (age in the other pair's byte), mut_trunk (TRUNK_MUT=1),
mut_flag (FLAG_D_ADJ=1), mut_cfg_swap_p1 at T 300/1000 (mut_cfg_swap_p1_T300_T1000.log). The T 1/100 p1 swap run
(mut_cfg_swap_p1.log) PASSES vacuously (rows=0) -> runall now runs it at T 300/1000.

Open (not this element): 34 public-status residual bits UNRESOLVED (kv-pvw-role-audit) and the GEN9 strict bind v2 failure
'static child nb identity/role changed head_EN_0_0__g_t_0__u_l8' (a QK head lane, not PVW) belong to KV-GEN9 / KV-BIND3.
Registry: fleet-viz elements.py has no die-placed parent category -> row stays 'parent open' until COORD adds the fold.
