#!/usr/bin/env python3
"""Distinct actual guarded23/160-packet21-bank nine-node mechanism.

Preserves the tested producer's exact hash inputs and external DRAM oracle.
Native link clock pins stay stopped/reset during setup; at the fixed clock
origin they start the unchanged proved16:17 startup and continuous window.
This is a functional fixture startup boundary, not clock-gating qualification.
"""
import argparse,hashlib,json,pathlib,subprocess,time
from run_engram_chain import NODES,SCORE
ROOT=pathlib.Path(__file__).resolve().parents[2]
PREFIX=15300

def bench():
 t=(ROOT/'results/arch/hcoll_engram_rowgather_1015/guarded_fixture/producer_l1.sv').read_text()
 t=t.replace('`timescale 1ps/1fs','`timescale 1ns/1fs').replace('task tick;begin @(posedge core_clk);#3;', 'task tick;begin @(posedge core_clk);#0.003;')
 old='reg core_clk=0,hbm_clk=0;always #416.667 core_clk=~core_clk;initial begin #17;forever #512 hbm_clk=~hbm_clk;end'
 t=t.replace(old,f'''localparam real TICK=0.0520833333333333;
localparam integer PREFIX={PREFIX},FPREFIX=0;
reg core_clk=0,fec_clk=0,hbm_clk=0;
always #(8*TICK)core_clk=~core_clk;initial begin wait(link_core_on);forever #(8.5*TICK)fec_clk=~fec_clk;end
initial begin #0.017;forever #0.512 hbm_clk=~hbm_clk;end
integer fc=0,cc=0;realtime link_origin;reg phase_checked=0;always @(posedge link_core_on)link_origin=$realtime;always @(posedge fec_clk)if(!phase_checked)begin phase_checked=1;if($realtime-link_origin<0.4427075 || $realtime-link_origin>0.4427085)$fatal(1,"FEC_ORIGIN_PHASE");end''')
 t=t.replace('reg local_read_v=0;reg[1:0]local_read_slot=0;reg[3:0]local_read_sector=0;','wire[7:0]local_read_v;wire[1:0]local_read_slot[0:7];wire[3:0]local_read_sector[0:7];\nwire[3:0]owned_valid[0:7];wire[19:0]owned_rows[0:7];wire[2:0]owned_count[0:7];wire[7:0]response_v,response_present;wire[4:0]response_row[0:7];wire[3:0]response_sector[0:7];')
 for h in range(8):
  t=t.replace(f'.local_read_v(local_read_v),.local_read_slot(local_read_slot),.local_read_sector(local_read_sector),.fetch_start(fetch_start),.read_v(read_v[{h}]),.read_row(read_row),.read_sector(read_sector)',f'.local_read_v(local_read_v[{h}]),.local_read_slot(local_read_slot[{h}]),.local_read_sector(local_read_sector[{h}]),.fetch_start(fetch_start),.read_v(1\'b0),.read_row(5\'b0),.read_sector(4\'b0),.owned_slot_valid(owned_valid[{h}]),.owned_slot_global_row(owned_rows[{h}]),.owned_row_count(owned_count[{h}]),.slot_response_v(response_v[{h}]),.slot_response_present(response_present[{h}]),.slot_response_row(response_row[{h}]),.slot_response_sector(response_sector[{h}])')
 a=t.index('always @(posedge core_clk)begin:scoreboard');b=t.index('task tick;',a)
 score=SCORE.replace('LAYER','0').replace('cc==2900','cc==3050').replace('actual8homehash controllers256 sectors216 rows24 packets120 hops540 nodes9 programme171SRAM','actual8homehash guarded23 sectors216 rows24 packets160 NOP40 hops720 nodes9 programme189SRAM')
 score=score.replace('if(raw_checks!=216', 'if(node_done_edges!=1 || nodebusy!=0)$fatal(1,\"NATIVE_RETIREMENT_COUNT\");\n    if(!all_complete[8])$fatal(1,"SLOT_CHAIN_INCOMPLETE");\n    if(raw_checks!=216')
 score=score.replace('if(MUT==0 && ((|nodefault)', 'if(|nodedone)begin node_done_edges=node_done_edges+1;if(cc!=404+program_limit || nodedone!==9\'h1ff)$fatal(1,\"NATIVE_DONE_EDGE C%0d\",cc);end\n  if(MUT==0 && ((|nodefault)')
 score=score.replace('core_edge=core_edge+1;cc=core_edge-PREFIX;#0.000001;', 'core_edge=core_edge+1;cc=core_edge-PREFIX;#0.000001;\n if(core_edge%2048==0)begin $display("SLOT_CHAIN_PROGRESS globalC%0d phaseC%0d",core_edge,cc);$fflush;end')
 t=t[:a]+score+t[b:]
 a=t.index(' repeat(36+8192-1)')
 t=t[:a]+''' repeat(36+8192-1)begin tick;if(done!=0)$fatal(1,"earlycompletion");end
 tick;if(done!==8'hff || core_edge-fetch_edge!=36+8192)$fatal(1,"fixedfullfetchdone");
 if(reads!=216 || descriptors!=24)$fatal(1,"nativefetchcounts");
 for(integer w=0;w<1344;w=w+1)begin
  @(negedge core_clk);cfg_v=1;cfg_addr=12'(w*2);
  for(integer n=0;n<9;n=n+1)cfg_data[n]=images[n*2688+w*2];tick;
  @(negedge core_clk);cfg_addr=12'(w*2+1);
  for(integer n=0;n<9;n=n+1)cfg_data[n]=images[n*2688+w*2+1];tick;
  @(negedge core_clk);cfg_v=0;repeat(2)tick;
 end
 @(negedge core_clk);desc_v=1;tick;@(negedge core_clk);desc_v=0;
 repeat(1346)tick;
 if(MUT==1)begin if(!nodefault[0])$fatal(1,"reservedprogramme_mutant_escaped");$display("ENGRAM_SLOT_PROGRAM_MUTANT_PASS");$finish;end else begin
 if(configured!==9'h1ff || init_busy!=0)$fatal(1,"nativecatalogue_notconfigured");
 $display("SLOT_CHAIN_PREFLIGHT actual24rows216DRAMreads 9x21nativeprogrammeSRAMs ready C%0d",core_edge);$fflush;
 end
end
endmodule
'''
 t=t.replace(' $readmemh("external_hbm_sectors.hex",external_words);',''' $readmemh("external_hbm_sectors.hex",external_words);
 $readmemh("expected_bf16.hex",golden);
 IMAGE_LOADS
 if($value$plusargs("mut=%d",MUT))begin end
 if(MUT==1)images[0]=images[0]^(256'd1<<238);
 if(MUT==3)begin
  for(integer i=0;i<2688;i=i+1)if(images[i][107])begin images[i]=images[i]^(256'd1<<108);break;end
 end
'''.replace('IMAGE_LOADS','\n'.join(f'$readmemh("n{n}.hex",images,{n*2688},{(n+1)*2688-1});cfg_data[{n}]=0;' for n in range(9))))
 # Published strict oracle remains unchanged except explicit runtime input corruption.
 t=t.replace('hit*9+off];reads=reads+1;',"hit*9+off]^((MUT==2&&hit==0&&off==0)?256'd1:256'd0);reads=reads+1;")
 nodes=NODES.replace('wire launch=cc+1==399,linkepoch=cc+1==450;', 'reg launch=0,linkepoch=0;always @(negedge core_clk)begin launch=cc+1==399;linkepoch=cc+1==450;end').replace('HOMEBASE','0').replace('images[0:8][0:2431]','images[0:24191]').replace('images[0:21887]','images[0:24191]').replace('ot_hcoll_engram_chain_node','ot_hcoll_engram_chain_slot_node').replace('{19{core_clk}}','{21{core_clk}}').replace("13'd2424","program_limit")
 nodes=nodes.replace('assign read_v[n]=source_v;assign read_row[n]=source_row;assign read_sector[n]=source_sector;', 'assign local_read_v[n]=source_v;assign local_read_slot[n]=source_row[1:0];assign local_read_sector[n]=source_sector;')
 nodes="integer node_done_edges=0;integer program_limit=2091;initial if($value$plusargs(\"limit=%d\",program_limit))begin end\n"+nodes
 nodes=nodes.replace('wire[8:0]configured,init_busy,nodebusy,nodedone,nodefault;', 'wire[8:0]configured,init_busy,nodebusy,nodedone,nodefault,all_complete;')
 nodes=nodes.replace('.source_raw_v(n<8?', '.owned_slot_valid(n<8?owned_valid[n]:4\'b0),.owned_slot_global_row(n<8?owned_rows[n]:20\'b0),\n .source_response_v(n<8?response_v[n]:1\'b0),.source_response_present(n<8?response_present[n]:1\'b0),.source_response_row(n<8?response_row[n]:5\'b0),.source_response_sector(n<8?response_sector[n]:4\'b0),\n .source_raw_v(n<8?')
 nodes=nodes.replace('.configured(configured[n])','.consumer_complete(all_complete[n]),.configured(configured[n])')
 nodes=nodes.replace('ot_hbm_core_fec_frame_link link(.core_clk(core_clk),.rst_n(rst_n),.fec_clks({16{fec_clk}}),.phy_clks({6{core_clk}})', 'ot_hbm_core_fec_frame_link link(.core_clk(link_core_clk),.rst_n(link_rst_n),.fec_clks({16{link_fec_clk}}),.phy_clks({6{link_core_clk}})')
 nodes=nodes.replace('reg txstart=0', '''reg link_core_on=0,link_fec_on=0,link_rst_n=0;
 wire link_core_clk=core_clk&&link_core_on,link_fec_clk=fec_clk&&link_fec_on;
 always @(negedge core_clk)if(core_edge==PREFIX)begin link_core_on=1;link_fec_on=1;end
 always @(negedge fec_clk)begin if(fc==8)link_rst_n=1;end
 reg txstart=0''')
 nodes += "\nfor(genvar d=0;d<9;d=d+1)begin:g_diagnostic\n always @(negedge core_clk)if((cc+1>=508 && cc+1<=513)||(cc+1>=699 && cc+1<=707))begin $display(\"FRAME_INPUT C%0d n%0d tx%b rx%b expect%b seq%0d\",cc+1,d,txv[d],rxv[d],g_node[d].node.ctl[124],g_node[d].node.ctl[125+:16]);$fflush;end\n always @(posedge core_clk)begin #0.0000005;if((cc>=508 && cc<=513)||(cc>=699 && cc<=707))begin $display(\"FRAME_EDGE C%0d n%0d tx%b rx%b expect%b seq%0d\",cc,d,txv[d],rxv[d],g_node[d].node.ctl[124],g_node[d].node.ctl[125+:16]);$fflush;end if(cc>450 && (g_node[d].node.packet_fault || g_node[d].node.qfault || (|g_node[d].node.bf) || (|g_node[d].node.rf) || g_node[d].node.tx_abort || g_node[d].node.rx_abort))begin\n $display(\"NODE_DETAIL C%0d n%0d program%b packet%b q%b kind%h bridge%h face%h tx%h rx%h ctl%h\",cc,d,g_node[d].node.program_fault,g_node[d].node.packet_fault,g_node[d].node.qfault,g_node[d].node.qkind,g_node[d].node.bf,g_node[d].node.rf,g_node[d].node.tx_cause,g_node[d].node.rx_cause,g_node[d].node.ctl);$fflush;end end\nend\n"
 t=t.replace('integer j,s,cididx,fetch_edge;','integer j,s,cididx,fetch_edge;\n'+nodes)
 assert 'images[0:24191]' in t
 return t

