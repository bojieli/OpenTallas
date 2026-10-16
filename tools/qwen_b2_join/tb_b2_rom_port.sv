`timescale 1ns/1ps
// Declared component boundary: real ME command and already-reduced tree words.
// Actual DUT owns controller/frame, 384 released ROM macros, all multiplier/argmax RTL.
// Expected arrays are observers only and never feed a DUT compute or memory port.
module tb_b2_rom_port;
reg clk=0,rs=0;always #1 clk=~clk;
reg[379:0]cmd=0;wire scale_re,pv;wire[23:0]gre;wire[575:0]scale_addr;wire[112:0]pf;
wire[12:0]sel,tv;wire[305:0]pam;wire[5:0]p_fault;
wire[23:0]acc;wire idle;wire[15:0]prog;wire[94:0]ret;wire mxwe;wire[23:0]mxa;wire[15:0]mxm;wire[511:0]mxd;
qfd_tt_ctlm_tree_b2 tree(.clk(clk),.rst_n(rs),.me_acc_o(acc),.me_idle_o(idle),.me_prog_o(prog),
 .up_fault(1'b0),.land_cnt(16'd0),.scale_re(scale_re),.scale_gre(gre),.scale_addr(scale_addr),.t_sel_e(sel),.t_tv_e(tv),.tr_fault(16'd0),
 .p_v_e2(pv),.p_f_e2(pf),.p_am(pam),.p_fault(p_fault),.fab_fault(1'b0),.ov(),.mx_we(mxwe),.mx_addr(mxa),.mx_mask(mxm),.mx_data(mxd),.cmd(cmd),.ret(ret));
wire[340:0]tc[0:5];wire[2212:0]rq[0:5];wire[51:0]am[0:5];wire[2049:0]cw[0:5];
for(genvar h=0;h<6;h=h+1)begin:g_port
 assign tc[h]={scale_addr[192*(h/2)+:192],gre[8*(h/2)+:8],scale_re,pf,pv,tv,sel};
 qfd_port_half_b2 #(.ROM_BAND(h/2),.ROM_HALF(h%2))port(
  .hb(3'(h)),.ck(clk),.rst_n(rs),
  .ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),
  .ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),
  .ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),
  .ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),
  .ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),
  .bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
  .tc(tc[h]),.ty({64{32'h3f800000}}),.rq(rq[h]),.am(am[h]),.cw0(cw[h]));
 assign pam[51*h+:51]=am[h][50:0];assign p_fault[h]=am[h][51];
end
reg[255:0]expected_scale[0:30575];reg[8191:0]expected_path;
integer op_pc=0,op_sp=0,op_tiles=0,op_nout=0,op_wcs=0,op_base=0,op_ots=0,op_ojs=0,op_oen=1,op_amax=0;
integer burst[0:5],firstcap[0:5],firsttag=-1,cycle=0,writes=0,checked_lanes=0;
integer g,k,nb,addr,mask,sa;reg[31:0]want;
reg[50:0]am_expect[0:5][0:7];integer am_due[0:5][0:7];
reg[50:0]head_winner,entry,global_winner;
integer amchecks=0;
function automatic [31:0]okey(input[31:0]v);okey=v[31]?~v:{1'b1,v[30:0]};endfunction
function automatic [50:0]winner(input[50:0]a,b);
 winner=(a[50]&&(!b[50]||{a[49:18],~a[17:0]}>{b[49:18],~b[17:0]}))?a:b;
endfunction
always @(negedge clk)if(rs)begin
 cycle=cycle+1;
 if(pv&&pf[112]&&firsttag<0)firsttag=cycle;
 for(integer h=0;h<6;h=h+1)for(integer j=0;j<8;j=j+1)if(am_due[h][j]==cycle)begin
  if(am[h][50]!==am_expect[h][j][50]||(am_expect[h][j][50]&&am[h][50:0]!==am_expect[h][j]))$fatal(1,"actual wholeport AM data/phase pc%0d h%0d cycle%0d got%h want%h",op_pc,h,cycle,am[h][50:0],am_expect[h][j]);
  amchecks=amchecks+1;am_due[h][j]=-1;
 end
 for(integer h=0;h<6;h=h+1)if(rq[h][2212])begin
  if(firstcap[h]<0)firstcap[h]=cycle;
  head_winner=0;
  k=burst[h];nb=(k/8)*(3072>>op_sp)*128+(k%8)*16;
  for(integer q=0;q<4;q=q+1)begin
   g=(op_sp<=9)?h*(1<<(9-op_sp))+q:q;
   if(q<((op_sp<=7)?4:(op_sp==8)?2:(op_sp==9)?1:(op_sp==10)?3:1)&&(op_sp<=9||h==0))begin
    if(rq[h][2208+q]!==1'(op_oen))$fatal(1,"missing realport row pc%0d h%0d q%0d",op_pc,h,q);
    addr=op_base+(k/8)*op_ots*(3072>>op_sp)+(k%8)*op_ojs+g*op_ots;
    mask=0;for(integer l=0;l<16;l=l+1)if(nb+g*128+l<op_nout)mask=mask|(1<<l);
    if(rq[h][552*q+528+:24]!==24'(addr)||rq[h][552*q+512+:16]!==16'(mask))$fatal(1,"actual port row/mask pc%0d h%0d q%0d k%0d gotrow%0d want%0d gotmask%h want%h",op_pc,h,q,k,rq[h][552*q+528+:24],addr,rq[h][552*q+512+:16],16'(mask));
    sa=op_wcs+nb/16+g*8;
    for(integer l=0;l<16;l=l+1)if(mask&(1<<l))begin
     want={expected_scale[sa][16*l+:16],16'd0};
     if(rq[h][552*q+32*l+:32]!==want)$fatal(1,"actual ROM→hardmul mismatch pc%0d h%0d q%0d k%0d lane%0d scaleaddr%0d got%h want%h",op_pc,h,q,k,l,sa,rq[h][552*q+32*l+:32],want);
     entry={1'b1,okey(want),18'(nb+g*128+l)};
     head_winner=winner(head_winner,entry);global_winner=winner(global_winner,entry);
     checked_lanes=checked_lanes+1;
    end
    writes=writes+1;
   end else if(rq[h][2208+q])$fatal(1,"out of b2frame row");
  end
  am_expect[h][k%8]=head_winner;am_due[h][k%8]=cycle+5;
  burst[h]=burst[h]+1;
 end
end
task automatic op(input integer pc,nout,tiles,ksize,spacing,wbase,split,wcs,obase,ots,ojs,rounds,xbase,xcs,input integer output_en=1,input integer amax_en=0);
 begin
 rs=0;cmd=0;repeat(5)@(negedge clk);#0.01;
 op_oen=output_en;op_amax=amax_en;global_winner=0;
 op_pc=pc;op_sp=split;op_tiles=tiles;op_nout=nout;op_wcs=wcs;op_base=obase;op_ots=ots;op_ojs=ojs;firsttag=-1;
 for(integer h=0;h<6;h=h+1)begin burst[h]=0;firstcap[h]=-1;for(integer j=0;j<8;j=j+1)am_due[h][j]=-1;end
 rs=1;repeat(40)@(negedge clk);#0.01;
 cmd={24'd0,1'b0,1'(amax_en),1'(output_en),1'b0,24'(ojs),24'(ots),24'(obase),1'(rounds),24'(wcs),4'(split),3'd0,24'(xcs),24'd0,24'd1,24'(xbase),24'd1,24'd8,24'(spacing),24'(wbase),1'b0,18'(ksize),18'(tiles),18'(nout),1'b1};
 @(negedge clk);#0.01;cmd[0]=0;
 repeat(3000)@(negedge clk);#0.01;
 for(integer h=0;h<6;h=h+1)if(burst[h]!=8*tiles)$fatal(1,"actual port capture count pc%0d h%0d got%0d want%0d",pc,h,burst[h],8*tiles);
 if(amax_en&&(!ret[77]||ret[44:27]!==global_winner[17:0]||okey(ret[76:45])!==global_winner[49:18]))$fatal(1,"native controller scalarAM mismatch got%h idx%0d any%0d wantkey%h idx%0d",ret[76:45],ret[44:27],ret[77],global_winner[49:18],global_winner[17:0]);
 if(|p_fault||ret[94])$fatal(1,"actual controller/port fault pc%0d ret%h p_fault%b",pc,ret,p_fault);
 $display("PASS actualROMport pc%0d firsttag%0d caps%0d,%0d,%0d,%0d,%0d,%0d tag_to_capture%0d",pc,firsttag,firstcap[0],firstcap[1],firstcap[2],firstcap[3],firstcap[4],firstcap[5],firstcap[0]-firsttag);
 end
endtask
initial begin
 if(!$value$plusargs("EXPECTED=%s",expected_path))$fatal(1,"missing released expected scale observer");
 $readmemh(expected_path,expected_scale);
 op(1,768,1,8,64,0,9,0,768,8,1,1,4096,8);
 op(12,4096,3,2,16,64,8,48,0,8,1,1,50672,2);
 op(16,3072,1,32,256,112,7,336,2975,8,1,1,4096,32);
 op(20,4096,3,6,48,368,8,528,0,8,1,1,55280,6);
 op(103,6144,8,8,64,0,9,29376,0,8,1,1,8192,8,0,1);
 $display("PASS actual native controller→releasedROM→384hardmul port operations writes%0d checkedlanes%0d",writes,checked_lanes);$finish;
end
endmodule
