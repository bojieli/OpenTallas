- 2026-11-23 21:22 PST TAKING QC-FW-CAP (from COORD/FABLE-RC-QC hub 2751fd9b): QC fw types at 400k cap. Plan: (1) census synth vs placed cells, buffers by net class, inv share on 5 QC-STATION-REGEN kits on epyc11 (read-only); (2) structural row (stations/type cut/alt-polarity RTL); (3) rebase on QC-ALLFIX plan, PRE + scoped strict bind, ROW-REBASED to QC-ALLFIX cc FABLE-RC-QC. Census ETA 22:20 PST.
- 2026-11-23 21:30 PST FW-CAP CENSUS [QC-FW-CAP -> FABLE-RC-QC, QC-STATION-REGEN, QC-ALLFIX, COORD]. Measured, not estimated: 2_floorplan.odb vs 3_place.odb of the 5 fw probes, read-only. Data is in epyc11 /srv/opentallas-scratch2/claude/QC-FW-CAP/census/*.json.
  (1) Non-tap cells at floorplan -> place, and cells added:
  - sle_fw_v1 cl9d: 301,073 -> 386,338 (+90,069 BUF)
  - sle_fw_v1 clf5: 304,379 -> 388,296 (+89,103)
  - sle_fw_v2: 293,097 -> 368,688 (+75,591)
  - slw_fw_v1: 321,864 -> 405,171 (+83,307)
  - slw_fw_v3: 255,166 -> 329,913 (+79,441)
  Every added cell is a buffer. INV, FF and logic counts do not change at place.
  (2) Synth mix (slw_fw_v1): 120,806 FF (all QN-only DFFHQN/DFFLQN), 122,341 INV (38% of non-tap), 73,510 logic, 5,207 BUF.
  - Chain inverters (FF.QN -> INV -> FF.D only, pure relay): 76,268 / 73,382 / 72,358 / 80,407 / 54,174.
  - A further ~9.2k INV drive output ports only.
  - The chain inverters sit in stations and pads: u_pd*/u_ist*/u_ft_* (ot_dp_st, 138 inst, up to 1087 b) and ot_dp_dly (4,341 inst, 32k FF, 24k of them internal stages D>=2), plus 3.8k in u_core.
  (3) Placement buffers: repair_design inserted 65.6k buffers in 47.4k nets (slw_fw_v1), with the 100 um maxwire. 17.7k port nets carry 17.7k input/output port buffers. The rest are 1-3 buffers per 100-300 um net, on fanout-1 nets (72k of the 83k).
  - By root-net class: logic/INV-driven long >=150 um 25.9k, FF-driven long 21.0k, port 18.3k, local 18.1k, high-fanout 1.
  - By source: u_ft_cws/rsf/rsn feedthrough lanes 18-20k, u_ist stations ~15k, lpad/bin/cland ~10k.
  So the repeaters sit on station-to-station lane hops (~280 um apart on the ft lanes). More stations per hop would not cut cells, since a station costs 1 FF + 1 INV per bit against ~2 buffers.
  ROW (structural, RTL): store-complement relays. ot_dp_dly stages store ~prev; the parity INV goes at the output only when D is even. Fw station chains alternate polarity per stage at the instance boundary in the bound wrapper. Register names are kept (the istations/face/ft_polarity globs still match), and lane cycles are unchanged, so LAT/R8 are unchanged.
  - Expected saving: 54-80k INV per fw type, taking place to ~300-325k.
  - Checks: LEC is RTL vs netlist, so the complement is in gold. The hold recheck on QN->D relays comes from a place/CTS probe.
  ETA: overlay + probe 23:30.
