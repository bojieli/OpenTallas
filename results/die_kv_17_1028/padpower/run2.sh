L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
mkdir -p /tmp/l; for f in $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*; do b=$(basename $f .gz); case $f in *.gz) zcat $f > /tmp/l/$b;; *) cp $f /tmp/l/$b;; esac; done
sta -no_init -exit /w/pw.tcl > /w/pw.log 2>&1
