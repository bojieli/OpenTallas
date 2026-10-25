#!/bin/bash
# QC-TOK: tree-vs-chain equivalence on the xt1 carve.  The tree bind hoists the tt_ctlm -> dvs_W5.u_fdn pads (+4 on
# hr / cmd / table_req) into tt_ctlm, which is OUTSIDE the carve; the tb drives the slice pins, so the tree carve sees
# hr/cmd 4 cycles early.  Re-adding them at the tb (cmd/hr events +4) must reproduce the chain log exactly.
W=/srv/opentallas-scratch2/claude/qc-tok/smoke_tree_near; cd $W; OBJ=$(ls -d $W/obj_* | head -1)
python3 - <<'PY'
L=[l.split() for l in open('ev.txt') if l.strip()]
out=sorted(((int(c)+4 if p in ('0','1') else int(c)), int(p), v) for c,p,v in L)
open('ev_eq.txt','w').write(''.join(f'{c} {p} {v}\n' for c,p,v in out))
PY
for m in 0 1; do $OBJ/Vtb +EV=$W/ev_eq.txt +LOG=$W/log_eq_m$m.txt +NCYC=6464 +OT_ROM_DIR=$W/inputs/masks +SMOKE_MUT_SKEW=$m > sim_eq_m$m.out 2>&1 & done; wait
for m in 0 1; do
  C=$HOME/scratch/qc-tok/xt1/smoke_near/log_m$m.txt
  # chain log vs tree log: HRGO / HRXPF / END are tb-side (logged at the pin), compare everything else
  if diff <(grep -v "HRGO\|HRXPF\|END" $C) <(grep -v "HRGO\|HRXPF\|END" log_eq_m$m.txt) > eq_m$m.diff; then echo "m$m EQUIVALENT ($(grep -vc "HRGO\|HRXPF\|END" $C) lines)"; else echo "m$m DIFFER $(grep -c '^[<>]' eq_m$m.diff)"; fi
done
