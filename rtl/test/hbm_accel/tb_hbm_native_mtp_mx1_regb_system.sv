`timescale 1ns/1ps
// mtp-lead 2026-10-09: MX1 REGB=1 system bench.  = tb_hbm_native_mtp_cp_closed_control_mx1 (Codex 9e6e2b20e: real
// native 40-layer controller, typed operation backend with two CP results, finite-8 host queue, synthetic SM
// arithmetic) with the join + queue replaced by the PHYSICAL top hfd_cmdproc_s_mtp_native_mx1 (registered MTP
// boundary, AR instance included) and the controller by the generic-die master hgi_mtp_native.  Every MTP
// interaction crosses the top's pins: job / host emit / host done (host), t_mtp / f_mtp (controller), t_backend /
// f_backend / f_am (backend), t_provider -> f_provider (forced-token read, 2 extra cycles: controller PRL 4).
// Same expectations as the reference: two drained-reset jobs, 4 emitted tokens each in order with identity,
// final commit 5, no fault, drained after done.  Parameters: MUT (top mutants), PRL (controller read wait).
module tb_hbm_native_mtp_mx1_regb_system #(parameter integer MUT=0, parameter integer PRL=4);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,jv=0,iv=0;reg [3:0] ik=0;reg [63:0] ipc=0;
 wire [516:0] fm;wire [196:0] tm;reg [178:0] cfg=0,provider=0;
 wire [4:0] th;wire accepted=jv&&th[0];
 wire bv,br,bcv,bcr,bcf,bam,bd;wire [16:0] bai;
 wire [200:0] bc;wire [31:0] bj,bs,cj,cs;wire [3:0] bg,cg;
 wire [270:0] tb;wire [99:0] teh;wire [42:0] tprov;wire [37:0] temit;wire abort,drained;
 wire hv=teh[0],hdv=teh[74];wire [72:0] hd=teh[1+:73];wire [20:0] ac=teh[78+:21];wire [2:0] hs=teh[75+:3];
 reg hr=0,dr=0;integer received=0,cycles=0,headpass=0,headrow=0,k,t,run=0;
 wire [31:0] lv;wire [63:0] pc;wire [33:0] tok;wire [39:0] pos;wire [145:0] owner;
 reg [31:0] sd=0,rv=0,q=0;reg [63:0] qp=0;reg [1023:0] rd=0;reg [16:0] winner=0;
 wire [16:0] forced_token=17'd100+tprov[20+:23];
 wire [178:0] fprov={provider[178:140],1'b0,provider[138:82],forced_token,provider[64:0]};
 wire [826:0] cSE,cSW;wire [63:0] suSE,suSW;wire [146:0] xl;wire [15:0] xt;
 hgi_mtp_native #(.PRL(PRL)) native(.clk(clk),.rst_n(rst_n),.f_cmdproc(tm),.t_cmdproc(fm),
  .f_router(59'b0),.t_router(),.t_coll(),.f_coll(1'b1));
 hfd_cmdproc_s_mtp_native_mx1 #(.ENABLE_MTP(1),.REGB(1),.MUT(MUT)) dut(.cSE(cSE),.cSW(cSW),.ck(clk),.rst(~rst_n),
  .f_loader(341'b0),.f_router(64'b0),.t_su_SE(suSE),.t_su_SW(suSW),.xb(16'b0),.xl(xl),.xt(xt),
  .f_mtp(fm),.t_mtp(tm),.f_host({cfg,4'hb,32'h12345678,jv}),.t_host(th),.f_provider(fprov),
  .t_emit(temit),.t_provider(tprov),.f_emit_host({dr,hr}),.t_emit_host(teh),.t_abort(abort),.t_drained(drained),
  .f_am({bai,bam}),.f_backend({1'b0,1'b1,bcf,cs,cg,cj,bcv,br}),.t_backend(tb));
 assign bv=tb[0];assign bc=tb[1+:201];assign bj=tb[202+:32];assign bg=tb[234+:4];assign bs=tb[238+:32];assign bcr=tb[270];
 ot_hbm_native_mtp_operation_backend_mx1 #(.ENABLE(1)) backend(
 .clk(clk),.rst_n(rst_n),.external_fault(abort),.backend_quiescent(1'b1),.install_v(iv),.install_kind(ik),.install_pc(ipc),.noise_token(17'd129279),
 .cmd_v(bv),.cmd_ready(br),.cmd(bc),.cmd_job(bj),.cmd_generation(bg),.cmd_sequence(bs),
 .cpl_v(bcv),.cpl_ready(bcr),.cpl_job(cj),.cpl_generation(cg),.cpl_sequence(cs),.cpl_fault(bcf),.am_v(bam),.am_idx(bai),
 .launch_v(lv),.launch_pc(pc),.launch_token(tok),.launch_pos(pos),.launch_owner(owner),.sm_done(sd),.sm_fault(32'b0),.res_v(rv),.res_data(rd),.drained_ready(bd));
 integer emits=0;
 always @(posedge clk)if(rst_n)begin
  cycles=cycles+1;hr<=cycles%5==0;
  if(temit[0])emits=emits+1;
  if(bv&&br&&bc[3:0]==1)begin headpass=headpass+1;headrow=0;end
  if(|lv && pc[31:0]==500)begin winner<=(headpass<=2)?7:100+headrow;headrow=headrow+1;end
  q<=lv;qp<=pc;sd<=q;rv<=0;rd<=0;
  if(qp[31:0]==500)begin rv<=q;for(k=0;k<32;k=k+1)rd[k*32+:32]<=winner;end
  if(hv&&hr)begin
   if(hd!=={4'hb,32'h12345678,20'(received),17'((received==0)?7:99+received)})$fatal(1,"composed emittedtoken/identity idx=%0d token=%0d expected=%0d",received,hd[16:0],(received==0)?7:99+received);received=received+1;
  end
  if(abort||th[3]||th[4]||bcf)$fatal(1,"composed control fault");
  if(hdv&&received!=4)$fatal(1,"host done overtook tokens (received %0d)",received);
  if(cycles>60000)$fatal(1,"finite controlinventory992launch watchdog");
 end
 initial begin
 repeat(3)begin @(negedge clk);if(th[0])$fatal(1,"job admitted during reset");end
 rst_n=1;
 for(run=0;run<2;run=run+1)begin
 for(t=0;t<11;t=t+1)begin iv=1;ik=t;ipc={32'(100*(t+1)+1),32'(100*(t+1))};@(negedge clk);end
 iv=0;repeat(5)@(negedge clk);
 cfg[1+:4]=5;cfg[5]=1;cfg[6+:21]=20;cfg[27+:21]=2;cfg[140]=1;cfg[141+:17]=102;cfg[158+:21]=1048576;
 provider[48+:17]=5;provider[65+:17]=100;
 jv=1;wait(accepted);@(negedge clk);jv=0;
 wait(hdv);@(negedge clk);
 if(received!=4||ac!=4||hs!=1||fm[357+:32]!=5)$fatal(1,"composed finalcommit received=%0d ac=%0d hs=%0d n=%0d",received,ac,hs,fm[357+:32]);
 if(emits!=4)$fatal(1,"t_emit accepted beats %0d != 4",emits);
 dr=1;@(negedge clk);dr=0;repeat(10)@(negedge clk);
 if(!drained||!bd||th[1]||th[2]||fm[43]||!fm[81]||fm[82])$fatal(1,"MX1 not drained");
 rst_n=0;repeat(4)@(negedge clk);
 received=0;headpass=0;headrow=0;sd=0;rv=0;q=0;qp=0;winner=0;emits=0;
 rst_n=1;repeat(6)@(negedge clk);
 end
 $display("PASS MX1 REGB system drained reset twice native40layer pairedresults finitequeue cycles=%0d",cycles);$finish;
 end
endmodule
