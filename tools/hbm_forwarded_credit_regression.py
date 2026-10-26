#!/usr/bin/env python3
import pathlib,json,sys,ast,subprocess
import argparse
parser=argparse.ArgumentParser(description='Actual forwarded one-bit credit RTL: capture edge, held value, inverted clock, failing data mutant')
parser.add_argument('--source',type=pathlib.Path,required=True)
parser.add_argument('--ports',type=pathlib.Path,required=True)
parser.add_argument('--forwarded-map',type=pathlib.Path,required=True)
parser.add_argument('--out',type=pathlib.Path,required=True)
parser.add_argument('--generator',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent/'hbm_die_station_gen.py')
args=parser.parse_args();S=args.source.resolve();sys.path.insert(0,str(S/'tools'))
import importlib.util
sp=importlib.util.spec_from_file_location('stationgen_credit',args.generator);G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G)
fcm={ast.literal_eval(k):v for k,v in json.load(open(args.forwarded_map)).items()}
B=args.out;B.mkdir(parents=True,exist_ok=True)
results=[]
for face in ['W','S','E','N']:
 top='hfd_stn_q2'+face+'F'
 rec=json.load(open(args.ports/top/'ports.json'))
 assert 'ck' not in rec['ports'],top
 for mutant in [False,True]:
  tag=top+('_mutant' if mutant else '_positive');R=B/tag;R.mkdir(exist_ok=True)
  E,_=G.build(rec,fcm,mutant=mutant)
  (R/'dut.sv').write_text(G.module_text(rec,E))
  conn=[]
  for p,v in rec['ports'].items():
   conn.append('.'+p+'('+('a' if p=='a' else 'b' if p=='b' else "1'b0")+')')
  tb=chr(96)+'timescale 1ps/1fs\n'+'''module tb;
localparam realtime T_PS=833.333;
reg[1:0]a=2'b10;wire[1:0]b;integer i,errors=0;reg last_data;
TOP dut(CONNS);
initial begin
for(i=0;i<4096;i=i+1)begin
 a[1]=1; a[0]=((i*29+i/7)%11)<5; #1;
 if(i>0 && b[0]!==last_data)errors=errors+1;
 if(b[1]!==0)errors=errors+1;
 #(416.666-1); a[1]=0; #1;
 if(b[0]!==a[0])errors=errors+1;
 if(b[1]!==1)errors=errors+1;
 last_data=a[0]; #(T_PS-416.666-1);
end
$display("OT_CREDIT checks=4096 errors=%0d",errors);
if(errors)$fatal(1,"credit regression");$finish;end
endmodule
'''
  tb=tb.replace('TOP',top).replace('CONNS',','.join(conn));(R/'tb.sv').write_text(tb)
  c=['iverilog','-g2012','-s','tb','-o',str(R/'sim'),str(R/'tb.sv'),str(R/'dut.sv'),str(S/'physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv'),str(S/'rtl/common/ot_fwd_link_stage.sv')]
  p=subprocess.run(c,capture_output=True,text=True);(R/'build.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise SystemExit('compile failed '+tag+': '+p.stderr)
  p=subprocess.run(['vvp',str(R/'sim')],capture_output=True,text=True);(R/'run.log').write_text(p.stdout+p.stderr)
  if (p.returncode==0)==mutant:raise SystemExit('unexpected regression result '+tag+': '+p.stdout)
  results.append(dict(master=top,mutant=mutant,returncode=p.returncode,output=p.stdout))
(B/'results.json').write_text(json.dumps(results,indent=1)+'\n');print(json.dumps(results,indent=1))
