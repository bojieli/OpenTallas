#!/usr/bin/env python3
"""Bind real mapped calendar storage to the explicit static SU hardleaf graph.
Faults remain separate named outputs for the actual die fault collector. No
parent OR gate, hidden store, credit/ready issue or generated arithmetic result.
"""
import argparse,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();m=json.loads(Path(a.manifest).read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=True);path='rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_su_static_programmed.sv';raw=(R/path).read_text();s=raw.replace('module dsfd_sp_su_static_programmed #(', 'module dsfd_sp_su_static_programmed_hardleaf_candidate #(')
 s=s.replace('input wire sk,srs,arm,',f'input wire [{m["clock_entries"]-1}:0] ck_owner,\n    input wire ck_program,srs,arm,')
 s=s.replace('output wire flt,online,','output wire flt,program_fault,online,').replace('.clk(sk)', '.clk(ck_program)').replace('dsfd_sp_su_static u_su(.sk(sk),','dsfd_sp_su_static_hardleaf_candidate u_su(.ck_owner(ck_owner),')
 s=s.replace('assign flt=core_fault|store_fault;','assign flt=core_fault;\n    assign program_fault=store_fault;')
 assert s!=raw and '.sk(sk)' not in s and '.clk(sk)' not in s and 'core_fault|store_fault' not in s
 s='// OPT-IN ENGINEERING CANDIDATE. Actual mapped program SRAM and native arithmetic.\n// Clock entries must share the compiled SU epoch with actual per-child phi-R delivery.\n// flt and program_fault BOTH bind the real die fault collector; no production masking.\n'+s
 (out/'dsfd_sp_su_static_programmed_hardleaf_candidate.sv').write_text(s)
 r=dict(scope='actual source composition candidate; not native/token/physical qualification',source=dict(path=path,sha256=hashlib.sha256(raw.encode()).hexdigest()),core_clock_entries=m['clock_entries'],program_clock_entries=1,parent_state_bits=0,parent_logic_cells=0,normal_edges_added=0,program_store=dict(module='ot_s81_su_calendar_store',source='rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_store.sv',default_words=4096,word_bits=1024,default_macro_count=128,macro='ot_sram_1r1w_64x512_m1_r2c2',capacity='NOT_QUALIFIED: full compiled native timeline must fit declared DEPTH; actual overflow faults without extending timeline'),fault_abi=dict(flt='core_fault',program_fault='store_fault',both_required=True),vm_abi=dict(read_request_bits=240,response_bits=8208,write_bits=8688,su_clock_GHz=.9,vm_clock_GHz=1.2,clock_ratio='3:4',binding='OPEN actual native reserved-slot 3:4 bridges, phase/epoch and source capture/commit calendar'),open=['No die boot/program/arm and all-fault-sinks binding yet; exact native cycle profiles/capacity remain open.','Actual128program macros, select mux/controller physical homes/pins/CTS and phi-R remain open.','Owner reviews Explorer candidate before adoption; no old flat SU physical view alias.'])
 (out/'programmed_manifest.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
