#!/bin/bash
# QC-SMALLREG-1 build: main die_trial kit --tree-form link_htree (balance_legalize as-is, no builder edits) on a small-region
# map + locality fish feed -> placement clock STA -> combo GRT incl routed clock TT+FF (50 it, critical 0).
# usage: runK.sh NAME MAP FEED [extra kit args]
set -u
N=$1; R=$2; F=$3; shift 3
W=/srv/opentallas-scratch2/claude/wt/qc-smallreg-1027; D=/srv/opentallas-scratch2/claude/qc-smallreg-1027/$N; O=$D/trial
PLAN=$W/physical/die_plan/qwen_compute/die_plan_sliceclk.json
mkdir -p $D; log(){ echo "$* $(date)" >> $D/chain.log; }
log "START code $(git -C $W rev-parse --short HEAD) plan $(sha256sum $PLAN | cut -c1-12) map $R feed $F args $*"
cd $W
~/.local/bin/ot-run --mem 16 --threads 2 --hosts localhost --dir $W --priority die -- python3 -I $W/tools/die_plan/die_trial.py kit $PLAN --out $O --region-trees $R --feed $F --tree-form link_htree --rep-um 250 --tree-site-legal --tree-site-slide "$@" > $D/kit.log 2>&1; log "kit rc $?"
python3 -c "import json;m=json.load(open(\"$O/kit.json\"))[\"clock_tree\"];print({k:m[k] for k in m if k not in ('taps',)} )" 2>&1 | cut -c1-3000 >> $D/chain.log
cd $O
~/.local/bin/ot-run --mem 32 --threads 4 --hosts localhost --dir $O --priority die -- bash run_clock.sh > $D/clock_run.log 2>&1; log "clock rc $?"
mkdir -p $D/clk; cp $O/clock/{ctree.v,ctree.tcl,tree.json} $D/clk/
[ -n "${NOGRT:-}" ] && { log CHAIN_DONE_NOGRT; exit 0; }
for C in TT FF; do
  ( CORNER=$C python3 -I /srv/opentallas-scratch2/claude/die-qc-1027-r250/mk_combo_qc.py $O $D/clk $D/out_$C > $D/mk_$C.log 2>&1 || { log "MK_FAIL $C"; exit 1; }
    cat > $D/out_$C/run.sh <<EOR
#!/bin/bash
docker run --rm --name qcsr-$N-$C-\$\$ --memory=64g --memory-swap=64g --cpus=16 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/work:ro -v $D/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \\\$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
EOR
    chmod +x $D/out_$C/run.sh
    ~/.local/bin/ot-run --mem 64 --threads 16 --hosts localhost --dir $D/out_$C --priority die -- bash $D/out_$C/run.sh > $D/combo_run_$C.log 2>&1; log "combo $C rc $? $(tail -1 $D/out_$C/combo_$C.log)" ) &
done
wait
log CHAIN_DONE
