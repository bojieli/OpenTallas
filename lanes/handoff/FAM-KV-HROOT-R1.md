# FAM-KV-HROOT-R1 handoff (Sonnet). 2026-11-21 19:0x PST
Family: kv3_hroot (soft type 1900.8x838.08, 0 cores, 14 ft 534 b). Dead owners FABLE-FIX-KV-HG / KV-D23-COMPOSE. Coordinate: HUB-R4 (hub rings, no hroot builds), HGI-R6 (hg/hgi), KV-PLAN-R6 (applies D27d3, takes rows).
## Classification (real logs)
Attempts: D23 a3 / D25d a5 = post-CTS SETUP_TRIAGE (-325 / -753.66, GRT clock skew + 740 um hops); D25d a5 also GRT flat overflow; D26 (11-21 14:04, epyc8 gen/kv3_hroot) first to pass post-CTS+GRT: TT after GRT repair -50.56, GRT 2.46% usage with only 13 overflow gcells BUT detail route 82k violations at iter0, DRT-0255 net2446 at (1866,561) um.
Root cause: E-strip hotspot. grt/density.png: a 100% density column at x~1875 um, y~465-650 (E face ft + landing ring + fan/relay stations); tap/endcap 121k + 136k cells. Not GRT congestion, local pin-strip density. Same cause the D25d diagnosis found (hops 556-738 um, all logic packed in E strip).
Env diff (3+ fail rule): D26 hroot config.mk vs D26 hub_Ei/hub_Wo/sys_c = only per-type values (die area, max_displacement, OT_TAP_*, OT_CLAND_PINSLOT_DENSE=1 hroot-only, OT_KEEP_WIRES, SDC sha). OT_PLACE_MAX_FANOUT 32, OT_PGCAP 1, CLAND_STRIP_DENS 1, IO_HOLD same. No signed KV type exists as sibling. Conclusion: no settings error; structural.
## Fix
FAM-KV-HUB-R2 variant A rows (h1 equal-hop relay re-sites 3895 changed + 784 new u_esh.h_c keys, u_st.d spread W x1600-1900 off the E strip; h2 station -> (1590,710); h3 ring_hold sender -50; 0 cycles) applied to D27d3 plan 48b92c30c8f6 -> plan 30004fa0b2df. Never validated before (HUB-R2 bind a2 died, HUB-R3 only tried variant B which needs landing_remap).
Chain: epyc8 /srv/opentallas-scratch2/claude/fam-kv-hroot-r1/chain.sh (tree over sealed D27d3, rt 7b6af7dd0449, G0 + strict bind + LATCHECK), unit via ot-run, intel2 client log ~/tmp/famkvhrootr1/chain.log, gate out W/bindgate/gate.out.
## Next
1. bindgate RC_BIND 0 / BIND_ERRORS 0 / RC_LATCHECK 0 / ALL_DONE -> kit_wave.py private-spec qwen_kvsys kv3_hroot --plan W/ana/plan_hroot.json --tree W/tree --bind-out W/tree/physical/die_plan/qwen_kvsys/plan_of_record/bind_of_record --src-manifest off --rt 7b6af7dd0449(>=dd507bc8ba2a ok) --host epyc7|epyc9 --lane FAM-KV-HROOT-R1 (on intel2), run-item.
2. Read post-hook TT, final 5_1_grt.odb, and the E-strip density column in grt/density.png; if still >95% add a second spread (stations on kvpc/slg, TAP-GRID west-tap drop).
3. On signing: rows to KV-PLAN-R6 (W/ana/hroot-relay-d28.json + gen/h1_hroot_rows.py), rebuild from a manifest tree for export.
