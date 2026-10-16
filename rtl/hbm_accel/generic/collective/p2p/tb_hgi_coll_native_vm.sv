`timescale 1ns/1ps
module tb_hgi_coll_native_vm;
 parameter integer RG=5,WG=1,MUT=0;
 localparam integer NPT=(RG==5?3:2),NS=NPT+7,ND=NPT+13,COLL=RG-2;
 localparam [1:0] SID=(RG==5?2'd0:2'd2);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [1535:0] inst=0;
 reg [3:0] rv=0;reg [159:0] ra=0;reg [2047:0] rd=0;
 reg tv=0;reg [567:0] td=0;reg [4:0] ingress=0;
 reg [7:0] slots=0;reg [31:0] owners=0;
 wire [2247:0] kq;wire [4:0] launch_done;wire writer_fault;
 wire [135:0] rq;wire [2055:0] rr;
 wire [7:0] committed;wire [143:0] statuses;
 wire ctl_fault;wire [1:0] injreq,injv;wire [31:0] idx,cycles;
 wire [159:0] injaddr,deladdr,rgxaddr;wire [65:0] injmeta;
 wire [131:0] vmmeta;wire [2047:0] assembled;wire [3:0] assembled_v;
 wire [8*NPT-1:0] epoch;
 wire [NS-1:0] source_v;
 wire [NS*545-1:0] source_d;
 wire [ND-1:0] dest_v;wire [ND*545-1:0] dest_d;
 wire qfault;wire [3:0] qcause;
 reg [7:0] bank_read_slot=0,bank_write_slot=0;
 integer cyc,checks=0,commits=0,reads=0;
 reg [1535:0] calendar[0:127];
 reg [4:0] input_v[0:127];reg [199:0] input_a[0:127];
 reg [2559:0] input_d[0:127];reg [79:0] input_m[0:127];
 reg [2247:0] expect_launch[0:127];reg [31:0] expect_owner[0:127];reg [7:0] expect_resv[0:127];
 reg [7:0] expect_bank_write[0:127],expect_commit[0:127],expect_bank_read[0:127];
 reg [3:0] expect_delivery[0:127];reg [2179:0] expect_data[0:127];
 reg [255:0] gold_main[0:7][0:127],gold_mirror[0:7][0:127];
 ot_hgi_coll_static_vmwrite writer(.clk(clk),.rst_n(rst_n),.sid(SID),
  .rgx_v(rv),.rgx_addr(ra),.rgx_data(rd),.rgx_vm(1'b1),.tkw_v(tv),.tkw_d(td),
  .ingress_slot(ingress),.slot_valid(slots),.slot_owner(owners),.kq(kq),.launch_done(launch_done),.fault(writer_fault));
 ot_hgi_coll_q_static_ctl #(.NPT(NPT)) ctl(.clk_control(clk),.rst_n(rst_n),.inst(inst),.iteration(32'd0),
  .hgi_start(1'b0),.hgi_busy(1'b0),.issue_done(1'b0),.tkm_done(1'b0),.tkm_busy(1'b0),
  .dest_v({ND{1'b0}}),.rc_v(1'b0),.rc_tag(3'd0),.vm_rr(rr),.vm_req_pin(rq),
  .inj_req_pin(injreq),.inj_idx_pin(idx),.inj_addr_pin(injaddr),.delivery_obase_pin(deladdr),.rgx_addr_pin(rgxaddr),
  .inj_source_v(injv),.inj_source_meta(injmeta),.vm_source_meta(vmmeta),.vm_assembled(assembled),
  .vm_assembled_v(assembled_v),.held_epoch(epoch),.protocol_fault(ctl_fault),.cycles(cycles));
 if(1)begin:banks_0
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[0*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[0*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(0)),.sid(SID),
   .rslot_v(bank_read_slot[0]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[0]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[0*281+:281] ^ ((MUT==1 && 0==0)?(281'd1<<8):281'd0)),.kq_done(committed[0]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[0*18+:18]));
 end
 if(1)begin:banks_1
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[1*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[1*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(1)),.sid(SID),
   .rslot_v(bank_read_slot[1]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[1]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[1*281+:281] ^ ((MUT==1 && 1==0)?(281'd1<<8):281'd0)),.kq_done(committed[1]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[1*18+:18]));
 end
 if(1)begin:banks_2
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[2*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[2*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(2)),.sid(SID),
   .rslot_v(bank_read_slot[2]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[2]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[2*281+:281] ^ ((MUT==1 && 2==0)?(281'd1<<8):281'd0)),.kq_done(committed[2]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[2*18+:18]));
 end
 if(1)begin:banks_3
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[3*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[3*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(3)),.sid(SID),
   .rslot_v(bank_read_slot[3]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[3]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[3*281+:281] ^ ((MUT==1 && 3==0)?(281'd1<<8):281'd0)),.kq_done(committed[3]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[3*18+:18]));
 end
 if(1)begin:banks_4
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[4*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[4*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(4)),.sid(SID),
   .rslot_v(bank_read_slot[4]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[4]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[4*281+:281] ^ ((MUT==1 && 4==0)?(281'd1<<8):281'd0)),.kq_done(committed[4]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[4*18+:18]));
 end
 if(1)begin:banks_5
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[5*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[5*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(5)),.sid(SID),
   .rslot_v(bank_read_slot[5]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[5]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[5*281+:281] ^ ((MUT==1 && 5==0)?(281'd1<<8):281'd0)),.kq_done(committed[5]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[5*18+:18]));
 end
 if(1)begin:banks_6
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[6*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[6*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(6)),.sid(SID),
   .rslot_v(bank_read_slot[6]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[6]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[6*281+:281] ^ ((MUT==1 && 6==0)?(281'd1<<8):281'd0)),.kq_done(committed[6]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[6*18+:18]));
 end
 if(1)begin:banks_7
  wire [RG*17-1:0] brq;
  wire [RG*257-1:0] brr;
  for(genvar g=0;g<RG;g=g+1)assign brq[g*17+:17]=g==COLL?rq[7*17+:17]:17'd0;
  // Mutant crosses actual native group return wires; no invented response data.
  assign rr[7*257+:257]=brr[(MUT==3?COLL-1:COLL)*257+:257];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(7)),.sid(SID),
   .rslot_v(bank_read_slot[7]),.rslot($clog2(RG+1)'(COLL)),
   .wslot_v(bank_write_slot[7]),.wslot($clog2(WG+5)'(WG)),
   .rq(brq),.rr(brr),.wq({WG*281{1'b0}}),.wq_done(),.dq(281'd0),.dq_done(),
   .kq(kq[7*281+:281] ^ ((MUT==1 && 7==0)?(281'd1<<8):281'd0)),.kq_done(committed[7]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(statuses[7*18+:18]));
 end

 assign source_v[1:0]=2'b0;assign source_d[2*545-1:0]=0;
 for(genvar k=0;k<NPT;k=k+1)begin:unused_rails
  assign source_v[2+k]=0;assign source_d[(2+k)*545+:545]=0;
 end
 for(genvar j=0;j<4;j=j+1)begin:vm_source
  assign source_v[2+NPT+j]=assembled_v[j];
  assign source_d[(2+NPT+j)*545+:545]={vmmeta[j*33+:33],
    (MUT==4?{assembled[j*512+:256],assembled[j*512+256+:256]}:assembled[j*512+:512])};
 end
 assign source_v[NS-1]=0;assign source_d[(NS-1)*545+:545]=0;
 ot_hgi_coll_qslots #(.NPT(NPT)) qslots(.clk_capture(clk),.clk_output(clk),.rst_n(rst_n),
  .src_v(source_v),.src_d(source_d),.capture_slot(inst[NS-1:0]),
  .sink_slot(inst[10+:ND]),.sink_select(inst[26+:ND*4]),.dst_v(dest_v),.dst_d(dest_d),.fault(qfault),.fault_kind(qcause));
 function automatic [511:0] pattern(input integer seed);
  reg [31:0] v;begin v=32'hf93a71b5 ^ 32'(seed);
   for(integer w=0;w<16;w=w+1)begin v=v^(v<<13);v=v^(v>>17);v=v^(v<<5);pattern[w*32+:32]=v;end
  end
 endfunction
 task plan_line(input integer c,lane,input [15:0] sec,input [511:0] data,input [15:0] mask);
  integer bank,t;reg [15:0] s;begin
   input_v[c][lane]=1;input_a[c][lane*40+:40]=40'(sec)<<3;
   input_d[c][lane*512+:512]=data;input_m[c][lane*16+:16]=mask;
   for(integer h=0;h<2;h=h+1)begin
    s=sec+16'(h);bank=int'(s[2:0]);t=c+2+h; // writer v4 relay edge: launch low C+2, high C+3; reservation fields keep C+1/C+2
    if(expect_launch[t][bank*281+280])$fatal(1,"invalid test compiler bank collision");
    expect_launch[t][bank*281+:281]={1'b1,s,data[h*256+:256],mask[h*8+:8]};
    expect_owner[c+1+h][bank*4+:4]=4'(lane+5*h);expect_resv[c+1+h][bank]=1;
    expect_bank_write[t+1][bank]=1;expect_commit[t+4][bank]=1;
   end
  end
 endtask
 task plan_read(input integer c,input [15:0] base,input [7:0] valid,input integer reverse_pairs);
  integer low,high;reg [15:0] sec;reg [32:0] meta;begin
   for(integer b=0;b<8;b=b+1)begin
    sec=base+16'(b);calendar[c][1034+b*17+:17]={valid[b],sec};
   end
   expect_bank_read[c+1]=valid;
   for(integer j=0;j<4;j=j+1)begin
    low=reverse_pairs!=0?6-2*j:2*j;high=low+1;
    if(!valid[low]&&!valid[high])high=low;
    calendar[c][1383+j*6+:6]={3'(high),3'(low)};
    meta={1'b1,8'h63,8'(c),16'(j)};calendar[c][1170+j*33+:33]=meta;
    if(valid[low]&&valid[high]&&low!=high)begin
     calendar[c+10][2+NPT+j]=1;
     calendar[c+11][10+NPT+j]=1;calendar[c+11][26+(NPT+j)*4+:4]=4'(2+NPT+j);
     expect_delivery[c+12][j]=1;
    end
   end
  end
 endtask
 initial begin
  for(integer c=0;c<128;c=c+1)begin
   calendar[c]=0;input_v[c]=0;input_a[c]=0;input_d[c]=0;input_m[c]='1;
   expect_launch[c]=0;expect_owner[c]=0;expect_resv[c]=0;expect_commit[c]=0;expect_bank_write[c]=0;expect_bank_read[c]=0;
   expect_delivery[c]=0;expect_data[c]=0;
  end
  for(integer n=0;n<16;n=n+1)for(integer l=0;l<4;l=l+1)
   plan_line(n+4,l,{1'b0,SID,13'(n*16+2*l)},pattern(n*4+l),16'hffff);
  plan_line(24,0,{1'b0,SID,13'd384},pattern(400),16'hffff);
  plan_line(28,4,{1'b0,SID,13'd384},pattern(401),16'h5aa5);
  for(integer l=0;l<4;l=l+1)plan_line(32,l,16'h8200+16'(2*l),pattern(500+l),16'hffff);
  for(integer l=0;l<4;l=l+1)plan_line(36,l,{1'b0,SID,13'(640+2*l)},pattern(600+l),16'hffff);
  plan_line(36,4,{1'b0,SID,13'd641},pattern(604),16'hffff);
  plan_line(44,0,{1'b0,SID,13'd775},pattern(700),16'hffff);
  plan_read(64,{1'b0,SID,13'd0},8'hff,0);
  plan_read(65,{1'b0,SID,13'd240},8'hff,1);
  plan_read(66,{1'b0,SID,13'd384},8'h03,0);
  plan_read(67,16'h8200,8'hff,0);
  plan_read(68,{1'b0,SID,13'd640},8'hff,1);
  // A line whose first sector is bank7 crosses to bank0 of the next row.
  calendar[69][1034+7*17+:17]={1'b1,1'b0,SID,13'd775};
  calendar[69][1034+0*17+:17]={1'b1,1'b0,SID,13'd776};
  calendar[69][1383+:6]={3'd0,3'd7};calendar[69][1170+:33]={1'b1,32'h73112233};
  expect_bank_read[70]=8'h81;calendar[79][2+NPT]=1;
  calendar[80][10+NPT]=1;calendar[80][26+NPT*4+:4]=4'(2+NPT);
  expect_delivery[81][0]=1;
  for(cyc=0;cyc<110;cyc=cyc+1)begin
   @(negedge clk);rst_n=cyc>=3;inst=calendar[cyc];
   rv=input_v[cyc][3:0];tv=input_v[cyc][4];ra=input_a[cyc][159:0];rd=input_d[cyc][2047:0];
   td={input_a[cyc][199:160],input_m[cyc][79:64],input_d[cyc][2559:2048]};
   ingress=input_v[cyc];owners=expect_owner[cyc];
   for(integer b=0;b<8;b=b+1)slots[b]=expect_resv[cyc][b];
   bank_write_slot=expect_bank_write[cyc];bank_read_slot=expect_bank_read[cyc];
   if(MUT==2&&cyc==7)bank_write_slot[0]=0;
   @(posedge clk);#1;
   if(rst_n)begin
    if(writer_fault||ctl_fault||qfault)$fatal(1,"component fault cycle%0d writer%0d ctl%0d q%h",cyc,writer_fault,ctl_fault,qcause);
    for(integer b=0;b<8;b=b+1)begin:check_bank
     reg [15:0] sec;integer row;reg [255:0] data;reg [7:0] mask;
     if(statuses[b*18+16+:2]!=0)$fatal(1,"native bank fault cycle%0d bank%0d",cyc,b);
     if(kq[b*281+280]!==expect_launch[cyc][b*281+280])$fatal(1,"sector launch cycle");
     if(kq[b*281+280])begin
      if(kq[b*281+:281]!==expect_launch[cyc][b*281+:281])$fatal(1,"sector launch payload");
      sec=expect_launch[cyc][b*281+264+:16];row=int'(sec[12:3]);
      data=expect_launch[cyc][b*281+8+:256];mask=expect_launch[cyc][b*281+:8];
      for(integer w=0;w<8;w=w+1)if(mask[w])begin
       if(sec[15])gold_mirror[b][row][w*32+:32]=data[w*32+:32];
       else gold_main[b][row][w*32+:32]=data[w*32+:32];
      end
     end
     if(committed[b] !== expect_commit[cyc][b])$fatal(1,"actual SRAM commit timing cycle%0d bank%0d got%0d expected%0d",cyc,b,committed[b],expect_commit[cyc][b]);
     if(committed[b])commits=commits+1;
    end
    // Construct expected read data from declared write stimuli only, never DUT memory.
    if(cyc>=12)begin
     integer pc,low,high,row;reg [15:0] sec;reg [511:0] line;
     pc=cyc-12;
     for(integer j=0;j<4;j=j+1)if(expect_delivery[cyc][j])begin
      low=int'(calendar[pc][1383+j*6+:3]);high=int'(calendar[pc][1386+j*6+:3]);
      sec=calendar[pc][1034+low*17+:16];row=int'(sec[12:3]);
      line[255:0]=sec[15]?gold_mirror[low][row]:gold_main[low][row];
      sec=calendar[pc][1034+high*17+:16];row=int'(sec[12:3]);
      line[511:256]=sec[15]?gold_mirror[high][row]:gold_main[high][row];
      expect_data[cyc][j*545+:545]={calendar[pc][1170+j*33+:33],line};
     end
    end
    for(integer j=0;j<4;j=j+1)begin
     if(dest_v[NPT+j]!==expect_delivery[cyc][j])$fatal(1,"native VM->qslots fixed ten-edge capture/twelve-edge delivery cycle%0d lane%0d",cyc,j);
     if(dest_v[NPT+j])begin
      if(dest_d[(NPT+j)*545+:545]!==expect_data[cyc][j*545+:545])$fatal(1,"native SRAM data/metadata cycle%0d lane%0d",cyc,j);
      reads=reads+1;
     end
    end
    checks=checks+1;
   end
  end
  if(commits!=152 || reads!=18)$fatal(1,"coverage counts commits%0d reads%0d",commits,reads);
  $display("HCOLL_NATIVE_VM PASS RG%0d WG%0d banks8 SRAM24 commits%0d reads%0d request_to_capture10 delivery12 checks%0d",RG,WG,commits,reads,checks);
  $finish;
 end
endmodule
