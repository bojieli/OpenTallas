#!/bin/bash
set -uo pipefail
R=$(pwd)
C=$R/routes/gate/work/orfs
sha256sum src/rtl/qwen_dv/s5/qfd_dv_s5_su8{,_rst3}.sv > candidate.sha256
run_native() {
 docker run --rm -v "$R/src:/src:ro" -v "$C:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > synth.log 2>&1 || return $?
 docker run --rm -v "$R/src:/src:ro" -v "$C:/work" openroad/orfs:latest python3 -c 'import glob,subprocess;libs=sorted(glob.glob("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*"));v=glob.glob("/work/results/asap7/*/base/1_2_yosys.v")[0];cmd=["python3","/src/tools/ref_tile/native_census.py","--netlist",v,"--top","qfd_dv_s5_su8_rst3","--kit","qfd_dv_s5_su8","--out","/work/candidate_native.json"];[cmd.extend(["--liberty",x]) for x in libs];raise SystemExit(subprocess.call(cmd))' > native.log 2>&1
}
run_native & NP=$!
mkdir -p bench
BR=0
for case in '0 0' '0 1' '1 0' '2 0'; do
 read -r M X <<< "$case"
 (cd src && bash rtl/test/qwen_dv/s5/su8/bench.sh "$R/bench" "$M" "$X") > "bench_${M}_${X}.log" 2>&1
 RC=$?; echo "BENCH M=$M X=$X RC=$RC" | tee -a status.log
 if [ "$M" = 0 ] && [ "$RC" != 0 ]; then BR=1; fi
 if [ "$M" != 0 ] && [ "$RC" = 0 ]; then BR=1; fi
done
wait "$NP"; NR=$?
echo "NATIVE_RC=$NR BENCH_AGGREGATE_RC=$BR" | tee -a status.log
exit $((NR || BR))
