// Opt-in native PQ ingress. Model: tools/hbm_sm_command_model.py.
// Exact existing seq.hex representation: word indices 0 rows,1 c,2 g,3 fmt,
// 4 lines,5 gs,6 load,7 x extent,8 dependency,9 x base.
// Conservative serialization also protects ring reuse. Publication means the
// complete X operand is visible at the selected SM; retirement is that SAME
// accepted operation's actual completion, not a command-memory acknowledgement.
module ot_hbm_sm_seq_ingress #(parameter ENABLE=0, HOPS=8, DEPTH=1)(
 input wire clk,rst_n,
 input wire seq_valid, output wire seq_ready, input wire [319:0] seq_data,
 input wire operand_published, input wire retired,
 output wire start, input wire start_ready,
 output wire [12:0] op_rows, output wire [15:0] op_c,
 output wire [7:0] op_g, output wire op_gs, output wire [1:0] op_fmt,
 output wire [6:0] op_xb, output reg fault
);
 reg active,pending;
 reg [46:0] payload;
 wire credit;
 wire [46:0] received;
 wire valid_record = seq_data[31:0]>0 && seq_data[31:0]<=4096 &&
   seq_data[63:32]>0 && seq_data[63:32]<=65535 &&
   seq_data[95:64]>0 && seq_data[95:64]<=255 &&
   seq_data[127:96]<=2 && seq_data[191:160]<=1 &&
   seq_data[223:192]<=1 && seq_data[255:224]<=128 &&
   seq_data[287:256]<=1 && seq_data[319:288]<128;
 assign seq_ready=ENABLE && !active && !fault && operand_published;
 wire send=ENABLE && pending && !fault;
 wire ch_valid;
 assign start=ENABLE && ch_valid;
 assign {op_rows,op_c,op_g,op_gs,op_fmt,op_xb}=received;
 ot_hbm_accel_smv_chan #(.W(47),.P(HOPS),.DEPTH(DEPTH)) channel(
  .clk(clk),.rst_n(rst_n),.s_valid(send),.s_ready(credit),.s_data(payload),
  .m_valid(ch_valid),.m_ready(ENABLE && start_ready),.m_data(received));
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin active<=0;pending<=0;payload<=0;fault<=0;end
  else if(ENABLE) begin
   if(seq_valid && seq_ready && operand_published) begin
    if(!valid_record) fault<=1;
    else begin
     active<=1;pending<=1;
     payload<={seq_data[12:0],seq_data[47:32],seq_data[71:64],
               seq_data[160],seq_data[97:96],seq_data[294:288]};
    end
   end
   if(send && credit) pending<=0;
   if(retired) begin
    if(!active || pending) fault<=1;
    else active<=0;
   end
  end
 end
endmodule
