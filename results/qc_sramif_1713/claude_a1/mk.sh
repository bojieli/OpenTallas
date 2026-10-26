#!/bin/bash
# PATH-QC-SRAMIF2: make two place-only prototype kits from the Codex aspect profile (inputs preserved, read-only).
# M = signed-recipe anchoring (face_flops + macro_pin_flops); P = Codex planned_if_sites (FIRM pre-GPL, released at DPL).
set -euo pipefail
kind=$1; S=/srv/opentallas-scratch2/claude/codex-qc-sramif-1713/${kind}_aspect_a1; R=/srv/opentallas-scratch2/claude/path-qc-sramif2
mkdir -p $R
for v in m p; do
  D=$R/${kind}_a1$v; [ -e $D ] && { echo exists $D; exit 1; }
  cp -a $S $D
  sed -i 's/kq_qfd_dv_s8x_\(btab\|prog\)_adj0/kq_qfd_dv_s8x_\1_aspect1713a1/g' $D/*.sh $D/*.tcl 2>/dev/null || true
  sed -i "s#/srv/opentallas-scratch2/claude/codex-qc-sramif-1309/[a-z_0-9]*#$D#" $D/so_only.sh
done
cat > $R/${kind}_a1p/pre_gpl_s7.tcl <<'T'
# PATH-QC-SRAMIF2 variant P: face flops (pin registers at faces, unchanged), then the Codex 1713 planned whole-cell
# interface sites (planned_if_sites.tcl: macro IF + private write predecessors + boundary regs, FIRM). Released at DPL.
source /work/face_flops.tcl
source /work/planned_if_sites.tcl
T
python3 - $R/${kind}_a1p <<'PY'
import re,sys
d=sys.argv[1];names=re.findall(r'findInst \{(.*?)\}\]',open(d+'/planned_if_sites.tcl').read())
with open(d+'/planned_if_release.tcl','w') as f:
  f.write('# PATH-QC-SRAMIF2: release planned IF sites to PLACED for DPL legalisation.\nset b [ord::get_db_block]\n')
  for n in names: f.write('set i [$b findInst {%s}]; if {$i ne "NULL"} {$i setPlacementStatus PLACED}\n'%n)
print(len(names),'planned insts')
PY
printf '%s\n' '# PATH-QC-SRAMIF2 variant P PRE_DETAIL_PLACE' 'source /work/face_flops_release.tcl' 'source /work/planned_if_release.tcl' > $R/${kind}_a1p/pre_dpl_s7.tcl
for v in m p; do
cat > $R/${kind}_a1$v/go_a1.sh <<'G'
#!/bin/bash
# PATH-QC-SRAMIF2 prototype: floorplan + place only from the copied (same-netlist) 1_synth, then keep_check + F6 dump. No CTS/route.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock
echo "go_a1 start $(date -Is) host $(hostname)" >> "$K/image.txt"
docker run --rm --name sramif2-$(basename $K)-$$ --cpus=8 --memory=20g --memory-swap=20g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-floorplan do-place; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_a1.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "go_a1 place rc $rc $(date -Is)" >> "$K/image.txt"; [ $rc = 0 ] || exit $rc
python3 -I "$K/keep_check.py" "$K" > "$K/keep_check.txt" 2>&1; kc=$?; tail -2 "$K/keep_check.txt"
"$K/f6_dump.sh" "$K" 3_place > "$K/f6_place.log" 2>&1; tail -4 "$K/f6_place.log"
echo "go_a1 done keep $kc $(date -Is)" >> "$K/image.txt"; exit $kc
G
chmod +x $R/${kind}_a1$v/go_a1.sh; done
ls $R