def generate(out,inputs,programme=None):
 out.mkdir(parents=True,exist_ok=True)
 for name in ['external_hbm_sectors.hex','expected_bf16.hex']:(out/name).write_bytes((inputs/name).read_bytes())
 for n in range(9):
  p=(programme/f'n{n}.hex') if programme else ROOT/f'results/arch/hcoll_engram_rowgather_1015/ordered160_program/layer1/n{n}.hex';(out/f'n{n}.hex').write_bytes(p.read_bytes() if p.exists() else subprocess.check_output(['git','show',f'HEAD:{p.relative_to(ROOT)}'],cwd=ROOT))
 (out/'tb.sv').write_text(bench())
 src=json.loads((ROOT/'tools/hbm_coll_static/engram_slot_node_sources.json').read_text())
 src+=json.loads((ROOT/'results/arch/hcoll_engram_rowgather_1015/guarded_fixture/producer_sources.json').read_text())
 # Same actual link source inventory as the frozen functional API bench.
 import re
 text=(ROOT/'tools/hbm_io/run_core_fec_frame_link_gate.sh').read_text()
 for x in re.findall(r'"?((?:\$io/|\$p/|rtl/|physical/)[^\s"\\]+\.s[v]?)"?',text):
  x=x.replace('$io/','rtl/hbm_accel/io_static_20261015/').replace('$p/','rtl/hbm_accel/generic/collective/p2p/')
  if not x.endswith('tb_core_fec_frame_link.sv'):src.append(x)
 src=list(dict.fromkeys(src));assert all((ROOT/p).exists() for p in src),[p for p in src if not(ROOT/p).exists()]
 (out/'sources.json').write_text(json.dumps(src,indent=2)+'\n');(out/'hier.vlt').write_text('`verilator_config\nhier_block -module "ot_hbm_core_fec_frame_link"\n')
 return src

