#!/usr/bin/env python3
"""Fleet-only real-module fault-export proof, with immutable source mutation witnesses."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='rtl/qwen_sys/'
SOURCES=[BASE+'static_embedding_20261014/'+s+'.sv' for s in ('qkd_pc_fault_export_family','qkd_kv_pc_chain_station_b','qkd_static_kv_pc_es_merge_b','qkd_static_kv_pc_es_merge','qkd_embedding_static_map')]+[BASE+'static_kv_20261014/'+s+'.sv' for s in ('qkd_static_kv_pc_path_nc','qkd_static_kv_return_slots_mc','qkd_static_kv_ownership')]+[BASE+'kv_rly_std_20261016/qkd_rlys.sv']
TB='rtl/test/qwen_static_kv/tb_pc_fault_export.sv'
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verilator',default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator');p.add_argument('--mode',choices=['normal','missing_export','missing_chain','missing_merge','wrong_field'],default='normal');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 version=subprocess.check_output([a.verilator,'--version'],text=True)
 if '5.050' not in version:raise ValueError('requires pinned 5.050: '+version)
 tb=(ROOT/TB).read_text();src=(ROOT/SOURCES[0]).read_text()
 if a.mode=='missing_export':src=src.replace('(FAULT_EXPORT != 0 && extra_core_fault)','(1\'b0)')
 if a.mode=='missing_chain':tb=tb.replace('.extra_core_fault(chain_fault|merge_fault)', '.extra_core_fault(merge_fault)')
 if a.mode=='missing_merge':tb=tb.replace('.extra_core_fault(chain_fault|merge_fault)', '.extra_core_fault(chain_fault)')
 if a.mode=='wrong_field':tb=tb.replace('o_grp[304:296]','o_grp[303:295]')
 st=a.out/'family.sv';bt=a.out/'bench.sv';st.write_text(src);bt.write_text(tb)
 cmd=[a.verilator,'--binary','--timing','-Wno-fatal','-Wno-PINMISSING','--top-module','tb_pc_fault_export','-j','2','--Mdir',str(a.out/'obj'),str(st),*[str(ROOT/s) for s in SOURCES[1:]],str(bt)]
 r=subprocess.run(cmd,capture_output=True,text=True);(a.out/'compile.log').write_text(r.stdout+r.stderr)
 if r.returncode:print((r.stdout+r.stderr)[-12000:]);return r.returncode
 r=subprocess.run([str(a.out/'obj/Vtb_pc_fault_export')],capture_output=True,text=True);(a.out/'runtime.log').write_text(r.stdout+r.stderr)
 receipt=dict(mode=a.mode,exit_code=r.returncode,verilator=version.strip(),source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES+[TB,'tools/qwen_kv_die/pc_fault_export_family.py',str(Path(__file__).relative_to(ROOT))]},mutated_family_sha256=hashlib.sha256(st.read_bytes()).hexdigest(),mutated_assembly_sha256=hashlib.sha256(bt.read_bytes()).hexdigest(),claim='Complete real source primitives and exact assembly fault-field mechanism only, no full PC or physical qualification',mutation_scope='family export equation' if a.mode=='missing_export' else 'source-ledger assembly join mutation' if a.mode!='normal' else 'unchanged')
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(r.stdout+r.stderr,end='');return r.returncode
if __name__=='__main__':raise SystemExit(main())
