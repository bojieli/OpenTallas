#!/usr/bin/env python3
"""Launch the production-width original-vs-distributed SM transport proof."""
import base64,gzip,re,subprocess,tarfile,io,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--mutant',action='store_true');p.add_argument('--no-reset-relay',action='store_true');p.add_argument('--hard-transport',action='store_true');p.add_argument('--local',action='store_true');p.add_argument('--group-transport',action='store_true');p.add_argument('--verilator',action='store_true');p.add_argument('--west-split',action='store_true');p.add_argument('--land-mutant',action='store_true');a=p.parse_args()
if a.west_split: a.group_transport=True
source=(ROOT/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv').read_text()
mods=['ot_hbm_accel_smh_kreg','ot_hbm_accel_smh_kregk','ot_hbm_accel_smh_bundle_reg','ot_hbm_accel_smh_pt_w','ot_hbm_accel_smh_pt_e']
original='\n'.join(re.search(r'\bmodule\s+'+m+r'\b.*?\bendmodule',source,re.S).group() for m in mods)
files={'reference.sv':original.encode()}
# The extracted original modules are byte-for-byte current production bodies;
# no reference transformation or simulator replacement is applied.
for f in ['rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv','rtl/test/tb_hbm_smh_compact_transport.sv','rtl/lib/ot_hdly.sv','rtl/lib/ot_rst_relay.sv']:
 files[Path(f).name]=(ROOT/f).read_bytes()
if a.hard_transport:
 for f in ['ot_hbm_smh_transport_masters.sv','ot_hbm_smh_transport_hard.sv']:
  files[f]=(ROOT/'rtl/hbm_accel/sm'/f).read_bytes()
if a.group_transport:
 for f in ['ot_hbm_smh_transport_group_masters.sv','ot_hbm_smh_transport_group.sv']:
  files[f]=(ROOT/'rtl/hbm_accel/sm'/f).read_bytes()
if a.west_split:
 files['ot_hbm_smh_transport_split_masters.sv']=(ROOT/'rtl/hbm_accel/sm/ot_hbm_smh_transport_split_masters.sv').read_bytes()
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode='w') as t:
 for name,data in files.items():
  info=tarfile.TarInfo(name);info.size=len(data);t.addfile(info,io.BytesIO(data))
payload=base64.b64encode(gzip.compress(stream.getvalue())).decode()
defines=('-DOT_SMH_RSTRELAY ' if not a.no_reset_relay else '')+('-DOT_SMH_COMPACT_MUT_LAT' if a.mutant else '')
if a.hard_transport: defines+=' -DOT_SMH_COMPACT_HARD'
if a.group_transport: defines+=' -DOT_SMH_GROUP_TRANSPORT'
if a.west_split: defines+=' -DOT_SMH_WEST_SPLIT'
if a.land_mutant: defines+=' -DOT_SMH_LAND_MUT_LAT'
compile_cmd=(f'verilator --binary --timing -Wno-fatal -j 4 --top-module tb_hbm_smh_compact_transport {defines} *.sv > build.log 2>&1 || {{ tail -40 build.log; exit 1; }}\n./obj_dir/Vtb_hbm_smh_compact_transport' if a.verilator else f'iverilog -g2012 {defines} -s tb_hbm_smh_compact_transport -o bench *.sv\nvvp bench')
script=f'''set -e
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
work=$(mktemp -d /var/tmp/smh-compact-proof.XXXXXX)
trap 'rm -rf "$work"' EXIT
cd "$work"
printf '%s' '{payload}' | base64 -d | gzip -dc | tar xf -
{compile_cmd}
'''
if a.local: raise SystemExit(subprocess.call(['bash','-c',script]))
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem',('8' if a.verilator else '2'),'--threads',('4' if a.verilator else '1'),'--','bash','-c',script]))
