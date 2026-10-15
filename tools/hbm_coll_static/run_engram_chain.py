#!/usr/bin/env python3
"""Full selected-checkpoint eight-home -> consumer native mechanism.

Actual hash/DRAM controller/CDC/SRAM producers, nine native 256-programme
nodes and eight actual core/FEC/PMA links. This fixture is the frozen 120
payload selected-receipt mechanism, not the 160-slot all-token successor.
External DRAM follows the published six-HBM-edge numerical mechanism.
"""
import argparse, hashlib, importlib.util, json, pathlib, re, shutil, subprocess, time, types
ROOT=pathlib.Path(__file__).resolve().parents[2]
PREFIX=30005 # multiple17: both clocks keep their exact passed common phase

def bench(binding,li):
 p=ROOT/'results/arch/hbm_engram_partition_1015/first_compact_source/hbm_engram_home_fetch_gate.py'
 m=types.ModuleType('memory_gate');m.__file__=str(p)
 source=p.read_text() if p.exists() else subprocess.check_output(['git','show',f'HEAD:{p.relative_to(ROOT)}'],cwd=ROOT,text=True)
 exec(compile(source,str(p),'exec'),m.__dict__)
 t=m.bench(binding,li)
 t=t.replace('`timescale 1ps/1fs','`timescale 1ns/1fs').replace('task tick;begin @(posedge core_clk);#3;', 'task tick;begin @(posedge core_clk);#0.003;')
 old='reg core_clk=0,hbm_clk=0;always #416.667 core_clk=~core_clk;initial begin #17;forever #512 hbm_clk=~hbm_clk;end'
 t=t.replace(old,f'''localparam real TICK=0.0520833333333333;
localparam integer PREFIX={PREFIX},FPREFIX={PREFIX*16//17};
reg core_clk=0,fec_clk=0,hbm_clk=0;
always #(8*TICK)core_clk=~core_clk;always #(8.5*TICK)fec_clk=~fec_clk;
initial begin #0.017;forever #0.512 hbm_clk=~hbm_clk;end
integer fc=0,cc=0;''')
 t=t.replace('reg[7:0]read_v=0;reg[4:0]read_row=0;reg[3:0]read_sector=0;', 'wire[7:0]read_v;wire[4:0]read_row[0:7];wire[3:0]read_sector[0:7];')
 t=t.replace('ot_hbm_engram_home_fetch #','ot_hbm_engram_home_fetch_compact #')
 for h in range(8):t=t.replace(f'.read_v(read_v[{h}]),.read_row(read_row),.read_sector(read_sector)',f'.read_v(read_v[{h}]),.read_row(read_row[{h}]),.read_sector(read_sector[{h}])')
 # Keep the published physical DRAM oracle and hash setup verbatim.
 a=t.index('always @(posedge core_clk)begin:scoreboard');b=t.index('task tick;',a)
 t=t[:a]+SCORE+t[b:]
 a=t.index(' repeat(216*512+512-1)')
 t=t[:a]+''' repeat(36*512+512-1)begin tick;if(done!=0)$fatal(1,"earlycompletion");end
 tick;if(done!==8'hff || core_edge-fetch_edge!=36*512+512)$fatal(1,"fixedfullfetchdone");
 if(reads!=216 || descriptors!=24)$fatal(1,"nativefetchcounts");
 for(integer w=0;w<1216;w=w+1)begin
  @(negedge core_clk);cfg_v=1;cfg_addr=12'(w*2);
  for(integer n=0;n<9;n=n+1)cfg_data[n]=images[n*2432+w*2];tick;
  @(negedge core_clk);cfg_addr=12'(w*2+1);
  for(integer n=0;n<9;n=n+1)cfg_data[n]=images[n*2432+w*2+1];tick;
  @(negedge core_clk);cfg_v=0;repeat(2)tick;
 end
 @(negedge core_clk);desc_v=1;tick;@(negedge core_clk);desc_v=0;
 repeat(1218)tick;if(configured!==9'h1ff || init_busy!=0)$fatal(1,"nativecatalogue_notconfigured");
 $display("ENGRAM_CHAIN_PREFLIGHT actual24rows216DRAMreads 9x19nativeprogrammeSRAMs ready C%0d",core_edge);
end
endmodule
'''
 t=t.replace(' $readmemh("external_hbm_sectors.hex",external_words);',''' $readmemh("external_hbm_sectors.hex",external_words);
 $readmemh("expected_bf16.hex",golden);
 for(integer n=0;n<9;n=n+1)begin
  $readmemh($sformatf("n%0d.hex",n),images[n]);cfg_data[n]=0;
 end
 if($value$plusargs("mut=%d",MUT))begin end
 if(MUT==1)images[0]=images[0]^(256'd1<<238);
 if(MUT==3)begin
  for(integer i=0;i<2432;i=i+1)if(images[i][107])begin images[i]=images[i]^(256'd1<<108);break;end
 end
''')
 # Wire-level runtime payload mutation keeps actual CRC/FEC in the path.
 # All values still originate in external DRAM commands.
 t=t.replace('due_data[h][p]<=external_words[', 'due_data[h][p]<=external_words[')
 t=t.replace('hit*9+off];reads=reads+1;', 'hit*9+off]^((MUT==2&&hit==0&&off==0)?256\'d1:256\'d0);reads=reads+1;')
 t=t.replace('for(integer n=0;n<9;n=n+1)begin\n  $readmemh($sformatf("n%0d.hex",n),images[n]);cfg_data[n]=0;\n end', '\n'.join(f'$readmemh("n{n}.hex",images,{n*2432},{(n+1)*2432-1});cfg_data[{n}]=0;' for n in range(9)))
 t=t.replace('integer j,s,cididx,fetch_edge;','integer j,s,cididx,fetch_edge;\n'+NODES.replace('HOMEBASE',str(li*8)))
 return t

