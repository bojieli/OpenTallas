#!/usr/bin/env python3
import argparse,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--mut',choices=['PHW','SAW']);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
v=os.environ.get('OT_VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
src=[str(p) for p in (ROOT/'physical/s81_pq_hier/pinned').rglob('*.sv') if p.name!='ot_sram_1r1w_128x256_m1_r2c2.sv']
src += [str(p) for p in (ROOT/'rtl/dsrom_sys/s81_ph/pq').glob('*.sv')]
src += [str(ROOT/p) for p in ['rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv','rtl/test/dsrom_sys/tb_s81_pq_canonical_pins.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']]
defs=['OT_PQ_ROM_PORTS','OT_PQ_CTL_STATIC','OT_PQ_QB_PIPE','OT_PQ_QB_PHYS_SPLIT','OT_PQ_AQ_PHYS_SPLIT','OT_PQ_IX_PHYS_SPLIT','OT_PQ_IX_BANK_SPLIT','OT_PQ_BC_SLICED','DSFD_PQ_STATIC_X2']
if a.mut:defs.append('OT_S81_PQ_STATIC_MUT_'+a.mut)
cmd=[v,'--binary','--timing','--top-module','tb_s81_pq_canonical_pins','--Mdir',str(a.work.resolve()/'obj'),'-j','8','-Wno-fatal','-Wno-lint','-Wno-style',*[f'+define+{d}' for d in defs],*src]
with (a.work/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (a.work/'run.log').open('w') as f:rc=subprocess.run([str(a.work.resolve()/'obj/Vtb_s81_pq_canonical_pins')],stdout=f,stderr=subprocess.STDOUT).returncode
if a.mut:
 if rc==0 or 'CANONICAL_PINS FAIL' not in (a.work/'run.log').read_text():raise SystemExit('mutant did not fail the native pin gate')
elif rc:raise SystemExit(rc)
print((a.work/'run.log').read_text())
