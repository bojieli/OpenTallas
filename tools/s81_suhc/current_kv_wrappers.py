#!/usr/bin/env python3
"""Export current native KVT/KVE/KVP ABI without aliasing historical hard views."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
 source=ROOT/'rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_kv.sv';core=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_kv.sv';text=source.read_text();mods=[];rows=[]
 for name,count in [('kvt',4),('kve',56),('kvp',8)]:
  old='dsfd_su_t_'+name;new=old+'_current';m=re.search(r'module '+old+r'\s*\([\s\S]*?endmodule',text);assert m
  s=m.group().replace('module '+old+' (','module '+new+' (');h,b=s.split(');',1)
  if name=='kvt':h=h.rstrip();h+=',\n    output wire [1:0] e_mode, output wire [13:0] e_nb\n';b=b.replace('.e_go(e_go)', '.e_mode(e_mode), .e_nb(e_nb), .e_go(e_go)');added={'e_mode':2,'e_nb':14}
  else:h=h.rstrip();h+=',\n    output wire norm_v, output wire [127:0] norm_y\n';b=b.replace('.o_f(o_f)', '.norm_v(norm_v), .norm_y(norm_y), .o_f(o_f)');added={'norm_v':1,'norm_y':128}
  result=h+');'+b;assert result.count('.'+next(iter(added))+'(')==1
  mods.append(result);rows.append(dict(top=new,native_core='ot_s81_su_kvt' if name=='kvt' else 'ot_s81_su_kve',production_instances=count,added_output_bits=added,normal_edges_added=0,logic_or_state_added=0,physical_view='MISSING: never bind historical master; die must assign current output pins and native gate/bench+mutant/TT/FF/DRC'))
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text('`timescale 1ns/1ps\n// Source-current opt-in hardleaf wrappers; arithmetic is the existing native RTL.\n\n'+'\n\n'.join(mods)+'\n')
 record=dict(scope='Exact wrapper export of existing current native outputs; not numerical or physical qualification',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,core]},emitted_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),wrappers=rows)
 a.receipt.write_text(json.dumps(record,indent=1)+'\n');print(json.dumps(rows))
if __name__=='__main__':main()
