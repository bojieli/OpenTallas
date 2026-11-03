module ot_hgi_sfu_programme_store_r10 #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output reg programme_active,programme_done,
 output reg [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output reg io_active,io_done,
 output reg [31:0] io_ordinal,
 output wire [470:0] io_word,
 output wire [1741:0] compiler_control,
 output reg fault
);
 initial if(PAGE_AW!=1)$fatal(1,"programme store r10: PAGE_AW=1 only (2048-row stripes)");
 localparam integer NL=11;                        
  
 function automatic integer pred(input integer l);
  case(l) 1:pred=0; 2:pred=1; 4:pred=3; 5:pred=4; 7:pred=6; 9:pred=8; 10:pred=9; default:pred=-1; endcase
 endfunction
 function automatic integer depth(input integer l);
 
  
       

`line 93 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
   
   
  case(l) 0,3:depth=1; 7,9:depth=2; 1,4:depth=3; 10:depth=4; 2,5:depth=5; default:depth=0; endcase

`line 97 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 endfunction
  
 reg p_cfg_we,p_io_cfg_we,p_io_start_v;
 reg [2:0] p_cfg_stripe;
 reg [1:0] p_io_cfg_stripe;
 reg [AW-1:0] p_cfg_addr,p_io_cfg_addr,p_start_base,p_io_start_base;
 reg [255:0] p_cfg_data,p_io_cfg_data;
 reg [AW:0] p_start_limit,p_io_start_limit;
 reg [15:0] p_start_loops,p_io_start_loops;
 always @(posedge clk)begin
  p_cfg_we<=cfg_we;p_io_cfg_we<=io_cfg_we;p_io_start_v<=io_start_v;
  p_cfg_stripe<=cfg_stripe;p_cfg_addr<=cfg_addr;p_cfg_data<=cfg_data;
  p_start_base<=start_base;p_start_limit<=start_limit;p_start_loops<=start_loops;
  p_io_cfg_stripe<=io_cfg_stripe;p_io_cfg_addr<=io_cfg_addr;p_io_cfg_data<=io_cfg_data;
  p_io_start_base<=io_start_base;p_io_start_limit<=io_start_limit;p_io_start_loops<=io_start_loops;
 end
  
 reg rs1,rs2;
 always @(posedge clk)begin rs1<=rst_n;rs2<=rs1;end
 (* keep = "true", dont_touch = "true" *) reg [NL-1:0] ra_leaf;
 (* keep = "true", dont_touch = "true" *) reg ra_top;
 always @(posedge clk)begin ra_leaf<={NL{rs2}};ra_top<=rs2;end
 (* keep = "true", dont_touch = "true" *) reg [3:0] rb;      
 (* keep = "true", dont_touch = "true" *) reg rbd1;          
 always @(posedge clk)begin rb<={4{ra_top}};rbd1<=rb[3];end
  
 wire [NL-1:0] we0;
 for(genvar s=0;s<8;s=s+1)begin:g_pwe
  assign we0[s]=rbd1 && rb[3] && p_cfg_we && p_cfg_stripe==s;
 end
 for(genvar s=0;s<3;s=s+1)begin:g_iowe
  assign we0[8+s]=rbd1 && rb[3] && p_io_cfg_we && p_io_cfg_stripe==s;
 end
  
 (* keep = "true", dont_touch = "true" *) reg [NL-1:0] we_d1,we_d2,we_d3,we_d4,we_d5;
 always @(posedge clk)begin we_d1<=we0;we_d2<=we_d1;we_d3<=we_d2;we_d4<=we_d3;we_d5<=we_d4;end
 wire [NL-1:0] leaf_we;
 for(genvar l=0;l<NL;l=l+1)begin:g_wed
 
  
   

