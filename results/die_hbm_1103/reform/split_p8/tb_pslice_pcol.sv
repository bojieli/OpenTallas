`timescale 1ns/1ps
// DIE-HBM-62/CUTS 11-04: pslice_c5 per-column composition (subs in their kit face shell form) == gold cluster (recipe pin
// d34578d6f) with the kit shell (+1 in, +1 out) plus the declared split shift: every input and output +2 edges net, fault
// +4 (a leaf fault crosses leaf out + head in faces after the +2 start path). Gold inputs +1, outputs +1 +OS. Random config
// (incl. out-of-range banks), starts (legal + rejected-in-busy), lengths, periodic resets. X-safe idle (SS25 patch).
// A legal host waits >= 3 edges after reset release. Mutants must FAIL.
module tb_pslice_pcol;
  parameter integer SMUT=0, SB=2470, CYC=48000;
  localparam integer OS=2, FS=4;
  reg clk=1'b0; always #0.5 clk=~clk;
  reg rst_n=1'b0, cfg_we=1'b0, start=1'b0;
  reg [15:0] cfg_bank=0, length=0; reg [6:0] cfg_row=0; reg [255:0] cfg_data=0;
  // gold kit shell, inputs
  reg gi_we=0, gi_start=0; reg [15:0] gi_bank=0, gi_len=0; reg [6:0] gi_row=0; reg [255:0] gi_data=0;
  always @(posedge clk) begin gi_we<=cfg_we; gi_start<=start; gi_bank<=cfg_bank; gi_len<=length; gi_row<=cfg_row; gi_data<=cfg_data; end
  wire a_busy,a_valid,a_done,a_fault,b_busy,b_valid,b_done,b_fault; wire [15:0] a_ei,b_ei; wire [SB-1:0] a_cmd,b_cmd;
  gold_ot_hbm_su_programme_pslice_c5 #(.SB(SB)) u_g(.clk(clk),.rst_n(rst_n),.cfg_we(gi_we),.cfg_bank(gi_bank),
    .cfg_row(gi_row),.cfg_data(gi_data),.start(gi_start),.length(gi_len),.busy(a_busy),.valid(a_valid),
    .done(a_done),.fault(a_fault),.edge_index(a_ei),.command(a_cmd));
  localparam integer OWD=3+16+SB;
  reg [OWD-1:0] ol [0:OS]; reg [FS:0] fl; wire [OWD-1:0] oin={a_cmd,a_ei,a_done,a_valid,a_busy};
  integer i, j;
  always @(posedge clk) begin ol[0]<=oin; for(i=1;i<=OS;i=i+1) ol[i]<=ol[i-1]; fl<={fl[FS-1:0],a_fault}; end
  wire [OWD-1:0] ao=ol[OS]; wire af=fl[FS];
  ot_hbm_su_programme_pslice_c5__p8fs #(.SMUT(SMUT)) u_t(.clk(clk),.rst_n(rst_n),
    .cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
    .busy(b_busy),.valid(b_valid),.done(b_done),.fault(b_fault),.edge_index(b_ei),.command(b_cmd));
  wire [OWD-1:0] bo={b_cmd,b_ei,b_done,b_valid,b_busy};
  wire g_bi=u_g.g_c[0].u_c.u_p.busy_i, t_bi=u_t.u_c0.u_fcore.u_c.g_p.u_p.busy_i;
  integer col, cyc, bad=0, nc=0, nv=0, nf=0, nz=0, nr=0, ns=0, nrej=0, ph=0, last_s=-100000, last_l=0, ndone=0, nw=0, noor=0;
  reg idle, early, gap, live; integer idle_n=0; reg [9:0] nzc=0;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      ph=cyc%6000;
      rst_n=(ph>=16);
      if(ph==16) nr=nr+1;
      live=(ph>=26) && (ph<5980);
      idle=(g_bi===1'b0) && (t_bi===1'b0);
      idle_n=idle?idle_n+1:0;
      gap=idle_n>=4+OS+2;
      early=(g_bi===1'b1) && (t_bi===1'b1) && (cyc-last_s)>=8 && (cyc-last_s)<=last_l/2;
      col=$urandom%10;
      cfg_we=live && ((ph<2500)?(($urandom%3)!=0):(($urandom%60)==0)) && (idle || early);
      cfg_bank={11'(($urandom%800==0)?(10+$urandom%3):col),
                5'(($urandom%3000==0)?(17+$urandom%5):($urandom%((col>=1 && col<=3)?17:7)))};
      cfg_row=7'($urandom%16);
      for(j=0;j<16;j=j+1) cfg_data[16*j+:16]={9'($urandom%14),7'($urandom%16)};
      start=live && (ph>=2500) && (($urandom%30)==0) && (gap || early);
      length=16'(1+$urandom%150);
      if(start && gap) begin last_s=cyc; last_l=length; end
      if(start && !gap) nrej=nrej+1;
      ns=ns+start; nw=nw+cfg_we; noor=noor+(cfg_we && cfg_bank[15:5]>=10);
      if(cyc>60 && ph>40) begin
        nc=nc+1; nv=nv+ao[1]; nf=nf+af; ndone=ndone+ao[2];
        if(ao[1]===1'b1 && ao[OWD-1:19]!=0) nz=nz+1;
        if(ao[1]===1'b1) for(j=0;j<10;j=j+1) if(ao[19+256*j+:166]!=0) nzc[j]=1'b1;
        if(ao!==bo || af!==b_fault) begin bad=bad+1;
          if(bad<=5) $display("PCOL_EQ_MISMATCH cycle=%0d ph=%0d busy %b/%b valid %b/%b done %b/%b fault %b/%b ei %0d/%0d cmd_eq %b",
            cyc,ph,ao[0],bo[0],ao[1],bo[1],ao[2],bo[2],af,b_fault,ao[18:3],bo[18:3],ao[OWD-1:19]===bo[OWD-1:19]);
        end
      end
    end
    if(bad==0) $display("PCOL_EQ PASS compared=%0d valid=%0d done=%0d nonzero_cmd=%0d columns_nonzero=%b fault_cycles=%0d resets=%0d starts=%0d in_busy=%0d writes=%0d oor_writes=%0d",
      nc,nv,ndone,nz,nzc,nf,nr,ns,nrej,nw,noor);
    else $display("PCOL_EQ FAIL SMUT=%0d mismatches=%0d of %0d valid=%0d",SMUT,bad,nc,nv);
    $finish;
  end
endmodule
