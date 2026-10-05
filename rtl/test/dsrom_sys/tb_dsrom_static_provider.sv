`timescale 1ps/1ps
module tb_dsrom_static_provider;
reg [9:0] phase=0;reg[13:0] address=0;
wire[63:0] p370,p371,p380,p381;wire[47:0] s37,s38;
ot_v41_stage37_control_rom u37(.phase(phase),.stream_addr(address),.pq0(p370),.pq1(p371),.sq(s37));
ot_v41_stage38_control_rom u38(.phase(phase),.stream_addr(address),.pq0(p380),.pq1(p381),.sq(s38));
reg[63:0] ph37[0:2047],ph38[0:2047];reg[47:0] st37[0:16383],st38[0:16383];
integer i;
initial begin
$readmemh("results/rtl/dsrom_recovery_20261004/immutable_stage_controls/stage37/spine_phase.hex",ph37);
$readmemh("results/rtl/dsrom_recovery_20261004/immutable_stage_controls/stage38/spine_phase.hex",ph38);
$readmemh("results/rtl/dsrom_recovery_20261004/immutable_stage_controls/stage37/spine_stream.hex",st37);
$readmemh("results/rtl/dsrom_recovery_20261004/immutable_stage_controls/stage38/spine_stream.hex",st38);
for(i=0;i<1024;i=i+1)begin
phase=10'(i);#1;
if({p371,p370}!={ph37[2*i+1],ph37[2*i]} || {p381,p380}!={ph38[2*i+1],ph38[2*i]})$fatal(1,"DIFF PHASE index=%0d",i);
end
for(i=0;i<16384;i=i+1)begin
address=14'(i);#1;
if(s37!=st37[i] || s38!=st38[i])$fatal(1,"DIFF STREAM index=%0d",i);
end
$display("PASS static_provider stages=2 phase_word_assertions=4096 stream_word_assertions=32768");
$finish;
end
endmodule
