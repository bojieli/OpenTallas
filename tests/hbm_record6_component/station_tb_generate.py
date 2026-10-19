#!/usr/bin/env python3
"""Supporting41-node causal bench, NEVER a substitute for native512-lane proof.

This is text/integer source generation only. Inputs and per-add expectations
come from an immutable prior fleet generation; no floating-point evaluation is
performed here. No source or artifact under --native is changed.
"""
import argparse, hashlib, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/hbm_static')]
from tb_generate import emit


def main():
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--station-ledger',type=Path,required=True);p.add_argument('--source-binding',type=Path,required=True);p.add_argument('output',type=Path);a=p.parse_args()
 src=a.native.resolve();out=a.output.resolve()
 if out==src or src in out.parents:raise ValueError('supportoutput must be separate from frozen native directory')
 out.mkdir(parents=True,exist_ok=False)
 required=['receipt.json','adds.json','adds.mem','gold.mem','preload0.json','preload1.json','square0.mem','square1.mem','input0.mem','input1.mem']
 digests={}
 for n in required:
  shutil.copyfile(src/n,out/n);digests[n]=hashlib.sha256((out/n).read_bytes()).hexdigest()
 for q in range(4):shutil.copytree(src/f'q{q}',out/f'q{q}')
 shutil.copyfile(a.station_ledger,out/'station_ledger.json')
 receipt=json.loads((out/'receipt.json').read_text())
 # Reuse exact source ownership assertions. The complete-reference text is
 # generated in this NEW output only; the native c7 run remains immutable.
 emit(out,receipt,json.loads(a.source_binding.read_text()))
 reference=(out/'tb.sv').read_text()
 begin=reference.index('reg[95:0] adds[0:2561];')
 end=reference.index('integer roots=0,scalars=0,checked=0,fillcount=0,retired=0;')
 assertions=reference[begin:end]
 ownership=[]
 for si in range(40):
  owner=f'station.g_on.s{si}'
  ownership.append(f'''always @(posedge clk)if(runrq&&station.g_on.active&&{owner}.issue&&{owner}.as_lo&&!station.g_on.result_v[{si}])$fatal(1,"UNAVAILABLE_FEEDBACK station={si} cycle=%0d",cycle);\n''')
 for q in range(4):
  ownership.append('always @(posedge clk)if(runrq&&(cycle==64||cycle==176||cycle==288||cycle==400))begin #0.001;\n')
  for l in range(128 if q in(0,2)else 32):
   w=128*q+l;idx=f"episode*1280+((cycle-64)/112)*320+{(0,128,160,288)[q]+l}"
   ownership.append(f'''if(!station.g_on.valid_{w}||station.g_on.word_{w}!==square[{idx}])$fatal(1,"EARLY_CAPTURE q={q} lane={l} cycle=%0d",cycle);
$display("SUPPORT_HELD episode=%0d group=%0d q={q} lane={l} value=%h valid=%b",episode,(cycle-64)/112,station.g_on.word_{w},station.g_on.valid_{w});
''')
  ownership.append('end\n')
 assertions+=''.join(ownership)
 (out/'tb.sv').rename(out/'native_reference_not_compiled.sv')
 text='''`timescale 1ns/1ps
module tb #(parameter integer STATION_MUT=0);
reg refclk=0;always #5 refclk=~refclk;
reg por_n=0;wire clk,stream,rq,rs;
hfd_ckgen cg(.refclk(refclk),.por_n(por_n),.pll_stream(stream),.pll_serial(clk),.por_serial(rq),.por_stream(rs));
reg reset_n=0;wire runrq=rq&&reset_n;
integer qt=-1,st=-1;always @(posedge clk)if(rq)qt=qt+1;always @(posedge stream)if(rs)st=st+1;
integer cs=0,ct=0;time last_s=0,last_t=0;
always @(posedge clk)begin cs++;if(cs>1&&($rtoi($realtime*1000+0.5)-last_s)!=1112)$fatal(1,"CLOCK_SERIAL_PERIOD");last_s=$rtoi($realtime*1000+0.5);end
always @(posedge stream)begin ct++;if(ct>1&&($rtoi($realtime*1000+0.5)-last_t)!=834)$fatal(1,"CLOCK_STREAM_PERIOD");last_t=$rtoi($realtime*1000+0.5);end
initial begin #200;if(cs<2||ct<2||!cg.locked||!rq||!rs)$fatal(1,"CLOCK_CAUSAL_GUARD");$display("CLOCK_CAUSAL_PASS stream_half_ps=417 serial_half_ps=556");end
reg start=0;integer episode=0,abort_mode=0,startqt=0,roots=0;
reg[16383:0] lanes_x=0;reg[511:0] lanes_v=0;
wire[31:0] root_x;wire root_v,fault;wire[9:0] cycle;wire[10:0] capture_count,add_count;
wire[3:0] capmask=(cycle==64||cycle==176||cycle==288||cycle==400)?4'hf:4'h0;
wire[1:0] capgroup=(cycle-64)/112;
ot_hbm_r6_station41 #(.ENABLE(1),.MUT(STATION_MUT)) station(.clk(clk),.rst_n(runrq),.start(start),.episode_epoch(8'(episode+1)),.lane_x(lanes_x),.lane_v(lanes_v),.capture(capmask),.capture_group(capgroup),.root_v(root_v),.root_x(root_x),.fault(fault),.cycle(cycle),.capture_count(capture_count),.add_count(add_count));
reg[31:0] square[0:2559],gold[0:1];reg root_seen=0;
initial begin $readmemh("square0.mem",square,0,1279);$readmemh("square1.mem",square,1280,2559);$readmemh("gold.mem",gold);end
always @(posedge clk)begin
 if(start)begin startqt=qt;root_seen=0;$display("SUPPORT_START episode=%0d qt=%0d",episode,qt);end
 #0.001;
 if(runrq&&root_v&&!root_seen)begin
  root_seen=1;
  if(qt-startqt!=591||root_x!==gold[episode]||capture_count!=1280||add_count!=1281||fault)$fatal(1,"SUPPORT_ROOT_ID_COUNT_AGE");
  roots++;$display("SUPPORT_ROOT episode=%0d age=%0d data=%h captures=%0d adds=%0d",episode,qt-startqt,root_x,capture_count,add_count);
 end
end
'''+assertions+'''
initial begin
 $display("SUPPORT_SCOPE station_causal_only expected_squared_inputs; requires_actual_native_capture_binding");
 por_n=0;#100 por_n=1;wait(rq&&rs);reset_n=1;repeat(12)@(negedge clk);
 for(integer e=0;e<2;e++)begin
  episode=e;start=1;@(negedge clk);start=0;
  for(integer g=0;g<4;g++)begin
   while(cycle<64+112*g)@(negedge clk);
   lanes_x=0;lanes_v=0;
   for(integer q=0;q<4;q++)begin
    for(integer l=0;l<(q==0||q==2?128:32);l++)begin
     lanes_x[32*(128*q+l)+:32]=square[e*1280+g*320+(q==0?0:q==1?128:q==2?160:288)+l];
     lanes_v[128*q+l]=1;
     $display("SUPPORT_INPUT episode=%0d group=%0d q=%0d lane=%0d cycle=%0d data=%h",e,g,q,l,cycle,lanes_x[32*(128*q+l)+:32]);
    end
   end
   @(negedge clk);lanes_v=0;lanes_x=0;
  end
  while(qt-startqt<620)@(negedge clk);
  if(roots!=e+1||fault)$fatal(1,"SUPPORT_EPISODE_INCOMPLETE");
 end
 if(roots!=2)$fatal(1,"SUPPORT_FINAL");
 $display("STATION_CAUSAL_SUPPORT_PASS two_distinct_episodes; native_binding_PENDING");$finish;
end
endmodule
'''
 (out/'station_tb.sv').write_text(text)
 manifest=dict(scope='SUPPORTING STATION CAUSAL ONLY; not native-component/token/timing/physical qualification',frozen_native=str(src),frozen_input_sha256=digests,station_ledger_sha256=hashlib.sha256(a.station_ledger.read_bytes()).hexdigest(),source_binding_sha256=hashlib.sha256(a.source_binding.read_bytes()).hexdigest(),native_capture_binding='PENDING first actual full native positive capture/assert trace',required_native_binding='all1280 original and1280 distinct second input squares match actual native lane pins at64/176/288/400; source actualassertions/hashes retained',compile_top='tb',compile_bench='station_tb.sv',not_compiled='native_reference_not_compiled.sv',required_rtl=['ot_hbm_r6_station41.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_fastfp.sv','ot_hdc_prefix.sv','ckgen.sv','pll_functional_model.sv','rtl/lib/ot_rst_relay.sv'],no_synthesis_or_gate=True)
 (out/'support_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(dict(output=str(out),scope=manifest['scope'],frozen_native_unmodified=True),indent=2))

if __name__=='__main__':main()
