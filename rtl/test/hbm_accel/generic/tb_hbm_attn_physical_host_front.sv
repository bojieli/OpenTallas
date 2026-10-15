`timescale 1ns/1ps
module tb_hbm_attn_physical_host_front;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,iv=0;reg[222:0]instruction=0;wire[135:0]rq;wire[2055:0]rr;
 wire[6:0]events;wire[9:0]phase;wire valid,pv,qv,fault;wire[15:0]rows;wire[8191:0]q;
    reg s_awvalid=0,s_wvalid=0,s_arvalid=0;
    reg [11:0] s_awaddr=0,s_araddr=0;
    reg [31:0] s_wdata=0;
    wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;
    wire [31:0] s_rdata;
    wire c_awvalid,c_awready,c_wvalid,c_wready,c_bvalid,c_arvalid,c_arready,c_rvalid,c_bready,c_rready;
    wire [11:0] c_awaddr,c_araddr;
    wire [31:0] c_wdata,c_rdata;
    wire [3:0] c_wstrb;
    wire [459:0] lcp_full;
    wire [418:0] lcp=lcp_full[418:0];
    wire loader_fault,host_fault;
    wire [3:0] cfg_we,start_v,program_active,program_done,program_fault;
    wire [39:0] cfg_addr,start_base;
    wire [43:0] start_limit;
    wire [63:0] start_loops;
    wire [1023:0] cfg_data;
    wire [3:0] calendar_v;
    wire [4*202-1:0] calendar;
    wire [127:0] ordinal;
    wire ext_cfg_v,ext_desc_v,ext_launch_v;
    wire [7:0] ext_target;
    wire [11:0] ext_cfg_addr,ext_base;
    wire [255:0] ext_cfg_data;
    wire [12:0] ext_limit;
    wire [15:0] ext_loops;
    ot_vms_calendar_host_static host(
        .clk(clk),.rst_n(rst_n),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(4'hf),
        .s_bvalid(s_bvalid),.s_bready(1'b1),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
        .s_rvalid(s_rvalid),.s_rready(1'b1),.s_rdata(s_rdata),
        .c_awvalid(c_awvalid),.c_awready(c_awready),.c_awaddr(c_awaddr),
        .c_wvalid(c_wvalid),.c_wready(c_wready),.c_wdata(c_wdata),.c_wstrb(c_wstrb),
        .c_bvalid(c_bvalid),.c_bready(c_bready),.c_arvalid(c_arvalid),.c_arready(c_arready),.c_araddr(c_araddr),
        .c_rvalid(c_rvalid),.c_rready(c_rready),.c_rdata(c_rdata),.lcp_doorbell(lcp[71]),
        .program_active(program_active),.program_done(program_done),.program_fault(program_fault),
        .cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),
        .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .ext_cfg_v(ext_cfg_v),.ext_target(ext_target),.ext_cfg_addr(ext_cfg_addr),.ext_cfg_data(ext_cfg_data),
        .ext_desc_v(ext_desc_v),.ext_base(ext_base),.ext_limit(ext_limit),.ext_loops(ext_loops),.ext_launch_v(ext_launch_v),
        .fault(host_fault));
    // The actual existing loader/CP producer, rather than an idealized LCP pulse.
    ot_hgi_loader_cp #(.MTPH(1)) loader(
        .clk(clk),.rst_n(rst_n),.s_awvalid(c_awvalid),.s_awready(c_awready),.s_awaddr(c_awaddr),
        .s_wvalid(c_wvalid),.s_wready(c_wready),.s_wdata(c_wdata),.s_wstrb(c_wstrb),
        .s_bvalid(c_bvalid),.s_bready(c_bready),.s_arvalid(c_arvalid),.s_arready(c_arready),.s_araddr(c_araddr),
        .s_rvalid(c_rvalid),.s_rready(c_rready),.s_rdata(c_rdata),
        .c_awvalid(),.c_awready(1'b1),.c_awaddr(),.c_wvalid(),.c_wready(1'b1),.c_wdata(),.c_wstrb(),
        .c_bvalid(1'b0),.c_bready(),.c_arvalid(),.c_arready(1'b1),.c_araddr(),
        .c_rvalid(1'b0),.c_rready(),.c_rdata(32'd0),.lcp(lcp_full),.cpl(230'd0),
        .m_req_v(),.m_req_rdy(1'b1),.m_req_addr(),.m_req_len(),.m_rsp_v(1'b0),.m_rsp_data(256'd0),.fault(loader_fault));
    wire[7:0]ne_rslot_v,ne_wslot_v;wire[23:0]ne_rslot,ne_wslot;
    genvar Q;
    generate for(Q=0;Q<4;Q=Q+1)begin:g_programme
      if(Q==3)begin:actual_NE
       hfd_hgi_vm_calendar_NE prog(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we[Q]),.cfg_addr(cfg_addr[Q*10+:10]),.cfg_data(cfg_data[Q*256+:256]),
        .start_v(start_v[Q]),.start_base(start_base[Q*10+:10]),.start_limit(start_limit[Q*11+:11]),.start_loops(start_loops[Q*16+:16]),
        .calendar_v(calendar_v[Q]),.active(program_active[Q]),.done(program_done[Q]),.fault(program_fault[Q]),
        .rslot_v(ne_rslot_v),.rslot(ne_rslot),.wslot_v(ne_wslot_v),.wslot(ne_wslot));
      end else begin:idle_other_quadrants
       ot_vms_calendar_static #(.W(202))prog(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we[Q]),.cfg_addr(cfg_addr[Q*10+:10]),.cfg_data(cfg_data[Q*256+:256]),
        .start_v(start_v[Q]),.start_base(start_base[Q*10+:10]),.start_limit(start_limit[Q*11+:11]),.start_loops(start_loops[Q*16+:16]),
        .calendar(),.calendar_v(calendar_v[Q]),.ordinal(),.active(program_active[Q]),.done(program_done[Q]),.fault(program_fault[Q]));
      end
    end endgenerate
    wire att_active,att_done;
    ot_hbm_attn_physical_host_program_front dut(.clk(clk),.rst_n(rst_n),
      .cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
      .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
      .active(att_active),.done(att_done),.fault(fault),.query_rq(rq),.query_rr(rr),.events(events),.phase(phase),.event_valid(valid),
      .rows(rows),.pv_only(pv),.q_words(q),.q_present(qv));
 reg preload=1;reg[2247:0]pwq=0;wire[143:0]status;
 for(genvar b=0;b<8;b=b+1)begin:banks
  wire[7*17-1:0]arq={51'd0,(preload?17'd0:rq[b*17+:17]),51'd0};
  wire[3*281-1:0]awq={562'd0,(preload?pwq[b*281+:281]:281'd0)};
  wire[7*257-1:0]arr;
  ot_vms_bank_static #(.RG(7),.WG(3))bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(!preload&&ne_rslot_v[b]),.rslot(ne_rslot[b*3+:3]),.wslot_v(preload&&pwq[b*281+280]),.wslot(3'd0),
   .rq(arq),.rr(arr),.wq(awq),.wq_done(),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
   .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]));
  assign rr[b*257+:257]=arr[3*257+:257];
 end
 function automatic[15:0]word(input integer ep,h,e);word=16'h3b00+16'(ep*4096+h*131+e*3);endfunction
 reg[222:0]cfg[0:511],outer[0:255],necal[0:899];reg[6:0]cal[0:511];integer mut=0,profile=0,selected_profile=0,checked=0,heads=0,seen=0,eventcycles=0;
 integer ep,h,s,b,w,i;string dir,fn;reg active=0;
 always @(posedge clk)if(active)begin
  if(fault||host_fault||loader_fault||(|program_fault))$fatal(1,"ATT_FRONT source/calendar fault");
  for(integer bb=0;bb<8;bb++)if(!preload&&rq[bb*17+16]&&(ne_rslot_v[bb]!=1||ne_rslot[bb*3+:3]!=3))$fatal(1,"ATT_FRONT actual NE calendar/request mismatch");
  for(integer bb=0;bb<8;bb++)if(status[bb*18+17])$fatal(1,"ATT_FRONT bank fault");
  if(valid)begin
   if(events!==cal[phase])$fatal(1,"ATT_FRONT wrong actual event profile/phase%0d",phase);
   eventcycles++;
   if(events[1])begin
    if(!qv)$fatal(1,"ATT_FRONT missing actual query SRAM head");
    for(integer ee=0;ee<512;ee++)begin
     if(q[ee*16+:16]!==word(profile/2,heads,ee))$fatal(1,"ATT_FRONT query payload mismatch profile%0d head%0d elem%0d",profile,heads,ee);
     checked++;
    end
    heads++;
   end
   if(events[0])seen++;
  end
 end

 task automatic write32(input[11:0]addr,input[31:0]data_);
 begin
  @(negedge clk);s_awaddr=addr;s_wdata=data_;s_awvalid=1;s_wvalid=1;
  #1;while(!s_awready||!s_wready)begin @(negedge clk);#1;end
  @(posedge clk);#1;@(negedge clk);s_awvalid=0;s_wvalid=0;@(negedge clk);
 end
 endtask
 reg[255:0]word_;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");void'($value$plusargs("MUT=%d",mut));void'($value$plusargs("PROFILE=%d",selected_profile));
  repeat(8)@(negedge clk);rst_n=1;
  for(ep=0;ep<2;ep++)for(h=0;h<16;h++)for(s=0;s<8;s++)begin
   @(negedge clk);pwq=0;
   for(b=0;b<8;b++)begin pwq[b*281+:281]={1'b1,16'(ep*1024+h*64+s*8+b),256'd0,8'hff};
    for(w=0;w<8;w++)pwq[b*281+8+w*32+:32]={word(ep,h,s*64+b*8+w),16'd0};end
  end
  @(negedge clk);pwq=0;repeat(8)@(negedge clk);preload=0;
  $readmemh({dir,"/config.hex"},cfg);
  for(profile=selected_profile;profile<selected_profile+1;profile++)begin
   fn=$sformatf("%s/outer%0d.hex",dir,profile);$readmemh(fn,outer);fn=$sformatf("%s/event%0d.hex",dir,profile);$readmemh(fn,cal);
   fn=$sformatf("%s/ne%0d.hex",dir,profile);$readmemh(fn,necal);
   // Actual independently compiled NE programme selects RG3 at fixed absolute
   // bank edges. Other quadrants are explicitly isolated NOPs in this component.
   for(integer qq=0;qq<4;qq++)begin
    write32(12'hf00,32'(qq));
    for(integer pc=0;pc<(qq==3?900:1);pc++)begin
     word_=0;word_[255:240]=16'hc7a1;word_[233:224]=10'(pc);
     if(qq==3)word_[222:0]=necal[pc];
     if(mut==3&&qq==3&&pc==343)word_[41]=~word_[41];
     for(integer ww=0;ww<8;ww++)write32(12'hf04,word_[ww*32+:32]);
    end
    write32(12'hf08,32'((qq==3?900:1)<<10));write32(12'hf0c,1);
   end
   heads=0;seen=0;active=1;
   write32(12'hf20,49);
   for(i=0;i<339+(profile%2?1:138);i++)begin
    word_=0;word_[255:240]=16'hc7a1;word_[233:224]=10'(i);
    word_[222:0]=(i<339)?cfg[i]:outer[i-339];
    if(mut==1&&i==0)word_[100]=1;
    if(mut==2&&i==476)word_[5:4]=2'(profile^1);
    for(integer ww=0;ww<8;ww++)write32(12'hf24,word_[ww*32+:32]);
   end
   write32(12'hf28,32'((339+(profile%2?1:138))<<12));write32(12'hf2c,1);
   write32(12'hc10,1);
   repeat(1000)@(negedge clk);
   if(seen!=1||heads!=(profile%2?0:16))$fatal(1,"ATT_FRONT event/head accounting profile%0d seen%0d heads%0d",profile,seen,heads);
   $display("ATT_FRONT_PROFILE PASS profile%0d heads%0d",profile,heads);active=0;
  end
  $display("PASS ATT_PHYSICAL_HOST_PROGRAM_QUERY_FRONT cold_boot_profiles=1 words=%0d event_cycles=%0d native_RG=3 native_RG_total=7 real_query_macros=64 actual_VM_macros=24 actual_programme_macros=6 real_AXI_loaderCP_target=49 actual_NE_programme_selectors=1",checked,eventcycles);$finish;
 end
endmodule
