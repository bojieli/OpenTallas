`timescale 1ns/1ps
// Bounded actual XR/rstop and real VP/SRAM cut; no die/PHY timing claim.
module tb_rd_pair;
 reg clk=0; always #0.416 clk=~clk;
 reg rst_n=0; reg aborting=0; wire rst_cut=(mut==11 && aborting)?1'b1:rst_n; integer cyc=0,mut=0,phase=0,errors=0,writes=0,expected=0,vcount=0,localcount=0;
 reg [1103:0] line[0:1]; wire [275:0] vo[0:1]; wire [275:0] vi[0:1];
 wire [2:0] cid[0:1]; wire [1103:0] cib[0:1];
 wire [4:0] cv[0:1],swv[0:1],lov[0:1]; wire [159:0] cd[0:1];
 wire [49:0] swa[0:1]; wire [39:0] swm[0:1]; wire [1279:0] swd[0:1],lod[0:1];
 wire [1:0] rf,xf; wire [2:0] pf;
 reg preload=0; reg [9:0] pa=0; reg [255:0] pd=0;
 reg [2:0] rv=0; reg [9:0] ra=0; wire [2:0] qv; wire [255:0] qd[0:2];
 integer vseen=0; reg [275:0] previous=0,lateword=0;
 always @(posedge clk) lateword <= (mut==8 && clean[0] && vseen==3)?clean:276'd0;
 wire [275:0] clean=vo[0];
 wire[1103:0] collide_rd=(1104'd1 | (1104'd4<<1) | (1104'd1<<4) | (1104'd32<<21) | (1104'd1<<37) | (1104'd448<<40) | (1104'd3<<50));
 reg [275:0] changed;
 always @* begin
   changed=clean;
   if (mut==1 && vseen==1) changed=0; // missing
   if (mut==2 && vseen==1) changed=previous; // duplicate/replace
   if (mut==3 && clean[0]) changed[7]=~changed[7]; // odd/wrong row
   if (mut==4 && clean[0]) changed[4]=~changed[4]; // wrong leaf
   if (mut==5 && clean[0]) changed[17]=~changed[17]; // payload
   if (mut==6 && clean[0]) changed[3:1]=0; // wrong type
   if (mut==7 && vseen==3) changed=0; // partial message
   if (mut==8 && vseen==3) changed=0;
   if (mut==8 && lateword[0]) changed=lateword;
 end
 assign vi[1]=changed; assign vi[0]=0;
 integer due[0:31]; integer ndue=0,read_seen=0,local_due=0;
 function automatic [255:0] pattern(input integer n);
   integer j; begin for(j=0;j<8;j=j+1) pattern[32*j+:32]=32'hc065a100^(n*32'h1010101)^(j*32'h183a71);end
 endfunction
 function automatic [1103:0] ctl(input integer sid,input integer target,input integer leafmask,input reg[159:0] body);
   reg[185:0] p; begin p=0;p[15:0]=16'd1<<sid;p[20:16]=target;p[25:21]=leafmask;p[185:26]=body;
   ctl=0;ctl[0]=1;ctl[8:4]=1;ctl[21+:186]=p;end
 endfunction
 task automatic tick(input integer n); repeat(n) @(negedge clk);endtask
 task automatic issue(input integer target,input integer leafmask,input reg[159:0] body);
  begin line[0]=ctl(4,target,leafmask,body);tick(1);line[0]=0;end
 endtask
 task automatic load;
  integer j; begin for(j=0;j<4;j=j+1) begin preload=1;pa=128+2*j;pd=pattern(j);tick(1);end preload=0;tick(12);end
 endtask
 task automatic send(input integer local_,input integer n,input integer row_);
  reg[159:0] cfg,cmd; begin
   cfg=0;cfg[3:0]=local_?0:4;cfg[6:4]=4;cfg[11:7]=1;cfg[27:12]=16'd1<<(local_?4:5);
   if(mut==10&&!local_)cfg[27:12]=16'd1<<4;
   cfg[30:28]=1;cfg[40:31]=row_;cfg[42:41]=n-1;cfg[44]=local_;
   issue(4,0,cfg);tick(8);cmd=6|(128<<4)|(n<<24);issue(0,1,cmd);
  end
 endtask
 task automatic readback(input integer vp,input integer n,input integer row_);
  integer j; begin
    for(j=0;j<n;j=j+1) begin rv=1<<vp;ra=row_+2*j;tick(1);rv=0;tick(8);end
  end
 endtask
 genvar k;
 generate for(k=0;k<2;k=k+1) begin:g
   wire de,dw,dv;wire[1103:0] e,w;wire[275:0] v;
   ot_s81sl_rstop r(.clk(clk),.rst_n(rst_cut),.sid(4+k),.ri_w((k==1&&mut==9&&clean[0])?collide_rd:line[k]),.ri_e(1104'd0),
     .vi(vi[k]),.vo(vo[k]),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_eo(173'd0),.nx_wo(173'd0),
     .dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(v),.ci_dir(cid[k]),.ci_b(cib[k]),.fault(rf[k]));
   ot_s81sl_xr x(.clk(clk),.rst_n(rst_cut),.sid(4+k),.dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(v),
     .ci_dir(cid[k]),.ci_b(cib[k]),.bi(1104'd0),.c_v(cv[k]),.c_d(cd[k]),.sw_v(swv[k]),.sw_a(swa[k]),.sw_m(swm[k]),.sw_d(swd[k]),
     .lo_v(lov[k]),.lo_d(lod[k]),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),
     .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(xf[k]));
 end endgenerate
 wire lv[0:2];wire[255:0] ld[0:2];
 assign lov[0]={3'd0,lv[1],lv[0]};assign lod[0]={768'd0,ld[1],ld[0]};
 assign lov[1]={3'd0,lv[2],1'b0};assign lod[1]={768'd0,ld[2],256'd0};
 generate for(k=0;k<3;k=k+1) begin:p
   localparam integer NODE=(k==2)?1:0,LEAF=(k==0)?0:1;
   ot_s81sl_vp u(.clk(clk),.rst_n(rst_cut),.c_v(cv[NODE][LEAF]),.c_d(cd[NODE]),
    .sw_v(k==0?preload:swv[NODE][LEAF]),.sw_a(k==0?pa:swa[NODE][10*LEAF+:10]),
    .sw_m(k==0?8'hff:swm[NODE][8*LEAF+:8]),.sw_d(k==0?pd:swd[NODE][256*LEAF+:256]),
    .cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),.lo_v(lv[k]),.lo_d(ld[k]),
    .x_rv(rv[k]),.x_ra(ra),.x_qv(qv[k]),.x_qd(qd[k]),.x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),
    .hq_v(1'b0),.hq_d(256'd0),.fault(pf[k]));
 end endgenerate
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(!rst_n && aborting && clean[0]) begin errors=errors+1;$display("RESET_ABORT_LEAK %0d",cyc);end
  if(rst_n) begin
   if(line[0][0])$display("CTL_PIN %0d %h",cyc,line[0]);
   if(cv[0][0])$display("SOURCE_VP_COMMAND %0d %h",cyc,cd[0]);
   if(lov[0][0])$display("SOURCE_VP_PAIR %0d %h",cyc,lod[0][0+:256]);
   if(phase==5&&clean[0])begin errors=errors+1;$display("POST_RESET_LEAK %0d",cyc);end
   if(clean[0]) begin
    if(ndue<32) begin due[ndue]=cyc+6;ndue=ndue+1;end
    $display("VPAIR %0d %0d %h",cyc,vseen,clean);previous<=clean;vseen<=vseen+1;
   end
   if(cib[0][0]&&cid[0]==0&&cib[0][3:1]==4) begin
    localcount=localcount+1;local_due=cyc+3;$display("LOCAL %0d",cyc);
   end
   if(phase==1&&swv[0][1]) begin
    if(swa[0][10+:10]!==320+2*writes||swd[0][256+:256]!==pattern(writes)||cyc!==local_due+writes) begin errors=errors+1;$display("LOCAL_DATA_FAIL %0d row%0d",cyc,swa[0][10+:10]);end
    $display("LOCAL_WRITE %0d %0d %h",cyc,swa[0][10+:10],swd[0][256+:256]);writes=writes+1;
   end
   if((phase==2||phase==3)&&swv[1][1]) begin
    if(swa[1][10+:10]!==((phase==2?448:464)+2*writes)||swd[1][256+:256]!==pattern(writes)||cyc!==due[writes]) begin
       errors=errors+1;$display("V_DATA_AGE_FAIL cyc%0d row%0d due%0d index%0d",cyc,swa[1][10+:10],due[writes],writes);end
    $display("WRITE %0d %0d %h",cyc,swa[1][10+:10],swd[1][256+:256]);writes=writes+1;
   end
   if(|qv) begin
    if(qv[1]&&qd[1]!==pattern(read_seen)) errors=errors+1;
    if(qv[2]&&qd[2]!==pattern(read_seen)) errors=errors+1;
    read_seen=read_seen+1;
   end
  end
 end
 initial begin
  line[0]=0;line[1]=0;void'($value$plusargs("MUT=%d",mut));
  tick(8);rst_n=1;tick(24);load();
  phase=1;writes=0;send(1,4,320);tick(70);
  if(writes!=4) begin errors=errors+1;$display("LOCAL_COUNT_FAIL %0d",writes);end
  read_seen=0;readback(1,4,320);if(read_seen!=4) errors=errors+1;
  phase=2;writes=0;ndue=0;vseen=0;send(0,4,448);tick(70);
  if(writes!=4) begin errors=errors+1;$display("V_COUNT_FAIL %0d",writes);end
  read_seen=0;readback(2,4,448);if(read_seen!=4) errors=errors+1;
  phase=3;writes=0;ndue=0;vseen=0;send(0,2,464);tick(70);
  if(writes!=2) errors=errors+1;
  read_seen=0;readback(2,2,464);if(read_seen!=2) errors=errors+1;
  // Reset is a deliberate fault-injection event, not a run-time scheduling wait.
  phase=4;send(0,4,480);
  wait(clean[0]);@(posedge clk);@(negedge clk);aborting=1;rst_n=0;
  tick(8);rst_n=1;phase=5;tick(32);aborting=0;
  load();phase=2;writes=0;ndue=0;vseen=0;send(0,4,448);tick(70);
  if(writes!=4)errors=errors+1;
  tick(10);if((|rf)||(|xf)||(|pf))begin errors=errors+1;$display("FAULT_FAIL r%h x%h p%h",rf,xf,pf);end
  $display("RDPAIR errors=%0d local_packets=%0d mut=%0d",errors,localcount,mut);
  if(errors==0) $display("PASS");else $display("FAIL");$finish;
 end
endmodule
