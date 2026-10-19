from pathlib import Path
p=Path('ot_qwen_d2d_cal_sf_fe.sv')
s=p.read_text()
a='(start_allowed ? start_c : 4\'b0) : start_c;'
assert a in s
s=s.replace(a,"start_c : start_c;")
a='''wire [3:0] effective_halt = halt_c | {4{ENABLE_FIRST_EPOCH_GUARD != 0 &&
               (poisoned || fault || bad_write || pair_poison || reload || (any_start && !start_allowed))}};'''
assert a in s
s=s.replace(a,'wire [3:0] effective_halt = halt_c;')
s=s.replace("ev_v <= 1'b1; ev_port", "ev_v <= (ENABLE_FIRST_EPOCH_GUARD == 0 || (!poisoned && !pair_poison)); ev_port")
p.write_text(s)