`line 139 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
  assign leaf_we[l]=(depth(l)==0)?we0[l]:(depth(l)==1)?we_d1[l]:(depth(l)==2)?we_d2[l]:(depth(l)==3)?we_d3[l]:(depth(l)==4)?we_d4[l]:we_d5[l];

`line 141 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 end
  
 wire p_legal=p_start_limit>{1'b0,p_start_base} && p_start_limit<=(1<<AW) && p_start_loops!=0;
 wire [AW:0] p_span=p_start_limit-{1'b0,p_start_base};
 wire p_lone=p_start_loops==16'd1;
 wire io_legal=p_io_start_limit>{1'b0,p_io_start_base} && p_io_start_limit<=(1<<AW) && p_io_start_loops!=0;
 wire [AW:0] io_span=p_io_start_limit-{1'b0,p_io_start_base};
 wire io_lone=p_io_start_loops==16'd1;
 wire io_sv=rb[1] && rbd1 && p_io_start_v;       
  
 function automatic integer rowof(input integer l);
  case(l) 0,1,2:rowof=0; 6,8:rowof=1; 7,9,10:rowof=2; default:rowof=3; endcase
 endfunction
 wire p_sv;
 (* keep = "true", dont_touch = "true" *) reg [3:0] pr_sv,pr_legal,pr_lone;
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] pr_base[0:3];
 (* keep = "true", dont_touch = "true" *) reg [AW:0] pr_span[0:3];
 (* keep = "true", dont_touch = "true" *) reg [15:0] pr_loops[0:3];
 for(genvar r=0;r<4;r=r+1)begin:g_prow
  always @(posedge clk)begin
   pr_sv[r]<=p_sv;pr_legal[r]<=p_legal;pr_lone[r]<=p_lone;
   pr_base[r]<=p_start_base;pr_span[r]<=p_span;pr_loops[r]<=p_start_loops;
  end
 end
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] cr_addr0,cr_addr3;
 (* keep = "true", dont_touch = "true" *) reg [255:0] cr_data0,cr_data3;
 always @(posedge clk)begin cr_addr0<=p_cfg_addr;cr_data0<=p_cfg_data;cr_addr3<=p_cfg_addr;cr_data3<=p_cfg_data;end
  
 wire [AW-1:0] c_addr[0:NL-1];
 wire [255:0] c_data[0:NL-1];
 wire [221:0] cal[0:NL-1];
 wire [NL-1:0] lv,la,ld,lf,b26;
 wire [1:0] hz[0:NL-1];
 wire [31:0] ord[0:NL-1];
 wire [NL-1:0] own_cv;                           
 wire io_cv;
 reg p_sv_q;
 for(genvar l=0;l<NL;l=l+1)begin:g_leaf
  localparam integer PR=pred(l);
  wire io=(l>=8);
  wire [AW-1:0] a_in;
  wire [255:0] d_in;
  localparam integer RW=rowof(l);
  if(l==0)begin:g_cr0
   assign a_in=cr_addr0;
   assign d_in=cr_data0;
  end else if(l==3)begin:g_cr3
   assign a_in=cr_addr3;
   assign d_in=cr_data3;
  end else if(PR<0)begin:g_head
   assign a_in=(l>=8)?p_io_cfg_addr:p_cfg_addr;
   assign d_in=(l>=8)?p_io_cfg_data:p_cfg_data;
  end else begin:g_chain
   assign a_in=c_addr[PR];
   assign d_in=c_data[PR];
  end
  ot_hgi_sfu_store_stripe_leaf_r10 u_leaf(    
  .clk(clk),.rst_a(ra_leaf[l]),.in_we(leaf_we[l]),
   .in_addr(a_in),.in_data(d_in),.out_addr(c_addr[l]),.out_data(c_data[l]),
 
   
   

`line 204 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
   .in_start_v((l>=8)?io_sv:pr_sv[RW]),

`line 206 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
   .in_start_base((l>=8)?p_io_start_base:pr_base[RW]),.in_legal((l>=8)?io_legal:pr_legal[RW]),
   .in_span((l>=8)?io_span:pr_span[RW]),.in_loops((l>=8)?p_io_start_loops:pr_loops[RW]),.in_loops_one((l>=8)?io_lone:pr_lone[RW]),
   .in_cv(own_cv[l]),.out_cal(cal[l]),.out_v(lv[l]),.out_active(la[l]),.out_done(ld[l]),.out_fault(lf[l]),
   .out_ord(ord[l]),.out_hz(hz[l]),.out_b26(b26[l]));
 end
  
 wire nb7_now=hz[7][1];
 wire nbio_now=hz[10][0];
 reg nb7_s,nbio_s;
 always @(posedge clk)begin
  nb7_s<=rb[2] && ((rbd1 && nb7_now) || nb7_s);
  nbio_s<=rb[1] && ((rbd1 && nbio_now) || nbio_s);
 end
  
 wire [7:0] pv=lv[7:0],pa=la[7:0],pd=ld[7:0];
 wire [7:0] pf={lf[7]|(rbd1&&nb7_now)|nb7_s,lf[6:0]};
 wire [2:0] vio=lv[10:8],aio=la[10:8],dio=ld[10:8];
 wire [2:0] iof={lf[10]|(rbd1&&nbio_now)|nbio_s,lf[9:8]};
 assign own_cv[7:0]=pv & ~pf;                      
 assign own_cv[10:8]=vio & ~iof;
 assign io_cv=(&vio) && !(|iof);                   
 
 
      

`line 231 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 always @(posedge clk)p_sv_q<=rb[2] && io_cv && b26[10];    

`line 233 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 assign p_sv=p_sv_q;
  
 localparam [7:0] PM0=8'b0000_0111, PM1=8'b0100_0000, PM2=8'b1000_0000, PM3=8'b0011_1000;    
 localparam integer PREP0=0, PREP1=6, PREP2=7, PREP3=3;                                     
 function automatic [7:0] pmask(input integer r);
  case(r) 0:pmask=PM0; 1:pmask=PM1; 2:pmask=PM2; default:pmask=PM3; endcase
 endfunction
 function automatic integer prep(input integer r);
  case(r) 0:prep=PREP0; 1:prep=PREP1; 2:prep=PREP2; default:prep=PREP3; endcase
 endfunction
 (* keep = "true", dont_touch = "true" *) reg [3:0] sp_vall,sp_vany,sp_aall,sp_aany,sp_dall,sp_dany,sp_f,sp_mm;
 (* keep = "true", dont_touch = "true" *) reg [31:0] sp_ord[0:3];
 for(genvar r=0;r<4;r=r+1)begin:g_sp
  localparam [7:0] M=pmask(r);
  localparam integer RP=prep(r);
  wire [7:0] mm;
  for(genvar s=0;s<8;s=s+1)begin:g_m assign mm[s]=M[s] && ord[s]!=ord[RP]; end
  always @(posedge clk)begin
   sp_vall[r]<=&(pv|~M);sp_vany[r]<=|(pv&M);sp_aall[r]<=&(pa|~M);sp_aany[r]<=|(pa&M);
   sp_dall[r]<=&(pd|~M);sp_dany[r]<=|(pd&M);sp_f[r]<=|(pf&M);sp_mm[r]<=|mm;sp_ord[r]<=ord[RP];
  end
 end
  
 (* keep = "true", dont_touch = "true" *) reg [1:0] si_vall,si_vany,si_aall,si_aany,si_dall,si_dany,si_f;
 (* keep = "true", dont_touch = "true" *) reg si_mm;
 (* keep = "true", dont_touch = "true" *) reg [31:0] si_ord[0:1];
 always @(posedge clk)begin
  si_vall[0]<=vio[0];si_vany[0]<=vio[0];si_aall[0]<=aio[0];si_aany[0]<=aio[0];si_dall[0]<=dio[0];si_dany[0]<=dio[0];
  si_f[0]<=iof[0];si_ord[0]<=ord[8];
  si_vall[1]<=&vio[2:1];si_vany[1]<=|vio[2:1];si_aall[1]<=&aio[2:1];si_aany[1]<=|aio[2:1];si_dall[1]<=&dio[2:1];
  si_dany[1]<=|dio[2:1];si_f[1]<=|iof[2:1];si_mm<=ord[10]!=ord[9];si_ord[1]<=ord[9];
 end
 (* keep = "true", dont_touch = "true" *) reg [2:0] rb_d;         
 always @(posedge clk)rb_d<=rb[2:0];
  
  
  
 wire p_omm=(|sp_mm) || sp_ord[1]!=sp_ord[0] || sp_ord[2]!=sp_ord[0] || sp_ord[3]!=sp_ord[0];
 wire p_dis=(|sp_vany && !(&sp_vall)) || (|sp_dany && !(&sp_dall)) || (|sp_aany && !(&sp_aall)) || (&sp_vall && p_omm);
 wire io_omm=si_mm || si_ord[1]!=si_ord[0];
 wire io_dis=(|si_vany && !(&si_vall)) || (|si_dany && !(&si_dall)) || (|si_aany && !(&si_aall)) || (&si_vall && io_omm);
 reg p_fault,io_fault;
 always @(posedge clk)begin
  if(!rb_d[2])p_fault<=0; else if(p_dis || |sp_f)p_fault<=1;
  if(!rb_d[1])io_fault<=0; else if(io_dis || |si_f)io_fault<=1;
 end
  
 reg [470:0] o_io;
 reg [1741:0] o_ctl;
 always @(posedge clk)begin
  o_io<={cal[10][26:0],cal[9],cal[8]};
  o_ctl<={cal[7][187:0],cal[6],cal[5],cal[4],cal[3],cal[2],cal[1],cal[0]};
 end
 assign io_word=o_io;
 
  

`line 290 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 
  

`line 293 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 
     

`line 296 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 assign compiler_control=o_ctl;

`line 298 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv" 0
 always @(posedge clk)
  if(!rb_d[0])begin
   io_active<=0;io_done<=0;io_ordinal<=0;programme_active<=0;programme_done<=0;programme_ordinal<=0;fault<=0;
  end else begin
   io_active<=|si_aany;io_done<=&si_dall;io_ordinal<=si_ord[0];
   programme_active<=|sp_aany;programme_done<=&sp_dall;programme_ordinal<=sp_ord[0];
   if(io_fault||p_fault)fault<=1;
  end
endmodule
