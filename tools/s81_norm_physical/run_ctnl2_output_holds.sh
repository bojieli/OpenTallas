#!/usr/bin/env bash
set -euo pipefail
# A new physical characterization; never modify the immutable CLOSED run.
parent=/srv/opentallas-scratch/codex/s81-norm-physical-1015/ctnl2-surplus-v2
run=/srv/opentallas-scratch/codex/s81-norm-physical-1015/ctnl2-output-v3
rel=results/asap7/opentallas_ot_s81_hc_ctnl_l2_asap7_ref_s81hc_ctnl_l2_native_ref_np2_granted_57b4f1931/base
mkdir -p "$run"
test ! -e "$run/orfs"
cp -a --reflink=auto "$parent/orfs" "$run/orfs"
cp -a --reflink=auto "$parent/src" "$run/src"
cp "$run/input/ctnl2_output_holds.tcl" "$run/src/ctnl2_output_holds.tcl"
# Load the known TT libraries using the original FF diagnosis preamble: topology
# edits themselves do not depend on corner. No old SPEF is used after the edit.
sed '/set ::ot_ce_corner/,$d' "$run/input/ctnl2_fdx331_ff.tcl" > "$run/orfs/eco.tcl"
printf 'source /src/ctnl2_output_holds.tcl\nremove_fillers\nwrite_db /work/%s/4_1_cts.odb\nwrite_db /work/%s/4_cts.odb\nexit\n' "$rel" "$rel" >> "$run/orfs/eco.tcl"
docker image inspect --format '{{.Id}}' openroad/orfs:latest > "$run/tool-image.txt"
sha256sum "$run/input/ctnl2_output_holds.tcl" "$run/input/run_ctnl2_output_holds.sh" > "$run/source-sha256.txt"
docker run --rm -v "$run/src:/src:ro" -v "$run/orfs:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/eco.tcl > "$run/eco.log" 2>&1
# Only successor copies are discarded. GRT, detailed route and extraction must
# recompute every wire; neither old SPEF nor old DRC establishes qualification.
find "$run/orfs/$rel" -maxdepth 1 -type f \( -name '5_*' -o -name '6_*' -o -name 'route.guide' \) -delete
docker run --rm -v "$run/src:/src:ro" -v "$run/orfs:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base finish' > "$run/route.log" 2>&1
cd "$run/src"
python3 tools/w18/corner_sta_ref.py --orfs-dir "$run/orfs" --extra-sdc "$run/src/physical/ref_tile/s81hc_ctnl_l2_native_ref/signoff.sdc" --output "$run/corner_sta.json" > "$run/sta.log" 2>&1
