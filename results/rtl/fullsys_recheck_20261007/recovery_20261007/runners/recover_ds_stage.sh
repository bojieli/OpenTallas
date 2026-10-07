#!/bin/bash
set -u
B=/srv/opentallas-scratch/claude/tk-hbm-harvest
D=$B/fsr
W=$B/lorentz-margin/work
# Preserve and reuse the complete child libraries; wait for the predecessor.
while [ ! -f "$D/qwen8k.done" ]; do sleep 30; done
python3 - "$W" "$D" <<'PY'
import sys,time,json,math,shutil
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch')
import admit_core
w,d=map(Path,sys.argv[1:])
# Largest measured peak from this exact campaign, build_resources_o0.log.
peak=468774208*1024
memtotal=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
headroom=max(32*2**30,math.ceil(memtotal/10))
need=peak+max(0,headroom-admit_core.RESERVE)
inventory=sum(p.stat().st_size for p in w.rglob('*') if p.is_file())
while True:
 if shutil.disk_usage(w).free>=2*inventory+headroom and admit_core.try_admit(need):break
 time.sleep(30)
(d/'ds1m_recovery_admission.json').write_text(json.dumps(dict(time=time.time(),measured_peak_bytes=peak,host_headroom_bytes=headroom,guard_request_bytes=need,guard_file=admit_core.__file__,actual_build_inventory_bytes=inventory,disk_free_bytes=shutil.disk_usage(w).free),indent=2)+'\n')
PY
cd "$W/obj"
TMPDIR=$W/tmp /usr/bin/time -v -o "$W/build_resources_recovery.log" make -j 6 -f Vtb_hbm_integrated_minimum_parent_hier.mk hier_build OPT_SLOW=-O0 OPT_FAST=-O0 OPT_GLOBAL=-O0 > "$W/build_recovery.log" 2>&1
rc=$?
echo "$rc" > "$W/build_recovery.exit"
if [ "$rc" -eq 0 ]; then
 for mode in base wrong_release corrupt_gold; do
  R=$W/run_recovery_$mode; mkdir -p "$R"; cp "$B"/lorentz-margin/fixture/die*_p*.hex "$B/lorentz-margin/fixture/fixture_manifest.json" "$R/"; cd "$R"
  extra=""; X=$B/lorentz-margin/fixture/gold
  [ "$mode" = wrong_release ] && extra="+WRONG_RELEASE"
  [ "$mode" = corrupt_gold ] && X=$B/lorentz-margin/gold_corrupt
  /usr/bin/time -v -o resources.log "$W/obj/Vtb_hbm_integrated_minimum_parent" +DIR="$X" $extra > run.log 2>&1
  echo "$?" > run.exit
 done
fi
echo "$rc" > "$D/ds1m_recovery.done"
