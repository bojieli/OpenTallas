# KV-AHUB-RH1 handoff (Opus 5.5). Goal: re-harden qkd_ahub (hc_qkd_ahub 604.8x440.64, no growth) to FULL SIGN-OFF with strap_ofs_ap[31:0]/strap_ofs_fr[7:0] strap inputs.
Gates: DRC 0, TT >= -42, FF hold >= 0, bind+LATCHECK, LEC. Deliver: signed view + hub_C hard_cores row + strap-tie parent row -> KV-PLAN-R6 (D28 cut 11-22 12:00 PST, else late row/D29).
Peers: FAM-KV-HUBC-SYSC-R2 (hub_C/sys_c ops), KV-PLAN-R6 (plan rows).
Clone: epyc8 /srv/opentallas-scratch2/claude/kv-ahub-rh1/wt (main 0092847a58). Tmp: epyc8 .../kv-ahub-rh1/tmp.
## Plan
1. bo RTL: rename ofs_ap/ofs_fr -> strap_ofs_*; ahub_clock7 bo substitution set.
2. bench: closed-hub equivalence old table (old core) + new table (new core).
3. core.json/pins +40 strap pins; kit gen (wave env); P&R variants epyc8/epyc9.
4. swap_ahub_boundary reads tied strap value; tests; ot-push-main.
## State (11-22 00:1x)
- ON MAIN 9cdc3bde91: cores/harden/ahub_strap_ofs.py (+test, bench ahub_strap_eq.sh/_mk.py), kit_core_clocks adapter qkd_ahub_ck7_strap, schema enum.
- BENCH PASS (epyc8 kv-ahub-rh1/eq): old + D27d3 tables 108097/108097 equiv; wrong ties fail. Posted.
- s1 = h1 kit + strap (epyc8 kv-ahub-rh1/k_s1; pins N face M5 x 420.024+1.248i). GRT final TT +28.89 / FF +2.84. Detailed route running
  (ot-run oth-ubuntu-3692252-1795329404, log intel2 ~/tmp/kv-ahub-rh1/s1.log; ctl.sh then runs post-route LEC into k_s1/lec_post).
- Prepared: epyc8 kv-ahub-rh1/view.sh (export exact_b0, abstract_detail splice, porous probe -> view_k_s1/), rows/qkd_ahub_pins_r28_strap.json (671),
  row script draft (scratch, fill after view): ROWS_KV-AHUB-RH1.py edits kv3_hub_C hard_cores[ahub] lef/lib/pins_file/adapter + 7 ahub.ck tap insertions.
## Next
1. route done -> resign_driver (tag dir epyc8 /srv/opentallas-scratch3/claude/auto-resign/tools/flow-20261117-je-kv; run --kit k_s1 --tag flow-20261117-je-kv
   --repo TD/tag_manifest.json --tools TD/tools/die_plan --out k_s1/sign_je --lane KV-AHUB-RH1) via ot-run epyc8; bash view.sh k_s1.
2. SIGNED -> stage payload (view/ + pins), fill row script, drop in epyc8 kv-plan-r6/d28/rows/ROWS_KV-AHUB-RH1.py, post ROWS-READY.
## Log
- 11-21 22:3x started. 22:55 s1 launched; at CTS by 23:10.

## 11-22 07:4x UTC (KV-AHUB-RH1)
- s1 ROUTED: DRC 0, ant 0. je-kv sign-off (k_s1/sign_je): NOT SIGNED: TT -6.5 (passes -42), FF internal hold -38.63 (30 ends), DRV slew 58 tt/33 ff. routed LEC running in resign_driver.
- eco_loop launched (R-MINIMAL eligible): ot-run oth-ubuntu-268171-1795332308 epyc8, out epyc8 kv-ahub-rh1/eco_s1, log intel2 ~/tmp/kv-ahub-rh1/eco_s1.log.
- view probe: ck[3], ck[5] no access (M6 straps over pins). Pin ECO ready: epyc8 kv-ahub-rh1/tmp/eco_pin.tcl (eco2 form; ck5 box = eco2, ck3 extend up 200 nm). Apply to eco BEST 6_final -> 6_1_fill copy, do-6_report, run_kit_kv.sh post, resign_driver je-kv, view.sh.
- k_s1/freeze.json now points at pins/qkd_ahub_pins_r28_strap.json (sha 3a98e21b, canon ff6803d3) = the row pins_file.

## 11-22 08:0x UTC (KV-AHUB-RH1) -- SIGNED, LEC pending
- eco_s1/i1 (eco_loop 1 it) SIGNED; k_s2 = i1 + ck[3]/ck[5] pin ECO (tmp/eco_pin.tcl), do-6_report, kit post SIGNED; je-kv resign_driver k_s2/sign_je: SIGNED TT +24.6 FF +5.42 DRC 0; routed LEC running (ot-run oth-ubuntu-713267-1795334005, log intel2 ~/tmp/kv-ahub-rh1/sign_s2.log).
- local DRC around ck3/ck5 base=eco=0; view_k_s2 splice OK + probe DRT-0073=0 (34/34 AP).
- payload epyc8 kv-ahub-rh1/payload_s2 (view/ lef+tt+ff, pins r28_strap, signoff_je.json, splice.json). core latency mean TT 242.72 / FF 193.02.
- row script filled: epyc8 kv-ahub-rh1/rows/ROWS_KV-AHUB-RH1.py, dry-run on D27d3 plan_c: only kv3_hub_C changes, schema PASS.
- NEXT: LEC EQUIVALENT -> copy row into kv-plan-r6/d28/rows/, post ROWS-READY. Cancelled superseded k_s1 jobs (resign + ctl).

## 11-22 08:5x UTC (KV-AHUB-RH1) -- DONE: SIGNED + ROWS-READY
- k_s2 SIGNED je-kv + routed LEC EQUIVALENT (k_s2/sign_je/PROVENANCE.json). Payload epyc8 kv-ahub-rh1/payload_s2 (+PROVENANCE, lec_routed.json).
- Row dropped: epyc8 kv-plan-r6/d28/rows/ROWS_KV-AHUB-RH1.py sha a99605ffc7e9; posted ROWS-READY (hub 794aa5e). Nothing running. If R6 asks: re-run dry with plan_c, payload staging lines printed by script.
