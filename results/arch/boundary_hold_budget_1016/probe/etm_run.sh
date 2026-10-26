R=/srv/opentallas-scratch2/claude/closure-loop/hcoll_v5_ctl2-v7-e11086804/routes/hcoll_v5_ctl2_v7_e11086804
B=$(ls -d $R/work/orfs/results/asap7/*/base); P=/OpenROAD-flow-scripts/flow/platforms/asap7
D=/srv/opentallas-scratch2/claude/flowhold-1016; mkdir -p $D/etm; chmod 777 $D/etm
LIBS=$(for l in AO_RVT_FF_nldm_211120.lib.gz INVBUF_RVT_FF_nldm_220122.lib.gz OA_RVT_FF_nldm_211120.lib.gz SEQ_RVT_FF_nldm_220123.lib SIMPLE_RVT_FF_nldm_211120.lib.gz; do echo -n "$P/lib/NLDM/asap7sc7p5t_$l "; done)
docker run --rm -v $R:$R:ro -v $D:$D -e BH_BASE=$B -e BH_SDC=$R/signoff.sdc -e BH_OUT=$D/etm -e "BH_LIBS=$LIBS" -e "BH_LEFS=$P/lef/asap7_tech_1x_201209.lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef" openroad/orfs:asap7lock bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $D/etm_probe.tcl" > $D/etm/log 2>&1
cmp $D/etm/etm_old.lib $D/etm/etm_new.lib && echo ETM_IDENTICAL || diff $D/etm/etm_old.lib $D/etm/etm_new.lib | head -20
