`timescale 1ns/1ps
// Actual sequencer PW/start face: 17 reserved words944..960.
// dh fields are those of qfd_seq_su; no readiness gates the issue cycle.
// This separate source leaf permits a minimal real mechanism bench.
module qfd_seq_su_collective_calendar(
 input wire ck,rsi,input wire[186:0]dh,input wire cmd_free,
 output wire[49:0]cmd,output wire fault
);
 wire v,mode,active,done;wire[15:0]words;wire[31:0]tag;
 ot_coll_cmd_issue #(.DEPTH(8),.BASE(944)) u_issue(
 .clk(ck),.rst_n(rsi),.pw_v(dh[118]),.pw_addr(dh[117:108]),.pw_data(dh[107:44]),
 .start(dh[42]),.cmd_free(cmd_free),.cmd_v(v),.cmd_mode(mode),
 .cmd_words(words),.cmd_tag(tag),.active(active),.done(done),.fault(fault));
 assign cmd={v,tag,mode,words};
endmodule
