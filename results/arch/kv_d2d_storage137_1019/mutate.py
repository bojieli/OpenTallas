import sys
from pathlib import Path
mode=sys.argv[1]
p=Path('out/candidate.sv');s=p.read_text()
if mode=='no_h0': s=s.replace('wire h0 = we && wa == ra;', "wire h0 = 1'b0;")
if mode=='no_h1': s=s.replace('wire h1 = wq && aq == ra;', "wire h1 = 1'b0;")
if mode=='swap_group': s=s.replace('(MUTFO == 2 && g == 3)', '(g == 3)')
p.write_text(s)
if mode=='new_macro':
 p=Path('out/macro.v');s=p.read_text();s=s.replace('if (r_ce_in) rd_out <= word_read(r_addr_in);\n        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);','if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);\n        if (r_ce_in) rd_out <= word_read(r_addr_in);');p.write_text(s)
