`timescale 1ns/1ps
// Distinct exact native8192-position/statictotal12 pin profile.
// Public18-bitposition/24-bitaddress retained; high position or wronglat faults3.
// HB2 is physicalrecipe selection, not logic latency/timing-budget relaxation.
// CROM response remains five edges. Far request gains one edge, all fields atomic.
// f_lat_total counts inner-leaf emission -> return: pins->return = f_lat_total-1.
module qfd_su_cbuf_native_l0_p13_l12_h2 #(parameter integer MUT=0,PIPE_MUT=0)(
 input wire clk,rst_n,input wire[7:0]crom_re,input wire[191:0]crom_addr,input wire[5:0]crom_stage,
 output wire[511:0]crom_q,input wire[5:0]stage,input wire tok_start,input wire[17:0]tpos,
 input wire[2:0]grp,output reg st_rdy,output reg[5:0]st_rdy_stage,output reg[17:0]st_rdy_tpos,
 output wire[7:0]f_re,output reg[191:0]f_addr,output reg[5:0]f_stage,
 input wire[511:0]f_q,input wire f_fault,input wire[4:0]f_lat_total,
 output reg fault,output reg[1:0]fault_code);
 wire rr,ff;wire[5:0]rs,fs;wire[7:0]fr;wire[191:0]fa;wire[1:0]fc;
 reg[7:0]fr_q;
 wire[12:0]rp;reg[2:0]grp_q;reg[4:0]lat_pin,pos_hi_pin;reg cfg_fault;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin lat_pin<=12;pos_hi_pin<=0;cfg_fault<=0;end
 else begin lat_pin<=f_lat_total;pos_hi_pin<=tpos[17:13];cfg_fault<=cfg_fault||(lat_pin!=12)||(|pos_hi_pin);end
 always @(posedge clk)grp_q<=grp;
 ot_qfd_crom_lbuf_ready_epoch #(.SW(8),.NW(13),.QK0(4096),.POST0(4736),.QSCALE(8832),.ROPE0(8833),
 .OSC0(533121),.DSC0(537217),.END(541313),.QKR(10),.NWIN(138),.HEAD(36),
 .SRAM(2),.FLP(12),.PINREG(1),.FLS(0),.FLMAX(31),.FLW(5),.RSTR(1),.MUT(MUT))u_body(
  .clk(clk),.rst_n(rst_n),.crom_re(crom_re),.crom_addr(crom_addr),.crom_stage(crom_stage),.crom_q(crom_q),
  .stage(stage),.tok_start(tok_start),.tpos(tpos[12:0]),.lane_base({18'd0,grp_q,3'd0}),
  .st_rdy(rr),.st_rdy_stage(rs),.st_rdy_tpos(rp),.f_re(fr),.f_addr(fa),.f_stage(fs),
  .f_q(f_q),.f_fault(f_fault||cfg_fault),.f_lat(f_lat_total),.fault(ff),.fault_code(fc));
 always @(posedge clk)begin f_addr<=fa;f_stage<=fs;st_rdy_stage<=rs;st_rdy_tpos<={5'd0,rp};end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin fr_q<=0;st_rdy<=0;fault<=0;fault_code<=0;end
 else begin fr_q<=fr;st_rdy<=rr&&!cfg_fault;fault<=ff||cfg_fault;fault_code<=cfg_fault?2'b11:fc;end
 assign f_re=(PIPE_MUT!=0)?fr:fr_q;
endmodule
