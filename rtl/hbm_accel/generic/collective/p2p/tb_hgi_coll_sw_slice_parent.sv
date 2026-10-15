`timescale 1ns/1ps
`default_nettype none
// SW slice-parent gate (H-COLL 2026-10-15): the WHOLE production COLL parent ot_hfd_coll_q3_static_host_v4
// (host programme target 52, SRAM issuer, V4 control, qslots, ring, reduce, ARGMAX, TKM, links, VM writer) joined
// to the WHOLE SW VM slice master hfd_hgi_vms_static_SW (8 static banks, 24 SRAM macros, hub, ring stops, replay,
// status) through the v15 contract edges coll_vm_rq_SW (slice rq group 3), coll_vm_rr_SW (slice rr group 3) and
// coll_vm_kq_SW (slice kq). Programme = the native SW ARGMAX join (G96, 24 four-line VM reads, flush, publish,
// RGX write, native readback) loaded through the actual 256-bit host frames. The slice calendar (rslot/wslot) is the
// compiler reservation, replayed by the bench; it is never derived from the DUT. Expected-answer functions only
// check outputs. MUT1 = ARG inputs deselected, MUT2 = writer source wrong, MUT3 = early publication,
// MUT4 = COLL rq bound to the wrong slice read group (contract wiring mutant).
module tb_hgi_coll_sw_slice_parent;
 parameter integer MUT=0;
 localparam integer OFF=2;           // V4 host launch -> issuer start (measured: V2 start 34/38 = host 36/40)
 localparam integer COLLG=(MUT==4)?2:3;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cv=0,dv_cfg=0,launch=0;
 reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;
 wire configured,init_busy,program_fault,busy,done,hfault,qfault_o;
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr,ob;
 wire [3:0] delv;wire [2179:0] deld;
 wire [2:0] txv,retry;wire [1835:0] txd;
 wire [279:0] cwo,ccwo;wire rrv;wire [2:0] rrt;wire [255:0] rrd;wire [31:0] cycles;
 wire [135:0] vm_rq;wire [2055:0] vm_rr;wire [2247:0] vm_kq;
 // slice
 wire [821:0] cr;wire [10279:0] rr;wire [7:0] wq_done,dq_done,kq_done;
 wire [2223:0] cw_out,ccw_out;wire [143:0] bank_status;wire [2:0] hub_status,ring_fault;wire [1:0] mirror_busy;
 wire [18:0] vmstat;
 reg [7:0] rslot_v=0,wslot_v=0;reg [23:0] rslot=0,wslot=0;
 reg [2247:0] dq=0;reg [679:0] rq_bench=0;
 wire [679:0] rq;
 // v15 contract slices: coll_vm_rq_SW -> rq[136*3 +:136], rr[2056*3 +:2056] -> vm_rr, vm_kq -> kq
 generate if(COLLG==3)begin:g_rq3
  assign rq={rq_bench[679:544],vm_rq,rq_bench[407:0]};
 end else begin:g_rq2
  assign rq={rq_bench[679:408],vm_rq,rq_bench[271:0]};
 end endgenerate
 assign vm_rr=rr[2056*3+:2056];
 ot_hfd_coll_q3_static_host_v4 #(.QID(2'd0)) dut(.rst_n(rst_n),.clk_program(clk),.clk_control(clk),.clk_issue({4{clk}}),
  .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),.clk_tkm({34{clk}}),.clk_vmwrite(clk),
  .clk_link({15{clk}}),.cfg_v(cv),.cfg_target(8'd52),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dv_cfg),.desc_base(12'd0),.desc_limit(13'd64),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(configured),.program_init_busy(init_busy),.program_fault(program_fault),
  .hgi_busy(busy),.hgi_done(),.hgi_fault(hfault),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(1024'd0),
  .del_valid(delv),.del_flit(deld),.hgi_del_obase(ob),.rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),
  .rr_v(rrv),.rr_tag(rrt),.rr_d(rrd),.phy_up(3'b111),.tx_pin_v(txv),.tx_pin_flit(txd),
  .rx_pin_v(3'b0),.rx_pin_flit(1836'd0),.retry_requested(retry),
  .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.vm_kq(vm_kq),.fault(qfault_o),.done(done),.stat_cycles(cycles));
 hfd_hgi_vms_static_SW slice(.clk_bank({8{clk}}),.clk_hub(clk),.clk_ring({2{clk}}),.clk_replay(clk),.rst_n(rst_n),
  .cq('0),.cr(cr),.client_seq('0),.response_enable('0),.response_seq('0),
  .bank_enable(8'd0),.bank_client('0),.hub_ring_enable(2'd0),.hub_ring_client('0),
  .rslot_v(rslot_v),.wslot_v(wslot_v),.rslot(rslot),.wslot(wslot),.rq(rq),.rr(rr),
  .wq(2248'd0),.wq_done(wq_done),.dq(dq),.kq(vm_kq),.dq_done(dq_done),.kq_done(kq_done),
  .cw_in(2224'd0),.ccw_in(2224'd0),.cw_out(cw_out),.ccw_out(ccw_out),.ring_tx_enable(2'd0),
  .ring_tx_source(6'd0),.replay_enable(1'b0),.replay_source(1'b0),.bank_status(bank_status),
  .hub_status(hub_status),.mirror_busy(mirror_busy),.vmstat(vmstat),.ring_fault(ring_fault));
 // observation only (never driven): ARG publication and writer sink inside the actual parent
 wire av=dut.u_q.u_q.arg_out_v;
 wire [15:0] pdv=dut.u_q.u_q.dest_v;
 reg [1535:0] code[0:63];
 integer round=0,c,commits=0,pubs=0,halted=0,reads=0,readbacks=0;
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
 task set_ar(input integer row,input [54:0] fields);
  begin code[row][1505+:31]=fields[30:0];code[row][688+:24]=fields[54:31];end
 endtask
 // identical to tb_hgi_coll_sw_arg_join make_program (same ISA fields in V4)
 task make_program;
  reg [54:0] a;reg [15:0] sec;integer rank;
  begin
   for(integer row=0;row<64;row=row+1)begin code[row]=0;a=0;a[47]=1;set_ar(row,a);end
   a=0;a[47]=1;a[48]=1;a[23+:8]=3;set_ar(0,a);
   code[0][761+:8]=96;
   for(integer row=1;row<=24;row=row+1)begin
    for(integer b=0;b<8;b=b+1)begin sec=16'((row-1)*8+b);code[row][1034+b*17+:17]={1'b1,sec};end
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
   code[47][424+:40]=40'(16'd800)<<3;
   code[48][584]=1;code[48][585]=1;
   code[49][590+0]=1;code[49][598+0*4+:4]=0;
   code[50][590+1]=1;code[50][598+1*4+:4]=5;
   code[56][1034+0*17+:17]={1'b1,16'd800};
   code[56][1034+1*17+:17]={1'b1,16'd801};
   if(MUT==1)begin a=0;set_ar(20,a);end
  end
 endtask
 task host_frame(input integer row,input integer segment,input [255:0] v);
  begin @(negedge clk);cv=1;cfg_addr=12'(row*8+segment);cfg_data=v;end
 endtask
 task upload;
  reg [63:0] md;begin
   for(integer row=0;row<64;row=row+1)begin
    md=64'(row+1);if(row==63)md[44]=1;
    for(integer s=0;s<6;s=s+1)host_frame(row,s,code[row][s*256+:256]);
    host_frame(row,6,{192'b0,md});
    @(negedge clk);cv=0;
    repeat(55)@(negedge clk);          // fixed reservation per row, no init_busy polling
    if(init_busy||program_fault)$fatal(1,"host row drain did not finish on reserved edge row%0d",row);
   end
   @(negedge clk);dv_cfg=1;@(negedge clk);dv_cfg=0;repeat(66)@(negedge clk);
   if(!configured||program_fault)$fatal(1,"descriptor did not validate");
  end
 endtask
 // external DMA boundary: 96 operand lines through the slice's actual dq port (wslot 5)
 task preload;
  reg [511:0] line;integer src;begin
   for(integer row=0;row<24;row=row+1)begin
    @(negedge clk);wslot_v=8'hff;wslot=0;dq=0;
    for(integer b=0;b<8;b=b+1)begin
     wslot[b*3+:3]=3'd5;
     src=row*4+b/2;line={448'd0,ident(round,src),value(round,src)};
     dq[b*281+:281]={1'b1,16'(row*8+b),line[(b%2)*256+:256],8'hff};
    end
   end
   @(negedge clk);dq=0;wslot_v=0;wslot=0;repeat(12)@(negedge clk);
  end
 endtask
 initial begin
  for(round=0;round<5;round=round+1)begin
   rst_n=0;launch=0;cv=0;dq=0;wslot_v=0;rslot_v=0;
   repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
   make_program();preload();upload();
   @(negedge clk);launch=1;@(posedge clk);#1;
   for(c=1;c<=74+OFF;c=c+1)begin
    @(negedge clk);launch=0;
    // compiler slice calendar: COLL read group 3 at the programme read edges, kq write slot 1 at the commit edges
    rslot_v=0;rslot=0;wslot_v=0;wslot=0;
    for(integer b=0;b<8;b=b+1)begin
     if((c-OFF>=6&&c-OFF<=29)||(c-OFF==61&&b<2))begin rslot_v[b]=1;rslot[b*3+:3]=3'd3;end
     if((c-OFF==54&&b==0)||(c-OFF==55&&b==1))begin wslot_v[b]=1;wslot[b*3+:3]=3'd1;end
    end
    @(posedge clk);#1;
    if(hfault||qfault_o||program_fault)$fatal(1,"slice-parent fault round%0d cycle%0d",round,c-OFF);
    if(bank_status!==144'd0||hub_status!==3'd0||ring_fault!==3'd0)
     $fatal(1,"slice status round%0d cycle%0d bank%h hub%b ring%b",round,c-OFF,bank_status,hub_status,ring_fault);
    for(integer b=0;b<8;b=b+1)
     if(vm_rr[b*257+256]!==((c-OFF>=12&&c-OFF<=35)||(c-OFF==67&&b<2)))
      $fatal(1,"native COLL read-group response availability round%0d cycle%0d bank%0d",round,c-OFF,b);
    if(c-OFF>=12&&c-OFF<=35)for(integer b=0;b<8;b=b+1)begin
     integer src;reg [511:0] line;src=(c-OFF-12)*4+b/2;line={448'd0,ident(round,src),value(round,src)};
     if(vm_rr[b*257+:256]!==line[(b%2)*256+:256])$fatal(1,"COLL operand data from actual SRAM round%0d cycle%0d bank%0d",round,c-OFF,b);
     reads=reads+1;
    end
    if(av!==(c-OFF==48))$fatal(1,"ARG publication cycle%0d",c-OFF);
    if(av)pubs=pubs+1;
    if(pdv[7]!==(c-OFF==51))$fatal(1,"writer sink phase cycle%0d",c-OFF);
    if(kq_done!==(c-OFF==57?8'h01:c-OFF==58?8'h02:8'h00))$fatal(1,"slice kq commit cycle%0d got%h",c-OFF,kq_done);
    if(|kq_done)commits=commits+1;
    if(c-OFF==67)begin
     if(vm_rr[255:0]!=={224'd0,expected(round)}||vm_rr[257+:256]!==256'd0)
      $fatal(1,"slice readback of the committed ARGMAX token round%0d got%0d",round,vm_rr[31:0]);
     readbacks=readbacks+1;
    end
    if(done!==(c-OFF==66))$fatal(1,"programme completion cycle%0d",c-OFF);
    if(done)halted=halted+1;
   end
  end
  if(reads!=960||commits!=10||pubs!=5||halted!=5||readbacks!=5)$fatal(1,"coverage counts");
  $display("HCOLL_SW_SLICE_PARENT PASS whole_q3_host_v4+whole_SW_slice rounds5 operand_sectors960 publish48 commit57_58 readback67 halt66 (+%0d host launch) contract rq/rr group3 kq",OFF);
  $finish;
 end
endmodule
`default_nettype wire
