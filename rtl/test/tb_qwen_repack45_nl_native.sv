`timescale 1ns/1ps
// Q-TILE45 node-less twin: qfd_tile_nl_rp2_45 (NODE 0, 41 entries) against the original 25-entry qfd_tile_nk_rp1 tree
// output t_out (the nk node leaf's t_d feed-through = the nl TOREG register: same edge and value). n_a/n_b held 0 (no
// node traffic; a node-less tile has no tree-node ports).  Mutants stop ck_tx0 (1), ck_rp5 (2), the t_out face ck_fa2 (3).
// Native clock-partition equivalence: both sides instantiate all64 actual MAC lanes,
// the closed LSL/node RTL bodies, and ten real 4096x266 mapped-ROM functional models.
// Raw via-array initialization is declared memory stimulus, not internal compute substitution.
// Fixed issue slots: five full-width GT3072 operations, all five physical ROM banks exercised.
module tb_qwen_repack45_nl_native;
parameter integer MUT=0;
reg ck=0,rs=0; always #0.5 ck=~ck;
reg [507:0] tap=0;
reg [513:0] na=0,nb=0;
wire [513:0] rt,rn,ut;
wire rhi,rlo,uhi,ulo;
qfd_tile_nk_rp1 ref_tile (.ck(ck), .ck_rp0(ck), .ck_rp1(ck), .ck_rp2(ck), .ck_rp3(ck), .ck_rp4(ck), .ck_rom0(ck), .ck_rom1(ck), .ck_rom2(ck), .ck_rom3(ck), .ck_rom4(ck), .ck_rom5(ck), .ck_rom6(ck), .ck_rom7(ck), .ck_rom8(ck), .ck_rom9(ck), .ck_lsl0(ck), .ck_lsl1(ck), .ck_lsl2(ck), .ck_lsl3(ck), .ck_lsl4(ck), .ck_lsl5(ck), .ck_lsl6(ck), .ck_lsl7(ck), .ck_node(ck), .rst_n(rs),.tile_id(16'd0),.tie_hi(rhi),.tie_lo(rlo),.tap(tap),.t_out(rt),.n_a(na),.n_b(nb),.n_y(rn));
qfd_tile_nl_rp2_45 dut (.ck(ck), .ck_rp0(ck), .ck_rp1(ck), .ck_rp2(ck), .ck_rp3(ck), .ck_rp4(ck), .ck_rom0(ck), .ck_rom1(ck), .ck_rom2(ck), .ck_rom3(ck), .ck_rom4(ck), .ck_rom5(ck), .ck_rom6(ck), .ck_rom7(ck), .ck_rom8(ck), .ck_rom9(ck), .ck_lsl0(ck), .ck_lsl1(ck), .ck_lsl2(ck), .ck_lsl3(ck), .ck_lsl4(ck), .ck_lsl5(ck), .ck_lsl6(ck), .ck_lsl7(ck), .ck_tx0((MUT==1 ? 1'b0 : ck)), .ck_tx1(ck), .ck_tx2(ck), .ck_tx3(ck), .ck_tx4(ck), .ck_tx5(ck), .ck_tx6(ck), .ck_tx7(ck), .ck_rp5((MUT==2 ? 1'b0 : ck)), .ck_rp6(ck), .ck_rp7(ck), .ck_rp8(ck), .ck_rp9(ck), .ck_rqr0(ck), .ck_rqr1(ck), .ck_fa2((MUT==3 ? 1'b0 : ck)), .ck_fa4(ck), .rst_n(rs),.tile_id(16'd0),.tie_hi(uhi),.tie_lo(ulo),.tap(tap),.t_out(ut));
genvar p,b;
generate for(p=0;p<2;p=p+1)begin: cols
 for(b=0;b<5;b=b+1)begin:banks
  integer row,bitn;
  initial begin
   #0.1;
   for(row=0;row<512;row=row+1)for(bitn=0;bitn<2128;bitn=bitn+1) begin
    ref_tile.u_tile.u_tile.g_col[p].g_bank[b].u_rom.arr[row][bitn]=((row*17+bitn*13+p*31+b*7)%29)<14;
    dut.u_tile.u_tile.g_col[p].g_bank[b].u_rom.arr[row][bitn]=((row*17+bitn*13+p*31+b*7)%29)<14;
   end
  end
 end
end endgenerate
function automatic [378:0] command(input integer bank);
 command={18'd4096,18'd2,18'd32,1'b0,24'(bank*4096),24'd64,24'd8,24'd1,
          24'd0,24'd1,24'd1,24'd1,3'd0,4'd7,24'd1,1'b0,24'd0,24'd1,24'd1,
          1'b0,1'b1,1'b0,1'b0,24'd0};
endfunction
integer cyc,errors=0,checks=0,valids=0,nonzero=0;
integer leafcounts[0:7];
genvar leaf;
generate for(leaf=0;leaf<8;leaf=leaf+1)begin:activity
 always @(negedge ck) if(rs && ref_tile.u_tile.u_tile.u_logic.u_me.g_hier.g_sl[leaf].g_hd.u_lh.v_d)
  leafcounts[leaf]=leafcounts[leaf]+1;
end endgenerate
initial begin
 for(integer l=0;l<8;l=l+1)leafcounts[l]=0;
 repeat(8)@(negedge ck);rs=1;
 for(cyc=0;cyc<6500;cyc=cyc+1)begin
  tap[0]=0;
  if(cyc>=200 && (cyc-200)%1200==0 && cyc<6200)begin
   tap[379:1]=command((cyc-200)/1200);tap[0]=1;
  end
  for(integer g=0;g<4;g=g+1)tap[380+g*32+:32]=32'h3f800000+((cyc%8+g)<<18);
  @(negedge ck);
  if(cyc>100)begin
   checks=checks+1;
   if(rt!==ut || rhi!==uhi || rlo!==ulo)begin
    errors=errors+1;if(errors<5)$display("REPACK45NL_MISMATCH cycle%0d rt%h ut%h",cyc,rt,ut);
   end
   if(rt[512])begin valids=valids+1;if(|rt[511:0])nonzero=nonzero+1;end
  end
 end
 for(integer l=0;l<8;l=l+1)if(leafcounts[l]==0)$fatal(1,"NATIVE_ACTIVITY_MISSING leaf%0d",l);
 if(valids==0||nonzero==0)$fatal(1,"NATIVE_ACTIVITY_MISSING valids%0d nonzero%0d",valids,nonzero);
 if(errors)$fatal(1,"REPACK45NL_NATIVE_FAIL MUT%0d errors%0d checks%0d valids%0d nonzero%0d",MUT,errors,checks,valids,nonzero);
 $display("REPACK45NL_NATIVE_PASS checks%0d valids%0d nonzero%0d leaves%p",checks,valids,nonzero,leafcounts);$finish;
end
endmodule
