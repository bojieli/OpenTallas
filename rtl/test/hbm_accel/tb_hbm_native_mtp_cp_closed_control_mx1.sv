`timescale 1ns/1ps
// Minimum control component: real native40layer controller, guarded commands,
// typed lowering/twoCPs, and finite host output. SM arithmetic is synthetic.
module tb_hbm_native_mtp_cp_closed_control_mx1 #(parameter integer MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,jv=0,iv=0;reg [3:0] ik=0;reg [63:0] ipc=0;
 wire [516:0] fm;wire [196:0] tm;reg [178:0] cfg=0,provider=0;
 wire gjr,qjr;wire accepted=jv&&gjr&&qjr;
 wire bv,br,bcv,bcr,bcf,bam;wire [16:0] bai;
 wire [200:0] bc;wire [31:0] bj,bs,cj,cs;wire [3:0] bg,cg;
 wire active,inflight,gif,gfault,qfault,er,hv,hdv;wire [72:0] hd;wire [20:0] ac;wire [2:0] hs;
 reg hr=0,dr=0;integer received=0,cycles=0,headpass=0,headrow=0,target=0,k,t,run=0;
 wire [31:0] lv;wire [63:0] pc;wire [33:0] tok;wire [39:0] pos;wire [145:0] owner;
 reg [31:0] sd=0,rv=0,q=0;reg [63:0] qp=0;reg [1023:0] rd=0;reg [16:0] winner=0;
 wire [16:0] forced_token=17'd100+fm[20+:23];
 wire [178:0] ownedprovider={provider[178:140],er,provider[138:82],forced_token,provider[64:0]};
 hfd_mtp_native_cp_stop #(.ENABLE(1)) native(.clk(clk),.rst_n(rst_n),.f_cmdproc(tm),.t_cmdproc(fm),.f_su_red(523'b0),.f_router(59'b0),.f_coll(1'b1));
 ot_hbm_native_mtp_transaction_cp_join_mx1 #(.ENABLE(1)) guard(
 .clk(clk),.rst_n(rst_n),.external_fault(qfault),.backend_quiescent(1'b1),
 .job_v(jv&&qjr),.job_rdy(gjr),.job_id(32'h12345678),.job_generation(4'hb),.job_config(cfg),.provider_controls(ownedprovider),.f_mtp(fm),.t_mtp(tm),
 .eng_cmd_v(bv),.eng_cmd_rdy(br),.eng_cmd(bc),.eng_job(bj),.eng_generation(bg),.eng_sequence(bs),
 .cp_am_v(bam),.cp_am_idx(bai),.eng_cpl_v(bcv),.eng_cpl_rdy(bcr),.eng_cpl_job(cj),.eng_cpl_generation(cg),.eng_cpl_sequence(cs),.eng_cpl_fault(bcf),
 .active(active),.inflight(inflight),.identity_fault(gif),.fault(gfault));
 ot_hbm_native_mtp_operation_backend_mx1 #(.ENABLE(1)) backend(
 .clk(clk),.rst_n(rst_n),.external_fault(gfault),.backend_quiescent(1'b1),.install_v(iv),.install_kind(ik),.install_pc(ipc),.noise_token(17'd129279),
 .cmd_v(bv),.cmd_ready(br),.cmd(bc),.cmd_job(bj),.cmd_generation(bg),.cmd_sequence(bs),
 .cpl_v(bcv),.cpl_ready(bcr),.cpl_job(cj),.cpl_generation(cg),.cpl_sequence(cs),.cpl_fault(bcf),.am_v(bam),.am_idx(bai),
 .launch_v(lv),.launch_pc(pc),.launch_token(tok),.launch_pos(pos),.launch_owner(owner),.sm_done(sd),.sm_fault(32'b0),.res_v(rv),.res_data(rd));
 ot_hbm_native_mtp_emit_queue_mx1 #(.ENABLE(1)) queue(
 .clk(clk),.rst_n(rst_n),.external_fault(gfault),.job_v(jv&&gjr),.job_rdy(qjr),.job_id(32'h12345678),.job_generation(4'hb),
 .emit(fm[43+:38]),.native_done(fm[81]),.native_status(fm[514+:3]),.emit_ready(er),.host_v(hv),.host_ready(hr),.host_data(hd),.host_done_v(hdv),.host_done_ready(dr),.host_status(hs),.accepted_count(ac),.fault(qfault));
 always @(posedge clk)if(rst_n)begin
  cycles=cycles+1;hr<=cycles%5==0;
  if(bv&&br&&bc[3:0]==1)begin headpass=headpass+1;headrow=0;end
  if(|lv && pc[31:0]==500)begin winner<=(headpass<=2)?7:100+headrow;headrow=headrow+1;end
  q<=lv;qp<=pc;sd<=q;rv<=0;rd<=0;
  if(qp[31:0]==500)begin rv<=q;for(k=0;k<32;k=k+1)rd[k*32+:32]<=winner;end
  if(hv&&hr)begin
   if(hd!=={4'hb,32'h12345678,20'(received),17'((received==0)?7:99+received)})$fatal(1,"composed emittedtoken/identity idx=%0d token=%0d expected=%0d",received,hd[16:0],(received==0)?7:99+received);received=received+1;
  end
  if(gfault||qfault||gif||bcf)$fatal(1,"composed control fault");
  if(cycles>50000)$fatal(1,"finite controlinventory992launch watchdog");
 end
 initial begin
 repeat(3)begin @(negedge clk);if(gjr||qjr)$fatal(1,"job admitted during reset");end
 rst_n=1;
 for(run=0;run<2;run=run+1)begin
 for(t=0;t<11;t=t+1)begin iv=1;ik=t;ipc={32'(100*(t+1)+1),32'(100*(t+1))};@(negedge clk);end
 iv=0;repeat(5)@(negedge clk);
 cfg[1+:4]=5;cfg[5]=1;cfg[6+:21]=20;cfg[27+:21]=2;cfg[140]=1;cfg[141+:17]=102;cfg[158+:21]=1048576;
 provider[48+:17]=5;provider[65+:17]=100;
 jv=1;wait(accepted);@(negedge clk);jv=0;
 wait(hdv);@(negedge clk);
 if(received!=4||ac!=4||hs!=1||fm[357+:32]!=5)$fatal(1,"composed finalcommit");
 dr=1;@(negedge clk);dr=0;repeat(8)@(negedge clk);
 if(!gjr||!qjr||active||inflight||fm[43]||fm[81]||fm[82]||!br)$fatal(1,"MX1 not drained");
 rst_n=0;repeat(4)@(negedge clk);
 received=0;headpass=0;headrow=0;sd=0;rv=0;q=0;qp=0;winner=0;
 rst_n=1;repeat(6)@(negedge clk);
 end
 $display("PASS MX1 drained reset twice native40layer pairedresults finitequeue cycles=%0d",cycles);$finish;
 end
endmodule
