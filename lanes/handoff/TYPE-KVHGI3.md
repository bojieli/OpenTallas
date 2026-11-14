# TYPE-KVHGI3 (Sonnet) 2026-11-14 ~10:35 PST
Target qwen_kvsys/kv3_hgi_v3. Latest attempt: kv102sem_ftgrid attempt_3 (job f91014c45280, GRT-0116), kit epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv102sem_ftgrid/items/kv3_hgi_v3/attempt_3/gen/kv3_hgi_v3.
FT-grid cause (KV-102 02:13) is FIXED: attempt 3 placed fine (ft5,4,0 snapped); it now fails only at GRT.
GRT finding (5_1_grt.log, congestion-*.rpt): NOT diffuse. Iteration 5/10/15/20/25/30 leave 10886/10483/7025/736/21/5 violation gcells, final 4 (all capacity:0 usage:1; total M4 7, M5 16, M6 5, M7 11, M8 2). The 4 gcells are inside macros: (a) net173130 (rst_n, from reset sync flops at x384,y125 into g_*_rst_n interior M5 pins at centre of u_head2_e0) and clk_c8 (g_front_0_u_front__clk, centre pin of e0) at (185,124); (b) net207922/net207930 = max-wire repaired nets BUFx16f (816,555.4, N of head3_e2) -> BUFx6f (816,332, S of head3_e2): a 216 um over-macro feed-through of head3_e2 (gcells (831,343),(799,362)). Not ft/station pin access, not core logic: it is over-macro routing at the macro centre pins / feed-through, residue of a converging run that ran out of the 30 ORFS iterations (violations fell 10x per 5 it).
Forms (private, intel1 /srv/opentallas-scratch2/claude/type-kvhgi3/<f>/kit, copies of attempt_3 kit with 4_cts.odb, config.mk mtime kept so no resynth; goal route via ot-run; logs intel2 ~/typekv3/<f>.log):
 fA = GLOBAL_ROUTE_ARGS -congestion_iterations 80
 fB = GLOBAL_ROUTE_ARGS -congestion_iterations 120 + GRT_SEED 5
Next: on pass (5_1_grt past GRT-0116, DRT DRC 0, TT setup >=-42, hold >=0) add AUTO-RESIGN row + RESULT, archive per SIGNED-RECOVER.md; a wave fix needs gen_phys to emit GLOBAL_ROUTE_ARGS for this type (ASK KIT-OPS-5 for retry key kv3_hgi_v3@N).
COORD 10:4x: added fC = GLOBAL_ROUTE_ARGS "-congestion_iterations 30 -allow_congestion" (goes on to DRT; judge DRT DRC + timing) and fD = fA (80 it) + temporary GRT keep-out M7/M8 over u_bound.u_head3_e2 (3 um inside edge, grt_pre.tcl, removed in grt_post via ot_pgtt_remove) so net207922/930 route around. All four on intel1 via ot-run, logs ~/typekv3/f{A,B,C,D}.log.

WAITER fC Sat Nov 14 10:16:19 PST 2026 ended
Total        221726484       23265252           10.49%             3 /  4 / 41
[ERROR GRT-0116] Global routing finished with congestion. Check the congestion regions in the DRC Viewer.
Error: global_route.tcl, 194 GRT-0116
ls: cannot access '/srv/opentallas-scratch2/claude/type-kvhgi3/fC/kit/signoff.json': No such file or directory
OT_LAYOUT_RENDER grt 2026-11-14 17:29:37 2 PNG 92 s: grt 1/6 flagged: local_density=1.385 | not computable: opposite_face_pins,channel_tracks,clock,fanout_spread | GRT max 98%, 23520 gcells >90%
make[1]: *** [Makefile:585: do-5_1_grt] Error 1
make: *** [Makefile:585: /work/run/results/asap7/dp_kv3_hgi_v3/base/5_1_grt.odb] Error 2

WAITER fD Sat Nov 14 10:16:19 PST 2026 ended
Total        221726484       23265252           10.49%             3 /  4 / 41
[ERROR GRT-0116] Global routing finished with congestion. Check the congestion regions in the DRC Viewer.
Error: global_route.tcl, 194 GRT-0116
ls: cannot access '/srv/opentallas-scratch2/claude/type-kvhgi3/fD/kit/signoff.json': No such file or directory
OT_LAYOUT_RENDER grt 2026-11-14 17:29:37 2 PNG 92 s: grt 1/6 flagged: local_density=1.385 | not computable: opposite_face_pins,channel_tracks,clock,fanout_spread | GRT max 98%, 23520 gcells >90%
make[1]: *** [Makefile:585: do-5_1_grt] Error 1
make: *** [Makefile:585: /work/run/results/asap7/dp_kv3_hgi_v3/base/5_1_grt.odb] Error 2
COORD 10:2x: fC/fD moved to epyc10 (kits epyc10:/srv/opentallas-scratch2/claude/type-kvhgi3/f{C,D}/kit, ot-run --hosts epyc10, logs ~/typekv3/f{C,D}.log); fA/fB stay on intel1. The two "WAITER fC/fD ... ended" blocks above (10:16) are SPURIOUS (I killed the queued intel1 ot-run clients, PIDs 4001342/4001989, cmdline checked, nothing had started; the block shows the old attempt log). Live waiters: waiter.sh (fA/fB intel1), waiter3.sh (fC/fD epyc10), results appended as WAITER/WAITER3 blocks.
