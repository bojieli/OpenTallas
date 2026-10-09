`timescale 1ps/1fs
// Minimum mechanism: full hub, real shadow SRAM macros, timed Gray respondents.
module tb_hbm_kvwb_hub_sram #(parameter integer MUT=0, WR0=0, CR0=80, KR0=96);
 reg clk=0,svc_clk=0,rst_n=0; always #416.5 clk=~clk; always #512 svc_clk=~svc_clk;
 reg[6:0] die=0; reg ri_v=0,ri_hdr=0;reg[255:0] ri_d=0;wire ri_cr;
 wire[1167:0] so_d;wire[63:0] si_g;wire fence_ok,map_fault;wire[15:0] issued,acked;
 ot_hbm_kvwb_hub_sram #(.ENABLE(1),.MUT(MUT),.WIN_ROW0(WR0),.CKV_ROW0(CR0),.KEY_ROW0(KR0)) dut
 (.clk(clk),.rst_n(rst_n),.die(die),.ri_v(ri_v),.ri_hdr(ri_hdr),.ri_d(ri_d),.ri_cr(ri_cr),.so_d(so_d),.si_g(si_g),.fence_ok(fence_ok),.issued(issued),.acked(acked),.map_fault(map_fault));
 integer cycle=0,fo,completed=0,received=0,stall=0,backpressure=0,shwait=0,shaccepted=0;
 genvar t;
 generate for(t=0;t<4;t=t+1)begin:resp
 reg[7:0] pop=0,ack=0;integer wp=0,pp=0,ap=0;
 integer pdue[0:1023],adue[0:1023];reg[29:0] addr[0:1023];reg[255:0] data[0:1023];
 reg[255:0] mem[integer];
 assign si_g[16*t+:16]={ack^(ack>>1),pop^(pop>>1)};
 always @(posedge clk)if(rst_n)begin
 if(so_d[292*t])begin
 addr[wp]=so_d[292*t+6+:30];data[wp]=so_d[292*t+36+:256];
 pdue[wp]=cycle+120+t*7;adue[wp]=cycle+400+t*13;
 $fdisplay(fo,"W %0d %0d %0d %h",t,so_d[292*t+1+:5],addr[wp],data[wp]);
 wp=wp+1;received=received+1;
 if(wp-pp>8)$fatal(1,"sector credit overflow");
 end
 end
 always @(posedge svc_clk)if(rst_n)begin
 if(pp<wp&&cycle>=pdue[pp])begin pp=pp+1;pop<=pop+1;end
 if(ap<pp&&cycle>=adue[ap])begin mem[addr[ap]]=data[ap];ap=ap+1;ack<=ack+1;completed=completed+1;end
 end
 end endgenerate
 reg[256:0] beats[0:8191];integer nbq=0,ibq=0,credits=32;reg go=0;
 always @(posedge clk)begin
 cycle<=cycle+1;ri_v<=0;
 if(go&&ibq<nbq)begin
 if(credits-(ri_v?1:0)+(ri_cr?1:0)>0)begin
 ri_v<=1;ri_hdr<=beats[ibq][256];ri_d<=beats[ibq][255:0];ibq<=ibq+1;
 end else stall<=stall+1;
 end
 credits<=credits-(ri_v?1:0)+(ri_cr?1:0);
 if(credits<0||credits>32)$fatal(1,"producer credit violation");
 if(rst_n&&dut.on.wq_v&&!dut.on.wq_r)backpressure<=backpressure+1;
 if(rst_n&&dut.on.u_wb.on.preload)shwait<=shwait+1;
 if(rst_n&&dut.on.sh_v&&dut.on.sh_r)shaccepted<=shaccepted+1;
 end
 integer fr,rc,k,kind,slot,r2,pos,sh,b,nb,nrows=0,early=0,expected,startcycle,lastcycle,fencecycle;
 reg[4351:0] dat;string rowsfile,outfile,peekfile;
 initial begin
 if(!$value$plusargs("rows=%s",rowsfile))$fatal;
 if(!$value$plusargs("out=%s",outfile))$fatal;
 if(!$value$plusargs("peek=%s",peekfile))$fatal;
 if(!$value$plusargs("expected=%d",expected))$fatal;
 if($value$plusargs("die=%d",k))die=k;
 if($value$plusargs("early=%d",early))begin end
 fo=$fopen(outfile,"w");fr=$fopen(rowsfile,"r");
 while(!$feof(fr))begin
 rc=$fscanf(fr,"%d %d %d %d %d %h\n",kind,slot,r2,pos,sh,dat);if(rc!=6)break;
 nb=sh?17:(kind==1?9:(kind==2?3:17));
 beats[nbq]={1'b1,226'd0,sh[0],pos[19:0],r2[0],slot[5:0],kind[1:0]};nbq++;
 for(b=0;b<nb;b++)begin beats[nbq]={1'b0,dat[256*b+:256]};nbq++;end
 nrows++;
 end
 repeat(10)@(negedge clk);rst_n=1;repeat(10)@(negedge clk);startcycle=cycle;go=1;
 while(ibq<nbq)@(negedge clk);
 lastcycle=cycle;
 if(!early)begin
 // Observe the first fence after producer completion, without a drain grace period.
 while(!fence_ok)@(negedge clk);
 end
 fencecycle=cycle;
 $fdisplay(fo,"F rows=%0d issued=%0d acked=%0d fence_ok=%0d map_fault=%0d received=%0d completed=%0d expected=%0d producer_stalls=%0d sector_stalls=%0d shadow_wait=%0d shadow_accepted=%0d row_cycles=%0d fence_cycles=%0d",nrows,issued,acked,fence_ok,map_fault,received,completed,expected,stall,backpressure,shwait,shaccepted,lastcycle-startcycle,fencecycle-startcycle);
 begin:peek
 integer pf,st,a;reg[255:0] word_;pf=$fopen(peekfile,"r");
 while(!$feof(pf))begin
 rc=$fscanf(pf,"%d %d\n",st,a);if(rc!=2)break;
 word_=0;
 case(st)
 0:if(resp[0].mem.exists(a))word_=resp[0].mem[a];
 1:if(resp[1].mem.exists(a))word_=resp[1].mem[a];
 2:if(resp[2].mem.exists(a))word_=resp[2].mem[a];
 3:if(resp[3].mem.exists(a))word_=resp[3].mem[a];
 endcase
 $fdisplay(fo,"M %0d %0d %h",st,a,word_);
 end end
 $fdisplay(fo,"END");$fclose(fo);$finish;
 end
endmodule
