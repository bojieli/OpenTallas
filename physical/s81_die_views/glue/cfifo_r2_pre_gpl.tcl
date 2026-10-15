# dsfd_cfifo colck recipe-2 pin-register re-route (claude s81-grpA r5, 2026-10-14; S-DIE v19 cfifo_edge owed item):
# native pin audit of the CLOSED colck view (s81-dsfd-cfifo-colck-a6ca75fbe-tt-srcfix): 252 xb outputs launch 263.3 ps
# > 220 at phi - R.  Same RTL / outline / pin positions / SDC as the closed job; only the ref_tile recipe-2 pin stage
# (one dedicated launch flop per output pin FIRM at its pin, HB2 pin pad, capture flop at each input pin).
source /src/physical/common_flow/pin_reg_split.tcl
source /src/physical/dsrom_window_source/leaf_iohold.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
