#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/codex/fspine-v9-parent-context-20261005
python3 - <<"PY"
import os,time,json,shutil
from pathlib import Path
b=Path("/srv/opentallas-scratch2/codex/fspine-v9-parent-context-20261005")
def cpu():return [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
a=cpu();time.sleep(3);c=cpu();d=[y-x for x,y in zip(a,c)]
idle=os.cpu_count()*d[3]/sum(d);load=float(Path("/proc/loadavg").read_text().split()[0]);mem=int(next(l for l in Path("/proc/meminfo").read_text().splitlines() if l.startswith("MemAvailable:")).split()[1])*1024;disk=shutil.disk_usage(b).free
r=dict(time_ns=time.time_ns(),load1=load,idle_cores=idle,MemAvailable_bytes=mem,disk_free_bytes=disk,cores=1,expected_peak_GiB=2)
(b/"pq0_fault_lowering_r3/headroom.json").write_text(json.dumps(r,indent=2)+"\n")
assert load<128 and idle>=1 and mem>=102*2**30 and disk>2**30,r
PY
