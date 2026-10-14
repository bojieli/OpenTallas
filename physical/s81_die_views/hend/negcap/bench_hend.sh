#!/bin/bash
# Transaction scoreboard independent of the DUT capture register. Driver changes
# lane data on the physical launch (posedge fi); receiver captures on negedge.
set -eu
mode=$1; top=$2; kind=$3; O=$4
mkdir -p "$O"; O=$(realpath "$O")
G=results/rtl/dsrom_s81_fulldie_20261004/v17_negcap/dsfd_hend.sv
if [ "$mode" = mut ]; then
  sed 's/dq0 <= di0;/dq0 <= di0 ^ 514\x27h4;/' "$G" > "$O/mut.sv"
  cmp -s "$G" "$O/mut.sv" && exit 2
  G=$O/mut.sv
fi
cat > "$O/tb.sv" <<'EOT'
`timescale 1ps/1fs
module tb;
parameter integer KIND=0;
reg ck=0, fi=0, rs=1;
reg [513:0] di=0;
wire [514:0] o;
`DUT dut(.ck(ck),.fi0(fi),.rs(rs),.di0(di[`DW-1:0]),.o(o));
integer ph, ns=0, nr=0, err=0, launches=0;
reg [511:0] sent[0:16383];
reg [513:0] cap=0;
reg [511:0] w;
initial begin
  if (!$value$plusargs("PH=%d",ph)) ph=0;
  #(ph);
  if(KIND==2) #833.331; else #833.333;
  fi=1;
  forever begin if(KIND==2) #416.6655 fi=~fi; else #416.6665 fi=~fi; end
end
initial begin
  if(KIND==2) #1111.108; else #833.333;
  ck=1;
  forever begin if(KIND==2) #555.554 ck=~ck; else #416.6665 ck=~ck; end
end
initial begin #100 rs=0; #20000 rs=1; #8000 di[0]=1; end
always @(posedge fi) begin
  if (KIND==0) begin
    if (dut.u_0.w_rdy) begin sent[ns]=cap[511:0]; ns=ns+1; end
  end else if (dut.u_0.w_rdy && cap[1]) begin sent[ns]=cap[513:2]; ns=ns+1; end
  launches=launches+1;
  w={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
  if (KIND==0) di[511:0]<=w;
  else begin
    di[513:2]<=w;
    // R2L consumer is slower: send sparse words, no backpressure at this boundary.
    di[1]<=di[0] && launches>60 && launches<8000 && ((launches % 4)==0);
  end
end
always @(negedge fi) cap=di;
always @(posedge ck) if(rs && o[0]) begin
  if(nr>=ns || o[512:1] !== sent[nr]) begin
    if(err<4) $display("ERROR word %0d ns=%0d got=%h want=%h",nr,ns,o[512:1],sent[nr]);
    err=err+1;
  end
  nr=nr+1;
end
initial begin
  #8000000;
  if(nr<1500 || (KIND!=0 && nr!=ns) || (KIND==0 && ns-nr>16)) err=err+1;
  $display("HEND_BENCH %s kind=%0d phase=%0d sent=%0d received=%0d errors=%0d",err ? "FAIL":"PASS", KIND,ph,ns,nr,err);
  $finish;
end
endmodule
EOT
if [ "$kind" = m2l_raw ]; then K=0; DW=512; elif [ "$kind" = m2l_vr ]; then K=1; DW=514; else K=2; DW=514; fi
verilator --binary --timing -j 4 -O1 --x-assign unique --x-initial unique -Wno-fatal -Wno-lint -Wno-style --top-module tb -DDUT=$top -DDW=$DW -GKIND=$K "$O/tb.sv" "$G" rtl/common/ot_meso_fifo.sv rtl/common/ot_ratio_cdc_fifo.sv -Mdir "$O/obj" -o tb > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; exit 2; }
fail=0
for ph in 0 200 416 600 820; do
 "$O/obj/tb" +PH=$ph +verilator+rand+reset+2 +verilator+seed+$((ph+1)) > "$O/run_$ph.log" 2>&1
 grep HEND_BENCH "$O/run_$ph.log"
 grep -q 'HEND_BENCH PASS' "$O/run_$ph.log" || fail=1
done
exit $fail
