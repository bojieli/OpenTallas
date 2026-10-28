#!/bin/bash
# DIE-QC-2 build: kit (slice-spine + length-match, leaf 300, rep 250) -> placement clock STA -> combo GRT incl routed clock TT+FF
# usage: runB.sh NAME REGIONS [extra kit args]
set -u
N=$1; R=$2; shift 2
W=/srv/opentallas-scratch2/claude/wt/qc-sliceclk-1027; D=/srv/opentallas-scratch2/claude/die-qc2-1027/$N; O=$D/trial
PLAN=$W/physical/die_plan/qwen_compute/die_plan_sliceclk.json
mkdir -p $D; log(){ echo "$* $(date)" >> $D/chain.log; }
log "START code $(git -C $W rev-parse --short HEAD) dirty $(git -C $W diff --stat | tail -1) plan $(sha256sum $PLAN | cut -c1-12) regions $R args $*"
cd $W
~/.local/bin/ot-run --mem 16 --threads 2 --hosts localhost --dir $W --priority die -- python3 -I $W/tools/die_plan/die_trial.py kit $PLAN --out $O --region-trees $R --slice-spine --rep-um 250 --leaf-um 300 "$@" > $D/kit.log 2>&1; log "kit rc $?"
python3 -c "import json;m=json.load(open(\"$O/kit.json\"))[\"clock_tree\"];print(m[\"site_legal\"]);print(m[\"slice_spine\"].get(\"length_match\"));print(m[\"wire_um\"],m[\"repeaters\"])" >> $D/chain.log 2>&1
cd $O
~/.local/bin/ot-run --mem 32 --threads 4 --hosts localhost --dir $O --priority die -- bash run_clock.sh > $D/clock_run.log 2>&1; log "clock rc $?"
mkdir -p $D/clk; cp $O/clock/{ctree.v,ctree.tcl,tree.json} $D/clk/
for C in TT FF; do
  ( CORNER=$C python3 -I /srv/opentallas-scratch2/claude/die-qc-1027-r250/mk_combo_qc.py $O $D/clk $D/out_$C > $D/mk_$C.log 2>&1 || { log "MK_FAIL $C"; exit 1; }
    cat > $D/out_$C/run.sh <<EOR
#!/bin/bash
docker run --rm --name dieqc2-$N-$C-\$\$ --memory=64g --memory-swap=64g --cpus=16 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/work:ro -v $D/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \\\$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
EOR
    chmod +x $D/out_$C/run.sh
    ~/.local/bin/ot-run --mem 64 --threads 16 --hosts localhost --dir $D/out_$C --priority die -- bash $D/out_$C/run.sh > $D/combo_run_$C.log 2>&1; log "combo $C rc $? $(tail -1 $D/out_$C/combo_$C.log)" ) &
done
wait
log CHAIN_DONE
