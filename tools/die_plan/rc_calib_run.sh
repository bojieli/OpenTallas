#!/bin/bash
# rc_calib_run.sh <signoff_dir> <out_dir> <layers> <mem_gb> <modes: e.g. "wd rcx_tt rcx_ff est_tt est_ff"> (diagnostic; read-only mounts)
SO=$1; OUT=$2; L=$3; MEM=$4; MODES=$5; T=$(cd $(dirname $0); pwd)
mkdir -p $OUT/rc; cp $T/rc_calib_probe.tcl $T/rc_calib_wire_dump.py $OUT/ 2>/dev/null
cmd=$(cat $SO/tt/cmd.sh)
base=$(echo "$cmd" | grep -oP -- '-v \K[^ ]*(?=:/base)')
extra=$(echo "$cmd" | grep -o -- '-v [^ ]*' | grep -v ':/out$' | grep -v ':/base' | grep -v ':/sdc' | tr '\n' ' ')
img=$(echo "$cmd" | grep -oP 'openroad/orfs:\S+')
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
nm=flowrc_$(basename $OUT)
for c in tt ff; do grep -E '^foreach l|^read_liberty' $SO/$c/session.tcl > $OUT/libs_$c.tcl; done
pids=""
for m in $MODES; do
  case $m in
    wd) docker run --rm --name ${nm}_wd --memory ${MEM}g -v $base:/base:ro -v $OUT:/w $img $OR -python -exit /w/rc_calib_wire_dump.py /base/6_final.odb /w/wire.tsv > $OUT/wd.log 2>&1 ;;
    rcx_*|est_*)
      c=${m#*_}; mode=${m%_*}
      if [ $mode = rcx ]; then odb=/base/6_final.odb; else odb=/base/5_1_grt.odb; fi
      rcf=$(ls $OUT/rc/*.tcl 2>/dev/null | sed "s#$OUT#/w#" | tr '\n' ' ')
      docker run --rm --name ${nm}_$m --memory ${MEM}g -v $base:/base:ro -v $SO/$c/sdcdir:/sdc:ro $extra -v $OUT:/w \
        -e OT_MODE=$mode -e OT_LIBS=/w/libs_$c.tcl -e OT_ODB=$odb -e OT_SPEF=/base/6_final.spef -e OT_SDC=/sdc/golden.sdc \
        -e OT_LAYERS=$L -e "OT_RC_FILES=$rcf" -e OT_NETS=/w/nets.txt -e OT_OUT=/w/${c}_${mode} \
        $img $OR -no_init -exit /w/rc_calib_probe.tcl > $OUT/$m.log 2>&1 & pids="$pids $!" ;;
  esac
done
wait $pids
grep -h "RC_PROBE_DONE\|WIRE_DUMP_DONE\|stored_routes" $OUT/*.log
