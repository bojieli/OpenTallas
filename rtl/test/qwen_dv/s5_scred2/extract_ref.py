#!/usr/bin/env python3
"""Extract the ORIGINAL leaf modules (unchanged text) from qfd_dv_s5_leaves.sv as renamed references."""
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text();out=[]
for name,new in (('qfd_dv_s5_rst2','qfd_dv_s5_rst2'),('qfd_dv_s5_red','ref_s5_red'),('qfd_dv_s5_sc','ref_s5_sc')):
    m=re.search(r'module '+name+r'\b.*?endmodule',s,re.S).group()
    out.append(m.replace('module '+name,'module '+new,1))
Path(sys.argv[2]).write_text('`timescale 1ns/1ps\n'+'\n'.join(out)+'\n')
