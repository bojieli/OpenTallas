# HBMc/TILES 10-22 (SVG native census): the reviewed Gray FIFO is instantiated bit-sliced (landing banks RSN x RSW, the
# descriptor DSN x DSW); every slice's ot_reset_sync pipe and wr/rd_online flag has identical inputs, so opt_merge folded
# them into one flop per family (a3080d9c9 census: 132-244 async-reset pins per merged pipe).  Mark them keep (wires) so
# ot_keep_regs keeps one flop per slice as the RTL declares.  Function and RTL unchanged.
yosys setattr -set keep 1 w:reset_pipe w:wr_online w:rd_online
source /src/physical/common_flow/ot_keep_regs.tcl
