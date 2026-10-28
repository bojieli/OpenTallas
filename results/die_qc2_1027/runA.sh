#!/bin/bash
# DIE-QC-2 (A): combo GRT incl ROUTED clock, R35 16w NDR on the trunk (spine+column+legs), TT+FF in parallel
set -u
D=/srv/opentallas-scratch2/claude/die-qc2-1027; S=/srv/opentallas-scratch2/claude/die-qc-1027-r250; O=$S/trial
log(){ echo "$* $(date)" >> $D/chainA.log; }
for C in TT FF; do
 ( CORNER=$C python3 -I $D/mk_combo_qc.py $O $S/clk $D/outA_$C > $D/mkA_$C.log 2>&1 || { log MK_FAIL $C; exit 1; }
   cp $D/ndr.tcl $D/outA_$C/ndr.tcl
   cat > $D/outA_$C/run.sh <<EOR
#!/bin/bash
docker run --rm --name dieqc2-ndr-$C-\$\$ --memory=64g --memory-swap=64g --cpus=16 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O:/work:ro -v $D/outA_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 16 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \\\$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
EOR
   chmod +x $D/outA_$C/run.sh
   ~/.local/bin/ot-run --mem 64 --threads 16 --hosts localhost --dir $D/outA_$C --priority die -- bash $D/outA_$C/run.sh > $D/comboA_run_$C.log 2>&1; log "combo $C rc $? $(tail -1 $D/outA_$C/combo_$C.log)" ) &
done
wait; log A_DONE
