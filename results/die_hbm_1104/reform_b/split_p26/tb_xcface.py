#!/usr/bin/env python3
"""HBM-REFORM-B5 part 26 bench: rel_id runs behind its kit shell (+1 in, +1 out), so xc must too; in the die xc is a hard core with the same shell and its command stays aligned with the group's.
    tb_xcface.py TB.sv   (in place)"""
import sys
p=sys.argv[1]; s=open(p).read()
a=""".cfg_v(cfg_v),.cfg_target(target),.cfg_addr(addr),.cfg_data(data),.desc_v(desc_v),.desc_base(dbase),.desc_limit(dlimit),
  .desc_loops(dloops),.launch_v(launch_v),.cmd_ext(cmd_ext),.kv_desc(kv_desc),"""
assert s.count(a)==1
s=s.replace(a,""".cfg_v(fx_cfg_v),.cfg_target(fx_target),.cfg_addr(fx_addr),.cfg_data(fx_data),.desc_v(fx_desc_v),.desc_base(fx_dbase),.desc_limit(fx_dlimit),
  .desc_loops(fx_dloops),.launch_v(fx_launch_v),.cmd_ext(fx_cmd_ext),.kv_desc(fx_kv_desc),""")
b=" wire[108:0]cmd_ext;wire[63:0]kv_desc;wire xc_done,xc_cfgd,xc_fault,xc_active;\n"
assert s.count(b)==1
s=s.replace(b," reg[108:0]cmd_ext;reg[63:0]kv_desc;wire xc_done,xc_cfgd,xc_fault,xc_active;wire[108:0]fx_cmd_ext;wire[63:0]fx_kv_desc;\n"
 " reg fx_cfg_v,fx_desc_v,fx_launch_v;reg[$bits(target)-1:0]fx_target;reg[$bits(addr)-1:0]fx_addr;reg[$bits(data)-1:0]fx_data;reg[$bits(dbase)-1:0]fx_dbase;reg[$bits(dlimit)-1:0]fx_dlimit;reg[$bits(dloops)-1:0]fx_dloops;\n"
 " always @(posedge stream)begin fx_cfg_v<=cfg_v;fx_desc_v<=desc_v;fx_launch_v<=launch_v;fx_target<=target;fx_addr<=addr;fx_data<=data;fx_dbase<=dbase;fx_dlimit<=dlimit;fx_dloops<=dloops;cmd_ext<=fx_cmd_ext;kv_desc<=fx_kv_desc;end\n")
open(p,'w').write(s)
