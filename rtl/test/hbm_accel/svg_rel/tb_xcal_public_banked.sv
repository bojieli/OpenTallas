`timescale 1ps/1ps
module tb_xcal_public_banked;
 parameter integer MUT=0,PREL=1,CLASS_ENABLE=0,CLASS_MUT=0,MIRROR_MUT=0,GAP=9;
 reg clk_core=0;always #417 clk_core=~clk_core;
 wire clk_bank0=clk_core,clk_bank1=clk_core;
 reg rst_n=0;reg [7:0] tgt=8'hc0,cfg_target=8'hc0;
 reg cfg_v=0,desc_v=0,launch_v=0;reg [11:0] cfg_addr=0,desc_base=0;
 reg [12:0] desc_limit=1;reg [15:0] desc_loops=3;reg [255:0] cfg_data=0;
 wire [108:0] cmd_ext,old_cmd;wire [63:0] kv_desc,old_kv;
 wire done,configured,fault,active,old_done,old_configured,old_fault,old_active;
 wire [174:0] command_envelope;wire command_class_observe,command_context_valid_observe;
 ot_hbm_svc_sm_xcal_rel_t_banked #(.MUT(MUT),.PREL(PREL),.CLASS_ENABLE(CLASS_ENABLE),.CLASS_MUT(CLASS_MUT),.MIRROR_MUT(MIRROR_MUT)) dut(.*);
 ot_hbm_svc_sm_xcal_rel_t #(.PREL(PREL)) reference_dut(
  .clk(clk_core),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
  .cmd_ext(old_cmd),.kv_desc(old_kv),.done(old_done),.configured(old_configured),.fault(old_fault),.active(old_active));
 // Independent class/valid association alongside canonical R/C, not DUT metadata.
 reg cr=0,cc=0,vr=0,vc=0;
 always @(posedge clk_core or negedge rst_n)begin
  if(!rst_n)begin cr<=0;cc<=0;vr<=0;vc<=0;end
  else begin
   cr<=reference_dut.u_xcal.cal_v?reference_dut.u_xcal.wctx[4]:0;cc<=cr;
   vr<=reference_dut.u_xcal.cal_v;vc<=vr;
   if(PREL!=0&&reference_dut.u_xcal.cal_v&&reference_dut.u_xcal.word_ord==0&&reference_dut.u_xcal.wctx[0])begin
    cc<=reference_dut.u_xcal.wctx[4];vc<=1;
   end
  end
 end
 wire [174:0] old_envelope={CLASS_ENABLE!=0?(PREL!=0?vc:vr):1'b0,CLASS_ENABLE!=0?(PREL!=0?cc:cr):1'b0,old_kv,old_cmd};
 reg [174:0] hist[0:3];reg [2:0] status_hist[0:3];
 integer errors=0,checks=0,edges=0,scenario=0,launch_edge=0,first_old=-1,first_new=-1;
 integer words=0,old_words=0,done_count=0,old_done_count=0,last_done=-1,last_cal_done=-1,last_word=-1;
 integer naive_premature=0,go_count=0,seen_go_done_simultaneous=0;
 integer score_outstanding=0,score_completions=0,expected_programmes=1,final_drain_edge=-1,active_gap_repairs=0;
 reg first_go_seen=0;reg go_before,cal_done_before;reg [4:0] busy_hist=0;
 reg checking=0,tight=0,expect_fault=0;integer i,j;
 always @(posedge clk_core)begin
  edges=edges+1;go_before=dut.u_xcal.go;cal_done_before=dut.u_xcal.cal_done;
  if(checking)begin
   if(go_before)begin score_outstanding=score_outstanding+1;go_count=go_count+1;first_go_seen=1;$display("PUBLIC_GO scenario=%0d edge=%0d",scenario,edges);end
   if(cal_done_before)begin
    score_outstanding=score_outstanding-1;score_completions=score_completions+1;
    $display("PUBLIC_CAL_DONE scenario=%0d edge=%0d remaining=%0d",scenario,edges,score_outstanding);
    if(score_completions==expected_programmes)final_drain_edge=edges;
   end
   if(go_before&&cal_done_before)seen_go_done_simultaneous=seen_go_done_simultaneous+1;
  end
  if(launch_v)launch_edge=edges;
  #100;
  if(checking)begin
   checks=checks+1;
   if(command_envelope!==hist[3])begin
    errors=errors+1;if(errors<8)$display("PUBLIC_ENVELOPE_MISMATCH scenario=%0d edge=%0d got=%h expected=%h",scenario,edges,command_envelope,hist[3]);
   end
   if({cmd_ext,kv_desc}!={command_envelope[108:0],command_envelope[172:109]}||
      command_class_observe!==command_envelope[173]||command_context_valid_observe!==command_envelope[174])begin
    errors=errors+1;if(errors<8)$display("PUBLIC_ENVELOPE_ALIAS_FAIL");
   end
   if(configured!==old_configured)begin errors=errors+1;if(errors<8)$display("PUBLIC_CONFIG_CHRONOLOGY_FAIL");end
   // Done/fault remain strict canonical+4, including tight twoGO runs.
   if({done,fault}!==status_hist[3][1:0])begin
    errors=errors+1;if(errors<8)$display("PUBLIC_STATUS_MISMATCH scenario=%0d edge=%0d got=%b expected=%b",scenario,edges,{active,done,fault},status_hist[3]);
   end
   if(active!==status_hist[3][2])begin
    if(active===1'b1&&status_hist[3][2]===1'b0&&busy_hist[4])begin
     active_gap_repairs=active_gap_repairs+1;
     $display("PUBLIC_ACTIVE_GAP_REPAIR scenario=%0d edge=%0d independent_outstanding5=%b dut_outstanding=%0d running=%b app_active=%b",scenario,edges,busy_hist[4],dut.u_xcal.n_done,dut.u_xcal.running,dut.u_xcal.cal_active);
    end else begin errors=errors+1;if(errors<8)$display("PUBLIC_UNEXPLAINED_ACTIVE_MISMATCH scenario=%0d edge=%0d ledger5=%b",scenario,edges,busy_hist[4]);end
   end
   if(dut.u_xcal.n_done!==9'(score_outstanding))begin errors=errors+1;if(errors<8)$display("PUBLIC_OUTSTANDING_LEDGER_FAIL expected=%0d got=%0d",score_outstanding,dut.u_xcal.n_done);end
   if(first_go_seen&&(final_drain_edge<0||edges<final_drain_edge+5)&&active!==1'b1)begin
    errors=errors+1;if(errors<8)$display("PUBLIC_ACTIVE_DRAIN_INVARIANT_FAIL edge=%0d final=%0d",edges,final_drain_edge);
   end
   if(final_drain_edge>=0&&edges==final_drain_edge+5&&active!==1'b0)begin errors=errors+1;$display("PUBLIC_ACTIVE_TAIL_FAIL");end
   if((cmd_ext!=0||kv_desc!=0)&&launch_edge!=0)begin words=words+1;last_word=edges;if(first_new<0)first_new=edges;end
   if((old_cmd!=0||old_kv!=0)&&launch_edge!=0)begin old_words=old_words+1;if(first_old<0)first_old=edges;end
   if(done)begin done_count=done_count+1;last_done=edges;end
   if(old_done)old_done_count=old_done_count+1;
   if(dut.u_xcal.cal_done)begin
    last_cal_done=edges;
    if(!dut.u_xcal.running&&dut.u_xcal.n_done>1)begin naive_premature=naive_premature+1;$display("PUBLIC_OLD_DONE_PREDICATE_WITNESS scenario=%0d outstanding=%0d edge=%0d",scenario,dut.u_xcal.n_done,edges);end
   end
   busy_hist={busy_hist[3:0],score_outstanding!=0};
  end
  for(i=3;i>0;i=i-1)begin hist[i]=hist[i-1];status_hist[i]=status_hist[i-1];end
  hist[0]=old_envelope;status_hist[0]={old_active,old_done,old_fault};
 end
 generate if(MUT==4)begin:g_raw_observer_check
  always @(posedge clk_core)begin #100;if(checking&&
   (dut.u_xcal.g_bypass_rc.raw_request0!==dut.u_xcal.request0||dut.u_xcal.g_bypass_rc.raw_request1!==dut.u_xcal.request1))begin
   errors=errors+1;if(errors<8)$display("PUBLIC_RAW_OBSERVER_REQUEST_FAIL");
  end end
 end endgenerate
 task idle(input integer n);begin repeat(n)@(negedge clk_core);end endtask
 task wr(input [7:0] id,input [11:0] addr,input [255:0] data);begin
  @(negedge clk_core);cfg_target=id;cfg_addr=addr;cfg_data=data;cfg_v=1;
  @(negedge clk_core);cfg_v=0;idle(6);
 end endtask
 function automatic [11:0] window_addr(input integer pc);
  window_addr=pc<1024?12'(pc):12'h800+12'(pc-1024);
 endfunction
 function automatic [255:0] programme(input integer pc,index,mode);
  reg [255:0] p;begin
   p=0;p[255:240]=16'hc7a1;p[234:224]=11'(pc);
   p[172:109]=64'h8000000000000001^(64'h0123456789abcdef*64'(index+1));
   case(index%4)
    0:begin p[108:101]=8'ha2;p[100:98]=3'(mode);p[82:0]=0;end
    1:begin p[108:101]=8'ha2;p[100:98]=3'(mode);p[97:0]=98'h123456789abcdef01234567;end
    2:begin p[108:101]=8'h51;p[100:0]=101'h123456789abcdef0123456789;end
    default:begin p[108:0]=0;end
   endcase
   programme=p;
  end
 endfunction
 function automatic [255:0] descriptor(input integer row,pc,limit,loops,at,mode,mrel,fl,bad200);
  reg [255:0] d;begin
   d=0;d[255:240]=16'h5d15;d[239:232]=8'(row);
   d[189]=1'(pc>>10);d[91:82]=10'(pc);d[190]=1'(limit>>11);d[102:92]=11'(limit);
   d[118:103]=16'(loops);d[142:119]=24'(at);d[197:195]=3'(mode);d[198]=1'(mrel);d[199]=1'(fl);d[200]=1'(bad200);
   descriptor=d;
  end
 endfunction
 task reset_case(input integer id);begin
  checking=0;rst_n=0;cfg_v=0;desc_v=0;launch_v=0;idle(6);rst_n=1;idle(20);
  scenario=id;launch_edge=0;first_old=-1;first_new=-1;words=0;old_words=0;done_count=0;old_done_count=0;
  last_done=-1;last_cal_done=-1;last_word=-1;naive_premature=0;go_count=0;seen_go_done_simultaneous=0;score_outstanding=0;score_completions=0;final_drain_edge=-1;first_go_seen=0;busy_hist=0;active_gap_repairs=0;
 end endtask
 task run_case(input integer id,multi,bad200,pc,mode,fl,loops);
  integer row,at;reg [255:0] p;begin
   reset_case(id);tight=multi!=0;expected_programmes=multi+1;expect_fault=bad200!=0;row=multi?127:255;
   for(j=0;j<4;j=j+1)wr(8'hc0,window_addr(pc+j),programme(pc+j,j,mode));
   p=programme(pc,0,mode);p[108:0]=109'd999;p[172:109]=64'hfedcba9876543210;
   wr(8'hc1,window_addr(pc),p); // Mut5 must expose an ignored target id.
   wr(8'hc0,12'h400+12'(row),descriptor(row,pc,pc+4,loops,20,mode,id==1?0:1,fl,bad200));
   if(multi)wr(8'hc0,12'h400+12'(row+1),descriptor(row+1,pc,pc+4,loops,20+GAP,mode,id==1?0:1,fl,bad200));
   desc_base=12'(row);desc_limit=13'(row+1+multi);desc_loops=3;
   @(negedge clk_core);desc_v=1;@(negedge clk_core);desc_v=0;idle(8);
   if(!configured)begin errors=errors+1;$display("PUBLIC_CONFIG_NOT_ARMED scenario=%0d",id);end
   checking=1;
   @(negedge clk_core);launch_v=1;@(negedge clk_core);launch_v=0;idle(100+loops*8);
   if(words!=old_words||first_new-first_old!=4)begin errors=errors+1;$display("PUBLIC_COUNTS_FAIL scenario=%0d words=%0d/%0d first_delta=%0d",id,words,old_words,first_new-first_old);end
   if(fault!==expect_fault)begin errors=errors+1;$display("PUBLIC_FAULT_FAIL scenario=%0d fault=%b expected=%b",id,fault,expect_fault);end
   if(done_count!=1||active)begin errors=errors+1;$display("PUBLIC_COMPLETION_FAIL scenario=%0d done=%0d active=%b old_done=%0d",id,done_count,active,old_done_count);end
   if(go_count!=expected_programmes||score_completions!=expected_programmes||score_outstanding!=0)begin errors=errors+1;$display("PUBLIC_LEDGER_COUNTS_FAIL");end
   if(multi&&GAP==9&&naive_premature!=1)begin errors=errors+1;$display("PUBLIC_OLD_DONE_WITNESS_MISSING");end
   if(multi&&GAP==11&&seen_go_done_simultaneous!=1)begin errors=errors+1;$display("PUBLIC_SIMULTANEOUS_GO_DONE_MISSING");end
   if(multi&&last_done!=last_cal_done+3)begin errors=errors+1;$display("PUBLIC_FINAL_DONE_EDGE_FAIL final=%0d calendar=%0d",last_done,last_cal_done);end
   $display("PUBLIC_CASE scenario=%0d words=%0d/%0d first_delta=%0d done=%0d old_done=%0d go=%0d naive_early=%0d simultaneous=%0d active_gap_repairs=%0d",id,words,old_words,first_new-first_old,done_count,old_done_count,go_count,naive_premature,seen_go_done_simultaneous,active_gap_repairs);
   checking=0;
  end
 endtask
 initial begin
  for(i=0;i<4;i=i+1)begin hist[i]=0;status_hist[i]=0;end
  run_case(0,0,0,1022,5,1,1); // both program banks, format edge, post-mrel class1
  run_case(1,0,0,2044,2,0,2); // last programme row2047, full KV and loops
  run_case(2,1,0,1022,4,1,1); // descriptor127/128 crossing, tight twoGO
  run_case(3,0,1,1022,1,0,1); // reserved bit200 remains illegal, no class reuse
  $display("XCAL_PUBLIC_BANKED %s errors=%0d checks=%0d mut=%0d prel=%0d class=%0d classmut=%0d mirrormut=%0d gap=%0d",errors==0?"PASS":"FAIL",errors,checks,MUT,PREL,CLASS_ENABLE,CLASS_MUT,MIRROR_MUT,GAP);
  if(errors)$fatal(1,"public banked XC mismatch");$finish;
 end
endmodule
