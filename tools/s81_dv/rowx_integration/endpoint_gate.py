#!/usr/bin/env python3
"""Packed ROWX codecs through two actual selected LEP cores over a direct finite-credit flit link.

This isolates the real XB/tag/land format from PHY/rack topology. It uses the selected native32/IN_PIPE source,
SRAM=0/RX_SRAM=0 behavioural storage and small finite queues. No PHY or routed-latency qualification is claimed.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/die_plan')]
import bind_elab as B
import die_port_bind as D
CORE='physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',type=int,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((ROOT/'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_text())
 prefer=[str(ROOT/f) for f in manifest['files']]+[str(ROOT/CORE)]
 idx=B.module_index(['rtl'],prefer,str(ROOT));sources,missing=B.closure(['ot_s81sl_lep_core'],idx,prefer);assert not missing,missing
 # The interface is concrete at these simulation parameters. Queue sizes are finite; the actual codec payload shape is full.
 raw=D.preprocess((ROOT/CORE).read_text(),{})
 m=next(x for x in D.parse_modules(raw,CORE) if x.name=='ot_s81sl_lep_core')
 params=dict(DT=16,DR=12,CRED=12,SRAM=0,HOST_EN=0,MU_EN=1,AB_EN=0,IDX_EN=0,RX_SRAM=0,IN_PIPE=1,NATIVE32=1)
 env=m.env(params)
 tb=['`timescale 1ps/1fs','module tb;','reg clk=0;always #416.5 clk=~clk;reg rst_n=0;',
     'reg tx_v=0;reg[1023:0]tx_d=0;reg[7:0]tx_index=0;wire[1103:0]packet;wire packet_v,tx_fault;',
     'wire got_v,rx_fault;wire[1023:0]got;reg[1023:0]gold[0:1119];integer nout=0,cyc=0,first_out=-1,last_out=-1;']
 for who in ('a','b'):
  for pn,(di,_) in m.ports.items():
   if di=='output':
    w=m.width(pn,env);assert w is not None,(pn,m.ports[pn]);tb.append(f'wire[{w-1}:0]{who}_{pn};')
 for who in ('a','b'):
  con=[]
  for pn,(di,_) in m.ports.items():
   if di=='output':sig=who+'_'+pn
   elif pn in ('clk','rst_n'):sig=pn
   elif who=='a' and pn=='ro':sig='{packet[1103:1],packet_v}'
   elif who=='a' and pn in ('lo0_r','lo1_r'):sig='b_li'+pn[2]+'_r'
   elif who=='b' and pn in ('li0_v','li0_d','li1_v','li1_d'):sig='a_lo'+pn[2:]
   else:sig="'0"
   con.append('.'+pn+'('+sig+')')
  tb.append('ot_s81sl_lep_core #('+','.join('.'+k+'('+str(v)+')' for k,v in params.items())+') '+who+' ('+','.join(con)+');')
 tb += [f'dsdv_rowx_xb #(.MUT({a.mutant})) tx(.clk(clk),.rst_n(rst_n),.tx_book(1\'b1),.sid(4\'d7),.user_id(10\'d0),.position(21\'d1234),.tx_v(tx_v),.tx_d(tx_d),.tx_index(tx_index),.ring_v(packet_v),.ring_d(packet),.rx_book(1\'b0),.ml_v(1\'b0),.ml_d(1104\'d0),.rx_v(),.rx_d(),.pass_v(),.pass_d(),.fault(tx_fault));',
 'dsdv_rowx_xb rx(.clk(clk),.rst_n(rst_n),.tx_book(1\'b0),.sid(4\'d0),.user_id(10\'d0),.position(21\'d1234),.tx_v(1\'b0),.tx_d(1024\'d0),.tx_index(8\'d0),.ring_v(),.ring_d(),.rx_book(1\'b1),.ml_v(b_ml_wv),.ml_d(b_ml_wd),.rx_v(got_v),.rx_d(got),.pass_v(),.pass_d(),.fault(rx_fault));',
 'always @(posedge clk) begin cyc=cyc+1;#0.001;if(rst_n)begin if(a_fault||b_fault||tx_fault||rx_fault)$fatal(1,"endpoint fault cycle%0d a%b b%b tx%b rx%b",cyc,a_fault,b_fault,tx_fault,rx_fault);if(b_ri[0])$fatal(1,"landed ROWX escaped to normal ring");if(got_v)begin if(nout>=1120||got!==gold[nout])$fatal(1,"payload/order n%0d",nout);if(first_out<0)first_out=cyc;last_out=cyc;nout=nout+1;end end end',
 'initial begin repeat(6)@(negedge clk);rst_n=1;repeat(32)@(negedge clk);for(int n=0;n<1120;n++)begin @(negedge clk);for(int k=0;k<32;k++)tx_d[32*k+:32]=$urandom;gold[n]=tx_d;tx_index=8\'(n);tx_v=1;@(negedge clk);tx_v=0;end repeat(144)@(negedge clk);if(nout!=1120)$fatal(1,"drain count %0d",nout);$display("ROWX_ENDPOINT_GATE PASS1120 user0 pairA tag/land native32 IN_PIPE first%0d last%0d",first_out,last_out);$finish;end endmodule']
 (a.out/'tb.sv').write_text('\n'.join(tb)+'\n')
 rel=[str(Path(f).resolve().relative_to(ROOT)) for f in sources]
 (a.out/'sources.json').write_text(json.dumps(dict(parameters=params,files=rel),indent=2)+'\n')
 cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','4','--Mdir',str(a.out/'obj')]+['-I'+str(Path(f).parent) for f in sources]+sources+[str(ROOT/'rtl/dsrom_sys/s81_dv/svc_rs/rowx/dsdv_rowx_xb.sv'),str(a.out/'tb.sv')]
 with (a.out/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (a.out/'run.log').open('w') as f:r=subprocess.run([str(a.out/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT)
 print((a.out/'run.log').read_text(),end='');return r.returncode
if __name__=='__main__':sys.exit(main())
