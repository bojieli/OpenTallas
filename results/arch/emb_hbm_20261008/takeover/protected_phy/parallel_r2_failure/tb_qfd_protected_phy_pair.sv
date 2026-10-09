`timescale 1ns/1ps
module tb_qfd_protected_phy_pair;
 import ot_gpu_w6_secded_pkg::*;
 parameter integer MUT=0,ENABLE=1,ROLL=0,OOO=1,LONGSTALL=0;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,q_v=0,q_we=0,q_emb=0;wire q_rdy;
 reg[18:0] q_row;reg[4:0]q_bank,q_col;reg[16:0]q_sec;reg[7:0]q_lrow;reg[287:0]q_code;
 wire o_v,o_we,o_emb,fault;reg o_rdy=1;
 wire[16:0]o_sec;wire[7:0]o_lrow;wire[18:0]o_row;wire[4:0]o_bank,o_col;wire[287:0]o_code;
 wire p_v,p_rdy,p_we;wire raw_ready;wire allow_request=(cycles%7)!=0 &&(cycles%7)!=1 && !(LONGSTALL && !dut.wr && dut.st==3 && first_accept>=0 && cycles-first_accept<60);wire[30:0]p_addr;wire[4:0]p_len;wire[15:0]p_tag;wire[255:0]p_data;
 wire[31:0]rv,rr;wire[511:0]rt;wire[127:0]rb;wire[8191:0]rd;
 wire r_rdy;reg pair_rv=0;reg[15:0]pair_rt;reg[3:0]pair_rb;reg[255:0]pair_rd;reg[255:0]held_d,held_e;reg[15:0]held_dt,held_et;reg[3:0]held_db,held_eb;reg got_d=0,got_e=0;integer release_phase=0;integer first_accept=-1,second_accept=-1,second_offer=-1,data_return=0,ecc_return=0,last_physical_return=0;integer completion_extra_sum=0,completion_extra_max=0;integer parallel_pairs=0;integer reads=0,writes=0,cycles=0; integer injected=0; integer wsum=0,rsum=0,wmin=100000,rmin=100000,wmax=0,rmax=0;reg[255:0]expectdata;
 wire[15:0]tagin=(dut.wr?rt[7*16+:16]:pair_rt)^((MUT==1)?16'd1:16'd0);
 wire[255:0]datain=(dut.wr?rd[7*256+:256]:pair_rd)^((MUT==3 && reads>=3)?256'd1:256'd0);
 assign rr=32'hffffffff;assign p_rdy=raw_ready&&allow_request;
 ot_qfd_protected_phy_pair_pc #(.ENABLE(ENABLE),.PC(7),.MUT(MUT==6)) dut(.*,
 .r_v(dut.wr?rv[7]:pair_rv),.r_pc((MUT==2)?5'd6:5'd7),.r_tag(tagin),.r_beat(dut.wr?rb[7*4+:4]:pair_rb),.r_data(datain));
 ot_hdc_hbm_model #(.NPC(32),.AW(31),.MEM_WORDS(65521),.CLK_PS(1024),.QD(8),.RQD(4),.RW(4),.PC_RDY(1)) mem(
 .clk(clk),.rst_n(rst_n),.req_v(p_v&&allow_request),.req_rdy(raw_ready),.req_we(p_we),.req_addr(p_addr),.req_len(p_len),.req_tag(p_tag),.req_wdata(p_data),.pc_room(),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));
 function automatic[287:0]encode(input[255:0]d);integer w;begin for(w=0;w<4;w=w+1)encode[w*72+:72]=encode64(d[w*64+:64]);end endfunction
 task automatic transaction(input integer n,input bit we);
 integer w,startc,delta;reg[255:0]d;reg[287:0]c,expectedc;reg[65:0]decoded;begin
 d={8{32'h76543210^32'(n)}};c=encode(d);expectedc=c;if(injected>=1)expectedc[2]=~expectedc[2];if(injected==2)expectedc[4]=~expectedc[4];
 @(negedge clk);while(!q_rdy)@(negedge clk);
 q_we=we;q_emb=we||n>=32;q_row=q_emb?19'd24427+19'(n/16):19'(n/16);
 q_bank=5'(n%4);q_col=5'(n%16);q_sec=17'(n*13+9);q_lrow=8'(n/16);q_code=c;
 if(MUT==4)begin q_emb=0;q_row=0;end
 if(MUT==5)q_row=24576;
 first_accept=-1;second_accept=-1;second_offer=-1;data_return=0;ecc_return=0;got_d=0;got_e=0;release_phase=0;startc=cycles;q_v=1;@(negedge clk);q_v=0;
 while(!o_v && !fault)@(negedge clk);
 if(fault)$fatal(1,"provider fault MUT=%0d n=%0d",MUT,n);
 if(o_we!==we||o_emb!==q_emb||o_row!==q_row||o_bank!==q_bank||o_col!==q_col||o_sec!==q_sec||o_lrow!==q_lrow||o_code!==expectedc)$fatal(1,"metadata/code mismatch n=%0d",n);
 if(injected!=0)begin decoded=decode64(o_code[71:0]);if(injected==1 && (decoded[65:64]!=2'b01 || decoded[63:0]!=d[63:0]))$fatal(1,"realdataCE notretained");if(injected==2 && decoded[65]!=1)$fatal(1,"realdataUE notretained");end
 if(!we && (first_accept<0||second_accept<first_accept||second_offer!=first_accept+1||second_offer>=data_return))$fatal(1,"ECC launch waitedfor DATAresponse");
 if(!we)begin parallel_pairs=parallel_pairs+1;completion_extra_sum=completion_extra_sum+cycles-last_physical_return;if(cycles-last_physical_return>completion_extra_max)completion_extra_max=cycles-last_physical_return;enddelta=cycles-startc;if(we)begin wsum=wsum+delta;if(delta<wmin)wmin=delta;if(delta>wmax)wmax=delta;end else begin rsum=rsum+delta;if(delta<rmin)rmin=delta;if(delta>rmax)rmax=delta;end
 @(negedge clk);end endtask
 always @(posedge clk)if(rst_n)begin cycles<=cycles+1;if(cycles>40000)$fatal(1,"finite test incomplete st=%0d q=%0d reads=%0d writes=%0d pv=%0d pr=%0d rv=%h fault=%0d",dut.st,q_sec,reads,writes,p_v,p_rdy,rv,fault);if(p_v&&!dut.wr&&dut.st==3&&second_offer<0)second_offer=cycles;
 if(p_v&&p_rdy)begin
 if(p_we)writes<=writes+1;else begin reads<=reads+1;if(!dut.wr)begin if(first_accept<0)first_accept=cycles;else second_accept=cycles;end end
 if(mem.pc_of(p_addr)!=7)$fatal(1,"address PC mismatch");
 if(p_len!=1)$fatal(1,"physical burst length");end end
 // Test-only two-return shim: both bursts originate in actual256-bit model.
 // Deliberately ECC-first on OOO1 and DATA-first on OOO0; request path stalls.
 always @(negedge clk)if(rst_n && !dut.wr)begin
 pair_rv=0;
 if(rv[7])begin
 last_physical_return=cycles;
 if(rt[7*16+:16]==dut.data_tag)begin data_return=cycles;held_d=rd[7*256+:256];held_dt=rt[7*16+:16];held_db=rb[7*4+:4];got_d=1;end
 else if(rt[7*16+:16]==dut.ecc_tag)begin ecc_return=cycles;held_e=rd[7*256+:256];held_et=rt[7*16+:16];held_eb=rb[7*4+:4];got_e=1;end
 else $fatal(1,"modelunexpectedtag");
 end
 if(OOO==2)begin if(rv[7])begin pair_rv=1;pair_rt=rt[7*16+:16];pair_rd=rd[7*256+:256];pair_rb=rb[7*4+:4];end end
 else if(got_d&&got_e)begin
 if(release_phase==0)begin pair_rv=1;pair_rt=OOO?held_et:held_dt;pair_rd=OOO?held_e:held_d;pair_rb=OOO?held_eb:held_db;release_phase=1;end
 else if(release_phase==1)begin pair_rv=1;pair_rt=(OOO && MUT!=7)?held_dt:held_et;pair_rd=(OOO && MUT!=7)?held_d:held_e;pair_rb=(OOO && MUT!=7)?held_db:held_eb;release_phase=2;end
 end
 end
 integer i,j,k,pos,idx;reg[287:0]initcode;reg[31:0]check32;reg[9:0]ej;reg[30:0]initda,inirea;initial begin
 for(i=0;i<65521;i=i+1)mem.mem[i]=0;
 for(i=0;i<32;i=i+1)begin
 initcode=encode({8{32'h76543210^32'(i)}});check32=0;
 for(j=0;j<4;j=j+1)begin for(k=0;k<7;k=k+1)check32[j*8+k]=initcode[j*72+(1<<k)-1];check32[j*8+7]=initcode[j*72+71];end
 idx={(3'd0),5'(i%16),2'(i%4)};ej=10'(idx>>3);
 initda=dut.address(16'(i/16),5'(i%4),5'(i%16));inirea=dut.address(16'(64+i/16),{ej[9:7],ej[1:0]},ej[6:2]);
 mem.mem[initda%65521]={8{32'h76543210^32'(i)}};mem.mem[inirea%65521][(idx%8)*32+:32]=check32;
 end
 repeat(5)@(negedge clk);rst_n=1; if(ROLL) dut.serial=16'hfffe;
 if(!ENABLE)begin q_v=1;repeat(50)@(negedge clk);if(q_rdy||p_v||o_v||fault)$fatal(1,"default off");$display("PASS default off");$finish;end
 for(i=0;i<64;i=i+1)transaction(i,1);
 for(i=0;i<64;i=i+1)transaction(i,0);
 if(writes!=128||reads!=320)$fatal(1,"actual transaction count %0d %0d",writes,reads);
 $display("latency coreHBM1024ps WR min=%0d sum=%0d max=%0d RD min=%0d sum=%0d max=%0d ACT=%0d conflicts=%0d",wmin,wsum,wmax,rmin,rsum,rmax,mem.st_act[7],mem.st_conf[7]);
 $display("PASS 64 WR 64 RD writes=%0d reads=%0d cycles=%0d parallel real256 two-slot taggedmetadata boot-onlyWR OOO=%0d",writes,reads,cycles,OOO);
 injected=1;mem.mem[dut.address(16'd0,5'd0,5'd0)%65521]=mem.mem[dut.address(16'd0,5'd0,5'd0)%65521]^256'd1;transaction(0,0);
 injected=2;mem.mem[dut.address(16'd0,5'd0,5'd0)%65521]=mem.mem[dut.address(16'd0,5'd0,5'd0)%65521]^256'd2;transaction(0,0);
 $display("pairpublication vsmaxrealphysicalreturn extra_sum=%0d extra_max=%0d LONGSTALL=%0d",completion_extra_sum,completion_extra_max,LONGSTALL);
 if(reads!=324||parallel_pairs!=66)$fatal(1,"faultreads missing");$display("PASS actualphysicaldata CE corrected and UE retained againstreal sidecarchecks");$finish;
 end
endmodule
