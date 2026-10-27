#!/bin/bash
# CLOCK-KV-R14 chain (intel1): r14 clock (band trees + strap_cover) combo GRT TT -> ndr016 RCX tree -> tree STA TT/FF
# -> mesh transient (RCX tree arrivals) -> stub STA (combo native stub SPEF)
set -e
R=/srv/opentallas-scratch2/claude/clock-kv-r14-1026; T=/srv/opentallas-scratch2/claude/wt/clock-kv-r14/tools/die_plan
export PYTHONPATH=$R/in/pylib:$T:$R/in
cd $R; echo "start $(date -Is) host $(hostname)"
O=${O:-r14}
python3 $T/die_clock_mesh.py combo $R/$O --kit $R/in/kit --plan $R/in/hm_r12.json --merge-shields > $O/combo_gen.log 2>&1; tail -2 $O/combo_gen.log
CORNERS=TT MEM=40 bash $R/$O/run_combo.sh || true; grep -H EXIT $R/$O/combo_TT.log; grep -A14 "Final congestion report" $R/$O/combo_TT.log | tail -3
grep -c "Start extra iteration" $R/$O/combo_TT.log || true
X=$R/$O/rcx; mkdir -p $X; python3 $T/rcx_kv.py $R/$O $X $T > $X/gen.log 2>&1 || { tail $X/gen.log; exit 1; }
docker run --rm --name r14-kv-rcx-$O-$$ --cpus 16 --memory 64g --memory-swap 64g -v "$R/$O:/b:ro" -v "$X:/out" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /out/rcx.tcl > /out/rcx.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc"
python3 $R/in/spef_connectivity.py $X/rcx.spef $X/connectivity.json | tail -1
for C in TT FF; do
 docker run --rm --name r14-kv-sta-$O-$C-$$ --cpus 4 --memory 24g -e CORNER=$C -e BASIS=rcx -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$X:/out" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /out/sta.tcl > /out/sta_\$CORNER.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc" &
done; wait
python3 $R/in/lvl.py $X/tree_TT_rcx.txt $X/tree_FF_rcx.txt
for C in TT FF; do
 cp $X/tree_${C}_rcx.txt $O/tree_${C}.txt
 python3 $T/die_clock_mesh.py mesh $O --corner $C | tail -1
 python3 $T/die_clock_mesh.py stubsta $O --corner $C
 python3 - $O $C <<"PY"
from pathlib import Path
from mix_clock_spef import header,sections
import sys
D=Path(sys.argv[1]);C=sys.argv[2];keep=set((D/"stub_nets.txt").read_text().split());n=0
with (D/f"native_{C}.spef").open() as f,(D/f"stubs_{C}.spef").open("w") as g:
 h,names,first=header(f);g.writelines(h)
 for name,lines in sections(f,first,names):
  if name in keep:g.writelines(lines);n+=1
print("stub nets",n,"of",len(keep))
PY
 docker run --rm --name r14-kv-stub-$O-$C-$$ --cpus 4 --memory 16g -v "$R/$O:/out" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sta -no_init -exit /out/stubs_$C.tcl > /out/stubs_$C.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc"
 awk "\$1==\"T\"" $O/taps_$C.txt | sort -k5 -g | awk "{n++; if(\$5>120)b++; s=\$5} END{print \"taps\",n,\"slew>120\",b+0,\"max\",s}"
done
echo "CHAIN_DONE $(date -Is)"
