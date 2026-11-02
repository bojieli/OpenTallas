`timescale 1ns/1ps
// DIE-HBM-57/PSLICE 11-01: trunk top (OT_PSLICE_TRUNK) == gold cluster top (d34578d6f, modules prefixed gold_) with every
// input except rst_n delayed XST edges and every output delayed OSTG edges. Random config (incl. out-of-range banks),
// starts, lengths and periodic resets. TMUT != 0 must FAIL.
module tb_pslice_trunk;
  parameter integer XST=3, OSTG=1, HG=3, LFX=1, OSRC=0, EIDX=9, TMUT=0, TMUT_COL=1, SB=2470, CYC=40000;
  reg clk=1'b0; always #0.5 clk=~clk;
  reg rst_n=1'b0, cfg_we=1'b0, start=1'b0;
  reg [15:0] cfg_bank=0, length=0; reg [6:0] cfg_row=0; reg [255:0] cfg_data=0;
  // gold input delay line (XST edges)
  localparam integer IW=1+16+7+256+1+16;
  reg [IW-1:0] dl [0:XST-1]; wire [IW-1:0] din={cfg_we,cfg_bank,cfg_row,cfg_data,start,length};
  integer i;
  always @(posedge clk) begin dl[0]<=din; for(i=1;i<XST;i=i+1) dl[i]<=dl[i-1]; end
  wire [IW-1:0] gi=dl[XST-1];
  wire a_busy,a_valid,a_done,a_fault,b_busy,b_valid,b_done,b_fault; wire [15:0] a_ei,b_ei; wire [SB-1:0] a_cmd,b_cmd;
  gold_ot_hbm_su_programme_pslice_c5 #(.SB(SB)) u_g(.clk(clk),.rst_n(rst_n),.cfg_we(gi[IW-1]),.cfg_bank(gi[IW-2-:16]),
    .cfg_row(gi[IW-18-:7]),.cfg_data(gi[IW-25-:256]),.start(gi[16]),.length(gi[15:0]),.busy(a_busy),.valid(a_valid),
    .done(a_done),.fault(a_fault),.edge_index(a_ei),.command(a_cmd));
  localparam integer OWD=4+16+SB;
  reg [OWD-1:0] ol [0:(OSTG>0?OSTG:1)-1]; wire [OWD-1:0] oin={a_cmd,a_ei,a_fault,a_done,a_valid,a_busy};
  always @(posedge clk) begin ol[0]<=oin; for(i=1;i<OSTG;i=i+1) ol[i]<=ol[i-1]; end
  wire [OWD-1:0] ao=(OSTG>0)?ol[(OSTG>0?OSTG:1)-1]:oin;
  ot_hbm_su_programme_pslice_c5 #(.SB(SB),.XST(XST),.OSTG(OSTG),.HG(HG),.LFX(LFX),.OSRC(OSRC),.EIDX(EIDX),.TMUT(TMUT),
    .TMUT_COL(TMUT_COL)) u_t(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),
    .cfg_data(cfg_data),.start(start),.length(length),.busy(b_busy),.valid(b_valid),.done(b_done),.fault(b_fault),
    .edge_index(b_ei),.command(b_cmd));
  wire [OWD-1:0] bo={b_cmd,b_ei,b_fault,b_done,b_valid,b_busy};
  integer col; integer cyc, bad=0, nc=0, nv=0, nf=0, nz=0, nr=0, ns=0, ph=0;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      ph=cyc%5000;
      rst_n=(ph>=16);                              // periodic reset (fault is sticky)
      if(ph==16) nr=nr+1;
      // phase: 16..2500 config heavy, then mostly starts; occasional out-of-range bank (head fault)
      cfg_we=(ph<2500)?(($urandom%2)==0):(($urandom%60)==0);
      // mostly legal writes; rare out-of-range column (head fault) and rare bank over a leaf's capacity (leaf fault); dictionary AND index banks (DB + 4 per leaf) are written,
      // so the sticky fault rises at a random edge inside most reset windows
      col=$urandom%10;
      cfg_bank={11'(($urandom%3000==0)?(10+$urandom%3):col),
                5'(($urandom%3000==0)?(17+$urandom%5):($urandom%((col>=1 && col<=3)?17:7)))};
      cfg_row=7'($urandom); cfg_data={8{$urandom}};
      start=(ph>=2500)&&(($urandom%30)==0); length=16'(1+$urandom%150);
      ns=ns+start;
      if(cyc>60 && ph>40) begin
        nc=nc+1; nv=nv+a_valid; nf=nf+ao[3]; nz=nz+(ao[1] && ao[OWD-1:20]!=0);
        if(ao!==bo) begin bad=bad+1;
          if(bad<=5) $display("TRUNK_EQ_MISMATCH cycle=%0d busy %b/%b valid %b/%b done %b/%b fault %b/%b ei %0d/%0d cmd_eq %b",
            cyc,ao[0],bo[0],ao[1],bo[1],ao[2],bo[2],ao[3],bo[3],ao[19:4],bo[19:4],ao[OWD-1:20]==bo[OWD-1:20]);
        end
      end
    end
    if(bad==0) $display("TRUNK_EQ PASS XST=%0d OSTG=%0d HG=%0d LFX=%0d OSRC=%0d EIDX=%0d TMUT=%0d compared=%0d valid=%0d nonzero_cmd=%0d fault_cycles=%0d resets=%0d starts=%0d",
      XST,OSTG,HG,LFX,OSRC,EIDX,TMUT,nc,nv,nz,nf,nr,ns);
    else $display("TRUNK_EQ FAIL XST=%0d OSTG=%0d HG=%0d LFX=%0d TMUT=%0d mismatches=%0d of %0d",XST,OSTG,HG,LFX,TMUT,bad,nc);
    $finish;
  end
endmodule
