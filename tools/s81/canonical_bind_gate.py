#!/usr/bin/env python3
"""Run both fail-closed gates against an immutable canonical construction snapshot."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--stage-map',type=Path,default=ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json');ap.add_argument('--plan',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 die=a.input/'construction_pass0_die.v';glue=a.input/'construction_pass0_die_glue.sv';shape=a.out/'shape.json'
 plan=a.plan or a.input/'construction_pass0_plan.json.gz'
 manifest=ROOT/'physical/s81_die_rtl/layer1.f'
 commands={'observed_shape':[sys.executable,'tools/s81/canonical_observed_shape.py','--die',str(die),'--plan',str(plan),'--stage-map',str(a.stage_map),'--sequencer-source',str(ROOT/'rtl/v41die/ot_s81_cfg7_seq.sv'),'--params',str(die)+'.params.json','--out',str(shape)], 'port_bind':[sys.executable,'tools/die_port_bind.py',str(die),'--rtl-file',str(glue),'-f',str(manifest),'--out',str(a.out/'port_bind.json')], 'hardware_ledger':[sys.executable,'tools/s81/actual_hardware_ledger.py','--manifest',str(manifest),'--die',str(die),'--port-bind',str(a.out/'port_bind.json'),'--shape',str(shape),'--out',str(a.out/'hardware_ledger.json')]}
 receipts={'scope':'COMPLETE_CONSTRUCTION_BEFORE_HOP_SIGNOFF_NOT_NATIVE','native_qualified':False,'sha256':{},'gates':{}}
 for p in list(a.input.glob('*'))+[manifest,a.stage_map,ROOT/'rtl/v41die/ot_s81_cfg7_seq.sv',ROOT/'tools/s81/canonical_observed_shape.py',ROOT/'tools/die_port_bind.py',ROOT/'tools/s81/actual_hardware_ledger.py',ROOT/'physical/s81_die_rtl/required_operations.json']:
  if p.is_file():receipts['sha256'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 for name,cmd in commands.items():
  with (a.out/(name+'.log')).open('w') as log:rc=subprocess.call(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  receipts['gates'][name]={'command':cmd,'exit_code':rc};(a.out/'status.json').write_text(json.dumps(receipts,indent=2)+'\n')
 return int(any(x['exit_code'] for x in receipts['gates'].values()))
if __name__=='__main__':sys.exit(main())
