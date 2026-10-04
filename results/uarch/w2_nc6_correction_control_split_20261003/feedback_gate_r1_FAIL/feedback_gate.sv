module feedback_gate(
input wire [0:0] enable,
input wire [767:0] context_current,
input wire [7:0] context_clean,
input wire [15767:0] current_raw,
input wire [15767:0] current_fixed,
input wire [9635:0] current_payload,
input wire [218:0] current_clean,
input wire [218:0] current_ce,
input wire [218:0] current_bad,
output wire [767:0] context_next,
output wire [7:0] context_we,
output wire [7:0] scrub_v,
output wire [79:0] scrub_index,
output wire [575:0] scrub_original,
output wire [575:0] scrub_candidate,
output wire [0:0] busy,
output wire [0:0] error);
wire [7:0] retire_ready = scrub_v & {8{!error}};
ot_w2_nc6_correction_control dut(.enable(enable),.context_current(context_current),.context_clean(context_clean),.current_raw(current_raw),.current_fixed(current_fixed),.current_payload(current_payload),.current_clean(current_clean),.current_ce(current_ce),.current_bad(current_bad),.retire_ready(retire_ready),.context_next(context_next),.context_we(context_we),.scrub_v(scrub_v),.scrub_index(scrub_index),.scrub_original(scrub_original),.scrub_candidate(scrub_candidate),.busy(busy),.error(error));
endmodule
