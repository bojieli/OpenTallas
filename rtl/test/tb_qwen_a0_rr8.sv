`timescale 1ns/1ps
// QW-A0-RC4 10-20 REGROOT 8 proof (NK parent).  Three instances, one stimulus:
//  ref  = qfd_tile_nk_rp1 (the golden flat parent, as tb_qwen_a0_rr7), dut = REGROOT_MODE 8, d7 = REGROOT_MODE 7.
//  Phase A (cycles < 6500): the rr7 fixture (five full-width GT3072 ROM ops over all five banks): ref == dut (t_out one
//  edge later, n_y, ties) AND d7 == dut.
//  Phase B (6500..PHB): random descriptors (random split 7..11, KV ops wsrc=1, tiles 1..3, k 1..24, strides, jsh,
//  round, random go gaps incl. go while busy, tile strap 37 from cycle 6500): d7 == dut on every output AND on the engine's memory-request
//  interface every cycle (wrom_re/addr, kv_re/addr, e_gm, k_r, tstep, the per-group KV offsets), so the KV-path
//  copies (whose data are zero in this KV_SLICE 0 parent) are compared directly.  Fault pins excluded (REGROOT 8
//  lands leaf faults one edge later; no fault is raised by either stimulus).
// Mutants (each must FAIL): MUT50 one descriptor load-group idle copy held 0 (its 23 bits never load),
//  MUT51 go copy 3 held 0 (field groups 6/7: nb_t / lb never initialise), MUT52 split-copy twin of copy 35 held 0
//  (kpad high bits: KV ceil(K/S) at split >= 10), MUT53 xk-low chunk k_last copy held 1, MUT54 rung-0 round select of leaf 0 held 0,
//  MUT55 ts copy of KV group 1 held 0.
module tb_qwen_a0_rr8;
integer MUT=0;
initial begin if ($value$plusargs("MUT=%d", MUT)) begin end end
`define ME dut.u_g.u_tile.u_tile.u_logic.u_me
`define M7 d7.u_g.u_tile.u_tile.u_logic.u_me
initial begin #0.2;
 if (MUT==50) force `ME.g_issue_fast.g_ctl_rr8.g_ld[5].i = 1'b0;
 if (MUT==51) force dut.u_g.u_tile.u_tile.u_logic.g_gocp.g_c[3].q = 1'b0;
 if (MUT==52) force `ME.g_rr6.g_sp[80].q = 4'd0;
 if (MUT==53) force `ME.g_issue_fast.g_ctl_rr8.g_fc[19].kl = 1'b1;
 if (MUT==54) force `ME.g_hier.g_sl[0].g_hd.g_raw.sel = '0;
 if (MUT==55) force `ME.g_issue_fast.g_ctl_rr8.tsc_q[24+:24] = '0;
