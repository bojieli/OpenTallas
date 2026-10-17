cd "$(dirname "$0")"; iverilog -g2012 -s tb -o p tb.sv m564.sv m1100.sv && vvp p | tail -2; iverilog -g2012 -DMUT -s tb -o m tb.sv m564.sv m1100.sv && vvp m | tail -2
