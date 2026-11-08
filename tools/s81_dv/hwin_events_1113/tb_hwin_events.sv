`timescale 1ns/1fs
module tb_hwin_events;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[52:0]f_ks=0;reg[25:0]f_mc=0,f_mw=0;reg[63:0]mu_rt=0;
wire[135:0]c0,c3,c4;wire[43:0]r0,r3,r4;wire[1:0]f0,f3,f4;
dsdv_mu_hwin #(.NSLOT(47),.NEV(8),.NEP(4),.NRT(2)) base(.ck(ck),.rst_n(rst_n),.f_ks(f_ks),.f_mc(f_mc),.f_mw(f_mw),.mu_rt(mu_rt),.mu_c(c0),.mu_rc(r0),.t_wf(f0));
dsdv_mu_hwin #(.NSLOT(47),.NEV(8),.NEP(4),.NRT(2),.MUT(3)) wrong_copy(.ck(ck),.rst_n(rst_n),.f_ks(f_ks),.f_mc(f_mc),.f_mw(f_mw),.mu_rt(mu_rt),.mu_c(c3),.mu_rc(r3),.t_wf(f3));
dsdv_mu_hwin #(.NSLOT(47),.NEV(8),.NEP(4),.NRT(2),.MUT(4)) wrong_enable(.ck(ck),.rst_n(rst_n),.f_ks(f_ks),.f_mc(f_mc),.f_mw(f_mw),.mu_rt(mu_rt),.mu_c(c4),.mu_rc(r4),.t_wf(f4));
localparam NSTART=94,GAP=64,RL=300;
integer cycle=0,launched=0,start_edge[0:NSTART-1];
integer errors=0,tx_count=0,replay_count=0,copy_control=0,enable_control=0;
integer stale_rx=0,rx_delay=160,checking=0,s,e,ep,d,sl;reg[135:0]ec;reg[43:0]er;reg ab,land;
always @(posedge ck)cycle=cycle+1;
function automatic integer delay_for(input integer event_index);delay_for=60+11*event_index;endfunction
always @(negedge ck)if(checking)begin
 ec=0;er=0;
 for(s=0;s<launched;s=s+1)for(e=0;e<8;e=e+1)begin
  ep=e%4;sl=s%47;ab=(sl+e)%2;land=e<4?((sl+e)%3==0):((sl+e)%2!=0);
  if(cycle==start_edge[s]+delay_for(e)+1)begin
   if(e<4)ec[34*ep+:34]={21'(100000+3*s),10'(s%47),land,ab,1'b1};
   else if(land)er[11*ep+:11]={10'(s%47),1'b1};
  end
 end
 if(c0!==ec||r0!==er)begin errors=errors+1;if(errors<8)$display("HWIN_DATA_ERROR cycle=%0d gotc=%h expectedc=%h gotr=%h expectedr=%h",cycle,c0,ec,r0,er);end
 if(c3!==ec||r3!==er)copy_control=copy_control+1;
 if(c4!==ec||r4!==er)enable_control=enable_control+1;
 for(ep=0;ep<4;ep=ep+1)begin if(c0[34*ep])tx_count=tx_count+1;if(r0[11*ep])replay_count=replay_count+1;end
end
task automatic cfg_mc(input[24:0]p);begin f_mc={1'b1,p};@(negedge ck);f_mc=0;end endtask
task automatic cfg_mw(input[24:0]p);begin f_mw={1'b1,p};@(negedge ck);f_mw=0;end endtask
integer i,j,t0,t,idx;reg[9:0]rxuser;reg[20:0]rxpos;
initial begin
 if($value$plusargs("STALE_RX=%d",stale_rx))begin end
 if($value$plusargs("RX_DELAY=%d",rx_delay))begin end
 repeat(16)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);
 cfg_mc(25'(GAP));cfg_mc((25'd1<<24)|25'(RL));
 for(i=0;i<8;i=i+1)begin
  cfg_mw(25'(i)|25'((i/4)<<8)|25'((i%4)<<9));
  cfg_mw((25'd1<<21)|25'(delay_for(i)));
  for(j=0;j<47;j=j+1)begin
   ab=(j+i)%2;land=i<4?((j+i)%3==0):((j+i)%2!=0);
   cfg_mw((25'd2<<21)|25'(j)|(25'(ab)<<10)|(25'(land)<<11));
  end
 end
 repeat(20)@(negedge ck);checking=1;t0=cycle+1;
 for(t=0;t<(NSTART-1)*GAP+RL+24;t=t+1)begin
  f_ks=0;mu_rt=0;
  if(t%GAP==0&&t/GAP<NSTART)begin
   idx=t/GAP;start_edge[idx]=cycle+1;launched=launched+1;
   f_ks={1'b1,10'(idx%47),21'(5000+idx),21'(100000+3*idx)};
  end
  if(t>=rx_delay&&(t-rx_delay)%GAP==0&&(t-rx_delay)/GAP<NSTART)begin
   idx=(t-rx_delay)/GAP;rxuser=10'(idx%47);rxpos=21'(100000+3*idx);
   if(stale_rx&&idx==0)rxpos=rxpos+1;
   mu_rt[31:0]={1'b1,rxuser,rxpos};
  end
  @(negedge ck);
 end
 checking=0;
 $display("HWIN_EVENT_RESULT starts=%0d tx=%0d replay=%0d errors=%0d copy_mutant=%0d enable_mutant=%0d fault=%b stale_rx=%0d",launched,tx_count,replay_count,errors,copy_control,enable_control,f0,stale_rx);
 if(errors||tx_count!=376||replay_count!=188||copy_control==0||enable_control==0)$fatal(1,"HWIN identity/date/control gate");
 if(stale_rx||rx_delay<1||rx_delay>=RL)begin if(f0!==2'b01)$fatal(1,"stale RX not rejected by actual membership checker");$display("HWIN_STALE_RX_CAUGHT");end
 else begin if(f0!==0)$fatal(1,"unexpected native HWIN fault");$display("HWIN_EVENTS_PASS sampling_to_pin=D+1");end
 $finish;
end
endmodule
