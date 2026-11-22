# KV-AHUB-RH1 handoff (Opus 5.5). Goal: re-harden qkd_ahub (hc_qkd_ahub 604.8x440.64, no growth) to FULL SIGN-OFF with strap_ofs_ap[31:0]/strap_ofs_fr[7:0] strap inputs.
Gates: DRC 0, TT >= -42, FF hold >= 0, bind+LATCHECK, LEC. Deliver: signed view + hub_C hard_cores row + strap-tie parent row -> KV-PLAN-R6 (D28 cut 11-22 12:00 PST, else late row/D29).
Peers: FAM-KV-HUBC-SYSC-R2 (hub_C/sys_c ops), KV-PLAN-R6 (plan rows).
Clone: epyc8 /srv/opentallas-scratch2/claude/kv-ahub-rh1/wt (main 0092847a58). Tmp: epyc8 .../kv-ahub-rh1/tmp.
## Plan
1. bo RTL: rename ofs_ap/ofs_fr -> strap_ofs_*; ahub_clock7 bo substitution set.
2. bench: closed-hub equivalence old table (old core) + new table (new core).
3. core.json/pins +40 strap pins; kit gen (wave env); P&R variants epyc8/epyc9.
4. swap_ahub_boundary reads tied strap value; tests; ot-push-main.
## State (11-21 23:0x)
- Tool (lane clone, not pushed yet): cores/harden/ahub_strap_ofs.py (rtl / kit / encode) + test_ahub_strap_ofs.py; tools/die_plan/kit_core_clocks.py
  new adapter qkd_ahub_ck7_strap (reads bound AP_OFS/FR_OFS, ties strap_ofs_ap/fr consts, 8-bit check) + tests; schema enum + die_plan.schema.json.
- Strap kit k_s1 = h1 kit (epyc7 fable-fix-kv-hub/r4/ahub/base/h1 copy at epyc8 kv-ahub-rh1/h1src) + ahub_strap_ofs.py kit: 40 strap pins N face M5
  x 420.024 + 1.248 i (strap_ofs_ap[0..31], strap_ofs_fr[0..7]), set_false_path -from strap_*, straps.json, no capture flop.
- s1 P&R: intel2 ~/tmp/kv-ahub-rh1/s1.log, ot-run unit oth-ubuntu-3692252-1795329404 (epyc8), ctl.sh = run_kit_kv.sh route 24 16 + post-route LEC (lec_post/).
- Bench: yosys equiv REF(h1 wrapper, AP_OFS=T) vs DUT(strap tied encode(T)), T = old ffddffdcffdfffdf / new ffe3ffe2ffe1ffe1, neg controls neg/negfr must FAIL.
  epyc8 kv-ahub-rh1/eq, driver tmp/eqdrv.sh, log intel2 ~/tmp/kv-ahub-rh1/eq3.log.
## Next
1. bench PASS -> push tool+swap via ot-push-main, post BENCH. 2. s1 route -> signoff.py run (rt current, flow tag) + routed LEC; LEF access-window splice as eco2 (abstract_detail.py splice) + probe.
3. export view; rows to KV-PLAN-R6: hard_cores ahub lef/lib -> new view, pins_file new (671 pins), native_boundary_adapter qkd_ahub_ck7_strap.
## Log
- 11-21 22:3x started. 22:55 s1 launched; at CTS by 23:10.
