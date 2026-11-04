`timescale 1ns/1ps
// DIE-HBM-61/CUTS 11-03: pslice_c5 dictionary-path cut form (DRLY/DBREG/DGRP, DK = DRLY+DBREG+(DGRP>0)) == gold cluster
// top (recipe pin d34578d6f, modules prefixed gold_) with every output delayed DK edges, inputs unchanged. Random config
// (incl. out-of-range banks), starts (legal + rejected-in-busy), lengths, periodic resets. Contract: a start or a
// configuration write is legal when both producers are idle (the cut form's internal busy ends DK edges later, so the
// DK-edge tail after the gold producer's busy end is excluded from the stimulus; a new programme starts >= XP+DK = 4+DK
// edges after both producers went idle, since the registered busy output merges programmes closer than its own XP
// delay in either form; starts/writes that hit a busy producer early in a programme are kept and must give the same
// fault edge). Mutants (runner sed) must FAIL.
module tb_pslice_dcut;
  parameter integer DRLY=1, DBREG=1, DGRP=2, SB=2470, CYC=24000;
  localparam integer DK=DRLY+DBREG+((DGRP>0)?1:0);
  reg clk=1'b0; always #0.5 clk=~clk;
  reg rst_n=1'b0, cfg_we=1'b0, start=1'b0;
  reg [15:0] cfg_bank=0, length=0; reg [6:0] cfg_row=0; reg [255:0] cfg_data=0;
  wire a_busy,a_valid,a_done,a_fault,b_busy,b_valid,b_done,b_fault; wire [15:0] a_ei,b_ei; wire [SB-1:0] a_cmd,b_cmd;
  gold_ot_hbm_su_programme_pslice_c5 #(.SB(SB)) u_g(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),.busy(a_busy),.valid(a_valid),
    .done(a_done),.fault(a_fault),.edge_index(a_ei),.command(a_cmd));
  localparam integer OWD=4+16+SB;
  reg [OWD-1:0] ol [0:DK-1]; wire [OWD-1:0] oin={a_cmd,a_ei,a_fault,a_done,a_valid,a_busy};
  integer i, j;
  always @(posedge clk) begin ol[0]<=oin; for(i=1;i<DK;i=i+1) ol[i]<=ol[i-1]; end
  wire [OWD-1:0] ao=ol[DK-1];
  ot_hbm_su_programme_pslice_c5 #(.SB(SB),.DRLY(DRLY),.DBREG(DBREG),.DGRP(DGRP)) u_t(.clk(clk),.rst_n(rst_n),
    .cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
    .busy(b_busy),.valid(b_valid),.done(b_done),.fault(b_fault),.edge_index(b_ei),.command(b_cmd));
  wire [OWD-1:0] bo={b_cmd,b_ei,b_fault,b_done,b_valid,b_busy};
  // producer-internal busy of leaf 0 (all leaves run the identical control)
  wire g_bi=u_g.g_c[0].u_c.u_p.busy_i, t_bi=u_t.g_c[0].u_c.g_p.u_p.busy_i;
  integer col; integer cyc, bad=0, nc=0, nv=0, nf=0, nz=0, nr=0, ns=0, nrej=0, ph=0, last_s=-100000, last_l=0;
  reg idle, early, gap; integer idle_n=0;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      ph=cyc%6000;
      rst_n=(ph>=16);
      if(ph==16) nr=nr+1;
      idle=!g_bi && !t_bi;
      idle_n=idle?idle_n+1:0;
      gap=idle_n>=4+DK;
      early=g_bi && (cyc-last_s)>=6 && (cyc-last_s)<=last_l/2;   // surely inside a running programme in both
      col=$urandom%10;
      cfg_we=((ph<2500)?(($urandom%3)!=0):(($urandom%60)==0)) && (idle || early);
      cfg_bank={11'(($urandom%3000==0)?(10+$urandom%3):col),
                5'(($urandom%3000==0)?(17+$urandom%5):($urandom%((col>=1 && col<=3)?17:7)))};
      // dense tables: rows 0..15 only (programme index rows pc>>4 <= 9) and every 16-bit word a dictionary address
      // {bank 0..13 (13 = out of range for every leaf), row 0..15}, so most reads hit written, distinct rows
      cfg_row=7'($urandom%16);
      for(j=0;j<16;j=j+1) cfg_data[16*j+:16]={9'($urandom%14),7'($urandom%16)};
      start=(ph>=2500)&&(($urandom%30)==0) && (gap || early);
      length=16'(1+$urandom%150);
      if(start && gap) begin last_s=cyc; last_l=length; end
      if(start && !gap) nrej=nrej+1;
      ns=ns+start;
      if(cyc>60 && ph>40) begin
        nc=nc+1; nv=nv+ao[1]; nf=nf+ao[3]; nz=nz+(ao[1] && ao[OWD-1:20]!=0);
        if(ao!==bo) begin bad=bad+1;
          if(bad<=5) $display("DCUT_EQ_MISMATCH cycle=%0d busy %b/%b valid %b/%b done %b/%b fault %b/%b ei %0d/%0d cmd_eq %b",
            cyc,ao[0],bo[0],ao[1],bo[1],ao[2],bo[2],ao[3],bo[3],ao[19:4],bo[19:4],ao[OWD-1:20]==bo[OWD-1:20]);
        end
      end
    end
    if(bad==0) $display("DCUT_EQ PASS DRLY=%0d DBREG=%0d DGRP=%0d DK=%0d compared=%0d valid=%0d nonzero_cmd=%0d fault_cycles=%0d resets=%0d starts=%0d in_busy=%0d",
      DRLY,DBREG,DGRP,DK,nc,nv,nz,nf,nr,ns,nrej);
    else $display("DCUT_EQ FAIL DRLY=%0d DBREG=%0d DGRP=%0d mismatches=%0d of %0d",DRLY,DBREG,DGRP,bad,nc);
    $finish;
  end
endmodule
