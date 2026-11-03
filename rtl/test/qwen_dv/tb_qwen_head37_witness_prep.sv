`timescale 1ns/1ps
// Small source-only observer/controller bench. Same stimulus ABI as TWC vectors.
module tb_qwen_head37_witness_prep #(parameter HEAD=1, SAFE=0, SELECT=0, PHYS=0, PAIR=0,
 parameter [63:0] DIGEST=64'hd24441af3d8d3139);
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg pv=0;reg[9:0]pa=0;reg[63:0]pd=0;reg au=0,fc=0;reg[63:0]di=0;reg[15:0]pe=0;
 reg sv=0;reg[1:0]su=0;reg[5:0]ss=0;reg[15:0]se=0;
 reg rv=0;reg[1:0]ru=0;reg me=0;
 reg issue=0;reg[1:0]iu=0;reg[3:0]isl=0;reg[8:0]ip=0;
 reg[5:0]es=0,esn=0;reg[15:0]ee=0,een=0;
 wire[15:0]ob;wire ofault;
 qfd_dv_typed_su_observer #(.ENABLE(1)) obs(.ck(ck),.rst_n(rst_n),.su_issue(issue),.cmd_user(iu),.su_pidx(ip),.cmd_slice(isl),.observation(ob),.fault(ofault));
 wire tr,gc,f;wire[3:0]ca,ac;wire[1:0]cu;wire[3:0]cg;
 qfd_dv_typed_witness_control_head37 #(.ENABLE(1),.HEAD_STAGE37(HEAD),.HEAD_PROFILE_DIGEST(DIGEST),.SAFE_COMPARE(SAFE),.SAFE_SELECT(SELECT),.SAFE_PHYS(PHYS)) dut(
 .ck(ck),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),.all_copies_authenticated(au),.fusedcap(fc),.installed_digest(di),.installed_epoch(pe),
 .start_v(sv),.start_user(su),.start_stage(ss),.start_epoch(se),.retire_v(rv),.retire_user(ru),.ME_XPF_retired(me),.observation(ob),.event_stage(es),.event_epoch(ee),
 .template_ready(tr),.context_active(ca),.all_witnesses_complete(ac),.group_complete(gc),.complete_user(cu),.complete_group(cg),.fault(f));
 generate if(PAIR)begin:refcheck
 wire rtr,rgc,rf;wire[3:0]rca,rac;wire[1:0]rcu;wire[3:0]rcg;
 qfd_dv_typed_witness_control #(.ENABLE(1),.SAFE_COMPARE(SAFE),.SAFE_SELECT(SELECT),.SAFE_PHYS(PHYS)) refdut(
 .ck(ck),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),.all_copies_authenticated(au),.fusedcap(fc),.installed_digest(di),.installed_epoch(pe),
 .start_v(sv),.start_user(su),.start_stage(ss),.start_epoch(se),.retire_v(rv),.retire_user(ru),.ME_XPF_retired(me),.observation(ob),.event_stage(es),.event_epoch(ee),
 .template_ready(rtr),.context_active(rca),.all_witnesses_complete(rac),.group_complete(rgc),.complete_user(rcu),.complete_group(rcg),.fault(rf));
 always @(negedge ck)if(rst_n&&{tr,ca,ac,gc,cu,cg,f}!=={rtr,rca,rac,rgc,rcu,rcg,rf})$fatal(1,"DEFAULT_BASE_EDGE_MISMATCH");
 end endgenerate
 integer fd,r,t,k,a,b,c,d,e,edge_i=0,have=0,done=0,groups=0,firstfault=-1,ready=0,expect_groups,expect_fault;
 integer nextgroup[0:3];reg[3:0]users=0;reg[14:0]coverage=0;string stim;
 initial begin
 if(!$value$plusargs("STIM=%s",stim))$fatal(1,"STIM required");
 if(!$value$plusargs("GROUPS=%d",expect_groups))expect_groups=8;
 if(!$value$plusargs("FAULT=%d",expect_fault))expect_fault=0;
 fd=$fopen(stim,"r");if(!fd)$fatal(1,"cannot open stimulus");
 for(integer u=0;u<4;u++)nextgroup[u]=0;
 repeat(4)@(posedge ck);#0.2 rst_n=1;repeat(PHYS?4:0)@(posedge ck);
 while(!done)begin
 pv=0;sv=0;rv=0;issue=0;es=esn;ee=een;esn=0;een=0;
 forever begin
 if(!have)begin r=$fscanf(fd,"%d %d %h %h %h %h %h\n",t,k,a,b,c,d,e);if(r!=7)$fatal(1,"stim read");have=1;end
 if(t>edge_i)break;if(t<edge_i)$fatal(1,"stim ordering");have=0;
 case(k)
 0:begin pv=1;pa=a;pd={b[31:0],c[31:0]};end
 1:au=a;
 2:begin di={a[31:0],b[31:0]};pe=c;fc=d;end
 3:begin sv=1;su=a;ss=b;se=c;nextgroup[a]=(b==37)?13:0;end
 4:begin issue=1;iu=a;isl=b;ip=c;esn=d;een=e;end
 5:begin rv=1;ru=a;me=b;end
 9:done=1;
 default:$fatal(1,"stim kind");endcase
 if(done)break;
 end
 @(posedge ck);#0.2;
 if(tr)ready=1;
 if(gc)begin
 if(!expect_fault&&cg!=nextgroup[cu])$fatal(1,"GROUP_ORDER user=%0d got=%0d expected=%0d",cu,cg,nextgroup[cu]);
 nextgroup[cu]=cg+1;groups++;coverage[cg]=1;users[cu]=1;
 end
 if((f||ofault)&&firstfault<0)firstfault=edge_i;
 edge_i++;
 end
 $display("HEAD37_SUMMARY head=%0d safe=%0d select=%0d phys=%0d pair=%0d ready=%0d groups=%0d users=%h coverage=%h fault=%0d first=%0d",HEAD,SAFE,SELECT,PHYS,PAIR,ready,groups,users,coverage,(f||ofault),firstfault);
 if((f||ofault)!=expect_fault)$fatal(1,"FAULT_VERDICT");
 if(!expect_fault&&(!ready||groups!=expect_groups||users!=15||ca!=0))$fatal(1,"NOMINAL_COVERAGE");
 $display("HEAD37_COMPONENT_PASS");$finish;
 end
endmodule