def run(out,inputs,generate_only=False,programme=None,limit=2091,cases=(0,1,2,3),run_only=False):
 out=out.resolve()
 oldtb=(out/'tb.sv').read_bytes() if (out/'tb.sv').exists() else None
 src=generate(out,inputs,programme)
 if run_only:
  assert oldtb==(out/'tb.sv').read_bytes(),'run-only bench differs from compiled source'
  assert all((ROOT/p).stat().st_mtime<=(out/'obj/sim').stat().st_mtime for p in src),'run-only source newer than binary'
 if generate_only:return
 v=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator');src.sort(key=lambda p:0 if p.endswith('_pkg.sv') else 1)
 cmd=[v,'--binary','--timing','--hierarchical','-O2','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-UNOPTFLAT','-Irtl/dsrom_sys/s81_link','--top-module','tb','--Mdir',str(out/'obj'),'-o','sim',str(out/'hier.vlt')]
 if not run_only:
  with(out/'build.log').open('w')as f:cp=subprocess.run(cmd+[str(ROOT/p) for p in src]+[str(out/'tb.sv')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  assert cp.returncode==0,'nativebuildfailed '+str(out/'build.log')
 results=[]
 for m in cases:
  with(out/f'm{m}.log').open('w')as f:rp=subprocess.run([str(out/'obj/sim'),f'+mut={m}',f'+limit={limit}'],cwd=out,stdout=f,stderr=subprocess.STDOUT)
  assert rp.returncode==0,(out/f'm{m}.log').read_text();results.append(dict(mutant=m,output=(out/f'm{m}.log').read_text()))
 r=dict(status='PASS requested guarded160 actual9node cases',cases=list(cases),native_profile='slot160_21_ordered_drain5',descriptor_limit=limit,native_nodes=9,native_links=8,programme_banks_per_node=21,rows=24,physical_packets=160,application_NOPs=40,physical_hops=720,raw_sectors=216,decoded_blocks=192,producer_guarded23=True,prefill_deadline=8228,prefix=PREFIX,transport_decode_done=2495,clock_startup='native link roots held reset/stopped during setup; fixed clock origin then unchanged16:17 startup and continuous active profile',source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in src},runs=results,full96_release=False,normative_unchanged_programme=False,universal_producer_service_bound=False,physical_qualified=False)
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--inputs',type=pathlib.Path,required=True);p.add_argument('--generate-only',action='store_true');p.add_argument('--programme',type=pathlib.Path);p.add_argument('--limit',type=int,default=2091);p.add_argument('--cases',default='0,1,2,3');p.add_argument('--run-only',action='store_true');a=p.parse_args();run(a.out,a.inputs,a.generate_only,a.programme,a.limit,tuple(map(int,a.cases.split(','))),a.run_only)
