`timescale 1ns/1fs
// One actual system loader path: unchanged ot_host_if lower BAR + upper loader
// BAR + 64-bit DMA + actual per-die memsys. No token run and no HBM image preload.
module tb_hbm_accel_loader_installed;
 reg por_n=0,clk_host=0,clk_sm=0,clk_mem=0,clk_link=0;
 real mem_half=0.5,mem_phase=0.0;integer dma_delay=400;
 initial begin
 void'($value$plusargs("MEM_HALF_NS=%f",mem_half));
 void'($value$plusargs("MEM_PHASE_NS=%f",mem_phase));
 void'($value$plusargs("DMA_DELAY=%d",dma_delay));
 #(mem_phase);forever #(mem_half) clk_mem=~clk_mem;
 end
 always #0.5 clk_host=~clk_host;
 always #0.55 clk_sm=~clk_sm;always #0.7 clk_link=~clk_link;
 reg av=0,wv=0,arv=0,br=1,rr=1;reg[11:0] aa=0,ra=0;reg[31:0] wd=0;
 wire aready,wready,bv,arready,rv;wire[31:0] rd;
 wire marv,mrr,mav,mwv,mwl,mbr;wire[63:0] mara,ma,mwd;wire[7:0] marl,mal,mws;
 wire[2:0] mars,mas;reg marr=1,ma_ready=1,mw_ready=1,mrv=0,mrl=0,mbv=0;
 reg[63:0] mrd=0;reg[1:0] mre=0,mbe=0;
 wire irq,fault;wire[31:0] steps;
 ot_hbm_accel_hbm_system_loader #(.ENABLE(1),.LOADER(1),.HA3(0),.ND(1),.NSM(1),.NL(32),.NS(2),.NPC(2),.MEM_WORDS(4096)) dut(
 .por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
 .s_awvalid(av),.s_awready(aready),.s_awaddr(aa),.s_wvalid(wv),.s_wready(wready),.s_wdata(wd),.s_wstrb(4'hf),.s_bvalid(bv),.s_bready(br),
 .s_arvalid(arv),.s_arready(arready),.s_araddr(ra),.s_rvalid(rv),.s_rready(rr),.s_rdata(rd),
 .m_arvalid(marv),.m_arready(marr),.m_araddr(mara),.m_arlen(marl),.m_arsize(mars),.m_rvalid(mrv),.m_rready(mrr),.m_rdata(mrd),.m_rresp(mre),.m_rlast(mrl),
 .m_awvalid(mav),.m_awready(ma_ready),.m_awaddr(ma),.m_awlen(mal),.m_awsize(mas),.m_wvalid(mwv),.m_wready(mw_ready),.m_wdata(mwd),.m_wstrb(mws),.m_wlast(mwl),.m_bvalid(mbv),.m_bready(mbr),.m_bresp(mbe),
 .irq(irq),.ld_v(1'b0),.ld_rdy(),.ld_target(1'b0),.ld_die(4'b0),.ld_sm(4'b0),.ld_addr(24'b0),.ld_data(64'b0),.sys_fault(fault),.st_steps(steps));
 reg[255:0] image[128];reg[63:0] host_mem[2048];longint cyc=0;
 integer r_left=0,r_i=0,w_left=0,w_i=0;longint r_when=0,b_when=0;
 reg read_active=0,write_active=0,b_pending=0;
 integer reads=0,writes=0,acks=0,fails=0;integer error_b=0;
 always @(posedge clk_host)begin
 cyc<=cyc+1;
 marr<=!read_active&&!mrv&&(cyc%13!=0);ma_ready<=!write_active&&!b_pending&&!mbv&&(cyc%11!=0);mw_ready<=cyc%17!=0;
 if(marv&&marr)begin
 if(mars!=3||((mara&4095)+8*(int'(marl)+1)>4096))$fatal(1,"read DMA size/4K");
 read_active=1;r_left=int'(marl)+1;r_i=int'(mara>>3);r_when=cyc+dma_delay;
 end
 if(mrv&&mrr)begin
 reads=reads+1;r_left=r_left-1;r_i=r_i+1;
 if(r_left==0)read_active=0;
 end
 if(!mrv||mrr)begin
 mrv<=read_active&&cyc>=r_when;
 if(read_active&&cyc>=r_when)begin mrd<=host_mem[r_i];mrl<=r_left==1;mre<=0;end
 else mrl<=0;
 end
 if(mav&&ma_ready)begin
 if(mas!=3||((ma&4095)+8*(int'(mal)+1)>4096))$fatal(1,"write DMA size/4K");
 write_active=1;w_left=int'(mal)+1;w_i=int'(ma>>3);
 end
 if(mwv&&mw_ready)begin
 if(!write_active||w_left<=0||mwl!=(w_left==1))$fatal(1,"write beat owner/last");
 for(integer b=0;b<8;b=b+1)if(mws[b])host_mem[w_i][b*8+:8]=mwd[b*8+:8];
 writes=writes+1;w_left=w_left-1;w_i=w_i+1;
 if(w_left==0)begin write_active=0;b_pending=1;b_when=cyc+dma_delay;end
 end
 if(mbv&&mbr)begin mbv<=0;acks=acks+1;end
 if(b_pending&&cyc>=b_when&&!mbv)begin mbv<=1;mbe<=error_b?2'b10:2'b0;b_pending=0;end
 end
 // Passive observers on the actual CDC and external ports. No ready/ACK drive.
 `define LD dut.g_on.u_loader_host.g_on.g_die[0].u_load.g_on
 `define ST dut.g_on.u_loader_host.g_on.g_die[0].u_store
 `define STI dut.g_on.u_loader_host.g_on.g_die[0].u_store.g_on
 integer lp=0,lc=0,sp=0,sc=0,lpeak=0,speak=0,ls=0,ss=0;
 integer reqs=0,rsps=0,reqstall=0,wstall=0,rtseen=0;
 realtime ltime[128],stime[128],reqtime[128];
 realtime lmin=1e9,lmax=0,smin=1e9,smax=0,amin=1e9,amax=0;
 realtime firstw=0,lastw=0,lastb=0,firstreq=0,lastack=0,done_time=0;
 integer observed=0;
 always @(posedge clk_host) begin
 if(`LD.u_data.in_v&&`LD.u_data.in_rdy)begin ltime[lp%128]=$realtime;lp++;if(lp-lc>lpeak)lpeak=lp-lc;end
 if(`LD.u_data.in_v&&!`LD.u_data.in_rdy)ls++;
 if(`STI.u_data.out_v&&`STI.u_data.out_rdy)begin
 realtime d;d=$realtime-stime[sc%128];if(d<smin)smin=d;if(d>smax)smax=d;sc++;
 end
 if(mwv&&!mw_ready)wstall++;
 if(mwv&&mw_ready)begin if(firstw==0)firstw=$realtime;lastw=$realtime;end
 if(mbv&&mbr)lastb=$realtime;
 if(`STI.done&&done_time==0)done_time=$realtime;
 end
 always @(posedge clk_mem)begin
 if(`LD.u_data.out_v&&`LD.u_data.out_rdy)begin
 realtime d;d=$realtime-ltime[lc%128];if(d<lmin)lmin=d;if(d>lmax)lmax=d;lc++;
 end
 if(`STI.u_data.in_v&&`STI.u_data.in_rdy)begin stime[sp%128]=$realtime;sp++;if(sp-sc>speak)speak=sp-sc;end
 if(`STI.u_data.in_v&&!`STI.u_data.in_rdy)ss++;
 if(`ST.req_v&&!`ST.req_rdy)reqstall++;
 if(`ST.req_v&&`ST.req_rdy)begin reqtime[`ST.req_tag%128]=$realtime;reqs++;if(firstreq==0)firstreq=$realtime;end
 if(`ST.rsp_v&&`ST.rsp_rdy)begin
 realtime d;d=$realtime-reqtime[`ST.rsp_tag%128];if(d<amin)amin=d;if(d>amax)amax=d;rsps++;lastack=$realtime;
 end
 end
 task automatic wr(input[11:0] a,input[31:0] d);
 @(negedge clk_host);av=1;wv=1;aa=a;wd=d;
 @(posedge clk_host);while(!(aready&&wready))@(posedge clk_host);
 @(negedge clk_host);av=0;wv=0;
 while(!bv)@(posedge clk_host);
 @(negedge clk_host);
 endtask
 task automatic readcsr(input[11:0] a,output[31:0] d);
 @(negedge clk_host);arv=1;ra=a;
 @(posedge clk_host);while(!arready)@(posedge clk_host);
 @(negedge clk_host);arv=0;
 while(!rv)@(posedge clk_host);d=rd;
 @(negedge clk_host);
 endtask
 task automatic transfer(input[11:0] bar,input[63:0] haddr,input[31:0] size,input[31:0] crc,input integer expected,input string name);
 reg[31:0] st,cg,vg,ns,cycles;longint t0;
 lp=0;lc=0;sp=0;sc=0;lpeak=0;speak=0;ls=0;ss=0;reqs=0;rsps=0;reqstall=0;wstall=0;
 lmin=1e9;lmax=0;smin=1e9;smax=0;amin=1e9;amax=0;firstw=0;lastw=0;lastb=0;firstreq=0;lastack=0;done_time=0;
 wr(bar+'h08,haddr[31:0]);wr(bar+'h0c,haddr[63:32]);wr(bar+'h10,0);wr(bar+'h14,size);wr(bar+'h18,crc);
 t0=cyc;wr(bar,bar[6]?32'b1:32'b11);
 readcsr(bar+'h04,st);while(!st[8])readcsr(bar+'h04,st);
 readcsr(bar+'h1c,cg);readcsr(bar+'h20,vg);readcsr(bar+'h24,ns);readcsr(bar+'h28,cycles);
 $display("INSTALLED %s status=%0d crc=%08h vcrc=%08h sectors=%0d host_cycles=%0d elapsed=%0d bytes=%0d",name,st[3:0],cg,vg,ns,cycles,cyc-t0,size);
 $display("FEASIBILITY %s host_ns=1 mem_ns=%0.6f phase_ns=%0.6f dma_delay=%0d LDpush=%0d LDpop=%0d LDpeak=%0d LDstall=%0d LDcross_min_ns=%0.3f LDcross_max_ns=%0.3f STpush=%0d STpop=%0d STpeak=%0d STstall=%0d STcross_min_ns=%0.3f STcross_max_ns=%0.3f req=%0d rsp=%0d reqstall=%0d ack_min_ns=%0.3f ack_max_ns=%0.3f Wstall=%0d first_req_to_W_ns=%0.3f last_W_to_B_ns=%0.3f B_to_done_ns=%0.3f",name,2*mem_half,mem_phase,dma_delay,lp,lc,lpeak,ls,lmin,lmax,sp,sc,speak,ss,smin,smax,reqs,rsps,reqstall,amin,amax,wstall,firstw-firstreq,lastb-lastw,done_time-lastb);
 if(expected==0&&bar[6]&&(reqs!=size/32||rsps!=size/32||sp!=size/32||sc!=size/32||lastb<lastw))fails++;
 if(st[3:0]!=expected||(expected==0&&(cg!=crc||vg!=crc||ns!=size/32)))fails++;
 wr(bar+'h04,256);
 endtask
 initial begin
 string path;reg[31:0] id,crc;integer bad=0;
 if(!$value$plusargs("HOSTIMG=%s",path)||!$value$plusargs("CRC4K=%h",crc))$fatal(1,"retained HOSTIMG/CRC4K required");
 $readmemh(path,image,0,127);
 for(integer i=0;i<2048;i++)host_mem[i]=0;
 for(integer i=0;i<128;i++)for(integer j=0;j<4;j++)host_mem[4*i+j]=image[i][j*64+:64];
 repeat(8)@(negedge clk_host);por_n=1;repeat(30)@(negedge clk_host);
 readcsr(0,id);if(id!=32'h4f544849)$fatal(1,"lower host BAR ID=%08h",id);
 transfer('h800,0,4096,crc,0,"LOAD_VERIFY");
 transfer('h840,8192,4096,crc,0,"STORE");
 for(integer i=0;i<512;i++)if(host_mem[1024+i]!==host_mem[i])bad++;
 $display("ROUNDTRIP words64=512 mismatches=%0d reads=%0d writes=%0d b_acks=%0d system_fault=%b steps=%0d",bad,reads,writes,acks,fault,steps);
 if(bad||fault||steps!=0)fails++;
 transfer('h840,8192,31,crc,3,"STORE_ALIGN");
 error_b=1;transfer('h840,8192,4096,crc,4,"STORE_B_ERROR");error_b=0;
 if(fails)$fatal(1,"installed loader failures=%0d",fails);
 $display("PASS installed_loader_roundtrip");$finish;
 end
endmodule
