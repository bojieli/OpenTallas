`timescale 1ns/1ps
module tb_hgi_sfu_static_calendar;
localparam N=16, AW=24, NW=16, WC=130+8+1+2+1+1+4+3+1+1+8+AW+5+1;
reg clk=0; always #0.416667 clk=~clk;
reg rst_n=0;
parameter integer MUT_PHASE=0, SPLIT_S_PIPE=0;
reg  go = '0;
reg [NW-1:0] i_nout = '0;
reg [NW-1:0] i_nin = '0;
reg [1:0] i_asrc = '0;
reg [1:0] i_bsrc = '0;
reg [1:0] i_csrc = '0;
reg [1:0] i_dsrc = '0;
reg [AW-1:0] i_abase = '0;
reg [AW-1:0] i_aso = '0;
reg [AW-1:0] i_asi = '0;
reg [AW-1:0] i_aibase = '0;
reg [1:0] i_aind = '0;
reg [AW-1:0] i_bbase = '0;
reg [AW-1:0] i_bso = '0;
reg [AW-1:0] i_bsi = '0;
reg  i_bhalf = '0;
reg [AW-1:0] i_cbase = '0;
reg [AW-1:0] i_cso = '0;
reg [AW-1:0] i_csi = '0;
reg  i_cpair = '0;
reg [AW-1:0] i_dbase = '0;
reg [AW-1:0] i_dso = '0;
reg [AW-1:0] i_dsi = '0;
reg  i_arnd = '0;
reg  i_arelu = '0;
reg  i_amin = '0;
reg  i_cclip = '0;
reg [2:0] i_m1 = '0;
reg [1:0] i_m2 = '0;
reg [2:0] i_qm = '0;
reg [2:0] i_ad = '0;
reg [2:0] i_sfu = '0;
reg [2:0] i_e1 = '0;
reg [1:0] i_e2 = '0;
reg  i_rnd = '0;
reg [1:0] i_dst = '0;
reg [AW-1:0] i_obase = '0;
reg [AW-1:0] i_oso = '0;
reg [AW-1:0] i_osi = '0;
reg [AW-1:0] i_orow = '0;
reg [1:0] i_red = '0;
reg  i_redsq = '0;
reg  i_redwhole = '0;
reg  i_redtree = '0;
reg  i_redrnd = '0;
reg [AW-1:0] i_rbase = '0;
reg [AW-1:0] i_rso = '0;
reg [31:0] i_imm1 = '0;
reg [31:0] i_imm2 = '0;
reg [31:0] i_imm3 = '0;
reg [1:0] i_ch_src = '0;
reg [7:0] i_ch_seq = '0;
reg [15:0] i_ch_lead = '0;
reg [15:0] i_ch_mul = '0;
reg [7:0] x_seq = '0;
reg [7:0] x_dseq = '0;
reg [15:0] x_cnt = '0;
wire [1741:0] actual; wire ready; wire admission_fault;
wire [15:0] avw,ovw,avr,ovr;wire [383:0] ava,ova,avi,ovi;
wire [511:0] avd,ovd;wire [1535:0] ard,ord;wire [63:0] arre,orre;
reg [2047:0] ardq='0,ordq='0;reg [511:0] aviq='0,oviq='0;
function automatic [31:0] memword(input [23:0] a);memword={1'b0,8'h7e,a[22:0]^23'h312345};endfunction
always @(posedge clk)begin
for(integer j=0;j<16;j++)begin
 if(avr[j])aviq[j*32+:32]<=memword(avi[j*24+:24]);
 if(ovr[j])oviq[j*32+:32]<=memword(ovi[j*24+:24]);
 for(integer k=0;k<4;k++)begin
 if(arre[j*4+k])ardq[(j*4+k)*32+:32]<=memword(ard[(j*4+k)*24+:24]);
 if(orre[j*4+k])ordq[(j*4+k)*32+:32]<=memword(ord[(j*4+k)*24+:24]);
end end end
reg [1741:0] compiled [0:8191];
reg [15:0] expected_we[0:8191];
reg [383:0] expected_addr[0:8191];
reg [511:0] expected_data[0:8191];
reg [1741:0] compiler_control=0;
ot_hgi_sfu_static_quarter dut(.clk_control(clk),.rst_control_n(rst_n),.compiler_control(compiler_control),
.clk_lane({16{clk}}),.clk_map({16{clk}}),.rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),
.vi_q(aviq),.rd_q(ardq),.side_y(512'd0),.vi_re(avr),.vi_addr(avi),.rd_addr(ard),.rd_re(arre),
.vm_we(avw),.vm_waddr(ava),.vm_wdata(avd));
ot_hdc_v41x_vec #(.N(16),.M(16),.AW(24),.NW(16),.MLAT(6),.ALAT(6),.DDIV(21),.OPR(1),.CAPR(1),.GSH(1),.KIMM(1),.DENR(1),.DRING(3),.BCAST_STAGES(1),.RET_STAGES(5),.CTL12(2),.SIDEX(4)) oracle(.go(go),.i_nout(i_nout),.i_nin(i_nin),.i_asrc(i_asrc),.i_bsrc(i_bsrc),.i_csrc(i_csrc),.i_dsrc(i_dsrc),.i_abase(i_abase),.i_aso(i_aso),.i_asi(i_asi),.i_aibase(i_aibase),.i_aind(i_aind),.i_bbase(i_bbase),.i_bso(i_bso),.i_bsi(i_bsi),.i_bhalf(i_bhalf),.i_cbase(i_cbase),.i_cso(i_cso),.i_csi(i_csi),.i_cpair(i_cpair),.i_dbase(i_dbase),.i_dso(i_dso),.i_dsi(i_dsi),.i_arnd(i_arnd),.i_arelu(i_arelu),.i_amin(i_amin),.i_cclip(i_cclip),.i_m1(i_m1),.i_m2(i_m2),.i_qm(i_qm),.i_ad(i_ad),.i_sfu(i_sfu),.i_e1(i_e1),.i_e2(i_e2),.i_rnd(i_rnd),.i_dst(i_dst),.i_obase(i_obase),.i_oso(i_oso),.i_osi(i_osi),.i_orow(i_orow),.i_red(i_red),.i_redsq(i_redsq),.i_redwhole(i_redwhole),.i_redtree(i_redtree),.i_redrnd(i_redrnd),.i_rbase(i_rbase),.i_rso(i_rso),.i_imm1(i_imm1),.i_imm2(i_imm2),.i_imm3(i_imm3),.i_ch_src(i_ch_src),.i_ch_seq(i_ch_seq),.i_ch_lead(i_ch_lead),.i_ch_mul(i_ch_mul),.x_seq(x_seq),.x_dseq(x_dseq),.x_cnt(x_cnt),.clk(clk),.rst_n(rst_n),.vi_q(oviq),.rd_q(ordq),.vi_re(ovr),.vi_addr(ovi),.rd_addr(ord),.rd_re(orre),.vm_we(ovw),.vm_waddr(ova),.vm_wdata(ovd));
wire [1199:0] oracle_terms;
for(genvar s=0;s<5;s++)for(genvar b=0;b<10;b++) begin
if(b<4)assign oracle_terms[(s*10+b)*24+:24]=oracle.tr_ldc[(s*4+b)*24+:24];else assign oracle_terms[(s*10+b)*24+:24]=0;end
wire [1741:0] expected={oracle.tr_ld,oracle.tr_ldbank,oracle_terms,oracle.tr_emit,oracle.tr_bank,oracle.tr_ov,oracle.tr_iv,oracle.tr_no,oracle.tr_ni,oracle.tr_ls,oracle.tr_lvw,oracle.tr_vb,oracle.tr_krow,oracle.tr_obase,oracle.tr_aibase,oracle.tr_aind,oracle.tr_gsh,oracle.tr_cpair,oracle.tr_dst,oracle.tr_srcs,oracle.cwx[WC-9],oracle.cwx[WC-10],oracle.cwx[WC-11],oracle.cwx[WC-12],oracle.cwx[WC-13 -: 32],oracle.cwp[WC-45 -: 3],oracle.cwp[WC-48 -: 32],oracle.cwm[WC-45 -: 3],oracle.cwm[WC-80 -: 2],oracle.cwm[WC-82 -: 3],oracle.cwm[WC-48 -: 32],oracle.cwa[WC-85 -: 3],oracle.cwa[WC-88 -: 32],oracle.cwi[WC-120 -: 3],oracle.cws[WC-120 -: 3],oracle.cws[WC-123 -: 3],oracle.cws[WC-88 -: 32],oracle.cwe[WC-126 -: 2],oracle.cwe[WC-48 -: 32],oracle.cwo[WC-128],oracle.cwo[WC-129 -: 2]};

reg [31:0] gold [0:32767];
reg seen[0:32767];
string image;
integer checks=0,words=0,cycles=0,case_words=0,total_cycles=0;
task reset_all;
begin
 @(negedge clk);rst_n=0;go=0;compiler_control=0;
 repeat(8)@(negedge clk);rst_n=1;
 repeat(8)@(negedge clk);
end endtask
initial begin
 i_dst=1;i_asrc=0;i_bsrc=0;i_csrc=0;i_dsrc=0;
 i_asi=1;i_bsi=1;i_csi=1;i_dsi=1;i_osi=1;
 i_imm1=32'h3f800000;i_imm2=32'h3f800000;i_imm3=32'h3f800000;
 x_seq=8'hff;x_dseq=8'hff;
 // Production vector dimensions, actual sixteen-lane arithmetic. The legacy
 // controller is ONLY an exact word oracle in pass 1. Pass 2 never runs
 // that controller: independently lowered Python image drives the engine.
 for(integer c=0;c<4;c++)begin
  i_nout=(c==3)?4:1;i_nin=(c==0)?4096:7168;
  i_aso=i_nin;i_bso=i_nin;i_cso=i_nin;i_dso=i_nin;i_oso=i_nin;
  i_abase=0;i_bbase=16384;i_cbase=32768;i_dbase=49152;i_obase=131072;
  i_m1=3'(c%3);i_m2=2'(c%2);i_ad=3'(c%3);i_sfu=(c==0)?1:(c==1)?4:(c==2)?5:0;
  i_e1=3'(c%2);i_e2=2'(c%2);
  reset_all();go=1;
  for(integer t=0;t<4096;t++)begin
   // Control is recorded before the edge that consumes it. Oracle output is
   // sampled after that edge and compared one edge later on replay.
   compiled[t]=expected;
   @(posedge clk);#0.001;
   expected_we[t]=ovw;expected_addr[t]=ova;expected_data[t]=ovd;
   for(integer j=0;j<16;j++)if(ovw[j])gold[ova[j*24+:24]-131072]=ovd[j*32+:32];
   @(negedge clk);go=0;
  end
  reset_all();case_words=0;
  for(integer k=0;k<32768;k++)seen[k]=0;
  image=$sformatf("%s/case%0d.hex", `SFU_IMAGE_DIR,c);
  $readmemh(image,compiled,0,4095);
  for(integer t=0;t<4097;t++)begin
   compiler_control=(t<4096)?compiled[t]:0;
   // Actual calendar mutant: suppress the first scheduled issue beat.
   if($test$plusargs("MUT_DROP") && t==8)compiler_control=0;
   @(posedge clk);#0.001;
   if(t>0)begin
    for(integer j=0;j<16;j++)if(avw[j])begin
     if(ava[j*24+:24]<131072 || ava[j*24+:24]>=131072+i_nout*i_nin)
      $fatal(1,"CALENDAR_ADDR case=%0d addr=%h",c,ava[j*24+:24]);
     if(seen[ava[j*24+:24]-131072] || avd[j*32+:32]!==gold[ava[j*24+:24]-131072])
      $fatal(1,"CALENDAR_WORD case=%0d edge=%0d lane=%0d",c,t,j);
     seen[ava[j*24+:24]-131072]=1;
     words++;case_words++;
    end
    checks++;
   end
   @(negedge clk);
  end
  if(case_words!=i_nout*i_nin)$fatal(1,"STATIC_SHAPE case=%0d got=%0d expected=%0d",c,case_words,i_nout*i_nin);
  $display("SFU_STATIC_CASE case=%0d shape=%0dx%0d words=%0d",c,i_nout,i_nin,case_words);
 end
 $display("PASS SFU static actual16lanes checks=%0d exact_words=%0d independent_vector_compiler=1 production_layer_calendar=unbound memory_contract=external",checks,words);$finish;
end
endmodule
