#!/usr/bin/env python3
"""Prepare source-exact admitted oneproductionSM native mapped-checkpoint run."""
import argparse,hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prepare(out):
 import dshbm_sm_pq_seq as P
 src=[p for p in P.SRC+P.SMH_SRC if not p.startswith('rtl/test/') and p not in ('rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v')]
 src += ['physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
 src += ['rtl/hbm_accel/sm/static/'+p for p in ['ot_smh_static_feed.sv','ot_smh_static_front.sv','ot_hbm_accel_smh_static.sv','ot_smh_calendar_static.sv','ot_smh_packed_program_join.sv']]
 src += ['rtl/hbm_accel/loader/service_native/'+p for p in ['ot_hbm_svc_async_fifo.sv','ot_hbm_svc_prefetch_burst_bank.sv','ot_hbm_svc_prefetch_mapped4_cdc.sv','ot_hbm_svc_prefetch_mapped4_owner.sv','ot_hbm_svc_static_sm_packed136.sv']]
 src += ['rtl/lib/ot_reset_sync.sv','results/rtl/hbm_smh_static_feed_1014/native_service_source/rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','results/rtl/hbm_smh_static_feed_1014/native_service_source/rtl/hdc/kv/ot_hdc_hbm_model.sv','results/rtl/hbm_smh_static_feed_1014/native_service_source/rtl/chip/ot_chip_v41x_hbm3e_phy.sv','rtl/test/tb_smh_mapped_checkpoint_native.sv']
 src=list(dict.fromkeys(src));out=Path(out);out.mkdir(exist_ok=False,parents=True)
 files={p:(ROOT/p).read_bytes() for p in src}
 for p in (ROOT/'results/rtl/hbm_smh_static_feed_1014/native_activation').glob('*'):files['inputs/activation/'+p.name]=p.read_bytes()
 for sm in range(13):
  for p in Path('/home/ubuntu/hbm-mapped4-checkpoint-1015-final',f'sm{sm:02d}').glob('*'):files[f'inputs/sm{sm:02d}/'+p.name]=p.read_bytes()
  for p in (ROOT/'results/rtl/hbm_smh_static_feed_1014/checkpoint_wqa_programme'/f'sm{sm:02d}').glob('*256.hex'):files[f'inputs/sm{sm:02d}/'+p.name]=p.read_bytes()
 pin={p:hashlib.sha256(b).hexdigest() for p,b in files.items()}
 (out/'source_pins.json').write_text(json.dumps(pin,indent=2)+'\n')
 with tarfile.open(out/'source.tgz','w:gz') as t:
  for name,b in files.items():
   info=tarfile.TarInfo(name);info.size=len(b);t.addfile(info,io.BytesIO(b))
 defines=['OT_SMH_FC_HIER','OT_FP_DATA_NORST','OT_SMH_DRST0','OT_SMH_RSTRELAY','OT_SMH_RSTPIN','OT_SMH_HIER','OT_SMH_PTW_OHDLY','OT_SMH_PINREG','OT_SMH_XREL','OT_SMH_PRODUCTION_SHAPE']
 build=' '.join(['verilator','--binary','--timing','-Wno-fatal','-Wno-TIMESCALEMOD','--top-module','tb_smh_mapped_checkpoint_native','-GSTACK=0','-j','8','--Mdir','obj','-o','native']+['-D'+d for d in defines]+src)
 script='''#!/bin/bash
set -euo pipefail
ulimit -c 0
cd /var/tmp/smh-native-mapped-1015-v2
tar xzf source.tgz
'''+build+''' > build.log 2>&1
./obj/native +DIR=inputs/sm00 +SM=0 +TAGBASE=1000 +XFILE=inputs/activation/xw.hex +GFILE=inputs/activation/sm00.gold.hex +CFILE=inputs/sm00/command256.hex +RFILE=inputs/sm00/read256.hex > sm00.log 2>&1
'''
 # One actualSM/stack0vehicle validates then samebinaryreplaysitsotheractualSMrows.
 script+='''for sm in 01 02 03 04 05 06 07; do
 ./obj/native +DIR=inputs/sm${sm} +SM=$((10#$sm)) +TAGBASE=1000 +XFILE=inputs/activation/xw.hex +GFILE=inputs/activation/sm${sm}.gold.hex +CFILE=inputs/sm${sm}/command256.hex +RFILE=inputs/sm${sm}/read256.hex > sm${sm}.log 2>&1
done
if ./obj/native +DIR=inputs/sm00 +SM=0 +TAGBASE=1000 +XFILE=inputs/activation/xw.hex +GFILE=inputs/activation/sm00.gold.hex +CFILE=inputs/sm00/command256.hex +RFILE=inputs/sm00/read256.hex +MUTANT=1 > mutant.log 2>&1; then exit 1; fi
grep -q 'NATIVE_CHECKPOINT numerical mismatch' mutant.log
printf '%s\\n' 0 > exitcode
'''
 (out/'run.sh').write_text(script);return pin
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();prepare(a.out)
