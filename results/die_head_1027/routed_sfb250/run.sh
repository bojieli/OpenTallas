B=/srv/opentallas-scratch2/claude/die-head-1; O=$B/sfb250c; WT=/srv/opentallas-scratch2/claude/wt/die-head-1; J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
echo START $(date)
for C in TT FF; do docker run --rm --name dh1-sfb250c-$C-$$ --memory=40g --memory-swap=40g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $B/sfb250/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"; grep -E "^Total " $O/out_$C/combo_$C.log | tail -1; done
python3 $WT/tools/s81_head/landed_phase_ocv.py $J $O --tools $WT/tools/die_plan --out $O/landed_ocv.json > $O/landed_ocv.log 2>&1
echo END $(date)