- 2026-11-23 21:32 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-1456045-1795498329 on viable-ram: rc=1 after 4 s, ended 05:32:11, log /srv/opentallas-scratch2/claude/QC-FW-CAP/census/pol_slw_fw_v3.log, cmd: --mem 24 --threads 1 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- docker run --rm --name fwpol_slw_fw_v3 -u 1000:1000 - | class=SETUP cause=FileNotFoundError: [Errno 2] No such file or directory: '/r/slw_fw_v3_bound.sv'
- 2026-11-23 21:48 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-2012367-1795499325 on viable-ram: rc=14 after 5 s, ended 05:48:46, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/cpl_run.log, cmd: --mem 64 --threads 16 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/slw_fw_v1__clf51c11d8__cl592e3d37_cpl -- bash /sr | class=SETUP cause=FAIL_PREFLOOR ENV-PROVENANCE FAIL: no kit_env_provenance.json and the kit is not a kit-wave attempt (hand-buil
- 2026-11-23 21:52 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-2034522-1795499393 on viable-ram: rc=0 after 139 s, ended 05:52:10 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/syn_cpl.log, cmd: --mem 64 --threads 8 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/synth_
- 2026-11-23 22:01 PST DONE [QC-FW-CAP] ot-push-main otpush-loved-redfish-124554 on loved-redfish: rc=0 after 1122 s, ended 06:01:22, log /srv/opentallas-scratch2/claude/QC-FW-CAP/tmp/push.log, cmd: ot-push-main 
- 2026-11-23 22:02 PST FWCPL-1 row built [QC-FW-CAP -> QC-ALLFIX, FABLE-RC-QC, COORD]:
  (1) main 5127d7a29ef: bind.py ot_dp_dly gains store-complement stages behind `ifdef OT_DLY_CPL. Ports, D, register names r[k] and q = d delayed D are all unchanged. Without the define the netlist is identical. Test test_bind_dly_cpl.py: 8 pass, incl. an iverilog check of D=1/6/7.
  (2) Plan row: epyc7 /srv/opentallas-scratch2/claude/QC-FW-CAP/row/fw_dly_cpl_row.py (610e5728d3ee, idempotent). It adds verilog_defines OT_DLY_CPL to all 9 sl[ew]_fw types. On C1c it gives plan_c1_fwcpl.json 0c14d74c49f2. Lane cycles are unchanged, so LAT and R8 are unchanged.
  (3) MEASURED by real ORFS synth of slw_fw_v1 (a kit copy with the define):
  - Chain INV (FF.QN->INV->FF.D): 80,407 -> 49,208 (-31.2k, as projected).
  - Total INV: 122,341 -> ~102.5k (-19.8k).
  - Expected place non-tap: ~385k (from 405k). The other fw types land at ~350-368k.
  The margin is thin, so phase 2 is the ot_dp_st polarity alternation: a further ~35k, 62-66k in total. It needs a CPL flop-name alias in the kit_istations/face/ft hooks (/q[ globs).
  Next: scoped strict bind of 0c14 on epyc7 cF (rt with 5127d7a), then a private place/CTS probe for the hold recheck.
- 2026-11-23 22:12 PST FWCPL status [QC-FW-CAP -> COORD, FABLE-RC-QC, QC-ALLFIX]:
  (1) Remaining chain INV after phase 1 (measured, slw_fw_v1 synth, 51.1k):
  - ot_dp_st -> ot_dp_st 34.7k: ist stations 23.9k, ft cws/rsf/rsn 10.8k.
  - non-relay FF -> first station 11.1k.
  - dly last-stage parity 4.2k (D even 3.7k).
  - o->o 1.0k.
  Phase 2 (paired-station complement, reg names q kept) removes 41.2k of these by the 2-colour count, giving place ~344k. The emitters are bind.py ft chains and kit_istations, plus kit_rsync's ot_dp_st variants.
  (2) Reset: ot_dp_dly is reset-less. A new test runs the reset-state compare from every start state (D=1..5): 14 pass (c40e2c38ea, not pushed yet).
  (3) Netlist proof: non-fw slw_su_l1 elaborated netlist hash fe277a9e is identical with old and new bind_cells. The fw_v3 define-on check is running.
  (4) Running on epyc11 in parallel: place A/B (base100, base200, cpl200) and cpl-to-CTS. Bind moved to epyc11, since epyc7 is at 98% disk and on HOLD.
- 2026-11-23 22:14 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-2541418-1795500666 on viable-ram: rc=0 after 178 s, ended 06:14:02 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/nh.log, cmd: --mem 48 --threads 1 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash -c bash /srv/opentallas-scratch2/claude/QC-FW-CA
- 2026-11-23 22:23 PST DONE [QC-FW-CAP] ot-push-main otpush-loved-redfish-1053219 on loved-redfish: rc=0 after 216 s, ended 06:23:07, log /srv/opentallas-scratch2/claude/QC-FW-CAP/tmp/push2.log, cmd: ot-push-main 
- 2026-11-23 22:24 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-2646269-1795501019 on viable-ram: rc=3 after 476 s, ended 06:24:53, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cG/bind.ot, cmd: --mem 48 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- env OT_FWCAP_RT=/srv/opentallas-scratch2/claude/rt/51 | class=DESIGN-FAIL cause=FAIL DEPTH qfd_sys_face_n32_opt_p192: 25 of 4483 flops at logic depth >= 18 (the 833 ps budget; max 20; worst 
- 2026-11-23 22:33 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-2866065-1795501607 on viable-ram: rc=0 after 427 s, ended 06:33:52, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cG/prebase.ot, cmd: --mem 32 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/tmp/pr
- 2026-11-23 22:44 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-2885079-1795501699 on viable-ram: rc=3 after 948 s, ended 06:44:04, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cH/bind.ot, cmd: --mem 48 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- env OT_FWCAP_RT=/srv/opentallas-scratch2/claude/rt/50 | class=DESIGN-FAIL cause=no cause line
- 2026-11-23 22:50 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-2953425-1795502067 on viable-ram: rc=4 after 960 s, ended 06:50:23, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cG/bind.ot, cmd: --mem 48 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- env OT_FWCAP_RT=/srv/opentallas-scratch2/claude/rt/51 | class=DESIGN-FAIL cause=FAIL DEPTH qfd_sys_face_n32_opt_p192: 25 of 4483 flops at logic depth >= 18 (the 833 ps budget; max 20; worst 
- 2026-11-23 23:12 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-2485683-1795500489 on viable-ram: rc=0 after 3841 s, ended 07:12:07 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/run_ab_cpl200.log, cmd: --mem 96 --threads 16 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/runab
- 2026-11-23 23:16 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-2486286-1795500489 on viable-ram: rc=0 after 4084 s, ended 07:16:10 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/run_ab_base100.log, cmd: --mem 96 --threads 16 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/runab
- 2026-11-23 23:47 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-3592038-1795501469 on key-cardinal: rc=0 after 4958 s, ended 23:47:05 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/run_ab_pf.log, cmd: --mem 96 --threads 16 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/runab
- 2026-11-23 23:49 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-3592033-1795501469 on key-cardinal: rc=0 after 5084 s, ended 23:49:11 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/run_ab_base200.log, cmd: --mem 96 --threads 16 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/runab
- 2026-11-24 01:41 PST FWCPL A/B place, measured [QC-FW-CAP -> FABLE-RC-QC, COORD, QC-ALLFIX]. Setup: slw_fw_v1__clf51c11d8__cl592e3d37, kit copies, the same ORFS make place for every row. Counts are non-tap cells from 3_place.odb.
  
  | Variant | Floorplan | Place | Buffers added |
  |---|---|---|---|
  | base | 323,309 | 409,533 | 86.2k |
  | maxwire 200 + ft 220 | 323,309 | 409,533 | 86.2k |
  | phase 1 cpl-first (main 5127d7a) | 304,674 | 394,389 | 89.7k |
  | phase 1 plain-first (main 5041641) | 295,095 | 387,310 | 92.2k |
  | phase 1 + phase 2 (89 stations to QN pairs) | | | |
  
  (1) The 200 um A/B is DEAD. OT_MAXWIRE_UM does not feed place repair_design. Those buffers come from slew/cap repair, set_max_transition 320 / cap_margin 20.
  (2) Removing the inverters adds 3.5-6k buffers, because QN now drives the long hop directly. Net gain for plain-first is -22.2k at place.
  (3) The phase 1 + phase 2 run is at place on intel1, ETA ~02:15.
  I will rebase on C1g 96cce77c1e2f, per QC-ALLFIX. ROW-REBASED follows only when a measured place is <=360k.
- 2026-11-24 01:49 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-1965743-1795513188 on viable-ram: rc=0 after 567 s, ended 09:49:14, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cH/prebase.ot, cmd: --mem 32 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/tmp/pr
- 2026-11-24 03:02 PST DONE [QC-FW-CAP] ot-run oth-ubuntu-2494910-1795513068 on key-cardinal: rc=0 after 5054 s, ended 03:02:00 env=wave+0, log /srv/opentallas-scratch2/claude/QC-FW-CAP/probe/run_ab_pfqn.log, cmd: --mem 96 --threads 16 --hosts intel1 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- bash /srv/opentallas-scratch2/claude/QC-FW-CAP/runab
- 2026-11-24 03:05 PST RESULT [QC-FW-CAP -> FABLE-RC-QC; cc COORD, QC-ALLFIX] slw_fw_v1 place non-tap: phase1 plain-first + phase2 QN pairs (pfqn) = 379,832 (floorplan 274,749). Baseline 409,533; plain-first alone 387,310. INV removal works (-48.6k at floorplan) but place adds 105.1k buffers: ff->logic >=150um 35.7k, reg2reg hop >=150um 32.2k, port nets 18.2k, logic >=150um 10.9k, local 8.0k. Under the 400k cap but not at the 360k target, so there is no ROW-REBASED yet and the fw types stay held. Next: a structural lever on the long-hop/long-fanout buffers (an extra station on hops >=150um, or a type cut); census of those nets is running.
- 2026-11-24 03:13 PST ACK [QC-FW-CAP -> QC-ALLFIX; cc FABLE-RC-QC] FWCPL-2 rebased on C1h 894e6f21991f: plan 02ddf1a18df7 (epyc7 QC-FW-CAP/plan_c1h_fwcpl2.json, copy at epyc11 row/), 9 fw types, row is idempotent (re-apply gives the same sha). epyc7 cF tree deleted with ot-delete (+57 GB). The gate (G0, PRE with RESETPUB_SOLVE + asbuilt, scoped strict of the 9 fw types, rt f6d43b117443, OT_PLAN_GATE_PRE=warn for the inherited DEPTH only) starts on epyc11 cI once your C1h strict passes. The C1g v2 strict is skipped.
- 2026-11-24 07:10 PST DIED [QC-FW-CAP] ot-run oth-ubuntu-1618552-1795525848 on viable-ram: rc=1 after 7192 s, ended 15:10:37, log /srv/opentallas-scratch2/claude/QC-FW-CAP/cI/bind.ot, cmd: --mem 48 --threads 2 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/QC-FW-CAP -- env OT_FWCAP_RT=/srv/opentallas-scratch2/claude/rt/f6 | class=DESIGN-FAIL cause=V4 bind errors 0 {}
