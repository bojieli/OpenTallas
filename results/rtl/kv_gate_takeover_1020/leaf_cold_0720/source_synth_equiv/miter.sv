module leaf_equiv(ck,rst_n,esh__stack,i_ctl,i_g,i_r,ok);
input ck;
input rst_n;
input [1:0] esh__stack;
input [1117:0] i_ctl;
wire [779:0] gold_o_pc;
wire [779:0] gate_o_pc;
input [143:0] i_g;
input [298:0] i_r;
wire [4:0] gold_o_c0;
wire [4:0] gate_o_c0;
wire [4:0] gold_o_c1;
wire [4:0] gate_o_c1;
wire [4:0] gold_o_c2;
wire [4:0] gate_o_c2;
wire [4:0] gold_o_c3;
wire [4:0] gate_o_c3;
wire [4:0] gold_o_c4;
wire [4:0] gate_o_c4;
wire [4:0] gold_o_c5;
wire [4:0] gate_o_c5;
wire [4:0] gold_o_c6;
wire [4:0] gate_o_c6;
wire [4:0] gold_o_c7;
wire [4:0] gate_o_c7;
wire [270:0] gold_o_ch0;
wire [270:0] gate_o_ch0;
wire [22:0] gold_o_kg;
wire [22:0] gate_o_kg;
wire [143:0] gold_o_ctl;
wire [143:0] gate_o_ctl;
wire [298:0] gold_o_emb;
wire [298:0] gate_o_emb;
output ok;
gold_top gold(.ck(ck),.rst_n(rst_n),.esh__stack(esh__stack),.i_ctl(i_ctl),.o_pc(gold_o_pc),.i_g(i_g),.i_r(i_r),.o_c0(gold_o_c0),.o_c1(gold_o_c1),.o_c2(gold_o_c2),.o_c3(gold_o_c3),.o_c4(gold_o_c4),.o_c5(gold_o_c5),.o_c6(gold_o_c6),.o_c7(gold_o_c7),.o_ch0(gold_o_ch0),.o_kg(gold_o_kg),.o_ctl(gold_o_ctl),.o_emb(gold_o_emb));
gate_top gate(.ck(ck),.rst_n(rst_n),.esh__stack(esh__stack),.i_ctl(i_ctl),.o_pc(gate_o_pc),.i_g(i_g),.i_r(i_r),.o_c0(gate_o_c0),.o_c1(gate_o_c1),.o_c2(gate_o_c2),.o_c3(gate_o_c3),.o_c4(gate_o_c4),.o_c5(gate_o_c5),.o_c6(gate_o_c6),.o_c7(gate_o_c7),.o_ch0(gate_o_ch0),.o_kg(gate_o_kg),.o_ctl(gate_o_ctl),.o_emb(gate_o_emb));

// Observer-only knowledge flags; no DUT/gold/gate FF init assumptions.
reg [2:0] input_known=0;
reg [3:0] reset_known=0;
reg [3:0] reset_samples;
reg head_ever_known=0;
always @(posedge ck)begin
 input_known<={input_known[1:0],1'b1};
 reset_known<={reset_known[2:0],1'b1};
 reset_samples<={reset_samples[2:0],rst_n};
 if(reset_known[3] && !reset_samples[3])head_ever_known<=1'b1;
end
wire relay_required=input_known[2];
wire head_required=head_ever_known || (reset_known[3] && !reset_samples[3]);
assign ok=(!head_required || gold_o_pc == gate_o_pc) && (!relay_required || gold_o_c0 == gate_o_c0) && (!relay_required || gold_o_c1 == gate_o_c1) && (!relay_required || gold_o_c2 == gate_o_c2) && (!relay_required || gold_o_c3 == gate_o_c3) && (!relay_required || gold_o_c4 == gate_o_c4) && (!relay_required || gold_o_c5 == gate_o_c5) && (!relay_required || gold_o_c6 == gate_o_c6) && (!relay_required || gold_o_c7 == gate_o_c7) && (!relay_required || gold_o_ch0 == gate_o_ch0) && (!relay_required || gold_o_kg == gate_o_kg) && (!relay_required || gold_o_ctl == gate_o_ctl) && (!relay_required || gold_o_emb == gate_o_emb);
endmodule
