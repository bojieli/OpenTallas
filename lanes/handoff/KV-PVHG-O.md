# KV-PVHG-O handoff (Opus successor of FABLE-FIX-KV-PV + FABLE-FIX-KV-HG; started 2026-11-16 02:36 PST; Fable back 11-21)

Read first: lanes/handoff/FABLE-FIX-KV-PV.md, FABLE-FIX-KV-HG.md (decisions + paths kept there).
My dir: epyc10 /srv/opentallas-scratch2/claude/kv-pvhg-o (pgp.sh; rt1c03 = main 1c0336e240c tools with the r273 checker; run_raw.sh + raw/kse_rawfix.py
= raw-row step isolated from ring/taps.py, which shadowed tools/die_plan/taps.py); intel2 ~/tmp/kvpvhgo (ot-run logs); intel2 .../kv-pvhg-o/repo (git clone).

## Done (11-16)
- ectlk q0 37/26: post-ECO LEC EQUIVALENT cp=17283; exported qkd_ectlk_q0__r37_eco1116 rtx-pro + AGIdock, odb sha 926f6cbb4836 equal, INDEX both. q0-q3 all archived.
- hg v25hv 76d7691ad625: G0 0, strict bind 0, R8 0, LATCHECK 2404/2404, plan_gate_pre PASS 0 (also v25h). READY-ROWS posted to KV-102 (~06:00).
- pv join header: claude/kv-pvhg-o-pvjoin-hdr-1116 @f79d061f1f3 (gen_phys macro blackbox header from multi-module root/rtl source). READY posted;
  reproduced on 7yhr kv3_pv_v1n gen (epyc8 kv-pvhg-o/genrepro.sh). Needed in the KV tree before any pv gen.

## In flight
- pv k2 (tap-stable, kvgeom7yhr 723fd5b4b006): 199/221 rings sited (22 NO_SITE stay soft), disp med 76 / max 337, 0 channels, clock+reset tap tables
  byte-equal on all 16 pv types. k2n (no-raw) FULL gate (HCPARAM on): G0 0, bind4 0 errors, PVX PASS, R8 0, LATCHECK 2404/2404; kit_rtl v1n/v7/v12 running
  (ring/k2n.gate.out). Raw rows: kv-pvhg-o/run_raw.sh k2n k2r k2n -> ring/k2r; then full gate on k2r -> READY-ROWS to KV-102.

## Next
1. k2r full gate pass -> READY-ROWS pv delta (k2r sha) to KV-102; cells per type decide which pv types still need the 3-way cut (>400k).
2. Rebind hg (v25hv) + pv (k2r) on the converged KV tree when TOOLS-CONVERGE posts it (r249 one tree); must carry @f79d061f1f3.
3. Pilots after ADOPT: kv3_pv_v1n; kv3_hg_v1 + kv3_hg_v3 (read at CTS).