SCORE=r'''
always @(posedge core_clk)begin:scoreboard
 integer idx;
 core_edge=core_edge+1;cc=core_edge-PREFIX;#0.000001;
 if(rst_n)begin
  if(request_valid[LAYER] && capture)descriptors=descriptors+1;
  if(hash_fault || fault!=0)$fatal(1,"nativeproducerfault C%0d hash%b home%h",cc,hash_fault,fault);
  if(MUT==0 && ((|nodefault)||consumer_fault||(|linkfault)||(|fecfault)||(|pmafault)||(|padfault)))
   $fatal(1,"CHAIN_FAULT C%0d node%h link%h fec%h pma%h pad%h consumer%b",cc,nodefault,linkfault,fecfault,pmafault,padfault,consumer_fault);
  if(craw_v)begin
   if(craw_data!==external_words[LAYER*216+craw_row*9+craw_sector])begin mismatches=mismatches+1;if(MUT==0)$fatal(1,"CHAIN_RAW_MISMATCH C%0d row%0d sector%0d",cc,craw_row,craw_sector);end
   raw_checks=raw_checks+1;
  end
  if(decoded_v)begin
   if(decoded_data!==golden[LAYER*192+decoded_row*8+decoded_block])begin mismatches=mismatches+1;if(MUT==0)$fatal(1,"CHAIN_DECODE_MISMATCH C%0d row%0d block%0d",cc,decoded_row,decoded_block);end
   decode_checks=decode_checks+1;
  end
  if(cwrite_v)write_checks=write_checks+1;
  if(cc==2900)begin
   if(MUT==0)begin
    if(raw_checks!=216 || decode_checks!=192 || write_checks!=216 || mismatches)$fatal(1,"WHOLE_CHAIN_COUNTS raw%0d decoded%0d writes%0d mismatch%0d",raw_checks,decode_checks,write_checks,mismatches);
    $display("ENGRAM_WHOLE_CHAIN_PASS actual8homehash controllers256 sectors216 rows24 packets120 hops540 nodes9 programme171SRAM links8 TX6RX2 FEC151 age16:17 decoded192 BF166144");
   end else begin
    if(MUT==1 && !nodefault[0])$fatal(1,"PROGRAM_MUTANT_ESCAPED");
    if(MUT==3 && !nodefault[0])$fatal(1,"SLOT_MUTANT_ESCAPED");
    if(MUT==2 && mismatches==0)$fatal(1,"PAYLOAD_MUTANT_ESCAPED");
    $display("ENGRAM_WHOLE_CHAIN_MUTANT_PASS m%0d mismatch%0d nodefault%h",MUT,mismatches,nodefault);
   end
   $finish;
  end
 end
end
'''
NODES=r'''
reg cfg_v=0,desc_v=0;reg[11:0]cfg_addr=0;reg[255:0]cfg_data[0:8];reg[255:0]images[0:21887];
wire[8:0]configured,init_busy,nodebusy,nodedone,nodefault;
wire[8:0]txv,rxv,cwv,crv;wire[611:0]txf[0:8],rxf[0:8];
wire[4:0]cwrow[0:8],crrow[0:8];wire[3:0]cwsec[0:8],crsec[0:8];wire[255:0]cwdata[0:8];
wire launch=cc+1==399,linkepoch=cc+1==450;
wire[31:0]linkfault,pmafault;wire[15:0]fecfault;wire[7:0]padfault;
wire[511:0]pma[0:7];wire[1:0]status[0:7];
reg txstart=0,rxstart=0,txstep=0,rxstep=0,slot=0;
reg ctxs=0,ctxt=0,ctxl=0,ftxs=0,ftxt=0,ftxl=0,frxs=0,frxt=0,frxl=0,crxs=0,crxt=0,crxl=0;
reg sers=0,serr=0,dess=0,desr=0,cap_s=0,cap_t=0,cap_l=0,read_s=0,read_t=0,read_l=0;
function automatic integer C(input integer base,k);C=base+17*k/16;endfunction
function automatic integer A(input integer j);A=C(511,613*j/487);endfunction
always @(negedge core_clk)begin
 txstart=cc+1==510;rxstart=cc+1==697;ctxs=cc+1==511;crxs=cc+1==696;
 ctxt=0;ctxl=0;crxt=0;crxl=0;txstep=0;rxstep=0;slot=0;
 serr=cc+1==40;dess=cc+1==41;
 for(integer k=0;k<2048;k=k+1)begin
  if(cc+1==C(511,k))txstep=1;
  if(cc+1==C(512,k))begin ctxt=1;ctxl=k==2047;end
  if(cc+1==C(697,k))begin crxt=1;crxl=k==2047;end
  if(cc+1==C(698,k))rxstep=1;
 end
 for(integer j=0;j<1628;j=j+1)if(cc+1==A(j))slot=1;
end
integer global_fc=0;
always @(posedge fec_clk)begin global_fc=global_fc+1;fc=global_fc-FPREFIX;end
always @(negedge fec_clk)begin
 ftxs=fc+1==487;ftxt=fc+1>=488&&fc+1<=2535;ftxl=fc+1==2535;
 frxs=fc+1==648;frxt=fc+1>=649&&fc+1<=2696;frxl=fc+1==2696;
 sers=fc+1==16;desr=fc+1==64;
 cap_s=fc+1==639;cap_t=fc+1>=640&&fc+1<=2687;cap_l=fc+1==2687;
 read_s=fc+1==647;read_t=fc+1>=648&&fc+1<=2695;read_l=fc+1==2695;
end
assign rxv[0]=0;assign rxf[0]=0;
for(genvar n=0;n<9;n=n+1)begin:g_node
 wire source_v;wire[4:0]source_row;wire[3:0]source_sector;
 if(n<8)begin assign read_v[n]=source_v;assign read_row[n]=source_row;assign read_sector[n]=source_sector;end
 ot_hcoll_engram_chain_node #(.NODE(n),.HOME_BASE(HOMEBASE)) node(
 .rst_n(rst_n),.clk_control(core_clk),.clk_mem({19{core_clk}}),.clk_program_capture({19{core_clk}}),
 .clk_qcapture(core_clk),.clk_qoutput(core_clk),.clk_bridge({8{core_clk}}),.clk_rxface({3{core_clk}}),.clk_endpoint_tx({5{core_clk}}),.clk_endpoint_rx({5{core_clk}}),
 .cfg_v(cfg_v),.cfg_target(8'd120),.cfg_addr(cfg_addr),.cfg_data(cfg_data[n]),.desc_v(desc_v),.desc_base(12'd0),.desc_limit(13'd2424),.desc_loops(16'd1),
 .launch_v(launch),.program_active(1'b0),.epoch_begin(linkepoch),.epoch(8'h72),.phy_up(1'b1),
 .source_read_v(source_v),.source_read_row(source_row),.source_read_sector(source_sector),
 .source_raw_v(n<8?raw_v[n]:1'b0),.source_raw_row(n<8?raw_row[n]:5'b0),.source_raw_sector(n<8?raw_sector[n]:4'b0),.source_raw_data(n<8?raw_data[n]:256'b0),
 .consumer_write_v(cwv[n]),.consumer_write_row(cwrow[n]),.consumer_write_sector(cwsec[n]),.consumer_write_data(cwdata[n]),
 .consumer_read_v(crv[n]),.consumer_read_row(crrow[n]),.consumer_read_sector(crsec[n]),
 .tx_pin_v(txv[n]),.tx_pin_frame(txf[n]),.rx_pin_v(rxv[n]),.rx_pin_frame(rxf[n]),
 .configured(configured[n]),.init_busy(init_busy[n]),.busy(nodebusy[n]),.done(nodedone[n]),.fault(nodefault[n]),.issued_v(),.issued_control());
end
for(genvar l=0;l<8;l=l+1)begin:g_link
 ot_hbm_core_fec_frame_link link(.core_clk(core_clk),.rst_n(rst_n),.fec_clks({16{fec_clk}}),.phy_clks({6{core_clk}}),
 .tx_start(txstart),.rx_start(rxstart),.tx_word_step(txstep),.rx_word_step(rxstep),.tx_slot_v(slot),.endpoint_tx_v(txv[l]),.endpoint_tx_frame(txf[l]),
 .expected_tx_slot(),.endpoint_rx_v(rxv[l+1]),.endpoint_rx_frame(rxf[l+1]),
 .ctx_start(ctxs),.ctx_take(ctxt),.ctx_last(ctxl),.ftx_start(ftxs),.ftx_take(ftxt),.ftx_last(ftxl),
 .frx_start(frxs),.frx_take(frxt),.frx_last(frxl),.crx_start(crxs),.crx_take(crxt),.crx_last(crxl),
 .capture_start(cap_s),.capture_take(cap_t),.capture_last(cap_l),.read_start(read_s),.read_take(read_t),.read_last(read_l),
 .ser_write_start(sers),.ser_read_start(serr),.des_write_start(dess),.des_read_start(desr),
 .pma_tx(pma[l]),.pma_rx(pma[l]),.fault_core(linkfault[l*4+:4]),.crossing_fault_fec(fecfault[l*2+:2]),.pma_fault(pmafault[l*4+:4]),.status(status[l]),.padding_fault(padfault[l]));
end
wire cwrite_v=cwv[8],decoded_v,craw_v,consumer_fault;wire[4:0]decoded_row,craw_row;wire[2:0]decoded_block;wire[3:0]craw_sector;wire[511:0]decoded_data;wire[255:0]craw_data;
reg[511:0]golden[0:383];integer raw_checks=0,decode_checks=0,write_checks=0,mismatches=0,MUT=0;
ot_hbm_engram_row_store_decode consumer(.clk(core_clk),.rst_n(rst_n),.epoch_begin(linkepoch),
 .write_v(cwv[8]),.write_row(cwrow[8]),.write_sector(cwsec[8]),.write_data(cwdata[8]),.read_v(crv[8]),.read_row(crrow[8]),.read_sector(crsec[8]),
 .out_v(decoded_v),.out_row(decoded_row),.out_block(decoded_block),.out_data(decoded_data),.raw_v(craw_v),.raw_row(craw_row),.raw_sector(craw_sector),.raw_data(craw_data),.fault(consumer_fault));
initial begin #40000;$fatal(1,"WHOLE_CHAIN_TIMEOUT");end
'''

