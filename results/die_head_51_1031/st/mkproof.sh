#!/bin/bash
# DIE-HEAD-51 helper st: l48w-st measured proof = trial_tap_arrivals (both-edge) + start_stage_emit proof (stage taps)
cd /srv/opentallas-scratch2/claude/die-head-48/clk_st51; TL=/srv/opentallas-scratch2/claude/wt/dh51-st/tools/die_plan
rm -rf base proof_l48w_st; mkdir -p base; cp ../sta/proof_l48c/mesh.json base/
for c in TT FF; do python3 - $c <<PY
import sys
c=sys.argv[1]
E=open(f"out_{c}/edges_{c}.txt").read().splitlines(); A=open(f"out_{c}/arr_{c}.txt").read().splitlines()
et={l.split()[1]:l.split()[2:4] for l in E if l.startswith("T ")}
at=[l for l in A if l.startswith("T ")]
print(c,"T rows",len(at),"edges vs arr max diff",max(abs(float(et[l.split()[1]][i])-float(l.split()[2+i])) for l in at for i in (0,1)))
open(f"out_{c}/both_{c}.txt","w").write("\n".join([E[0]]+at+[l for l in E[1:] if l[:2] in ("F ","N ","M ")])+"\n")
PY
python3 $TL/trial_tap_arrivals.py kit_l48w_st/kit/clock/tree.json out_$c/both_$c.txt $c base/tap_arrivals_$c.json | tail -1; done
python3 $TL/start_stage_emit.py proof base --stages patch/start_stages_l48w_st.json --arr TT=out_TT/both_TT.txt --arr FF=out_FF/both_FF.txt --out proof_l48w_st 2>&1 | tail -3; ls proof_l48w_st
