# TL-SLC1XT8 handoff
Work dir epyc10/epyc9 /srv/opentallas-scratch2/claude/tl-slc1xt8/{fA,fB,fC}; units log intel2 same path fX/unit.log (kit_wave.py run-item, AP_DIR fX/ap).
fC legalize plan fC/plan_C.json, sidecar_C.json, bind out epyc9 fC/out.
NEXT: (1) fC bind: epyc9 fC/bind.log BIND_RC; if 0 run python3 mkspec.py fC with plan=fC/plan_C.json, bind_out=epyc9 fC/out, gen_args clock-landing fC/sidecar_C.json (mkspec lacks gen_args override: add), gen_host epyc9, launch kit_wave.py run-item as for fA (cd rt/tools/autopilot; AP_DIR=fC/ap).
(2) fA/fB: read fX/unit.log; when route done check gates (DRC 0, setup>=-42, hold>=0); pass -> AUTO-RESIGN.tsv row + RESULT line.
(3) python3 on epyc10 is 3.14: street_rule legalize needs fC/runleg.py wrapper (numpy bool json); bind needs epyc7/9/intel1 (scratch3 codex-wave-bind-1106 inputs).
