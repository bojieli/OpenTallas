# REFILL-1725/HBMREG (10-19, owner LEAD2-HBM): combined-source regression of today's HBM changes

Source: claude/refill-hbmreg-1019 @17b861367 = claude/hd4g-gen2e3-l21-1019 @8fa2094c4 + l2h-idx256r-kit @a22fe0816 (FAN32 collar)
+ hbfd-rrlc-kits @5ddedcf7c (incl. RRL fix 5ab727c0f) + l2h-pslice-r8 @f54f2026d + l2h-idxsel @2eb3176f1 (merge-tree; the only
conflicts were tools/landed_parent/lp.py and tools/tt_views/view_export.py, resolved -X theirs = the main-lineage superset hunks;
both py_compile, lp.py audit PASS in the pslice legs). Not merged into main (main conflicts with the GEN2e3 lineage on 7 files).
Fleet: ot-epyc7 (run1/run2), ot-epyc8 (run3), Verilator 5.050 (logs/run1/verilator.txt), git archive of rtl/ + bench tools only.
Legs = every job.benches entry of the kits hidx_sel_s1a, hbfd_rrl_csync, hbm_su_pslice_c5_lp8a, hdie_col_idx256r_a
(scripts/gen_legs.py) + iverilog selector core/shell MUT0, idx256r FAN32=0 identity, l21 obs ring LMUT0..3, l21 strict replay.
Verdict rule = closure_loop bench_outcome/expected_fail_seen (expect-fail with fail_regex: the log decides).

RESULT: 23 bench/mutant legs, 0 unexpected (TABLE.md). run1 l21 LMUT1-3 rows are a harness bug (empty regex field collapsed by
bash read) -> re-run as run2; run1's own tail summary broke because the runner was replaced mid-run (TABLE.tsv intact).

FINDING (l21 strict replay on the combined source, run3): die.v re-emitted byte-identical (ff2e9f87..., contract cdb57b09...),
default bind structural 0 / unread 65,066, but the admitted manifest 056f138d is REFUSED: "source/contract/die/parameters/options
identity drift". Exactly ONE of 572 selected sources differs: rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256r.sv
(FAN32 successor bytes). => GEN2e4 (l21 + FAN32 collar) needs the transfer -> propose -> replay step again on its own S1 die
(new manifest digest, exact transfer, LEAD2-HBM admission); 056f138d is valid only with the pre-FAN32 collar.
FINDING (bind identity): the GEN2e3/l21 die binds ot_hbm_idx_selector_static_sel (rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv),
NOT the L2H-IDXSEL redesign ot_hbm_idx_selector_static (hidx_sel_s1a/s1b kits); and pslice_c5 as ot_hbm_su_programme_pslice_c5
(pgcol), not lp8. hbfd_rrl_c is not in the GEN2e die (GEN2d forest only). The die lead must name which selector master GEN2e4 binds.

Native audits (native/native_receipts_1019.json; own-R native_pin_audit.py --view, origin/main tools) of the 4 HBM views CLOSED
today after the 17:22 fleet-viz sync (no record yet):
- hbfd_pad_r17x115-p1-1e2fd202a PASS launch 157.9 / capture 62.8, spread 8.3/8.6 (R 113.3)
- hbm_argmax_swvm_r2_g2c_1019-pg1-c456d3869 FAIL launch 249.8 > 220 (257 pins, cq[297]); spread 31.5/30.6
- hdie_col_idx256r_a-ra1-f7ac00aab FAIL launch 273.3 > 220 (34 pins, prm[677]); spread 36.2/33.3
- hdie_col_idx256r_b-rb1-a22fe0816 FAIL launch 229.0 > 220 (6 pins, prm[723]); spread 42.6/40.5  -> b is the nearer view
Token-pass layer replays: none owed+unowned that can run now (TOK.HDS.VEH.1/.4 and TOK.HQ.LAYER rec6/10 wait R6 numerical
(Codex unit 662367 live) / GEN2e S5 SW cut; re-running sw5e/swx2b reproduces known pre-repair FAILs).