def generate(out,inputs,li):
 out.mkdir(parents=True,exist_ok=True);binding=json.loads((inputs/'receipt.json').read_text())
 for name in ['external_hbm_sectors.hex','expected_bf16.hex']:
  data=(inputs/name).read_bytes();assert hashlib.sha256(data).hexdigest()==binding['data_sha256'][name];(out/name).write_bytes(data)
 program=ROOT/f'results/arch/hcoll_engram_rowgather_1015/program/layer{[1,14][li]}'
 # Sparse checkouts can omit evidence data; immutable committed images remain authoritative.
 for n in range(9):
  p=program/f'n{n}.hex'
  if p.exists():data=p.read_bytes()
  else:data=subprocess.check_output(['git','show',f'7b939edbe:{p.relative_to(ROOT)}'],cwd=ROOT)
  (out/f'n{n}.hex').write_bytes(data)
 (out/'tb.sv').write_text(bench(binding,li).replace('LAYER',str(li)))
 # Extract actual native source inventory from the proven link runner.
 src=json.loads((ROOT/'tools/hbm_coll_static/engram_node_sources.json').read_text())
 link=(ROOT/'tools/hbm_io/run_core_fec_frame_link_gate.sh').read_text()
 for x in re.findall(r'"?((?:\$io/|\$p/|rtl/|physical/)[^\s"\\]+\.s[v]?)"?',link):
  x=x.replace('$io/','rtl/hbm_accel/io_static_20261015/').replace('$p/','rtl/hbm_accel/generic/collective/p2p/')
  if not x.endswith('tb_core_fec_frame_link.sv'):src.append(x)
 src+=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv','rtl/hbm_accel/service/native_sector_20261015/ot_hbm_native_sector_stack.sv','rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_hash_home_native.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_fetch_compact.sv']
 src=list(dict.fromkeys(src));assert all((ROOT/x).exists() for x in src),[x for x in src if not(ROOT/x).exists()]
 (out/'sources.json').write_text(json.dumps(src,indent=2)+'\n')
 (out/'hier.vlt').write_text('`verilator_config\nhier_block -module "ot_hbm_core_fec_frame_link"\n')
 return src

