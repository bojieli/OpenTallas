from pathlib import Path
import shutil,json,hashlib
for profile,bit in [("su10",244),("sfu14",235)]:
 old=Path(f"/srv/opentallas-scratch/codex/lg-{profile}-native-route-1015")
 new=Path(f"/srv/opentallas-scratch/codex/lg-{profile}-slew-repair-1015")
 assert not new.exists(),new
 new.mkdir();w=old/f"routes/lg_{profile}_native_route_1015/work/orfs"
 shutil.copytree(w,new/"work",copy_function=shutil.copy2);case=new/"work"
 frozen={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (case/"results").rglob("*") if p.is_file() and p.name.startswith(("1_","2_","3_","4_","4_cts"))}
 removed=[]
 for sub in ("results","reports","logs"):
  for p in (case/sub).rglob("*"):
   if p.is_file() and p.name.startswith(("5_","6_")):
    removed.append(str(p.relative_to(case)));p.unlink()
 hook=case/"hooks/pre_global_route_pre_grt.tcl"
 hook.write_text(f"set ::ot_lg_repair_net {{u_core.rr_d[{bit}]}}\nset ::ot_lg_repair_bit {bit}\n"+Path('/tmp/hvm_lg_slew_repair_1015.tcl').read_text()+"\n"+hook.read_text())
 (new/"prepared.json").write_text(json.dumps(dict(profile=profile,baseline=str(old),resume="unchanged actual4CTS",frozen=frozen,removed_in_successor_only=removed,repair_hook_sha256=hashlib.sha256(hook.read_bytes()).hexdigest()),indent=2)+"\n")
 script='''#!/bin/bash
set -euo pipefail
base=BASE
src=SOURCE
export PATH="$src/../bin:$PATH"
docker run --rm -v "$src:/src:ro" -v "$base/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts; python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 finish' > "$base/route.log" 2>&1
cd "$src"
python3 tools/w18/corner_sta_ref.py --orfs-dir "$base/work" --extra-sdc "$src/physical/ref_tile/vm_lg_bank_PROFILE_static_1015/signoff.sdc" --output "$base/corner_sta.json" > "$base/corner_sta.log" 2>&1
python3 /tmp/check_lg_slew_upstream_1015.py "$base"
'''.replace("BASE",str(new)).replace("SOURCE",str(old/"src")).replace("PROFILE",profile)
 (new/"run.sh").write_text(script)
 print(new,len(frozen),len(removed))
