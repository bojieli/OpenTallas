`timescale 1ns/1fs
// Actual S81 reset cells followed by the LP source's one root pad and
// DEPTH=3 one-leaf forest, then the lane's actual tree3 (223 native32 leaves).
module tb;
parameter integer HOLD=64;
reg clk=0,rst_n=1;
always #0.4165 clk=~clk;
wire root; wire [64:0] wave;
assign wave[0]=root;
ot_dp_rsync_s2 sync(.clk(clk),.async_rst_n(rst_n),.sync_rst_n(root));
for(genvar d=1;d<=64;d=d+1) begin:g_wave
  ot_dp_rrelay relay(.clk(clk),.d(wave[d-1]),.q(wave[d]));
end
reg phase1=0,phase2=0;
initial begin #0.200; forever #0.4165 phase1=~phase1;end
initial begin #0.600; forever #0.4165 phase2=~phase2;end
wire [2:0] lclk={phase2,phase1,clk};
integer low_pin[0:194], low_leaf[0:194];
for(genvar p=0;p<3;p=p+1) begin:g_phase
  for(genvar d=0;d<=64;d=d+1) begin:g_depth
    wire parent_root;
    ot_pl_pad #(.W(1),.N(1)) rp(.ck(clk),.d(wave[d]),.q(parent_root));
    wire [0:0] lane_rs;
    ot_pl_land_reset_forest #(.DEPTH(3),.LEAVES(1),.ROOT_LOADS(2))
      forest(.ck(lclk[p]),.d(parent_root),.q(lane_rs));
    wire [222:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(223)) tree(.clk(lclk[p]),.rst_n_in(lane_rs[0]),.rst_n(rr));
    always @(posedge lclk[p]) begin
      if(lane_rs[0]===1'b0) low_pin[p*65+d]=low_pin[p*65+d]+1;
      if(rr===223'b0) low_leaf[p*65+d]=low_leaf[p*65+d]+1;
    end
  end
end
integer i, minpin,minleaf;
task run(input integer warm); begin
  for(i=0;i<195;i=i+1) begin low_pin[i]=0;low_leaf[i]=0;end
  @(negedge clk);rst_n=0;repeat(HOLD)@(negedge clk);rst_n=1;
  repeat(150)@(negedge clk);
  minpin=100000;minleaf=100000;
  for(i=0;i<195;i=i+1) begin
    if(low_pin[i]<minpin)minpin=low_pin[i];
    if(low_leaf[i]<minleaf)minleaf=low_leaf[i];
  end
  $display("warm=%0d hold=%0d phases=3 depths=65 min_pin=%0d min_all223_leaves=%0d",warm,HOLD,minpin,minleaf);
  if(minpin<64 || minleaf<64)$display("BELOW64");
end endtask
initial begin run(0);run(1);$finish;end
endmodule
