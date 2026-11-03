#!/usr/bin/env python3
"""Exact native SRAM ABI preflight; not a transistor/mapped-EQ certificate."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MASTER='ot_sram_1r1w_256x256_m2_r2c2'
def flattened(ports):
 return {p['name']+f'[{i}]' if p['is_vector'] else p['name']:p['direction']for p in ports for i in range(p['width'])}
def liberty_ports(text):
 types={name:int(width)for name,width in re.findall(r'type\s*\((\w+)\)\s*\{.*?bit_width\s*:\s*(\d+)',text,re.S)}
 result={name:direction for name,direction in re.findall(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{\s*direction\s*:\s*(input|output|inout)',text)}
 for name,typ,direction in re.findall(r'bus\s*\((\w+)\)\s*\{\s*bus_type\s*:\s*(\w+)\s*;\s*direction\s*:\s*(input|output|inout)',text):
  for i in range(types[typ]):result[name+f'[{i}]']=direction
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True);p.add_argument('--selected-abi',type=Path,help='exact selected provider macro ABI; default is the original StoreA capsule');a=p.parse_args();r=a.repo
 abi_path=a.selected_abi or r/'results/hbm_l730_native_event_0015/providers/ot_hnx_sfu_store_a__da81d76763c9_hard_macro_ABIs.json'
 ABI=json.loads(abi_path.read_text());source=flattened(next(x['ports']for x in ABI if x['module']==MASTER));d=r/'physical/asap7_memory_macros_v2'/MASTER;lef=(d/(MASTER+'.lef')).read_text();lp={name:direction.lower()for name,direction in re.findall(r'PIN\s+(\S+)\s*\n\s*DIRECTION\s+(INPUT|OUTPUT|INOUT)',lef)}
 # PG pins have USE POWER/GROUND and are not signal ABI ports.
 libs={c:liberty_ports((d/(MASTER+'_'+c+'.lib')).read_text())for c in ('tt','ff')}
 tool=r/'tools/hbm_layer_vehicle/export_l730_native_providers.py';spec=importlib.util.spec_from_file_location('native_export',tool);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);bb=flattened(mod.abi((d/(MASTER+'_bb.v')).read_text()))
 failures={name:dict(missing=sorted(set(source)-set(portmap)),extra=sorted(set(portmap)-set(source)-{'VDD','VSS'}),direction=[n for n in source if n in portmap and source[n]!=portmap[n]])for name,portmap in dict(LEF=lp,TT=libs['tt'],FF=libs['ff'],nativeBB=bb).items()}
 status='PASS_EXACT_NATIVE_MASTER_ABI'if all(not any(x.values())for x in failures.values())else'FAIL'
 out=dict(status=status,master=MASTER,signal_bits=len(source),native_master_count=32,native_memory_bits=2097152,failures=failures,hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in d.iterdir()if f.suffix in('.lef','.lib')or f.name.endswith('_bb.v')},preserved_native_semantics='RB11 ra[10:3]/wa[10:3], registered ks=ra[2:0],32-bit ro[{ks,5b0}+:32],wd replicated8times with32-bit shifted mask; rr/cr repair controls stay literal0 in exact selected lbank. Same true native master only; no generic memory alias.',scope='Signal names/width/direction and exact selected consumer wiring. Does not prove macro transistor behavior, provider mapped EQ, reset release or physical timing.')
 out['selected_abi_file']=str(abi_path);out['selected_abi_sha256']=hashlib.sha256(abi_path.read_bytes()).hexdigest()
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(status,{n:(len(p))for n,p in dict(LEF=lp,TT=libs['tt'],FF=libs['ff'],nativeBB=bb).items()});raise SystemExit(status!='PASS_EXACT_NATIVE_MASTER_ABI')
if __name__=='__main__':main()