def run(out,inputs,li,generate_only=False,run_only=False):
 out=out.resolve();prior_tb=hashlib.sha256((out/'tb.sv').read_bytes()).hexdigest() if (out/'tb.sv').exists() else None
 src=generate(out,inputs,li)
 if run_only:
  assert prior_tb==hashlib.sha256((out/'tb.sv').read_bytes()).hexdigest(),'run-only requires identical compiled testbench'
  assert (out/'obj/sim').exists()
  assert all((ROOT/x).stat().st_mtime<=(out/'obj/sim').stat().st_mtime for x in src),'native source changed after binary'
 if generate_only:return
 v=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';start=time.monotonic()
 cmd=[str(v),'--binary','--timing','--hierarchical','-O2','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-UNOPTFLAT','-Irtl/dsrom_sys/s81_link','--top-module','tb','--Mdir',str(out/'obj'),'-o','sim',str(out/'hier.vlt')]
 # Packages must precede their importing modules.
 src.sort(key=lambda x:0 if x.endswith('_pkg.sv') else 1)
 if not run_only:
  with(out/'build.log').open('w')as f:cp=subprocess.run(cmd+[str(ROOT/x) for x in src]+[str(out/'tb.sv')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  if cp.returncode:raise RuntimeError('native build failed; see '+str(out/'build.log'))
 runs=[]
 for mutant in [0,1,2,3]:
  rp=subprocess.run([str(out/'obj/sim'),f'+mut={mutant}'],cwd=out,capture_output=True,text=True);(out/f'm{mutant}.log').write_text(rp.stdout+rp.stderr)
  expected_reject=mutant==1 and rp.returncode!=0 and 'nativecatalogue_notconfigured' in rp.stdout
  if rp.returncode and not expected_reject:raise RuntimeError(rp.stdout+rp.stderr)
  if mutant==1 and not expected_reject:raise RuntimeError('reserved catalogue word mutant escaped configuration rejection')
  runs.append(dict(mutant=mutant,returncode=rp.returncode,expected_configuration_rejection=expected_reject,output=rp.stdout.strip()))
 r=dict(status='PASS selected-receipt whole mechanism',layer=[1,14][li],rows=24,source_homes=8,nodes=9,native_control_SRAMs=171,actual_links=8,physical_qualified=False,all_token160=False,normative_unchanged_programme=False,external_HBM_oracle_edges=6,runs=runs,seconds=time.monotonic()-start,source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in src})
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--inputs',type=pathlib.Path,required=True);p.add_argument('--layer-index',type=int,choices=[0,1],default=0);p.add_argument('--generate-only',action='store_true');p.add_argument('--run-only',action='store_true');a=p.parse_args();run(a.out,a.inputs,a.layer_index,a.generate_only,a.run_only)
