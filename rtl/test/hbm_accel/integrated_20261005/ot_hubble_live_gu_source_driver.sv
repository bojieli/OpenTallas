`timescale 1ns/1ps
// Private minimum full-shape driver. Its immutable source images contain only
// released weights/real activation quantization. Expected files compare only.
module ot_hubble_live_gu_source_driver #(parameter integer ENABLE=0)(
 input wire clk,rst_n,start,permit,retire,input wire [72:0] frame,
 input wire [31:0] op_a,op_b,input wire [6:0] issue_index,
 output wire [2047:0] g,u,output wire ready,quiet,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(ENABLE==0)begin:g_off
  assign g=0;assign u=0;assign ready=0;assign quiet=1;assign fault=0;
 end else begin:g_on
  reg im_we=0,launch=0,capture_start=0,finished=0,started=0;
  reg [12:0] im_addr=0;reg [63:0] im_data=0;
  reg [71:0] context_code[0:2],response_code[0:1],response_data_code[0:3],stores[0:5];
  wire [65:0] cc0=decode64(context_code[0]),cc1=decode64(context_code[1]),cc2=decode64(context_code[2]);
  wire [191:0] cx={cc2[63:0],cc1[63:0],cc0[63:0]};
  wire context_bad=cc0[65]||cc1[65]||cc2[65]||cx[191:181]!=0;
  wire [65:0] rc0=decode64(response_code[0]),rc1=decode64(response_code[1]);
  wire [127:0] rx={rc1[63:0],rc0[63:0]};
  // {padding4,busy1,bulk1,we1,addr32,tag16,FRAME73} =128 bits.
  wire response_busy=rx[123],response_bulk=rx[122],response_we=rx[121];
  wire [15:0] response_tag=rx[88:73];wire [31:0] response_addr=rx[120:89];
  wire response_bad=rc0[65]||rc1[65]||rx[127:124]!=0||
   (response_busy&&(!permit||rx[72:0]!=frame));
  wire [65:0] rd0=decode64(response_data_code[0]),rd1=decode64(response_data_code[1]),
              rd2=decode64(response_data_code[2]),rd3=decode64(response_data_code[3]);
  wire [255:0] response_data={rd3[63:0],rd2[63:0],rd1[63:0],rd0[63:0]};
  wire response_data_bad=rd0[65]||rd1[65]||rd2[65]||rd3[65];
  wire lv,lr,lwe,tv,tr,lrsp_r,trsp_r,sm_done,sm_fault,sm_busy,gv,terminal;
  wire [31:0] la,ls,ta;wire [255:0] ld;wire [15:0] lt,tt;
  wire [2047:0] bf16;wire [8:0] ex,cn;wire mx;
  wire gu_retained,gu_ce,gu_due,gu_warm_ack;
  wire [11:0] rb;wire [7:0] first,sid,did;wire [72:0] gf;wire [31:0] go;
  wire cap_accept,cap_fault;
  integer cycle=0,span=0,exports=0,store_rows=0,store_acks=0,held=0,source_requests=0,ce_edges=0;
  reg memory_fault=0;
  wire capture_window=cycle%7>=2;
  wire export_match=!context_bad&&ex==cx[29:21]&&mx==cx[30]&&rb==cx[42:31]&&
   first==cx[50:43]&&cn==cx[59:51]&&gf==cx[132:60]&&go==cx[164:133]&&sid==cx[172:165]&&did==cx[180:173];
  ot_hubble_live_gu_capture #(.ENABLE(1)) capture(
   .clk(clk),.rst_n(rst_n),.start(capture_start),.permit(permit),.frame(frame),.op_a(op_a),.op_b(op_b),
   .span_v(gv&&capture_window&&export_match),.span_bf16(bf16),.expert(ex),.matrix(mx),.row_base(rb),
   .lane_first(first),.count(cn),.source_sm(sid),.source_die(did),.span_frame(gf),.span_op(go),
   .span_accept(cap_accept),.source_finished(finished),.retire(retire),.issue_index(issue_index),
   .g(g),.u(u),.ready(ready),.fault(cap_fault));
  wire accept=gv&&cap_accept&&capture_window&&export_match&&!gu_ce&&!gu_due;
  wire response_ok=response_busy&&!response_bad&&!response_data_bad;
  assign lr=!response_busy&&permit&&!context_bad&&!memory_fault;
  assign tr=lr&&!lv; // one finite protected seat; LSU priority, no tag dictionary
  wire response_take=response_ok&&(response_bulk?trsp_r:lrsp_r);
  assign quiet=!response_busy&&!sm_busy&&!launch&&!gu_retained&&!gu_ce&&!gu_due&&(!started||finished);
  assign fault=sm_fault||cap_fault||memory_fault||context_bad||response_bad||
    (response_busy&&response_data_bad)||(gv&&!export_match)||gu_due||gu_warm_ack;
  ot_hbm_accel_simt_sm #(.ENABLE(1),.GU_JOIN(1),.NL(128),.NV(16),.SMEM_WORDS(64),
   .MAXO(32),.TC_SUB(1),.TC_LS(1),.TC_XDEPTH(8),.TC_RMAX(16),.TC_LEV(4),
   .BC_DEPTH(8),.BC_MAXOUT(4),.HAS_BD(1),.BD_XDEPTH(32)) producer(
   .clk(clk),.rst_n(rst_n),.sm_id(cx[172:165]),.die_id(cx[180:173]),
   .im_we(im_we),.im_addr(im_addr),.im_data(im_data),.launch_v(launch),.launch_pc(32'd0),
   .launch_token(frame[51:36]),.launch_pos(frame[68:53]),.sm_done(sm_done),.sm_fault(sm_fault),
   .busy(sm_busy),.res_v(),.res_data(),.bar_arrive(),.bar_release(1'b0),
   .lreq_v(lv),.lreq_rdy(lr),.lreq_we(lwe),.lreq_addr(la),.lreq_wdata(ld),.lreq_wstrb(ls),.lreq_tag(lt),
   .lrsp_v(response_ok&&!response_bulk),.lrsp_rdy(lrsp_r),.lrsp_we(response_we),
   .lrsp_tag(response_tag),.lrsp_data(response_data),
   .treq_v(tv),.treq_rdy(tr),.treq_addr(ta),.treq_tag(tt),
   .trsp_v(response_ok&&response_bulk),.trsp_rdy(trsp_r),.trsp_tag(response_tag),.trsp_data(response_data),
   .coll_req_v(),.coll_req_rdy(1'b0),.coll_mode(),.coll_count(),.coll_data(),
   .coll_rsp_v(1'b0),.coll_rsp_rdy(),.coll_rsp_data(4096'd0),
   .coll_x(),.coll_off(),.coll_nown(),.coll_fuse(),.coll_resid(),.coll_rsp_ss(32'd0),.coll_rsp_err(1'b0),
   .gu_join_launch(1'b1),.gu_join_owner_valid(permit&&!context_bad),
   .gu_join_pc({19'd0,cx[12:0]}),.gu_join_src(cx[20:13]),.gu_join_expert(cx[29:21]),
   .gu_join_matrix(cx[30]),.gu_join_row_base(cx[42:31]),.gu_join_lane_first(cx[50:43]),
   .gu_join_count(cx[59:51]),.gu_join_frame(frame),.gu_join_op(cx[164:133]),
   .gu_join_v(gv),.gu_join_accept(accept),.gu_join_bf16(bf16),
   .gu_join_out_expert(ex),.gu_join_out_matrix(mx),.gu_join_out_row_base(rb),
   .gu_join_out_lane_first(first),.gu_join_out_count(cn),.gu_join_out_frame(gf),.gu_join_out_op(go),
   .gu_join_out_sm(sid),.gu_join_out_die(did),.gu_join_terminal(terminal),
   // This minimum CP caller has only root POR, no warm-reset command.
   // An unsolicited ack is a fault; retained/CE/DUE all block quiet/release.
   .gu_join_warm_reset_req(1'b0),.gu_join_warm_reset_ack(gu_warm_ack),
   .gu_join_retained(gu_retained),.gu_join_ce(gu_ce),.gu_join_due(gu_due),
   .st_instr(),.st_cycles(),.st_stall_mem(),.st_tc_rows());
  // These arrays model the frozen released input ROM service, not another
  // hardware payload queue. The actual rounded stores use protected memory.
  reg [255:0] codes[0:767],exponents[0:23],weights[0:2591];
  reg [63:0] program_words[0:177];reg [31:0] descriptors[0:4607],expected[0:9215];
  string directory,path;reg [191:0] launch_context;
  reg [127:0] new_response;reg [255:0] new_data;
  reg [65:0] decoded_store;reg [63:0] store_word;
  integer i,b,address,base,row,bank;
  always @(posedge clk)if(rst_n)begin
   cycle<=cycle+1;
   if(gu_ce)ce_edges<=ce_edges+1;
   if(gv&&!accept)held<=held+1;
   if(gv&&accept)begin
    exports<=exports+1;
    for(integer r=0;r<12;r=r+1)
     if(bf16[r*16+:16]!==expected[((ex==65?2:0)+integer'(mx))*2304+integer'(rb)+r][31:16])
      $fatal(1,"actual TC/CVT GU mismatch span=%0d row=%0d",span,r);
    $display("ACTUAL_GU_EXPORT span=%0d cycle=%0d expert=%0d matrix=%0d row=%0d count=%0d held=%0d",span,cycle,ex,mx,rb,cn,held);
   end
   if(response_take)begin
    response_code[0]<=encode64(0);response_code[1]<=encode64(0);
    if(response_we)store_acks<=store_acks+1;
   end
   if((lv&&lr)||(tv&&tr))begin
    address=integer'(lv?la:ta);new_data=0;
    new_response={4'd0,1'b1,!lv,lv&&lwe,32'(address),lv?lt:tt,frame};
    if((address&31)!=0)$fatal(1,"unaligned GU source address");
    if(lv&&lwe)begin
     if(address!=32'h30000&&address!=32'h30020)$fatal(1,"GU store range");
     if(ls!==(address==32'h30000 ? 32'hffffffff : 32'h0000ffff))$fatal(1,"missing/extra GU store bytes");
     base=(address-32'h30000)/8;
     for(i=0;i<4;i=i+1)if(base+i<6)begin
      decoded_store=decode64(stores[base+i]);if(decoded_store[65])$fatal(1,"GU store memory UE");
      store_word=decoded_store[63:0];
      for(b=0;b<8;b=b+1)if(ls[i*8+b])store_word[b*8+:8]=ld[(i*8+b)*8+:8];
      stores[base+i]<=encode64(store_word);
     end
     bank=(integer'(cx[29:21])==65?2:0)+integer'(cx[30]);
     for(i=0;i<8;i=i+1)if(ls[i*4+:4]!=0)begin
      row=(address-32'h30000)/4+i;
      if(row>=12||ls[i*4+:4]!=4'hf||ld[i*32+:32]!==expected[bank*2304+integer'(cx[42:31])+row])
       $fatal(1,"actual acknowledged GU rounded store mismatch span=%0d row=%0d",span,row);
     end
     store_rows<=store_rows+(address==32'h30000 ? 8 : 4);
    end else if(lv&&address>=32'h1000&&address<32'h7000)new_data=codes[(address-32'h1000)/32];
    else if(lv&&address>=32'h8000&&address<32'h8300)new_data=exponents[(address-32'h8000)/32];
    else if(!lv&&address>=32'h100000&&address<32'h114400)new_data=weights[(address-32'h100000)/32];
    else $fatal(1,"GU source port/address mismatch address=%h bulk=%0d",address,!lv);
    response_code[0]<=encode64(new_response[63:0]);response_code[1]<=encode64(new_response[127:64]);
    for(i=0;i<4;i=i+1)response_data_code[i]<=encode64(new_data[i*64+:64]);
    source_requests<=source_requests+1;
   end
   if(fault)$fatal(1,"live GU caller/capture fault span=%0d cycle=%0d",span,cycle);
  end
  initial begin : enroll_released_source
   reg [65:0] checked_store; integer checked_bank;
   for(i=0;i<3;i=i+1)context_code[i]=encode64(0);
   for(i=0;i<2;i=i+1)response_code[i]=encode64(0);
   for(i=0;i<4;i=i+1)response_data_code[i]=encode64(0);
   for(i=0;i<6;i=i+1)stores[i]=encode64(0);
   if(!$value$plusargs("LIVE_GU_DIR=%s",directory))$fatal(1,"full released GU images required");
   $readmemh({directory,"/kernel.hex"},program_words);
   $readmemh({directory,"/descriptors.hex"},descriptors);
   $readmemh({directory,"/expected_bf16.hex"},expected);
   $readmemh({directory,"/code_sectors.hex"},codes);
   $readmemh({directory,"/exponent_sectors.hex"},exponents);
   wait(start&&rst_n&&permit);started=1;
   @(negedge clk);capture_start=1;@(negedge clk);capture_start=0;
   for(integer p=0;p<178;p=p+1)begin
    im_we=1;im_addr=13'(p);im_data=program_words[p];@(negedge clk);
   end
   im_we=0;
   for(span=0;span<768;span=span+1)begin
    if(!permit||response_busy||sm_busy||gu_retained||gu_ce||gu_due)$fatal(1,"GU image replacement before protected drain");
    path=$sformatf("%s/weights/span%03d.hex",directory,span);$readmemh(path,weights);
    launch_context=0;
    launch_context[12:0]=13'd173;launch_context[20:13]=8'd3;
    launch_context[29:21]=9'(descriptors[span*6]);launch_context[30]=descriptors[span*6+1][0];
    launch_context[42:31]=12'(descriptors[span*6+2]);launch_context[59:51]=9'd12;
    launch_context[132:60]=frame;launch_context[164:133]=descriptors[span*6+5]==0?op_a:op_b;
    launch_context[172:165]=8'(descriptors[span*6+3]);launch_context[180:173]=8'(descriptors[span*6+4]);
    for(integer c=0;c<3;c=c+1)context_code[c]=encode64(launch_context[c*64+:64]);
    @(negedge clk);launch=1;@(negedge clk);launch=0;
    // The coded terminal persists through a late CE after sm_done. Completion
    // is observed only after scrub/recheck and genuine native/export drain.
    wait((terminal&&!gu_retained&&!gu_ce&&!gu_due)||sm_fault||gu_due);@(negedge clk);
    if(sm_fault||gu_due||gu_ce||gu_retained||!terminal||response_busy||sm_busy)
     $fatal(1,"GU coded terminal lacks real store/export drain span=%0d",span);
    checked_bank=(integer'(cx[29:21])==65?2:0)+integer'(cx[30]);
    for(integer c=0;c<6;c=c+1)begin
     checked_store=decode64(stores[c]);
     if(checked_store[65]||checked_store[31:0]!==expected[checked_bank*2304+integer'(cx[42:31])+2*c]||
        checked_store[63:32]!==expected[checked_bank*2304+integer'(cx[42:31])+2*c+1])
      $fatal(1,"GU actual stored payload/SECDED mismatch span=%0d word=%0d",span,c);
    end
    @(negedge clk);
   end
   if(exports!=768||store_rows!=9216||store_acks!=1536||source_requests!=2600448)
    $fatal(1,"GU exact span/source/store/ack counts %0d %0d %0d %0d",exports,store_rows,store_acks,source_requests);
   finished=1;wait(ready);
   $display("PASS_LIVE_TC_PROTECTED_GU_CAPTURE rows=9216 spans=768 stores=%0d ACK=%0d held=%0d CEedges=%0d metadata_useful=188 metadata_coded=216 cycles=%0d",store_rows,store_acks,held,ce_edges,cycle);
  end
 end endgenerate
endmodule
