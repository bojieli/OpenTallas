#!/bin/bash
# yosys 0.68 + ASAP7 RVT SS NLDM: area/flops of pad chain vs elastic receive FIFO (+ send credit counter)
set -e
trap "rm -rf libs" EXIT
cd "$(dirname "$0")"
L=$HOME/.cache/opentallas/asap7_nldm
mkdir -p libs out
for f in SEQ_RVT_SS_nldm_220123.lib; do cp $L/asap7sc7p5t_$f libs/; done
for f in SIMPLE_RVT_SS_nldm_211120 AO_RVT_SS_nldm_211120 OA_RVT_SS_nldm_211120 INVBUF_RVT_SS_nldm_220122; do zcat $L/asap7sc7p5t_$f.lib.gz > libs/$f.lib; done
LIBS=$(ls libs/*.lib | sed 's/^/-liberty /' | tr '\n' ' ')
run() { # top params tag
  yosys -q -p "read_verilog -sv pad_vs_fifo.sv; chparam $2 $1; synth -flatten -top $1; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib; abc -D 833 $(ls libs/*.lib | sed 's/^/-liberty /' | tr '\n' ' '); opt_clean; tee -o out/$3.stat stat $LIBS" >/dev/null
}
W=64
for D in 1 2 4 5 8 12 15; do run cal_pad "-set W $W -set D $D" pad_W${W}_D$D; done
for D in 2 4 6 8 10 12 16; do run cal_erx "-set W $W -set D $D" erx_W${W}_D$D; run cal_etx "-set D $D" etx_D$D; done
