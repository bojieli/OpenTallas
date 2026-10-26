`timescale 1ns/1ps
// Selected-mechanism native SW composition. All internal operands and results
// pass through the actual VM SRAMs and the actual operator RTL. Unselected
// production TKM/reduce/ring/link subtrees are outside this component boundary.
module tb_hgi_coll_sw_arg_join;
 parameter integer MUT=0;
 localparam integer NS=11,ND=16,RG=5,WG=1,COLL=3;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg [36:0] cfg=0;
 wire busy,done,issuer_fault,uop_v;wire [1535:0] uop;
 wire [31:0] iteration;wire [5:0] pc;
 wire [1535:0] inst=uop_v?uop:1536'd0;
 wire [54:0] ar={inst[688+:24],inst[1505+:31]};
 wire arg_mode=ar[47];
 wire [135:0] vm_rq;wire [2055:0] vm_rr;
 wire [1:0] injreq,injv;wire [31:0] idx,cycles;
 wire [159:0] injaddr,deladdr,rgxaddr;wire [65:0] injmeta;wire [131:0] vmmeta;
 wire [2047:0] assembled;wire [3:0] assembled_v;wire [23:0] epoch;
 wire [47:0] ws,rs,xs;wire ctl_fault;
 wire [NS-1:0] sv;wire [NS*545-1:0] sd;
 wire [ND-1:0] dv;wire [ND*545-1:0] dd;wire qfault;wire [3:0] qcause;
 wire av;wire [544:0] ad;wire afault;
 wire [3:0] actual_arg_v=dv[11+:4] & {4{arg_mode}};
 wire [3:0] excluded_tkm_v=dv[11+:4] & {4{!arg_mode}};
 wire [3:0] excluded_tkm_slots=inst[719+:4] & {4{!arg_mode}};
 wire [2247:0] kq;wire [4:0] launch_done;wire w_fault;
 wire [7:0] kdone;wire [143:0] status;
 reg [7:0] init_v=0;reg [8*281-1:0] init_data=0;
 reg [7:0] bank_rslot=0,bank_wslot=0;reg init_mode=1;
 reg [1535:0] code[0:63];
 reg [31:0] request_index=0;
 integer round=0,c,received=0,commits=0,pubs=0,halted=0;
 function automatic [31:0] value(input integer r,input integer src);
  case(r)
   0:value=(src==7||src==88)?32'h42280000:32'hbf800000;
   1:value=32'h7fc00000+32'(src);
   2:value=src==0?32'h80000000:src==95?32'h00000000:32'hbf800000;
   3:value=src==0?32'h7fc00001:(src==7||src==95)?32'h7f800000:32'h3f800000;
   default:value=src==17?32'hbf000000:32'hc0000000;
  endcase
 endfunction
 function automatic [31:0] ident(input integer r,input integer src);
  case(r)
   0:ident=src==7?32'd17:src==88?32'd5:32'(100+src);
   1:ident=32'(1000-src);
   2:ident=src==95?32'd7:32'(100+src);
   3:ident=src==7?32'd9:src==95?32'd22:32'(src);
   default:ident=32'(200+src);
  endcase
 endfunction
 function automatic [31:0] expected(input integer r);
  case(r)0:expected=5;1:expected=905;2:expected=7;3:expected=9;default:expected=217;endcase
 endfunction
 ot_hgi_coll_static_issuer u_issuer(.clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),
  .cfg(cfg),.start(start),.start_pc(6'd0),.busy(busy),.done(done),.fault(issuer_fault),
  .uop_v(uop_v),.uop(uop),.iteration(iteration),.uop_pc(pc));
 ot_hgi_coll_q_static_ctl_v2 #(.NPT(3),.SOLO(1)) u_control(.clk_control(clk),.rst_n(rst_n),.inst(inst),.iteration(iteration),
  .hgi_start(start),.hgi_busy(busy),.issue_done(done),.tkm_done(1'b0),.tkm_busy(1'b0),
  .dest_v(dv),.rc_v(1'b0),.rc_tag(3'd0),.vm_rr(vm_rr),.vm_req_pin(vm_rq),
  .inj_req_pin(injreq),.inj_idx_pin(idx),.inj_addr_pin(injaddr),.delivery_obase_pin(deladdr),.rgx_addr_pin(rgxaddr),
  .inj_source_v(injv),.inj_source_meta(injmeta),.vm_source_meta(vmmeta),.vm_assembled(assembled),.vm_assembled_v(assembled_v),
  .held_epoch(epoch),.wr_sequence_pin(ws),.rd_sequence_pin(rs),.rx_sequence_pin(xs),.protocol_fault(ctl_fault),.cycles(cycles));
 // Actual VM output faces, with no stimulus or expected-answer substitution.
 assign sv[4:0]=0;assign sd[5*545-1:0]=0;
 for(genvar j=0;j<4;j=j+1)begin:vm_source
  assign sv[5+j]=assembled_v[j];assign sd[(5+j)*545+:545]={vmmeta[j*33+:33],assembled[j*512+:512]};
 end
 assign sv[9]=0;assign sd[9*545+:545]=0;
 assign sv[10]=av;assign sd[10*545+:545]=ad;
 ot_hgi_coll_qslots #(.NPT(3),.NS(11)) u_qslots(.clk_capture(clk),.clk_output(clk),.rst_n(rst_n),
  .src_v(sv),.src_d(sd),.capture_slot({inst[712],inst[9:0]}),
  .sink_slot(inst[10+:16]),.sink_select(inst[26+:64]),.dst_v(dv),.dst_d(dd),.fault(qfault),.fault_kind(qcause));
 ot_hgi_coll_argmax_static u_arg(.clk(clk),.rst_n(rst_n),.start(ar[48]),
  .cfg_g(inst[761+:8]),.cfg_gbase(inst[769+:8]),.cfg_rank(ar[23+:8]),
  .in_slot(ar[51+:4] & {4{arg_mode}}),.in_v(actual_arg_v),.in_flit(dd[11*545+:2180]),
  .flush_slot(ar[49]),.publish_slot(ar[50]),.out_v(av),.out_flit(ad),.fault(afault));
 wire [2047:0] writer_data;
 for(genvar j=0;j<4;j=j+1)assign writer_data[j*512+:512]=dd[(7+j)*545+:512];
 ot_hgi_coll_static_vmwrite u_writer(.clk(clk),.rst_n(rst_n),.sid(2'd0),
  .rgx_v(dv[7+:4]),.rgx_addr(rgxaddr),.rgx_data(writer_data),.rgx_vm(inst[584]),
  .tkw_v(1'b0),.tkw_d(568'd0),.ingress_slot(inst[585+:5]),.slot_valid(inst[590+:8]),.slot_owner(inst[598+:32]),
  .kq(kq),.launch_done(launch_done),.fault(w_fault));
 if(1)begin:bank0
  wire [84:0] rq_all={17'd0,vm_rq[0+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[0+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),
   .rslot_v(bank_rslot[0]),.rslot(3'd3),.wslot_v(bank_wslot[0]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[0+:281]),.dq_done(),
   .kq(kq[0+:281]),.kq_done(kdone[0]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[0+:18]));
 end
 if(1)begin:bank1
  wire [84:0] rq_all={17'd0,vm_rq[17+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[257+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd1),.sid(2'd0),
   .rslot_v(bank_rslot[1]),.rslot(3'd3),.wslot_v(bank_wslot[1]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[281+:281]),.dq_done(),
   .kq(kq[281+:281]),.kq_done(kdone[1]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[18+:18]));
 end
 if(1)begin:bank2
  wire [84:0] rq_all={17'd0,vm_rq[34+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[514+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd2),.sid(2'd0),
   .rslot_v(bank_rslot[2]),.rslot(3'd3),.wslot_v(bank_wslot[2]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[562+:281]),.dq_done(),
   .kq(kq[562+:281]),.kq_done(kdone[2]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[36+:18]));
 end
 if(1)begin:bank3
  wire [84:0] rq_all={17'd0,vm_rq[51+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[771+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd3),.sid(2'd0),
   .rslot_v(bank_rslot[3]),.rslot(3'd3),.wslot_v(bank_wslot[3]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[843+:281]),.dq_done(),
   .kq(kq[843+:281]),.kq_done(kdone[3]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[54+:18]));
 end
 if(1)begin:bank4
  wire [84:0] rq_all={17'd0,vm_rq[68+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[1028+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd4),.sid(2'd0),
   .rslot_v(bank_rslot[4]),.rslot(3'd3),.wslot_v(bank_wslot[4]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[1124+:281]),.dq_done(),
   .kq(kq[1124+:281]),.kq_done(kdone[4]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[72+:18]));
 end
 if(1)begin:bank5
  wire [84:0] rq_all={17'd0,vm_rq[85+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[1285+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd5),.sid(2'd0),
   .rslot_v(bank_rslot[5]),.rslot(3'd3),.wslot_v(bank_wslot[5]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[1405+:281]),.dq_done(),
   .kq(kq[1405+:281]),.kq_done(kdone[5]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[90+:18]));
 end
 if(1)begin:bank6
  wire [84:0] rq_all={17'd0,vm_rq[102+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[1542+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd6),.sid(2'd0),
   .rslot_v(bank_rslot[6]),.rslot(3'd3),.wslot_v(bank_wslot[6]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[1686+:281]),.dq_done(),
   .kq(kq[1686+:281]),.kq_done(kdone[6]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[108+:18]));
 end
 if(1)begin:bank7
  wire [84:0] rq_all={17'd0,vm_rq[119+:17],51'd0};
  wire [1284:0] rr_all;
  assign vm_rr[1799+:257]=rr_all[3*257+:257];
  ot_vms_bank_static #(.RG(5),.WG(1)) u_bank(.clk(clk),.rst_n(rst_n),.bid(3'd7),.sid(2'd0),
   .rslot_v(bank_rslot[7]),.rslot(3'd3),.wslot_v(bank_wslot[7]),.wslot(init_mode?3'd5:3'd1),
   .rq(rq_all),.rr(rr_all),.wq(281'd0),.wq_done(),.dq(init_data[1967+:281]),.dq_done(),
   .kq(kq[1967+:281]),.kq_done(kdone[7]),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[126+:18]));
 end

 task config_word(input [36:0] word);
  begin @(negedge clk);cfg=word;@(posedge clk);#1;end
 endtask
 task set_ar(input integer row,input [54:0] fields);
  begin code[row][1505+:31]=fields[30:0];code[row][688+:24]=fields[54:31];end
 endtask
 task make_program;
  reg [54:0] a;reg [15:0] sec;integer rank;
  begin
   for(integer row=0;row<64;row=row+1)begin
    code[row]=0;a=0;a[47]=1;set_ar(row,a);
   end
   a=0;a[47]=1;a[48]=1;a[23+:8]=3;set_ar(0,a);
   code[0][761+:8]=96;
   for(integer row=1;row<=24;row=row+1)begin
    for(integer b=0;b<8;b=b+1)begin
     sec=16'((row-1)*8+b);code[row][1034+b*17+:17]={1'b1,sec};
    end
    for(integer j=0;j<4;j=j+1)begin
     rank=(row-1)*4+j;
     code[row][1170+j*33+:33]={1'b1,8'hff,8'(rank),16'd0};
     code[row][1383+j*6+:6]={3'(2*j+1),3'(2*j)};
     code[row+10][5+j]=1;
     code[row+11][10+11+j]=1;code[row+11][26+(11+j)*4+:4]=4'(5+j);
    end
    a=0;a[47]=1;a[51+:4]=15;set_ar(row+13,a);
   end
   a=0;a[47]=1;a[49]=1;set_ar(38,a);
   a=0;a[47]=1;a[50]=1;set_ar(MUT==3?43:44,a);
   code[45][712]=1;
   code[46][10+7]=1;code[46][26+7*4+:4]=(MUT==2?4'd9:4'd10);
   // Address word47 prepares registered writer address for reservation48.
   code[47][424+:40]=40'(16'd800)<<3;
   code[48][584]=1;code[48][585]=1;
   code[49][590+0]=1;code[49][598+0*4+:4]=0;
   code[50][590+1]=1;code[50][598+1*4+:4]=5;
   // Actual native readback of the committed token via the COLL read group.
   code[56][1034+0*17+:17]={1'b1,16'd800};
   code[56][1034+1*17+:17]={1'b1,16'd801};
   // Equal selectors disable assembly lanes: readback is checked at native pins.
   if(MUT==1)begin
    a=0;set_ar(20,a); // actual arg inputs at20 are no longer selected; TKM would see them.
   end
  end
 endtask
 task upload;
  begin
   for(integer row=0;row<64;row=row+1)begin
    for(integer bank=0;bank<3;bank=bank+1)begin
     config_word({1'b1,4'd0,24'd0,2'(bank),6'(row)});
     for(integer frag=0;frag<16;frag=frag+1)config_word({1'b1,4'd1,code[row][bank*512+frag*32+:32]});
    end
    config_word({1'b1,4'd2,26'd0,6'(row+1)});
    config_word({1'b1,4'd3,32'(row==63?4096:0)});
   end
   config_word(37'd0);repeat(4)@(negedge clk);
  end
 endtask
 task preload;
  reg [511:0] line;integer src;begin
   init_mode=1;
   // Actual DMA writes are the declared external input boundary.
   for(integer row=0;row<24;row=row+1)begin
    @(negedge clk);bank_wslot=8'hff;
    for(integer b=0;b<8;b=b+1)begin
     src=row*4+b/2;line={448'd0,ident(round,src),value(round,src)};
     init_data[b*281+:281]={1'b1,16'(row*8+b),line[(b%2)*256+:256],8'hff};
    end
    @(posedge clk);#1;
   end
   @(negedge clk);init_data=0;bank_wslot=0;
   repeat(8)@(negedge clk);init_mode=0;
  end
 endtask
 initial begin
  for(round=0;round<5;round=round+1)begin
   rst_n=0;start=0;cfg=0;init_data=0;bank_wslot=0;bank_rslot=0;
   repeat(4)@(negedge clk);rst_n=1;
   make_program();preload();upload();
   @(negedge clk);start=1;@(posedge clk);#1;
   for(c=1;c<=74;c=c+1)begin
    @(negedge clk);start=0;
    // Executed program word0 is start+4; real bank samples request one edge later.
    bank_rslot=(c>=6&&c<=29)?8'hff:c==61?8'h03:8'h00;
    bank_wslot=c==55?8'h01:c==56?8'h02:8'h00; // writer v4 relay edge (+1)
    @(posedge clk);#1;
    if(issuer_fault||ctl_fault||qfault||afault||w_fault)$fatal(1,"native ARG join fault round%0d cycle%0d issuer%0d ctl%0d q%h arg%0d writer%0d",round,c,issuer_fault,ctl_fault,qcause,afault,w_fault);
    for(integer b=0;b<8;b=b+1)begin
     if(status[b*18+16+:2]!=0)$fatal(1,"native bank fault cycle%0d bank%0d",c,b);
     if(vm_rr[b*257+256] !== ((c>=12&&c<=35)||(c==67&&b<2)))$fatal(1,"actual native operand/readback availability cycle%0d bank%0d",c,b);
    end
    if(|excluded_tkm_v || |excluded_tkm_slots)$fatal(1,"ARG mode leaked valid/slot to TKM cycle%0d",c);
    if(actual_arg_v!==((c>=17&&c<=40)?4'hf:4'h0))$fatal(1,"actual G96 operand delivery cycle%0d got%h",c,actual_arg_v);
    if(|actual_arg_v)begin
     for(integer j=0;j<4;j=j+1)begin
      integer src;src=(c-17)*4+j;
      if(dd[(11+j)*545+:545] !== {1'b1,8'hff,8'(src),16'd0,448'd0,ident(round,src),value(round,src)})
       $fatal(1,"actual SRAM operand identity/data cycle%0d lane%0d",c,j);
     end
     received=received+4;
    end
    if(av!==(c==48))$fatal(1,"ARG flush6 publication cycle%0d",c);
    if(av)begin
     if(ad!=={1'b1,8'hff,8'd3,16'd0,480'd0,expected(round)})$fatal(1,"ARG exact golden round%0d token%0d",round,ad[31:0]);
     pubs=pubs+1;
    end
    if(dv[7] !== (c==51))$fatal(1,"ARG source switch writer phase cycle%0d",c);
    if(kdone!==(c==58?8'h01:c==59?8'h02:8'h00))$fatal(1,"actual SRAM result commit cycle%0d got%h",c,kdone);
    if(|kdone)commits=commits+1;
    if(c==67)begin
     if(vm_rr[256]!==1'b1 || vm_rr[257+256]!==1'b1)$fatal(1,"actual SRAM readback valid");
     if(vm_rr[255:0]!=={224'd0,expected(round)} || vm_rr[257+:256]!==256'd0)$fatal(1,"actual SRAM token readback round%0d",round);
    end
    if(done!==(c==66))$fatal(1,"program completion cycle%0d",c);
    if(done)halted=halted+1;
   end
  end
  if(received!=480||commits!=10||pubs!=5||halted!=5)$fatal(1,"coverage counts");
  $display("SW_ARG_NATIVE_JOIN PASS G96 rounds5 operands480 exactgoldens5 SRAM27 commits10 flush6 first_operand17 last_operand40 publish48 write58_59 halt66");
  $finish;
 end
endmodule
