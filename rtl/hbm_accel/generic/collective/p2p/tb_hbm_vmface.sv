`timescale 1ns/1fs
`default_nettype none
module vmface_vehicle #(parameter integer GOLD=0, RT=81, EXTRA=0, ASM_EXTRA=0, FACES=0)(
 input wire clk,rst_n,input wire [1535:0] inst,
 output wire [3:0] valid,output wire [131:0] meta,output wire [2047:0] payload,
 output wire [23:0] select_core,output wire [135:0] request_core,output wire fault);
 wire [135:0] rq_inner,rq;
 wire [7:0] rv_inner,rv;
 wire [2055:0] rr;
 wire [131:0] meta_inner;wire [3:0] valid_inner;
 wire [23:0] sel_inner,sel;
 assign request_core=rq_inner;assign select_core=sel_inner;
 generate if(GOLD)begin:g_old
  ot_hgi_coll_q_static_ctl_v5_gold #(.NPT(3),.SOLO(1),.INJLAT(12),.VM_RT(RT)) u(
   .clk_control(clk),.rst_n(rst_n),.inst(inst),.m_idx(16'd0),.m_vm(16'd0),
   .m_iaddr_l(32'd0),.m_del_l(32'd0),.m_rgx_l(32'd0),.m_iaddr_h(16'd0),.m_del_h(16'd0),.m_rgx_h(16'd0),
   .m_lk_l(24'd0),.m_lk_h(24'd0),.hgi_start(1'b0),.hgi_busy(1'b0),.issue_done(1'b0),.tkm_done(1'b0),.tkm_busy(1'b0),
   .dest_v(16'd0),.rc_v(1'b0),.rc_tag(3'd0),.vm_rv(rv),.vm_req_pin(rq_inner),.vm_source_meta(meta_inner),
   .vm_assembled_v(valid_inner),.protocol_fault(fault),.vm_sel_d(sel_inner));
 end else begin:g_new
  ot_hgi_coll_q_static_ctl_v5 #(.NPT(3),.SOLO(1),.INJLAT(12),.VM_RT(RT),.VM_FACE_RT(EXTRA),.VM_ASM_FACE_RT(ASM_EXTRA)) u(
   .clk_control(clk),.rst_n(rst_n),.inst(inst),.m_idx(16'd0),.m_vm(16'd0),
   .m_iaddr_l(32'd0),.m_del_l(32'd0),.m_rgx_l(32'd0),.m_iaddr_h(16'd0),.m_del_h(16'd0),.m_rgx_h(16'd0),
   .m_lk_l(24'd0),.m_lk_h(24'd0),.hgi_start(1'b0),.hgi_busy(1'b0),.issue_done(1'b0),.tkm_done(1'b0),.tkm_busy(1'b0),
   .dest_v(16'd0),.rc_v(1'b0),.rc_tag(3'd0),.vm_rv(rv),.vm_req_pin(rq_inner),.vm_source_meta(meta_inner),
   .vm_assembled_v(valid_inner),.protocol_fault(fault),.vm_sel_d(sel_inner));
 end endgenerate
 // Every physical boundary retains its real input/output register.
 generate if(FACES)begin:g_faces
  reg [135:0] rq_q;reg [7:0] rv_q;reg [23:0] sel_b,sel_v;
  always@(posedge clk)begin rq_q<=rq_inner;rv_q<=rv_inner;sel_b<=sel_inner;sel_v<=sel_b;end
  assign rq=rq_q;assign rv=rv_q;assign sel=sel_v;
 end else begin:g_direct assign rq=rq_inner;assign rv=rv_inner;assign sel=sel_inner;end endgenerate
 function automatic [255:0] word(input integer bank,input [15:0] sector);
  reg[255:0] w;for(integer k=0;k<8;k++)w[k*32+:32]=32'h9e3779b9*(32'(sector)*16+32'(bank)*2+32'(k)+1)^32'h5bd1e995;
  return w;
 endfunction
 // Physical memory latency stays81 in every vehicle, including the global-RT83 mutant.
 localparam integer DEPTH=7+81;
 reg [256:0] pipe[0:7][0:DEPTH-1];reg[256:0] rr_q[0:7];
 always@(posedge clk)for(integer b=0;b<8;b++)begin
  if(!rst_n)begin rr_q[b]<=0;for(integer d=0;d<DEPTH;d++)pipe[b][d]<=0;end
  else begin
   pipe[b][0]<=rq[b*17+16]?{1'b1,word(b,rq[b*17+:16])}:257'd0;
   for(integer d=1;d<DEPTH;d++)pipe[b][d]<=pipe[b][d-1];
   rr_q[b]<=pipe[b][DEPTH-2];
  end
 end
 for(genvar b=0;b<8;b++)begin:g_return assign rr[b*257+:257]=rr_q[b];assign rv_inner[b]=rr_q[b][256];end
 wire[2047:0] rd_il,rd,as_il,assembled;
 for(genvar b=0;b<8;b++)for(genvar i=0;i<256;i++)begin:g_split assign rd_il[i*8+b]=rr[b*257+i];end
 generate if(FACES)begin:g_vm_input reg[2047:0] rd_q;always@(posedge clk)rd_q<=rd_il;assign rd=rd_q;
 end else begin:g_vm_direct assign rd=rd_il;end endgenerate
 ot_hgi_coll_vmasm_sliced_v7 u_asm(.clk({16{clk}}),.sel(sel),.rd_il(rd),.as_il(as_il));
 for(genvar j=0;j<4;j++)for(genvar i=0;i<256;i++)begin:g_assembled
  assign assembled[j*512+i]=as_il[i*8+2*j];assign assembled[j*512+256+i]=as_il[i*8+2*j+1];
 end
 generate if(FACES)begin:g_endpoints
  reg[2047:0] data_v,data_b;
  always@(posedge clk)begin
   data_v<=assembled;data_b<=data_v;
  end
  assign payload=data_b;assign meta=meta_inner;assign valid=valid_inner;
 end else begin:g_outputs assign payload=assembled;assign meta=meta_inner;assign valid=valid_inner;end endgenerate
endmodule

module tb_hbm_vmface;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0;reg[1535:0]inst=0;
 wire[3:0]gv,dv,fv,mv,hv;wire[131:0]gm,dm,fm,mm,hm;
 wire[2047:0]gd,dd,fd,md,hd;wire[23:0]gs,ds,fs,ms,hs;wire[135:0]gr,dr,fr,mr,hr;
 wire gf,df,ff,mf,hf;
 vmface_vehicle #(.GOLD(1)) gold(clk,rst_n,inst,gv,gm,gd,gs,gr,gf);
 vmface_vehicle defaults(clk,rst_n,inst,dv,dm,dd,ds,dr,df);
 vmface_vehicle #(.EXTRA(2),.ASM_EXTRA(2),.FACES(1)) faces(clk,rst_n,inst,fv,fm,fd,fs,fr,ff);
 vmface_vehicle #(.FACES(1)) missing(clk,rst_n,inst,mv,mm,md,ms,mr,mf);
 vmface_vehicle #(.RT(83),.FACES(1)) global_rt(clk,rst_n,inst,hv,hm,hd,hs,hr,hf);
 reg[3:0]gvd[0:3];reg[131:0]gmd[0:3];reg[2047:0]gdd[0:3];
 always@(posedge clk)begin
  gvd[0]<=rst_n?gv:4'd0;gmd[0]<=gm;gdd[0]<=gd;
  for(integer i=1;i<4;i++)begin gvd[i]<=rst_n?gvd[i-1]:4'd0;gmd[i]<=gmd[i-1];gdd[i]<=gdd[i-1];end
 end
 integer cycles=0,age=0,checks=0,outputs=0,default_errors=0,face_errors=0,missing_errors=0,global_errors=0,resets=0;
 always@(negedge clk)begin
  cycles++;
  if(!rst_n)age=0;else age++;
  if(rst_n&&age>120)begin
   checks++;
   if(gf||df||dv!==gv||ds!==gs||dr!==gr||(gv&&(dm!==gm||dd!==gd)))default_errors++;
   if(ff||fv!==gvd[3]||fs!==gs||fr!==gr||(fv&&(fm!==gmd[3]||fd!==gdd[3])))begin
    if(face_errors<5)$display("FACE_MISMATCH cycle%0d valid%h/%h fault%0d payload_equal%0d meta_equal%0d",cycles,fv,gvd[3],ff,fd===gdd[3],fm===gmd[3]);
    face_errors++;
   end
   if(mf||mv!==gvd[3]||(mv&&(mm!==gmd[3]||md!==gdd[3])))missing_errors++;
   if(hf||hv!==gvd[3]||(hv&&(hm!==gmd[3]||hd!==gdd[3])))global_errors++;
   if(fv)outputs++;
  end
 end
 initial begin
  repeat(4)@(negedge clk);
  for(integer epoch=0;epoch<3;epoch++)begin
   rst_n=0;inst=0;resets++;repeat(6)@(negedge clk);rst_n=1;
   for(integer t=0;t<650;t++)begin
    inst=0;
    if(($urandom%4)!=0)begin
     integer perm[0:7];reg[131:0]m;
     for(integer b=0;b<8;b++)perm[b]=b;
     for(integer b=7;b>0;b--)begin integer q,x;q=$urandom%(b+1);x=perm[b];perm[b]=perm[q];perm[q]=x;end
     m={$urandom,$urandom,$urandom,$urandom,$urandom};inst[1170+:132]=m;
     for(integer b=0;b<8;b++)inst[1034+17*b+:17]={1'b1,16'($urandom)};
     for(integer j=0;j<4;j++)inst[1383+6*j+:6]={3'(perm[2*j+1]),3'(perm[2*j])};
    end
    @(negedge clk);
   end
   inst=0;repeat(130)@(negedge clk);
  end
  $display("VMFACE_SUMMARY checks%0d outputs%0d resets%0d default_errors%0d face_errors%0d missing_errors%0d global_errors%0d",checks,outputs,resets,default_errors,face_errors,missing_errors,global_errors);
  if(default_errors||face_errors||!outputs||!missing_errors||!global_errors)$fatal(1,"VMFACE_MITER_FAIL");
  $display("VMFACE_MITER_PASS exact_default physical4endpointedges select0extra missing_contract_CAUGHT global_RT83_CAUGHT");$finish;
 end
endmodule
`default_nettype wire
