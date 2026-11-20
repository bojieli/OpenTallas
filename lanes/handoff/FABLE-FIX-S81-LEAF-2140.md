# FABLE-FIX-S81-LEAF-2140 handoff (Fable; owns every ot_s81sl_leaf__t* and ot_s81sl_kv_leaf__t* type)
Predecessor: lanes/handoff/FABLE-FIX-S81-LEAF.md (Opus lane, closed 21:45). Work dirs: epyc9 and epyc10
/srv/opentallas-scratch2/claude/fable-fix-s81-leaf-2140 (B). Hub logs: intel2 ~/lanes-fable-s81leaf-2140 (D). Lane clone: epyc10 B/repo.

## State 2026-11-19 22:3x PST
On main (all mine, pushed with ot-push-main):
- 0747cc824096 SWR station tests: test_s81_leaf_swr_station.py (sim at depth 0/1/2 with controls, lint, --update on the row form), leaf_SWR2 matrix row.
  The restage tool itself is 6ac236963d (Opus). Command: stage_lfcs_netlist.py PLAN NETLIST OUT --update SWR_D --report R.json.
- a6e4c44e8cb0 + 6cf5fa3beeaf s81_hi_corridor.py: added taps cleared with the bind's rule (grid taps, placed boxes + tap clear); works under python3 -I.
- 069b960d0b85 kit release hook: a keep_firm ft flop on a tap / edge cell goes back to PLACED (leaf__t21 DPL-0033, 202 overlaps; t60 has keep_firm too).

Measured:
- WREG function: leaf_bench L0 / L2 and beat_bench L0 / L2 PASS with XR + WREG on the D8i tree RTL, XR-only controls PASS (epyc9 B/wregb/out).
- Family form C on f2ec (epyc9 B/cw/plan_famC.json 750f33553a0e): 611 banks sited; 871 rows on 35 types refused by the 400-um hop limit
  (they keep the old site); check after C: 0 OK, 3 RISK, 72 OVER (base 75 OVER). t28, t31, t60 are fully sited.
- Form A on t28 / t31 / t60 (epyc9 B/aw/plan_A.json 9ec7e5a7597b): 24 / 24 banks sited, tap rule clean; estimator still OVER (8.22, 8.22, 14.62 bits per track).

Running (do not relaunch):
- Tree CW = famC sites + 5 SWR rows + restaged netlist + WREG overlay + OT_S81SL_VP_WREG in asbuilt defines. Plan 0251647be92c. epyc9 B/cw/tree_CW,
  log D/cw_build_CW.log. Waiter D/cw_grt.sh launches GRT for t28 / t31 when the kits are clean.
- Tree AW = form A (t28 / t31 / t60) + same SWR + WREG. Plan c94729828ffe. epyc9 B/aw/tree_AW, log D/cw_build_AW.log, waiter D/aw_grt.sh.
- Opus control tree_C (sites only, t28 / t31): bind 0, LATCHECK 873 / 873; its waiter ~/lanes-opus-s81leaf/grt_launch.sh launches GRT.
- All three trees have kb_d8i/.keep_stage_odbs, so the stage cleaner cannot force a second CTS pass.

Next steps, in order:
1. t60 kits (CW and AW) are HELD on purpose: files D/cw_grt_{CW,AW}_ot_s81sl_leaf__t60.log. The tree tools dir is read-only, so the kit is patched instead:
   copy kit face_flops_release.tcl, add the cg_ft lines of main 069b960d0b85 (gen_phys.CLAND_RELEASE_GROWN_TCL), mv over, then
   ot-run --mem 64 --threads 8 --hosts epyc9 --priority proof --dir G -- bash G/run_kit.sh G/ot_s81sl_leaf__t60 grt 64 8 (G = tree/kb_d8i/kits/T/gen).
2. Read each kit at GRT: one CTS pass (grep cts in run_route.log), GRT overflow and extra iterations, TT setup and hold. Compare C control, CW, AW.
3. Decide the form per type. C if GRT closes with it; A where the estimator and GRT still show bits crossing. The 35 types with refused rows need A or one more bank stage.
4. Rows for event J to S81-DIE-R3: sites rows (tool command on the J plan), SWR rows (5 types), WREG define in the die-wide asbuilt defines + overlay, the lane moves for A types.
5. LATCHECK on CW / AW decides whether WREG needs a priced latency row (not known yet).

Not verified: any GRT or TT on form C or A; strict bind with SWR + WREG (in progress); the 35 partly sited types.