end
reg ck=0,rs=0; always #0.5 ck=~ck;
reg [15:0] tid=16'd0;   // phase B: a non-zero tile strap (dut and d7 only) so the per-group KV offsets / K limits are non-trivial
reg [507:0] tap=0;
reg [513:0] na=0,nb=0;
wire [513:0] rt,rn,ut,un,st,sn;
wire rhi,rlo,uhi,ulo,shi,slo;
reg [512:0] rt_prev;
always @(posedge ck) rt_prev <= rt[512:0];
wire [513:0] expected_t={rt[513],rt_prev};
qfd_tile_nk_rp1 ref_tile (.ck(ck), .ck_rp0(ck), .ck_rp1(ck), .ck_rp2(ck), .ck_rp3(ck), .ck_rp4(ck), .ck_rom0(ck), .ck_rom1(ck), .ck_rom2(ck), .ck_rom3(ck), .ck_rom4(ck), .ck_rom5(ck), .ck_rom6(ck), .ck_rom7(ck), .ck_rom8(ck), .ck_rom9(ck), .ck_lsl0(ck), .ck_lsl1(ck), .ck_lsl2(ck), .ck_lsl3(ck), .ck_lsl4(ck), .ck_lsl5(ck), .ck_lsl6(ck), .ck_lsl7(ck), .ck_node(ck), .rst_n(rs),.tile_id(16'd0),.tie_hi(rhi),.tie_lo(rlo),.tap(tap),.t_out(rt),.n_a(na),.n_b(nb),.n_y(rn));
qfd_tile_nk_rp2_romleaf_rr #(.REGROOT_MODE(8)) dut (.ck_rsw(ck), .ck_rnw(ck), .ck_dw(ck), .ck_de(ck), .ck_rp0(ck), .ck_rp1(ck), .ck_rp2(ck), .ck_rp3(ck), .ck_rp4(ck), .ck_rp5(ck), .ck_rp6(ck), .ck_rp7(ck), .ck_rp8(ck), .ck_rp9(ck), .ck(ck), .ck_rs(ck), .ck_rn(ck), .ck_tx0(ck), .ck_tx1(ck), .ck_tx2(ck), .ck_tx3(ck), .ck_tx4(ck), .ck_tx5(ck), .ck_tx6(ck), .ck_tx7(ck), .ck_fa0(ck), .ck_fa1(ck), .ck_fa2(ck), .ck_fa3(ck), .ck_fa4(ck), .ck_lsl0(ck), .ck_lsl1(ck), .ck_lsl2(ck), .ck_lsl3(ck), .ck_lsl4(ck), .ck_lsl5(ck), .ck_lsl6(ck), .ck_lsl7(ck), .ck_node(ck), .rst_n(rs),.tile_id(tid),.tie_hi(uhi),.tie_lo(ulo),.tap(tap),.t_out(ut),.n_a(na),.n_b(nb),.n_y(un));
qfd_tile_nk_rp2_romleaf_rr #(.REGROOT_MODE(7)) d7 (.ck_rsw(ck), .ck_rnw(ck), .ck_dw(ck), .ck_de(ck), .ck_rp0(ck), .ck_rp1(ck), .ck_rp2(ck), .ck_rp3(ck), .ck_rp4(ck), .ck_rp5(ck), .ck_rp6(ck), .ck_rp7(ck), .ck_rp8(ck), .ck_rp9(ck), .ck(ck), .ck_rs(ck), .ck_rn(ck), .ck_tx0(ck), .ck_tx1(ck), .ck_tx2(ck), .ck_tx3(ck), .ck_tx4(ck), .ck_tx5(ck), .ck_tx6(ck), .ck_tx7(ck), .ck_fa0(ck), .ck_fa1(ck), .ck_fa2(ck), .ck_fa3(ck), .ck_fa4(ck), .ck_lsl0(ck), .ck_lsl1(ck), .ck_lsl2(ck), .ck_lsl3(ck), .ck_lsl4(ck), .ck_lsl5(ck), .ck_lsl6(ck), .ck_lsl7(ck), .ck_node(ck), .rst_n(rs),.tile_id(tid),.tie_hi(shi),.tie_lo(slo),.tap(tap),.t_out(st),.n_a(na),.n_b(nb),.n_y(sn));
genvar p,b;
generate for(p=0;p<2;p=p+1)begin: cols
 for(b=0;b<5;b=b+1)begin:banks
  integer row,bitn;
  initial begin
   #0.1;
   for(row=0;row<512;row=row+1)for(bitn=0;bitn<2128;bitn=bitn+1) begin
    ref_tile.u_tile.u_tile.g_col[p].g_bank[b].u_rom.arr[row][bitn]=((row*17+bitn*13+p*31+b*7)%29)<14;
    dut.u_g.u_tile.u_tile.u_logic.g_rom_pipe.g_rph.g_rb[b].g_single.g_col[p].u_leaf.u_rom.arr[row][bitn]=((row*17+bitn*13+p*31+b*7)%29)<14;
    d7.u_g.u_tile.u_tile.u_logic.g_rom_pipe.g_rph.g_rb[b].g_single.g_col[p].u_leaf.u_rom.arr[row][bitn]=((row*17+bitn*13+p*31+b*7)%29)<14;
   end
  end
 end
end endgenerate
function automatic [378:0] command(input integer bank);
 command={18'd4096,18'd2,18'd32,1'b0,24'(bank*4096),24'd64,24'd8,24'd1,
          24'd0,24'd1,24'd1,24'd1,3'd0,4'd7,24'd1,1'(bank%2),24'd0,24'd1,24'd1,
          1'b0,1'b1,1'b0,1'b0,24'd0};
endfunction
integer seed=20261020;
function automatic [378:0] rcommand(input integer dummy);
 reg [17:0] nout,tiles,kk; reg wsrc; reg [3:0] split; reg [2:0] jsh;
 begin
  nout=18'($urandom_range(4096,1)); tiles=18'($urandom_range(3,1)); kk=18'($urandom_range(24,1));
  wsrc=($urandom_range(2,0)==0); split=4'($urandom_range(11,7)); jsh=3'($urandom_range(2,0));
  rcommand={nout,tiles,kk,wsrc,24'($urandom_range(20479,0)),24'($urandom_range(300,0)),24'($urandom_range(40,0)),24'($urandom_range(3,0)),
            24'($urandom_range(500,0)),24'($urandom_range(5,0)),24'($urandom_range(5,0)),24'($urandom_range(9,0)),jsh,split,24'($urandom_range(700,0)),
            1'($urandom_range(1,0)),24'($urandom_range(4000,0)),24'($urandom_range(9,0)),24'($urandom_range(5,0)),
            1'($urandom_range(1,0)),1'($urandom_range(1,0)),1'($urandom_range(1,0)),1'($urandom_range(1,0)),24'($urandom_range(900,0))};
 end
endfunction
integer cyc,errors=0,errors7=0,errorsi=0,checks=0,valids=0,nonzero=0,gos=0,kvops=0,next_go=6600;
integer leafcounts[0:7];
genvar leaf;
generate for(leaf=0;leaf<8;leaf=leaf+1)begin:activity
 always @(negedge ck) if(rs && ref_tile.u_tile.u_tile.u_logic.u_me.g_hier.g_sl[leaf].g_hd.u_lh.v_d)
  leafcounts[leaf]=leafcounts[leaf]+1;
end endgenerate
localparam integer PHB = 30000;
initial begin
 void'($urandom(seed));
 for(integer l=0;l<8;l=l+1)leafcounts[l]=0;
 repeat(8)@(negedge ck);rs=1;
 for(cyc=0;cyc<PHB;cyc=cyc+1)begin
  tap[0]=0;
  if(cyc>=200 && (cyc-200)%1200==0 && cyc<6200)begin
   tap[379:1]=command((cyc-200)/1200);tap[0]=1;
  end
  if(cyc==6500)tid=16'd37;
  if(cyc>=next_go)begin
   tap[379:1]=rcommand(0);tap[0]=1;gos=gos+1;if(tap[379-54])kvops=kvops+1;
   next_go=cyc+$urandom_range(700,1);
  end
  for(integer g=0;g<4;g=g+1)tap[380+g*32+:32]=32'h3f80c123+((cyc%8+g)<<18)+(cyc>=6500 ? $urandom_range(65535,0) : 0);
  for(integer lane=0;lane<16;lane=lane+1)begin
   na[lane*32+:32]=32'h3f000000+((cyc%16+lane)<<17);
   nb[lane*32+:32]=32'h3f800000+((cyc%8+lane)<<17);
  end
  na[513:512]={1'b0,(cyc%11==0)};nb[513:512]=na[513:512];
  @(negedge ck);
  if(cyc>100)begin
   checks=checks+1;
   if(cyc<6500 && (expected_t[512:0]!==ut[512:0] || rn[512:0]!==un[512:0] || rhi!==uhi || rlo!==ulo))begin
    errors=errors+1;if(errors<5)$display("ROMLEAF_PARENT_NK_MISMATCH cycle%0d rt%h ut%h",cyc,rt,ut);
   end
   if(st[512:0]!==ut[512:0] || sn[512:0]!==un[512:0] || shi!==uhi || slo!==ulo)begin
    errors7=errors7+1;if(errors7<5)$display("RR8_VS_RR7_OUT_MISMATCH cycle%0d st%h ut%h",cyc,st,ut);
   end
   if(`M7.wrom_re!==`ME.wrom_re || (`M7.wrom_re && `M7.wrom_addr!==`ME.wrom_addr) || `M7.kv_re!==`ME.kv_re ||
      (`M7.kv_re && `M7.kv_addr!==`ME.kv_addr) || (`M7.e_v && `M7.e_gm!==`ME.e_gm) || `M7.k_r!==`ME.k_r || `M7.tstep_r!==`ME.tstep_r ||
      `M7.e_v!==`ME.e_v || (`M7.e_v && (`M7.e_tag!==`ME.e_tag)) || `M7.active!==`ME.active || `M7.pend!==`ME.pend ||
      (`M7.active && (`M7.xc!==`ME.xc || `M7.xk!==`ME.xk || `M7.cur!==`ME.cur || `M7.base_k!==`ME.base_k || `M7.base_t!==`ME.base_t || `M7.oa!==`ME.oa || `M7.ot!==`ME.ot)))begin
    errorsi=errorsi+1;if(errorsi<5)$display("RR8_VS_RR7_ENGINE_MISMATCH cycle%0d wre%b/%b wa%h/%h kre%b/%b ka%h/%h gm%h/%h e_v%b/%b",cyc,`M7.wrom_re,`ME.wrom_re,`M7.wrom_addr,`ME.wrom_addr,`M7.kv_re,`ME.kv_re,`M7.kv_addr,`ME.kv_addr,`M7.e_gm,`ME.e_gm,`M7.e_v,`ME.e_v);
   end
   if(rt[512])begin valids=valids+1;if(|rt[511:0])nonzero=nonzero+1;end
  end
 end
 for(integer l=0;l<8;l=l+1)if(leafcounts[l]==0)$fatal(1,"NATIVE_ACTIVITY_MISSING leaf%0d",l);
 if(valids==0||nonzero==0)$fatal(1,"NATIVE_ACTIVITY_MISSING valids%0d nonzero%0d",valids,nonzero);
 if(gos<20||kvops<5)$fatal(1,"RANDOM_ACTIVITY_MISSING gos%0d kvops%0d",gos,kvops);
 if(errors||errors7||errorsi)$fatal(1,"A0_RR8_FAIL MUT%0d errors%0d errors7%0d errorsi%0d checks%0d",MUT,errors,errors7,errorsi,checks);
 $display("A0_RR8_PROOF_PASS MUT%0d checks%0d valids%0d nonzero%0d gos%0d kvops%0d leaves%p",MUT,checks,valids,nonzero,gos,kvops,leafcounts);$finish;
end
endmodule
