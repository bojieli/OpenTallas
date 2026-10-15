#!/usr/bin/env python3
"""Freeze actual VM activation/native controller -> unchanged SM numerical join."""
import argparse,hashlib,io,json,shlex,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E='results/rtl/hbm_smh_static_feed_1014/'
BASE=E+'connected_sources/'
def prepare(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 old=json.loads((ROOT/(E+'native_build_source_pins.json')).read_text())
 src=[]
 for p,h in old.items():
  if p.startswith('inputs/') or not p.endswith(('.sv','.v')):continue
  if '/native_service_source/' in p or p.startswith('rtl/test/'):continue
  assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
  src.append(p)
 names={Path(p).name:p for p in src}
 extra=['ot_hbm_sm_activation_programmed_static.sv','ot_hbm_sm_activation_static.sv','ot_hbm_sm_aq_static.sv',
 'ot_vms_calendar_static.sv','hfd_vms_bank_static_rg6wg2.sv','ot_vms_bank_static.sv','ot_hdc_fastfp_lat_f12.sv',
 'ot_hdc_fp32_f12.sv','ot_hdc_fastfp.sv','ot_hdc_prefix.sv','ot_hdc_sfu.sv','ot_hdc_delay.sv',
 'ot_sram_1r1w_1024x256_m2_r2c2.v','ot_sram_1r1w_32x128_m1.v']
 for n in extra:
  p=BASE+'activation/'+n
  if n in names:
   assert (ROOT/p).read_bytes()==(ROOT/names[n]).read_bytes(),n
  else:src.append(p)
 src += [BASE+'controller/'+n for n in ['ot_hbm_svc_native_stream_pc.sv','ot_hbm_svc_native_sector_guarded_stack.sv','tb_hbm_svc_command_dram_pipeline_fixture.sv']]
 src += ['rtl/test/tb_smh_activation_source_fixture.sv','rtl/test/tb_smh_connected_checkpoint_native.sv']
 files={p:(ROOT/p).read_bytes() for p in src}
 for sm in range(8,13):
  for p in Path('/home/ubuntu/hbm-mapped4-checkpoint-1015-final',f'sm{sm:02}').glob('*'):files[f'inputs/sm{sm:02}/'+p.name]=p.read_bytes()
  for p in (ROOT/(E+'checkpoint_wqa_programme')/f'sm{sm:02}').glob('*256.hex'):files[f'inputs/sm{sm:02}/'+p.name]=p.read_bytes()
 for p in (ROOT/(E+'native_activation')).glob('*'):files['inputs/activation/'+p.name]=p.read_bytes()
 for n in ['vm.hex','activation.hex','request_sectors.hex','raw_fp32.hex']:
  files['inputs/activation/'+n]=(ROOT/(BASE+'activation/'+n)).read_bytes()
 pins={p:hashlib.sha256(b).hexdigest() for p,b in files.items()}
 (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 with tarfile.open(out/'source.tgz','w:gz') as t:
  for n,b in files.items():
   i=tarfile.TarInfo(n);i.size=len(b);t.addfile(i,io.BytesIO(b))
 defines=['OT_SMH_FC_HIER','OT_FP_DATA_NORST','OT_SMH_DRST0','OT_SMH_RSTRELAY','OT_SMH_RSTPIN','OT_SMH_HIER','OT_SMH_PTW_OHDLY','OT_SMH_PINREG','OT_SMH_XREL','OT_SMH_PRODUCTION_SHAPE']
 cmd=['verilator','--binary','--timing','-Wno-fatal','-Wno-TIMESCALEMOD','--top-module','tb_smh_mapped_checkpoint_native','-GSTACK=1','-j','8','--Mdir','obj','-o','native']+['-D'+d for d in defines]+src
 script='''#!/bin/bash
set -euo pipefail
ulimit -c 0
cd /var/tmp/smh-native-connected-1015
cp /var/tmp/smh-native-mapped-1015-v2/obj/native /var/tmp/smh-native-mapped-1015-v2/native_stack1_preserved
tar xzf source.tgz
ln -sfn /var/tmp/smh-native-mapped-1015-v2/obj obj
'''+shlex.join(cmd)+''' > build.log 2>&1
for sm in 08 09 10 11 12; do
 ./obj/native +DIR=inputs/sm${sm} +SM=$((10#$sm)) +TAGBASE=1000 +ACTDIR=inputs/activation +XFILE=inputs/activation/xw.hex +GFILE=inputs/activation/sm${sm}.gold.hex +CFILE=inputs/sm${sm}/command256.hex +RFILE=inputs/sm${sm}/read256.hex > sm${sm}.log 2>&1
done
if ./obj/native +DIR=inputs/sm08 +SM=8 +TAGBASE=1000 +ACTDIR=inputs/activation +XFILE=inputs/activation/xw.hex +GFILE=inputs/activation/sm08.gold.hex +CFILE=inputs/sm08/command256.hex +RFILE=inputs/sm08/read256.hex +MUTANT=1 > mutant.log 2>&1; then exit 1; fi
grep -q 'native activation actual code SRAM beat payload mismatch' mutant.log
printf '%s\\n' 0 > exitcode
'''
 (out/'run.sh').write_text(script)
 return pins
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();prepare(a.out)
