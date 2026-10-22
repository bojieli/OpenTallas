#!/usr/bin/env python3
"""Real converter -> fixed route -> selected native VM bank minimum caller."""
import json,sys
from pathlib import Path
age=int(sys.argv[3]);v=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
loads=[l for w in v['windows'] for l in w['loads']];n=len(loads)
s='''`timescale 1ns/1ps
module tb_dma_integrated;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg [1:0] begin_v=0;reg [31:0] epoch=0;
 reg [15:0] lv=0;reg [16*62-1:0] cmds=0;
 reg [31:0] fv=0;reg [16*12-1:0] fs=0;reg [16*512-1:0] fd=0;
 wire [15:0] full0,full1,pbad,srcfault,busy,ov;wire [31:0] ready;
 wire [16*281-1:0] load_dq,raw_dq;wire [47:0] db;wire [31:0] destq;
 for(genvar q=0;q<2;q=q+1)begin:Q
 for(genvar b=0;b<8;b=b+1)begin:L
  localparam I=q*8+b;
  ot_hbm_svc_vmdel_lane_load_static #(.NPC(2)) conv(.clk(clk),.rst_n(rst),.bank_id(3'(b)),
  .begin_v_i(begin_v[q]),.begin_bank_i(1'b0),.begin_epoch_i(epoch[q*16+:16]),
  .start_i(1'b0),.start_bank_i(1'b0),.start_epoch_i(16'd0),.start_base_sector_i(16'd0),
  .fill_v_i(fv[I*2+:2]),.fill_bank_i(2'b0),.fill_slot_i(fs[I*12+:12]),
  .fill_epoch_i({2{epoch[q*16+:16]}}),.fill_data_i(fd[I*512+:512]),
  .full0_all(full0[q*8+:8]),.full1_all(full1[q*8+:8]),.pcbad_all(pbad[q*8+:8]),
  .full0(full0[I]),.full1(full1[I]),.pcbad(pbad[I]),.block_ready(ready[I*2+:2]),.busy(busy[I]),.fault(srcfault[I]),.dq(raw_dq[I*281+:281]),
  .load_v_i(lv[I]),.load_cmd_i(cmds[I*62+:62]),.load_dest_bank(db[I*3+:3]),.load_dest_q(destq[I*2+:2]),.load_dq(load_dq[I*281+:281]),.load_out_v(ov[I]));
 end end
 reg [4*2248-1:0] source_lanes;reg[4*40-1:0] source_dest;
 wire [1123:0] source_packet;wire[19:0] source_destination;wire[3:0] sf,df;
 reg mutate_bank;
 always @*begin
 source_lanes=0;source_dest=0;
 source_lanes[0+:4496]=load_dq;
 for(integer i=0;i<16;i=i+1)source_dest[i*5+:5]={destq[i*2+:2],db[i*3+:3]^(mutate_bank?3'd1:3'd0)};
 end
 for(genvar q=0;q<4;q=q+1)begin:S
  ot_hbm_dma_load_source_join sj(.clk(clk),.rst_n(rst),.lane_dq(source_lanes[q*2248+:2248]),.lane_destination(source_dest[q*40+:40]),.packet(source_packet[q*281+:281]),.destination(source_destination[q*5+:5]),.fault(sf[q]));
 end
 wire [1123:0] dest_packet;wire[11:0] dest_bank;
 for(genvar q=0;q<4;q=q+1)begin:D
 ot_hbm_dma_load_destination_join #(.QID(q)) dj(.clk(clk),.rst_n(rst),.source_packet(source_packet),.source_destination(source_destination),.packet(dest_packet[q*281+:281]),.bank(dest_bank[q*3+:3]),.fault(df[q]));
 end
 wire [2247:0] bank_dq;wire[7:0] bf,done;wire[143:0] status;
 reg [135:0] rq=0;wire[2055:0] rr;
 for(genvar b=0;b<8;b=b+1)begin:B
 ot_hbm_dma_load_bank_join #(.BANK(b)) bj(.clk(clk),.rst_n(rst),.raw_dq(281'd0),.load_dq(dest_packet[0+:281]),.load_bank(dest_bank[0+:3]),.dq(bank_dq[b*281+:281]),.fault(bf[b]));
 hfd_vms_bank_native_q0_faces mem(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst),
 .bid(3'(b)),.sid(2'd0),.rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(3'd6),
 .dq(bank_dq[b*281+:281]),.dq_done(done[b]),.status(status[b*18+:18]),
 .rq0(rq[b*17+:17]),.rr0(rr[b*257+:257]),.rq1(17'd0),.rr1(),.rq2(17'd0),.rr2(),.rq3(17'd0),.rr3(),.rq4(17'd0),.rr4(),
 .wq0(281'd0),.wq1(281'd0),.wq_done0(),.wq_done1(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr());
 end
'''
s+=f' localparam N={n},EXPECTED_ROUTE={age};\n'
s+=''' reg[280:0] expected[0:N-1];reg[2:0] banks[0:N-1];integer launched[0:N-1],driven[0:N-1];
 integer cyc=0,sent=0,routed=0,commits=0,readsent=0,reads=0;integer route_min=999,route_max=0,drive_min=999,drive_max=0;
 integer read_index[0:4095];reg[7:0] read_bank[0:4095];
 always @(posedge clk)begin
 cyc=cyc+1;
 if(rst)begin
 for(integer b=0;b<8;b=b+1)if(rq[b*17+16])begin read_index[cyc+7]=readsent;read_bank[cyc+7]=8'(1<<b);readsent=readsent+1;end
 end
 #0.1;
 if(rst)begin
 if((|srcfault)||(|sf)||(|df)||(|bf))$fatal(1,"PATH_FAULT cycle%0d src%h sj%h dj%h bj%h",cyc,srcfault,sf,df,bf);
 if(status!==0)$fatal(1,"VM_FAULT cycle%0d status%h",cyc,status);
 for(integer b=0;b<8;b=b+1)begin
 if(bank_dq[b*281+280])begin
 if(routed>=sent||banks[routed]!==3'(b)||bank_dq[b*281+264+:17]!==expected[routed][280:264]||bank_dq[b*281+:8]!==expected[routed][7:0])$fatal(1,"ROUTE_MISMATCH packet%0d bank%0d",routed,b);
 for(integer w=0;w<8;w=w+1)if(expected[routed][w]&&bank_dq[b*281+8+w*32+:32]!==expected[routed][8+w*32+:32])$fatal(1,"ROUTE_DATA packet%0d word%0d",routed,w);
 if(cyc-launched[routed]<route_min)route_min=cyc-launched[routed];
 if(cyc-launched[routed]>route_max)route_max=cyc-launched[routed];
 if(cyc-driven[routed]<drive_min)drive_min=cyc-driven[routed];
 if(cyc-driven[routed]>drive_max)drive_max=cyc-driven[routed];
 routed=routed+1;
 end
 if(done[b])commits=commits+1;
 if(rr[b*257+256]!==read_bank[cyc][b])$fatal(1,"READ_PHASE cyc%0d bank%0d actual%b exp%b",cyc,b,rr[b*257+256],read_bank[cyc][b]);
 if(read_bank[cyc][b])begin
 if(rr[b*257+:256]!==expected[read_index[cyc]][263:8])$fatal(1,"READBACK cyc%0d bank%0d packet%0d",cyc,b,read_index[cyc]);reads=reads+1;
 end
 end
 end
 end
 initial begin
 mutate_bank=$test$plusargs("MUTATE_BANK");
 for(integer t=0;t<4096;t=t+1)begin read_bank[t]=0;read_index[t]=0;end
'''
for i,l in enumerate(loads):s+=f" expected[{i}]=281'h{l['expected281']};banks[{i}]=3'd{l['destbank']};\n"
s+=' repeat(6)@(negedge clk);rst=1;repeat(16)@(negedge clk);\n'
for window in v['windows']:
 q=window['sourceq'];assert q<2
 s+=f" epoch[{q*16}+:16]=16'd{window['epoch']};begin_v=2'd{1<<q};@(negedge clk);begin_v=0;repeat(5)@(negedge clk);\n"
 fills={(f['lane'],f['group'],f['slot']):f for f in window['fills']}
 for slot in range(64):
  for lane in range(8):
   data=''.join(fills[lane,g,slot]['data'] for g in [1,0]);i=q*8+lane
   s+=f" fv[{2*i}+:2]=2'b11;fs[{12*i}+:12]=12'd{slot|(slot<<6)};fd[{512*i}+:512]=512'h{data};\n"
  s+=' @(negedge clk);\n'
 s+=' fv=0;repeat(12)@(negedge clk);\n'
 s+=f" for(integer b=0;b<8;b=b+1)if(!ready[({q}*8+b)*2])$fatal(1,\"SOURCE_NOT_READY\");\n"
 for l in window['loads']:
  i=q*8+l['lane'];s+=f" lv=16'h{1<<i:04x};cmds[{i*62}+:62]=62'h{l['command']};driven[sent]=cyc;launched[sent]=cyc+1;sent=sent+1;@(negedge clk);\n"
 s+=' lv=0;repeat(20)@(negedge clk);\n'
 cmd=int(window['release_all_payload159'],16)>>97
 s+=f" lv=16'h{255<<(q*8):04x};for(integer b=0;b<8;b=b+1)cmds[({q}*8+b)*62+:62]=62'h{cmd:016x};@(negedge clk);lv=0;repeat(10)@(negedge clk);\n"
s+=''' if(sent!=N||routed!=N||commits!=N)$fatal(1,"PACKET_COUNTS sent%0d routed%0d commits%0d",sent,routed,commits);
 for(integer p=0;p<N;p=p+1)begin
 rq=0;rq[banks[p]*17+:17]={1'b1,expected[p][279:264]};@(negedge clk);
 end
 rq=0;repeat(12)@(negedge clk);
 if(reads!=N||readsent!=N)$fatal(1,"READ_COUNTS sent%0d got%0d",readsent,reads);
 if(route_min!=EXPECTED_ROUTE||route_max!=EXPECTED_ROUTE)$fatal(1,"ROUTE_AGE min%0d max%0d",route_min,route_max);
 $display("DMA_INTEGRATED_PASS words384 packets%0d routed%0d commits%0d SRAM_readback%0d source_windows2 command_sample_to_bank_packet%0d/%0d command_drive_to_bank_packet%0d/%0d native_read_return7",sent,routed,commits,reads,route_min,route_max,drive_min,drive_max);$finish;
 end
endmodule
'''
out.write_text(s)
