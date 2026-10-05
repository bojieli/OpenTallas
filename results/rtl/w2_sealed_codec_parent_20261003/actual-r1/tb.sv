`timescale 1ps/1ps
module tb;
reg [43:0] payload; reg [71:0] current_word;
wire [71:0] encoded_word[0:1],repaired_word[0:1];
wire [43:0] repaired_payload[0:1];wire [5:0] flags[0:1];
genvar g;generate for(g=0;g<2;g=g+1) begin
ot_w2_sealed_secded72 #(.PC_ID(113),.WORD_INDEX(269),.WORD_KIND(3),.PAYLOAD_BITS(g==0?17:44)) dut(
.payload(payload),.current_word(current_word),.encoded_word(encoded_word[g]),
.syndrome(),.overall_odd(),.clean(flags[g][0]),.correctable(flags[g][1]),
.uncorrectable(flags[g][2]),.seal_ok(flags[g][3]),.padding_ok(flags[g][4]),
.release_clean(flags[g][5]),.repaired_payload(repaired_payload[g]),.repaired_word(repaired_word[g]));
end endgenerate
integer fd,n,width,k,checked;reg[71:0] ew,rw;reg[43:0] rp;reg[5:0] f;reg[2047:0] file_name;
initial begin
if(!$value$plusargs("VECTORS=%s",file_name)) $fatal(1,"vectors missing");
fd=$fopen(file_name,"r");if(!fd)$fatal(1,"open vectors");checked=0;
while(!$feof(fd)) begin
n=$fscanf(fd,"%d %h %h %h %h %h %h\n",width,payload,current_word,ew,f,rp,rw);
if(n!=7)$fatal(1,"malformed vector");k=(width==17?0:1);#1;
if(encoded_word[k]!==ew||flags[k]!==f||repaired_payload[k]!==rp||repaired_word[k]!==rw)
 $fatal(1,"codec mismatch case=%0d width=%0d flags=%h expected=%h",checked,width,flags[k],f);
checked=checked+1;
end
$display("PASS_ACTUAL_SEALED_CODEC cases=%0d",checked);$finish;
end
endmodule
