`timescale 1ns/1ps
// Simulation-only source census for the REAL SV producer's local-memory pins.
// Never grants, schedules, stalls, mutates data, or stands in for SRAM hardware.
module ot_hbm_su_port_census #(parameter integer N=512,LWB=18,AW=24,NR=N/8)(
 input wire clk,rst_n,
 input wire[N-1:0]vi_re,input wire[N*AW-1:0]vi_addr,
 input wire[4*N-1:0]rd_re,input wire[4*N*AW-1:0]rd_addr,
 input wire[N-1:0]vm_we,input wire[N*AW-1:0]vm_waddr,
 input wire[NR-1:0]res_we,input wire[NR*AW-1:0]res_addr,
 input wire[31:0]lsw_v,ldr_v,input wire[32*15-1:0]lsw_sec,ldr_sec
);
 localparam BB=$clog2(N);
 bit seen[0:5][0:N-1];integer firstrow[0:5][0:N-1];
 integer wc[0:N-1];
 integer cycle=0,active_cycles=0,read_row_conflict_cycles=0,write_conflict_cycles=0;
 integer rf_reads=0,rf_writes=0,off_column_reads=0;
 integer first_bad_cycle=-1,first_bad_class=-1,first_bad_bank=-1,first_bad_row_a=-1,first_bad_row_b=-1;
 integer q,b,l,k,a,bank,row;reg conflict,wconf,active;
 task read_access(input integer cls,input integer lane,input integer addr);
  integer bank,row;
  begin
   active=1;
   if((addr>>LWB)&1)rf_reads=rf_reads+1;
   else begin
    bank=addr&(N-1);row=(addr&((1<<LWB)-1))>>BB;
    if(cls<5&&bank!=lane)off_column_reads=off_column_reads+1;
    if(seen[cls][bank]&&firstrow[cls][bank]!=row)begin
     conflict=1;
     if(first_bad_cycle<0)begin
      first_bad_cycle=cycle;first_bad_class=cls;first_bad_bank=bank;
      first_bad_row_a=firstrow[cls][bank];first_bad_row_b=row;
     end
    end
    if(!seen[cls][bank])firstrow[cls][bank]=row;
    seen[cls][bank]=1;
   end
  end
 endtask
 task write_access(input integer addr);
  integer bank;
  begin
   active=1;
   if((addr>>LWB)&1)rf_writes=rf_writes+1;
   else begin bank=addr&(N-1);wc[bank]=wc[bank]+1;if(wc[bank]>1)wconf=1;end
  end
 endtask
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;conflict=0;wconf=0;active=0;
  for(b=0;b<N;b=b+1)begin wc[b]=0;for(q=0;q<6;q=q+1)seen[q][b]=0;end
  for(l=0;l<N;l=l+1)begin
   if(vi_re[l])read_access(0,l,int'(vi_addr[l*AW+:AW]));
   for(q=0;q<4;q=q+1)if(rd_re[4*l+q])read_access(q+1,l,int'(rd_addr[(4*l+q)*AW+:AW]));
   if(vm_we[l])write_access(int'(vm_waddr[l*AW+:AW]));
  end
  for(l=0;l<NR;l=l+1)if(res_we[l])write_access(int'(res_addr[l*AW+:AW]));
  for(l=0;l<32;l=l+1)begin
   if(lsw_v[l])for(k=0;k<8;k=k+1)write_access(int'(lsw_sec[l*15+:15])*8+k);
   if(ldr_v[l])for(k=0;k<8;k=k+1)read_access(5,l*8+k,int'(ldr_sec[l*15+:15])*8+k);
  end
  if(active)active_cycles=active_cycles+1;
  if(conflict)read_row_conflict_cycles=read_row_conflict_cycles+1;
  if(wconf)write_conflict_cycles=write_conflict_cycles+1;
 end
 final begin
  $display("SV_PORT_CENSUS {\"cycles\":%0d,\"active_cycles\":%0d,\"read_row_conflict_cycles\":%0d,\"write_conflict_cycles\":%0d,\"rf_reads\":%0d,\"rf_writes\":%0d,\"off_column_reads\":%0d,\"first_bad\":{\"cycle\":%0d,\"class\":%0d,\"bank\":%0d,\"row_a\":%0d,\"row_b\":%0d}}",cycle,active_cycles,read_row_conflict_cycles,write_conflict_cycles,rf_reads,rf_writes,off_column_reads,first_bad_cycle,first_bad_class,first_bad_bank,first_bad_row_a,first_bad_row_b);
 end
endmodule
