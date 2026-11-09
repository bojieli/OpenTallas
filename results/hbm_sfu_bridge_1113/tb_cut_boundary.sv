// DIE-HBM-92-SU-SFU2 11-08: does the SFU VM bridge depend on the exact response edge?  Actual as-built bridge
// (ot_hgi_sfu_vm_static_bridge LWB15 RR88 WR85, as in sfucore_<Q>.__cut_ctl) against a responder that is exact for the
// as-built die (read valid = request valid delayed RR edges, w_done = write valid delayed WR+1 edges) plus the bound
// die added round-trip edges per local group / write sector (DRg, DWgs from bind_d/bind_latency.json).
`timescale 1ns/1ps
module tb;
 parameter integer RR=127, WR=124, EXT_RR=125, EXT_WR=122, LWB=15, NCYC=3000;
 parameter integer DR0=0, DR1=0, DR2=0, DR3=0;
 parameter integer DW00=0, DW01=0, DW10=0, DW11=0, DW20=0, DW21=0, DW30=0, DW31=0;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg [7:0] prefetch_v=0; reg [127:0] prefetch_sector=0; reg [15:0] prefetch_group=0;
 reg [8*LWB-1:0] prefetch_local_addr=0; reg [7:0] prefetch_scalar=0; reg [23:0] prefetch_word=0; reg [95:0] scalar_addr=0;
 wire [135:0] local_rq; wire [2055:0] local_rr;
 reg [135:0] rq_boundary=0; reg [2247:0] wq_boundary=0; reg [2055:0] rr_boundary=0; reg [7:0] wd_boundary=0;
 wire [2055:0] rr_external; wire [7:0] wd_external;
 always @(posedge clk) begin rq_boundary<=local_rq; wq_boundary<=local_wq; rr_boundary<=rr_external; wd_boundary<=wd_external; end
 assign local_rr=rr_boundary; wire [7:0] stage_v; wire [15:0] stage_group; wire [8*LWB-1:0] stage_addr;
 wire [2047:0] stage_data; wire [63:0] stage_mask; wire [3:0] scalar_load; wire [95:0] scalar_load_addr; wire [127:0] scalar_data;
 reg [1:0] drain_v=0, drain_round_bf16=0, drain_result_v=0; reg [31:0] drain_vm_sector=0; reg [511:0] drain_data=0;
 wire [2247:0] local_wq; wire [7:0] local_w_done=wd_boundary; wire fault;
 ot_hgi_sfu_vm_static_bridge #(.LWB(LWB),.READ_RETURN(RR),.WRITE_RETURN(WR)) dut(
  .clk(clk),.rst_n(rst_n),.clk_lg({4{clk}}),.rst_lg_n({4{rst_n}}),.prefetch_v(prefetch_v),.prefetch_sector(prefetch_sector),
  .prefetch_group(prefetch_group),.prefetch_local_addr(prefetch_local_addr),.prefetch_scalar(prefetch_scalar),
  .prefetch_word(prefetch_word),.scalar_addr(scalar_addr),.local_rq(local_rq),.local_rr(local_rr),.stage_v(stage_v),
  .stage_group(stage_group),.stage_addr(stage_addr),.stage_data(stage_data),.stage_mask(stage_mask),.scalar_load(scalar_load),
  .scalar_load_addr(scalar_load_addr),.scalar_data(scalar_data),.drain_v(drain_v),.drain_round_bf16(drain_round_bf16),
  .drain_vm_sector(drain_vm_sector),.drain_result_v(drain_result_v),.drain_data(drain_data),.local_wq(local_wq),
  .local_w_done(local_w_done),.fault(fault));
 localparam integer MAXD=RR+80;
 function automatic integer DRV(input integer g); case (g) 0: DRV=DR0; 1: DRV=DR1; 2: DRV=DR2; default: DRV=DR3; endcase endfunction
 function automatic integer DWV(input integer k);
  case (k) 0: DWV=DW00; 1: DWV=DW01; 2: DWV=DW10; 3: DWV=DW11; 4: DWV=DW20; 5: DWV=DW21; 6: DWV=DW30; default: DWV=DW31; endcase
 endfunction
 reg [16:0] rqd [0:7][0:MAXD];
 reg wvd [0:7][0:MAXD];
 genvar b;
 for (b=0;b<8;b=b+1) begin:g_resp
  localparam integer RD = EXT_RR + DRV(b/2), WD = EXT_WR + DWV(b);
  // response data: the request valid + the sector bits the tb also used as local address (check below)
  wire [16:0] rq_late = rqd[b][RD];
  wire wv_late = wvd[b][WD];
  assign rr_external[b*257+:257] = {rq_late[16], 241'd0, rq_late[14:0]};
  assign wd_external[b] = wv_late;
 end
 integer i,j,c,bad_data,first_fault,gf0,gf1,gf2,gf3;
 always @(posedge clk) begin
  for (i=0;i<8;i=i+1) begin
   rqd[i][0] <= rq_boundary[i*17+:17];
   for (j=1;j<=MAXD;j=j+1) rqd[i][j] <= rqd[i][j-1];
   wvd[i][0] <= wq_boundary[562*(i/2)+281*(i%2)+280];
   for (j=1;j<=MAXD;j=j+1) wvd[i][j] <= wvd[i][j-1];
  end
 end
 always @(posedge clk) drain_result_v <= drain_v;   // engine 1-edge answer, not on the VM path: exact
 reg [15:0] sec;
 initial begin
  for (i=0;i<8;i=i+1) for (j=0;j<=MAXD;j=j+1) begin rqd[i][j]=0; wvd[i][j]=0; end
  bad_data=0; first_fault=-1; gf0=-1; gf1=-1; gf2=-1; gf3=-1;
  repeat (5) @(negedge clk); rst_n=1;
  for (c=0;c<NCYC;c=c+1) begin
   @(negedge clk);
   for (i=0;i<8;i=i+1) begin
    prefetch_v[i] = (($random & 3)==0) && (c < NCYC-300);
    sec = ($random & 16'hfff8) | i;  prefetch_sector[16*i+:16] = sec;
    prefetch_local_addr[LWB*i+:LWB] = sec[14:0];
   end
   drain_v = (c < NCYC-300) ? ($random & 3) : 0; drain_vm_sector = $random; drain_data = {16{$random}};
   // one drain per (local group, sector half) and cycle: the programme never collides (write_collision is a fault)
   if (drain_v == 2'b11 && drain_vm_sector[2:0] == drain_vm_sector[18:16]) drain_v = 2'b01;
   for (i=0;i<8;i=i+1) if (stage_v[i] && stage_data[256*i+:15] !== stage_addr[LWB*i+:LWB]) bad_data = bad_data + 1;
   if (gf0 < 0 && dut.g_lg[0].fault_q) gf0 = c;
   if (gf1 < 0 && dut.g_lg[1].fault_q) gf1 = c;
   if (gf2 < 0 && dut.g_lg[2].fault_q) gf2 = c;
   if (gf3 < 0 && dut.g_lg[3].fault_q) gf3 = c;
   if (first_fault < 0 && fault) first_fault = c;
  end
  $display("VMRT RR=%0d WR=%0d DR=%0d,%0d,%0d,%0d DW=%0d/%0d,%0d/%0d,%0d/%0d,%0d/%0d fault_first=%0d lg_fault_first=%0d,%0d,%0d,%0d bad_stage_data=%0d",
   RR,WR,DR0,DR1,DR2,DR3,DW00,DW01,DW10,DW11,DW20,DW21,DW30,DW31,first_fault,gf0,gf1,gf2,gf3,bad_data);
  $finish;
 end
endmodule
