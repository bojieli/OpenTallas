#!/usr/bin/env python3
"""Launch the production-width original-vs-distributed SM transport proof."""
import base64,gzip,re,subprocess,tarfile,io,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--mutant',action='store_true');p.add_argument('--no-reset-relay',action='store_true');a=p.parse_args()
source=(ROOT/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv').read_text()
mods=['ot_hbm_accel_smh_kreg','ot_hbm_accel_smh_kregk','ot_hbm_accel_smh_bundle_reg','ot_hbm_accel_smh_pt_w','ot_hbm_accel_smh_pt_e']
original='\n'.join(re.search(r'\bmodule\s+'+m+r'\b.*?\bendmodule',source,re.S).group() for m in mods)
files={'reference.sv':original.encode()}
# The extracted original modules are byte-for-byte current production bodies;
# no reference transformation or simulator replacement is applied.
for f in ['rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv','rtl/test/tb_hbm_smh_compact_transport.sv','rtl/lib/ot_hdly.sv','rtl/lib/ot_rst_relay.sv']:
 files[Path(f).name]=(ROOT/f).read_bytes()
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode='w') as t:
 for name,data in files.items():
  info=tarfile.TarInfo(name);info.size=len(data);t.addfile(info,io.BytesIO(data))
payload=base64.b64encode(gzip.compress(stream.getvalue())).decode()
defines=('-DOT_SMH_RSTRELAY ' if not a.no_reset_relay else '')+('-DOT_SMH_COMPACT_MUT_LAT' if a.mutant else '')
script=f'''set -e
work=$(mktemp -d /var/tmp/smh-compact-proof.XXXXXX)
trap 'rm -rf "$work"' EXIT
cd "$work"
printf '%s' '{payload}' | base64 -d | gzip -dc | tar xf -
iverilog -g2012 {defines} -s tb_hbm_smh_compact_transport -o bench *.sv
vvp bench
'''
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','2','--threads','1','--','bash','-c',script]))
