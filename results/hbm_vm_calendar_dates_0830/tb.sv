`timescale 1ns/1ps
module tb #(parameter PAD=0,REQMUT=0);
reg clk=0,rst=0;
always #0.4165 clk=~clk;
integer cycle=0,launch=-1,seen[0:3],near_seen[0:3];
reg [7:0] pv=0; reg [127:0] sector=0;
wire[135:0] rq; wire[2055:0] rr; wire[7:0] stage_v; wire fault;
wire[2247:0] wq;
ot_hgi_sfu_vm_static_bridge #(.LWB(15),.READ_RETURN(88),.WRITE_RETURN(85)) bridge(
 .clk(clk),.rst_n(rst),.clk_lg({4{clk}}),.rst_lg_n({4{rst}}),
 .prefetch_v(pv),.prefetch_sector(sector),.prefetch_group(16'b0),.prefetch_local_addr(120'b0),.prefetch_scalar(8'b0),.prefetch_word(24'b0),.scalar_addr(96'b0),
 .local_rq(rq),.local_rr(rr),.stage_v(stage_v),.stage_group(),.stage_addr(),.stage_data(),.stage_mask(),.scalar_load(),.scalar_load_addr(),.scalar_data(),
 .drain_v(2'b0),.drain_round_bf16(2'b0),.drain_vm_sector(32'b0),.drain_result_v(2'b0),.drain_data(512'b0),.local_wq(wq),.local_w_done(8'b0),.fault(fault));
for(genvar q=0;q<4;q=q+1)begin:g
 localparam RT=(q==0)?29:(q==2)?23:19;
 localparam REQ=3+((q==2)?15:0)+REQMUT;
 localparam ARRIVAL=(q==0)?37:(q==2)?46:27;
 localparam PAD_DEPTH=PAD?(88-ARRIVAL):0;
 wire[33:0] rq_leaf,near_rq;
 wire[513:0] leaf_rr,near_rr;
 wire[1:0] near_valid;
 wire tap_fault;
 // Wrapper timing projection only: CTL m21 + source BOUT + final BIN;
 // Q2 additionally has exact selected B012 six and B002 nine FT stages.
 ot_hdc_delay #(.W(34),.D(REQ),.RESET(1)) request_path(clk,rst,rq[34*q+:34],rq_leaf);
 ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(RT),.WRITE_RETURN(RT-3)) leaf(
 .clk(clk),.rst_n(rst),.c_rq(rq_leaf),.c_wq(562'b0),.c_rr(leaf_rr),.c_w_done(),
 .local_read(2'b11),.local_write(2'b11),.far_rq(34'b0),.far_wq(562'b0),.far_rr(),.far_w_done(),
 .near_rq(near_rq),.near_wq(),.near_rr(near_rr),.near_w_done(2'b0),.fault(tap_fault));
 // Ideal legal near-side response for this exact tap calendar, not native VMS proof.
 ot_hdc_delay #(.W(2),.D(RT-3),.RESET(1)) near_environment(clk,rst,{near_rq[33],near_rq[16]},near_valid);
 assign near_rr={near_valid[1],256'hb,near_valid[0],256'ha};
 // Actual return BOUT + B113 BIN + CTL g_compose_m23 capture.
 ot_hdc_delay #(.W(514),.D(3+PAD_DEPTH),.RESET(1)) return_path(clk,rst,leaf_rr,rr[514*q+:514]);
 always @(negedge clk)if(rst)begin
  if(cycle>130 && tap_fault)$fatal(1,"Ideal near environment violated tap calendar q%0d",q);
  if(near_rq[16]&&near_seen[q]<0)near_seen[q]=cycle;
  if(rr[514*q+256]&&seen[q]<0)begin seen[q]=cycle;$display("RETURN q=%0d cycle=%0d launch=%0d delta=%0d",q,cycle,launch,cycle-launch);if(cycle-launch!=(PAD?88:ARRIVAL))$fatal(1,"Response date differs from source-stage projection");end
 end
end
always @(posedge clk)cycle<=cycle+1;
initial begin
 for(integer q=0;q<4;q=q+1)begin seen[q]=-1;near_seen[q]=-1;end
 for(integer b=0;b<8;b=b+1)sector[16*b+:16]=b;
 repeat(10)@(negedge clk);rst=1;
 repeat(10)@(negedge clk);pv=8'hff;launch=cycle+1;
 @(negedge clk);pv=0;
 repeat(120)@(negedge clk);
 for(integer q=0;q<4;q=q+1)begin
  if(seen[q]<0)$fatal(1,"Missing projected source return q%0d",q);

 end
 if(fault !== (PAD?1'b0:1'b1))$fatal(1,"Unexpected bridge mismatch control");
 $display("END PAD=%0d diagnostic_bridge_fault=%b",PAD,fault);$finish;
end
always @(negedge clk)if(|stage_v)$display("META cycle=%0d launch=%0d delta=%0d stage=%h",cycle,launch,cycle-launch,stage_v);
endmodule
