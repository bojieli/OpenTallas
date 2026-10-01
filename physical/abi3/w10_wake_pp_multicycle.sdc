# Baseline closure companion; unchanged geometry/constraint body from d417de733 physical/abi3/v41_w10_elem_pp_multicycle.sdc SHA256 e29aab97de40ea9d6687997f9929ae8a72e6b3dac6e81343fc9d6361fbed72fd
# W10 ping-pong ROM slot (ot_v41_rom_elem PP=1): each ot_rom_4096x274_m8 is read at most every other cycle and its
# word is captured two edges after the read (cap0/cap1 load only in that cycle), so macro -> capture is a 2-cycle
# path.  Hold stays at the launch edge.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]
