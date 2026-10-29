#!/bin/bash
# HBM-CORES-KITS-5 vms_glue: ot_vms_rcl_static old (main) vs new (fix c2223a91d3), and vs a mutant (negative control)
# A: rcl old==new on every output from reset when the returned reserved tag bits hr[272:267] are 0 (BMC 20 + induction)
# B: the rcl itself only ever issues hq tag bits [15:10] = 0 (so the hub's tag store returns 0 for every WRITTEN slot)
# N1: without the A assumption the miter must FAIL (the dropped check is the only difference)
# N2: mutant (return_port bit forced 0) must FAIL under the A assumption
cd /c; O=/c/out2; mkdir -p $O
for v in old new mut; do
cat > $O/s_$v.ys <<YS
read_verilog -sv /c/$v/ot_vms_rcl_static.sv
hierarchy -top ot_vms_rcl_static
proc; flatten; opt -full; clean -purge
rename -top g_$v
write_verilog -noattr $O/$v.v
YS
yosys -q -s $O/s_$v.ys > $O/s_$v.log 2>&1 || echo "SYNTH FAIL $v"
done
cat > $O/wrap.v <<'V'
module wrap_GOLD_GATE(input clk, input rst_n, input [1:0] sid, input rx_enable, input rx_source, input [287:0] rce0, input [287:0] rce1,
  input [273:0] hr_in, input assume_res0, output trigger);
  wire [273:0] hr = assume_res0 ? {hr_in[273],6'b0,hr_in[266:0]} : hr_in;
  wire [337:0] hq_a, hq_b; wire [265:0] a0,a1,b0,b1; wire fa, fb;
  g_GOLD ua(.clk(clk),.rst_n(rst_n),.sid(sid),.rx_enable(rx_enable),.rx_source(rx_source),.rce0(rce0),.rce1(rce1),.hq(hq_a),.hr(hr),.ri0(a0),.ri1(a1),.fault(fa));
  g_GATE ub(.clk(clk),.rst_n(rst_n),.sid(sid),.rx_enable(rx_enable),.rx_source(rx_source),.rce0(rce0),.rce1(rce1),.hq(hq_b),.hr(hr),.ri0(b0),.ri1(b1),.fault(fb));
  assign trigger = (hq_a!=hq_b)||(a0!=b0)||(a1!=b1)||(fa!=fb);
endmodule
V
run() { # name gold gate assume extra
sed "s/GOLD/$2/g; s/GATE/$3/g" $O/wrap.v > $O/w_$1.v
cat > $O/i_$1.ys <<YS
read_verilog $O/$2.v $O/$3.v $O/w_$1.v
hierarchy -top wrap_$2_$3
proc; flatten; async2sync; opt_clean
sat -verify $5 -set assume_res0 $4 -set-at 1 rst_n 0 -prove trigger 0 -set-def-inputs -set-init-zero wrap_$2_$3
YS
if timeout 1800 yosys -q -s $O/i_$1.ys > $O/i_$1.log 2>&1; then echo "$1: PASS"; else echo "$1: FAIL (rc=$?)"; fi
}
run A_bmc20 old new 1 "-seq 20"
run A_induct old new 1 "-tempinduct -seq 1"
run N1_noassume old new 0 "-seq 6"
run N2_mutant old mut 1 "-seq 6"
# B: hq[15:10] == 0 on every edge (induction over the rcl alone)
cat > $O/b.v <<'V'
module bchk(input clk, input rst_n, input [1:0] sid, input rx_enable, input rx_source, input [287:0] rce0, input [287:0] rce1, input [273:0] hr, output bad);
  wire [337:0] hq; wire [265:0] r0,r1; wire f;
  g_new u(.clk(clk),.rst_n(rst_n),.sid(sid),.rx_enable(rx_enable),.rx_source(rx_source),.rce0(rce0),.rce1(rce1),.hq(hq),.hr(hr),.ri0(r0),.ri1(r1),.fault(f));
  assign bad = hq[15:10] != 6'b0;
endmodule
V
cat > $O/i_B.ys <<YS
read_verilog $O/new.v $O/b.v
hierarchy -top bchk
proc; flatten; async2sync; opt_clean
sat -verify -tempinduct -seq 1 -set-at 1 rst_n 0 -prove bad 0 -set-def-inputs -set-init-zero bchk
YS
if timeout 600 yosys -q -s $O/i_B.ys > $O/i_B.log 2>&1; then echo "B_hq_tag_upper0_induct: PASS"; else echo "B_hq_tag_upper0_induct: FAIL"; fi
echo DONE
