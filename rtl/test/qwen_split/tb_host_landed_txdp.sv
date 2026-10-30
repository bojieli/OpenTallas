`timescale 1ns/1ps
// Component reproduction of TOK-KV-4: exact native SRAM link end, one HOST record.
// The provider boundary is a declared fixed-latency model: 86 outward + 2 HOST +
// 67 return + 2 pin registers = 157. No die/token/physical qualification.
module tb_host_landed_txdp;
parameter integer MUT=0;
localparam integer HOST_D=157;
reg ck=0; always #0.4165 ck=~ck;
reg rst_n=0, txwe=0, start=0, eb=0;
reg [5:0] addr=0; reg [31:0] word=0;
wire [3:0] slot; wire pv,ab,ef; wire [7:0] fc; wire [582:0] flit;
reg [HOST_D-1:0] observed=0;
always @(posedge ck) if(!rst_n) observed<=0; else observed<={observed,slot[1]};
wire ov=observed[HOST_D-1] && MUT!=2;
localparam [547:0] PAYLOAD={17{32'hd293a65c}} | (548'hd << 544);
ot_qwen_d2d_static_end_sfm #(.TXD({8'd3,8'd3,8'(MUT==1?4:157),8'd169}),.FEG(0)) dut(
 .ck({5{ck}}),.rst_n({4{rst_n}}),.por_c({2{rst_n}}),.fg_we({1'b0,txwe}),.fg_addr({6'd0,addr}),
 .cfg_tx_we(txwe),.cfg_rx_we(1'b0),.cfg_addr_c({6'd0,addr}),.cfg_data_c({64'd0,word,word}),.cfg_base_c(10'd0),
 .eb_c({10{eb}}),.epoch_begin(eb),.epoch(8'd1),.cal_start(start),.cal_start_rx(1'b0),
 .start_c({4'd0,{4{start}}}),.seg_c(8'd0),.cal_user_tx(2'd0),.cal_user_rx(2'd0),
 .tx_slot(slot),.tx_kind(),.tx_beat(),.tx_valid({2'd0,ov,1'b0}),.tx_payload({1096'd0,PAYLOAD,548'd0}),
 .tx_user(),.rx_user(),.rx_event(),.rx_slot(),.rx_kind(),.rx_beat(),.rx_payload(),.st_ev_c(),.st_rs_c(),
 .p_tx_up(1'b1),.p_tx_v(pv),.p_tx_flit(flit),.p_rx_v(1'b0),.p_rx_flit(583'd0),
 .epoch_abort(ab),.fault_cause(fc),.end_fault(ef),.cal_running());
integer i,n_tx=0,n_slot=0,n_obs=0;
always @(negedge ck) begin
 if(pv) begin
  n_tx=n_tx+1;
  if(flit[547:0]!==PAYLOAD) $fatal(1,"payload mismatch");
 end
 if(slot[1]) n_slot=n_slot+1;
 if(ov) n_obs=n_obs+1;
end
initial begin
 repeat(4) @(negedge ck); rst_n=1;
 @(negedge ck); eb=1; @(negedge ck); eb=0;
 // A single terminated calendar event: dt 10, port1, kind13, beat0.
 word=(32'd10<<18)|(32'd1<<17)|(32'd1<<14)|(32'd13<<10); txwe=1;
 for(i=0;i<32;i=i+1) begin addr=i; @(negedge ck); end
 txwe=0; repeat(4) @(negedge ck); start=1; @(negedge ck); start=0;
 repeat(200) @(negedge ck);
 if(MUT!=0) begin
  if(ab!==1'b1 || fc!==8'h80) $fatal(1,"mutant escaped: ab=%b fc=%h ef=%b",ab,fc,ef);
  $display("HOST_LANDED_TXDP_CAUGHT MUT=%0d ab=%b fc=%h slots=%0d observed=%0d",MUT,ab,fc,n_slot,n_obs);
 end else begin
  if(ab!==0 || ef!==0 || fc!==0 || n_tx!=1 || n_slot!=1 || n_obs!=1)
    $fatal(1,"fixed failed ab=%b ef=%b fc=%h tx=%0d slot=%0d obs=%0d",ab,ef,fc,n_tx,n_slot,n_obs);
  $display("HOST_LANDED_TXDP_PASS delay=157 payload_bits=548 tx=%0d",n_tx);
 end
 $finish;
end
endmodule
