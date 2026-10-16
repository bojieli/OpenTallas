#!/usr/bin/env python3
"""Expose every existing RX native leaf clock/reset; preserve real arithmetic and edges."""
import argparse,hashlib,json,re
from pathlib import Path
import su_tile_tops as T
R=Path(__file__).resolve().parents[2]
SOURCE='rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv'
def generate():
 raw=(R/SOURCE).read_text();mod=T.modules(SOURCE)['ot_s81_su_rxh'];params,ports,body=mod
 roots={'ot_s81_su_rxc':'0','ot_s81_su_rxrb':'1','ot_s81_su_rxsf':'2+k','ot_s81_su_rxsb':'18+k','ot_s81_su_rxqr':'34+k*NQ+j'}
 changes=[]
 # Parser positions refer to comment-stripped body; comments retain positions.
 txt=T.strip_comments(body)
 for s,e,core,p,n,connections in T.instances(txt):
  if core not in roots:raise ValueError(core)
  old=body[s:e];idx=roots[core];new=old.replace('.clk(clk)',f'.clk(ck_leaf[{idx}])').replace('.rst_in(rst_in)',f'.rst_in(rs_leaf[{idx}])')
  if new==old or '.clk(clk)' in new or '.rst_in(rst_in)' in new:raise ValueError((core,n))
  changes.append((s,e,new,core,idx))
 out=body
 for s,e,new,_,_ in reversed(changes):out=out[:s]+new+out[e:]
 assert len(changes)==5 and not re.search(r'\b(always|reg)\b',T.strip_comments(out))
 ports=re.sub(r'input\s+wire\s+clk,\s*rst_in,','input wire [(34+32/QL)-1:0] ck_leaf, rs_leaf,',ports)
 assert 'clk, rst_in' not in ports
 text='`timescale 1ns/1ps\n// Generated from exact actual RX source; no arithmetic replacement or added edge.\nmodule ot_s81_su_rxh_clocked_candidate #(parameter '+', parameter '.join(k+'='+v for k,v in params.items())+') ('+ports+')'+out+'endmodule\n'
 manifest=dict(source=SOURCE,source_sha256=hashlib.sha256(raw.encode()).hexdigest(),candidate_sha256=hashlib.sha256(text.encode()).hexdigest(),root_count_production=38,parent_logic_cells=0,parent_state_bits=0,added_normal_edges=0,added_state_bits=0,roots=[dict(core=c,index=i) for _,_,_,c,i in changes],qualification='Source candidate only. Requires exact bench/mutants, native physical leaf views and all incident joins.')
 return text,manifest

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);text,manifest=generate();(out/'ot_s81_su_rxh_clocked_candidate.sv').write_text(text);(out/'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
 tb=(R/'rtl/dsrom_sys/s81_suhc/test/tb_s81_su_rxh_eq.sv').read_text();tb=tb.replace('module tb_s81_su_rxh_eq;','module tb_s81_su_rxh_clocked_eq;')
 tb=tb.replace('ot_s81_su_rxh #(', 'ot_s81_su_rxh_clocked_candidate #(').replace('u_clu (.clk(clk), .rst_in(rst),','u_clu (.ck_leaf(leaf_ck), .rs_leaf({38{rst}}),')
 tb=tb.replace('reg clk = 0, rst = 0;','reg clk = 0, rst = 0;\n    integer stop_root;\n    initial begin stop_root=-1; void\'($value$plusargs("STOP_ROOT=%d",stop_root)); end\n    wire [37:0] leaf_ck;\n    genvar cr; generate for(cr=0;cr<38;cr=cr+1)begin:g_clock assign leaf_ck[cr]=clk && !(stop_root==cr && rst); end endgenerate')
 (out/'tb_s81_su_rxh_clocked_eq.sv').write_text(tb);print(json.dumps(manifest))
if __name__=='__main__':main()
