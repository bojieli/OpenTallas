# S81-ALLFIX-SVC [SERDES-RING] notes (sub-unit of S81-ALLFIX-SVC; started 11-23 17:45 PST)
Order: FABLE-RC-ALL 17:38 (serdes t2 P13): whole landing ring + bin + lpad on ONE tap group, family rule for all 11 serdes types. t2 HELD until probe hold >= 0.
Evidence of the chase (epyc10 s81-misc-serdes-j9): pair_cts ring->bin -173 cleared -> bin->lpad -146; p13 triple (y+bin+lpad r[0]) cleared that -> sr[0].u_sel/di -> dch[0].u_dsel/y -226 (launch 212.7, capture 525.4) in p13/triple_cts/.../4_cts_post_hook.rpt.
## Row SERDES-RING-ONEGROUP
- Form: plan clock.tap_group.re on the 11 serdes__* types (gen_phys.tap_group_exports -> OT_TAP_GROUP_RE -> clock_taps.tcl group form: whole group on the tap nearest its centroid, pinned against the cap pass). One regex keeps the existing reset-tree key (u_core g_rst_tree rt_d / u_rm g_rd [0-7]) bit-for-bit and adds key coll_<io><k> for u_cland_coll_* (ring: dch[*].u_dsel sr + y + ctl), u_bin_coll_* and u_lpad_coll_* (ALL lpad stages, so lpad r[k]->r[k+1] cannot become the next boundary). Verified in python re and tclsh 8.6 (ARE).
- Tool epyc10 /srv/opentallas-scratch2/claude/s81-allfix-svc/frame/ring_onegroup_row.py; ops serdes_ring/SERDES-RING-ONEGROUP-ops.json 877bf1f92e06 (22 ops); plan serdes_ring/plan_ring_onegroup.json 68a0ac2ec157 (= B1 ae3101241d6b + row).
- Group size t2 coll_i0: ring + bin 512 + lpad 3584 (r 3072 + q 512) -> one tap above OT_TAP_MAX_SINKS 1700 (cap is pinned-over by design; TAP-LIMIT is info in G0). Watch: new boundary lpad q -> u_core.
- PRE: running (frame/ring_pre.otrun.log, serdes_ring/pre.log). Scoped strict bind serdes__t2 + serdes__t13: running (serdes_ring/scope_bind.otrun.log, out scope_bind_68a0ac2ec157). Probes next (private-spec --goal grt, wave env) on t2 + t13, read post-hook hold + launch/capture insertion per stage.

## 20:46 update
- RING bind t2+t12 (probe-only) on 68a0ac2ec157: BIND_RC=0 (epyc2 bind_ring_t2t12). Probe kits t2/t12 FAILED kit_rtl: probe-only bind has no s81_bound_top.sv -> need full die bind.
- t13 FSTART (COORD 19:15): inherited B1 refusal; all 3 landing_local_resets raws depth 8 vs consumer depth 10. Row T13-FSTART-RESEAT a5758c3b7b83 (674->675, 554->49, 554->555, anchor rewritten); PRE PASS 0/178; strict t13-only bind RC=0. Posted INT/ASSEMBLY/OPEN-FSTART (8c98a5c5). Class (22 other types) = S81-OPEN-FSTART, not extended here.
- Compose 72e95bb2eba7 = RING + T13 row; full strict bind running epyc2 (bind_full_ring_t13, private serdes probe bind) since 19:57. Expect refusal at other FSTART types -> then probe from c7 / OPEN-FSTART bind.
- Tools: epyc2 /srv/opentallas-scratch3/claude/s81-allfix-svc/{t13_fstart_row.py,diag_llr.py,sbind.sh,fbind.sh}

## 04:50 11-24 RESULT
- Full strict bind 10a4edbf516b (RING on FSTART-DEPTH-B1) RC=0. Tool bug found: bind_cells.sv lacks ot_dp_rrelay_fn (ENTRY_FALL_CELLS) for pin_entry_fall serdes -> kit_rtl fails all B1 serdes kits (posted INT c7edf6f5). Private workaround: bind_full_ring_fsd_ef.
- t2 CTS post-hook hold -644.97 (was -226): ungrouped reader_start (L198) -> grouped ring (C914). t12 hold -283 port->bin q (250/482). ONE-GROUP FAILS; next form = insertion matching, not grouping.

## 11-24 05:4x R1 SELLK (job: next serdes ring form, COORD 05:0x)
- Census posted 83f286c8: 473/473 failing ring hold eps = dsel sr (clk_t32/33) -> y (clk_t7), cross-tap; 0 same-tap.
- RTL+gen SELLK-1 pushed main 07359c423f (8c20aed38f + schema json): clock.ring_hold.read_lockup(_types); bench rtl/test/meso/sellk 11/11 + mutant caught.
- c9 row: epyc9 /srv/opentallas-scratch2/claude/s81-allfix-svc/c9_sellk.ops.json 1109984697f5, plan c9sellk_tree/physical/die_plan/s81/j9tail_c9sellk/p6w_sg_sellk.json ae1d2a21f59a (base c8 p6w_sg 9b25d6714339).
- private tree c9sellk_tree (ot-tree-fork of INT amd1_tree + SELLK RTL), tools rt_sellk = rt 69de849b3da1 + SELLK (3 files).
- PRE log s81-allfix-svc/pre_c9sellk.log; gate c9sellk_gate.sh -> gate_c9sellk/ (elab + scoped strict 11 serdes), unit oth-ubuntu-483920-1795527839.
