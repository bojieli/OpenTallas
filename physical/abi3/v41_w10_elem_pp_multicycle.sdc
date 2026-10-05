# W10 ping-pong ROM slot (ot_v41_rom_elem PP=1): each ot_rom_4096x274_m8 is read at most every other cycle and its
# word is captured two edges after the read (cap0/cap1 load only in that cycle), so macro -> capture is a 2-cycle
# path.  Hold stays at the launch edge.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]
