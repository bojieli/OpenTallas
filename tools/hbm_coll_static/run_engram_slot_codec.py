#!/usr/bin/env python3
"""Local160 codec unit with18 actual SRAMs; metadata is a declared unit input.

Not a substitute for actual hash/controller/endpoint/network composition.
Real checkpoint data enters only native source SRAM write pins; source read
faces provide every payload. Unit connector has one compiled publisher/edge.
"""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
TB=r'''`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,epoch=0;
integer cycle=0,mut=0,packets=0,nops=0,rawchecks=0,checks=0,writes=0;
reg[255:0]sectors[0:431];reg[511:0]golden[0:383];integer owner[0:23];integer owned[0:7][0:3];
reg[7:0]sw=0,sr=0,meta_req=0;reg[4:0]srow=0;reg[3:0]ssec=0;reg[255:0]sdata=0;
reg[4:0]rrow[0:7];reg[3:0]rsec[0:7];reg mpresent[0:7];
wire[7:0]rv,pv,sf,pf;wire[4:0]rr[0:7];wire[3:0]rs[0:7];wire[255:0]rd[0:7];wire[544:0]pd[0:7];
reg[7:0]x=0,low=0,pub=0;reg[1:0]pslot=0;reg[2:0]pair=0;
reg ax=0;reg[1:0]aslot=0;reg[2:0]apair=0;reg[7:0]ahome=0;
reg iv;reg[544:0]idata;
wire wv,af,complete;wire[4:0]wr;wire[3:0]ws;wire[255:0]wd;
reg cr=0;reg[4:0]crrow=0;reg[3:0]crsec=0;
wire cv,rawv,cf;wire[4:0]crow,rawrow;wire[2:0]block;wire[3:0]rawsec;wire[511:0]cd;wire[255:0]rawd;
for(genvar h=0;h<8;h=h+1)begin:g_home
 wire[19:0]orows={5'(owned[h][3]<0?0:owned[h][3]),5'(owned[h][2]),5'(owned[h][1]),5'(owned[h][0])};
 reg[2:0]vp=0,pp=0;reg[4:0]rp[0:2];reg[3:0]sp[0:2];reg mv=0,mp=0;reg[4:0]mr=0;reg[3:0]ms=0;
 always @(posedge clk)begin
  vp<={vp[1:0],meta_req[h]};pp<={pp[1:0],mpresent[h]};rp[0]<=rrow[h];sp[0]<=rsec[h];
  for(integer i=1;i<3;i=i+1)begin rp[i]<=rp[i-1];sp[i]<=sp[i-1];end
  mv<=vp[2];mp<=pp[2];mr<=rp[2];ms<=sp[2];
 end
 ot_hbm_engram_row_store_decode #(.DECODE_ENABLE(0)) source(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),
 .write_v(sw[h]),.write_row(srow),.write_sector(ssec),.write_data(sdata),.read_v(sr[h]),.read_row(rrow[h]),.read_sector(rsec[h]),
 .out_v(),.out_row(),.out_block(),.out_data(),.raw_v(rv[h]),.raw_row(rr[h]),.raw_sector(rs[h]),.raw_data(rd[h]),.fault(sf[h]));
 ot_hcoll_engram_slot_packetizer #(.HOME(h)) packet(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),
 .owned_slot_valid(4'b0111),.owned_slot_global_row(orows),.response_v(mv),.response_present(mp ^ (mut==2&&mv&&!mp)),.response_row(mr),.response_sector(ms),
 .raw_v(rv[h]),.raw_row(rr[h]),.raw_sector(rs[h]),.raw_data(rd[h]),.expect_response_v(x[h]),.capture_low(low[h]),.publish_v(pub[h]),.publish_slot(pslot),.publish_pair(pair),
 .out_v(pv[h]),.out_flit(pd[h]),.fault(pf[h]));
end
always @*begin
 iv=0;idata=0;
 for(integer h=0;h<8;h=h+1)if(pv[h])begin iv=1;idata=pd[h];end
 if(mut==1&&iv&&!idata[544])idata[0]=~idata[0];
end
ot_hcoll_engram_slot_assembler assembler(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),.in_v(iv),.in_flit(idata),
 .expect_v(ax),.expect_local_slot(aslot),.expect_pair(apair),.expect_home(ahome),.write_v(wv),.write_row(wr),.write_sector(ws),.write_data(wd),.fault(af),.complete(complete));
ot_hbm_engram_row_store_decode consumer(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch),
 .write_v(wv),.write_row(wr),.write_sector(ws),.write_data(wd),.read_v(cr),.read_row(crrow),.read_sector(crsec),
 .out_v(cv),.out_row(crow),.out_block(block),.out_data(cd),.raw_v(rawv),.raw_row(rawrow),.raw_sector(rawsec),.raw_data(rawd),.fault(cf));
initial begin
 if($value$plusargs("mut=%d",mut))begin end
 $readmemh("external_hbm_sectors.hex",sectors);$readmemh("expected_bf16.hex",golden);
 INITIAL_OWNERS
 for(cycle=0;cycle<1150;cycle=cycle+1)begin
  rst_n=cycle>=8;epoch=cycle==12;sw=0;sr=0;meta_req=0;x=0;low=0;pub=0;ax=0;cr=0;
  for(integer h=0;h<8;h=h+1)begin rrow[h]=0;rsec[h]=0;mpresent[h]=0;end
  if(cycle>=20&&cycle<236)begin
   srow=5'((cycle-20)/9);ssec=4'((cycle-20)%9);sdata=sectors[cycle-20];sw=8'b1<<owner[srow];
  end
  for(integer q=0;q<32;q=q+1)begin
   for(integer s=0;s<9;s=s+1)begin
    if(cycle==300+q*12+(s==8?9:s))begin
     meta_req[q/4]=1;mpresent[q/4]=owned[q/4][q%4]>=0;rrow[q/4]=5'(mpresent[q/4]?owned[q/4][q%4]:0);rsec[q/4]=4'(s);
     sr[q/4]=mpresent[q/4];
    end
    if(cycle==304+q*12+(s==8?9:s))begin
     x[q/4]=1;low[q/4]=s<8&&s%2==0;pub[q/4]=s==8||s%2==1;pslot=2'(q%4);pair=3'(s/2);
    end
    if((s==8||s%2==1)&&cycle==306+q*12+(s==8?9:s))begin
     ax=1;aslot=2'(q%4);apair=3'(s/2);ahome=8'(q/4);
     if(mut==3&&q==0&&s==1)aslot=1;
    end
   end
  end
  for(integer row=0;row<24;row=row+1)for(integer s=0;s<9;s=s+1)if(cycle==740+row*9+s)begin cr=1;crrow=5'(row);crsec=4'(s==0?8:s-1);end
  #4;clk=1;#1;
  if(iv)begin packets=packets+1;if(!idata[544])nops=nops+1;end
  if(wv)writes=writes+1;
  if(rawv)begin if(rawd!==sectors[rawrow*9+rawsec])$fatal(1,"SLOT_CODEC_RAW row%0d sector%0d",rawrow,rawsec);rawchecks=rawchecks+1;end
  if(cv)begin if(cd!==golden[crow*8+block])$fatal(1,"SLOT_CODEC_DECODE row%0d block%0d",crow,block);checks=checks+1;end
  if(mut==0&&((|sf)||(|pf)||af||cf))$fatal(1,"SLOT_CODEC_FAULT c%0d sf%h pf%h af%b cf%b",cycle,sf,pf,af,cf);
  #5;clk=0;
 end
 if(packets!=160||nops!=40||writes!=216||rawchecks!=216||checks!=192)$fatal(1,"SLOT_CODEC_COUNTS %0d/%0d/%0d/%0d/%0d",packets,nops,writes,rawchecks,checks);
 if(mut==0&&!complete)$fatal(1,"SLOT_CODEC_INCOMPLETE");
 if(mut==1&&!af)$fatal(1,"NOP_PAYLOAD_MUTANT_ESCAPED");
 if(mut==2&&pf!=8'hff)$fatal(1,"METADATA_MUTANT_ESCAPED");
 if(mut==3&&(!af||complete))$fatal(1,"PHYSICAL_SLOT_MUTANT_ESCAPED");
 $display("SLOT_CODEC_PASS mut%0d nativeSRAM18 packets160 NOP40 sectors216 blocks192 BF166144 complete%b",mut,complete);$finish;
end
endmodule
'''
def run(out,inputs):
 out=out.resolve();out.mkdir(parents=True,exist_ok=True);r=json.loads((inputs/'receipt.json').read_text());rows=[x for x in r['rows'] if x['layer']==1];initial=[]
 for row in rows:initial.append(f"owner[{row['list_index']}]={row['home']};")
 for h in range(8):
  owned=[x['list_index'] for x in rows if x['home']==h];assert len(owned)==3
  for k in range(4):initial.append(f"owned[{h}][{k}]={owned[k] if k<3 else -1};")
 (out/'tb.sv').write_text(TB.replace('INITIAL_OWNERS','\n'.join(initial)))
 for name in ['external_hbm_sectors.hex','expected_bf16.hex']:
  data=(inputs/name).read_bytes();assert hashlib.sha256(data).hexdigest()==r['data_sha256'][name];(out/name).write_bytes(data)
 src=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv','rtl/hbm_accel/generic/collective/p2p/ot_hcoll_engram_slot_transport.sv']
 cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'sim'),*[str(ROOT/p) for p in src],str(out/'tb.sv')],capture_output=True,text=True);(out/'build.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr
 runs=[]
 for m in [0,1,2,3]:
  rp=subprocess.run(['vvp',str(out/'sim'),f'+mut={m}'],cwd=out,capture_output=True,text=True);(out/f'm{m}.log').write_text(rp.stdout+rp.stderr);assert rp.returncode==0,rp.stdout+rp.stderr;runs.append(dict(mutant=m,output=rp.stdout.strip()))
 report=dict(status='PASS local160 codec unit only',native_SRAMs=18,source_metadata='declared unit input from exact checkpoint receipt; actual native producer join separate',packets=160,NOPs=40,sectors=216,decoded_blocks=192,runs=runs,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in src},native_hash_controller_join=False,native_endpoint_network_join=False,physical_qualified=False)
 (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--inputs',type=pathlib.Path,required=True);a=p.parse_args();run(a.out,a.inputs)
