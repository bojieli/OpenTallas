#!/usr/bin/env python3
"""Build an immutable actual-COL reset-copy miter capsule (no behavioral stubs)."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source_root',type=Path);p.add_argument('destination',type=Path);p.add_argument('--baseline',default='ebd0e1153f');a=p.parse_args()
r=a.source_root.resolve();l=r/'rtl/dsrom_sys/s81_link';d=a.destination.absolute()
if d.exists():raise SystemExit('destination exists; no overwrite')
d.mkdir(parents=True)
names=['ot_s81_kp4_common.sv','ot_s81_kp4_enc.sv','ot_s81_kp4_bm.sv','ot_s81_kp4_dsyn.sv','ot_s81_kp4_ddly.sv','ot_s81_kp4_dchn.sv','ot_s81_kp4_dout.sv','ot_s81_kp4_dec.sv','ot_pdie_serdes.sv','native/ot_s81_kp4_dec_native_flat.sv','lp/ot_s81_kp4_dec_native_flat_lp.sv','col/ot_pdie_serdes_col.sv','ot_pdie_serdes_locksafe.sv']
for n in names:shutil.copy2(l/n,d/Path(n).name)
for f in l.glob('*.svh'):shutil.copy2(f,d/f.name)
for f in [r/'rtl/common/landed_parent/ot_pl_land.sv',r/'rtl/common/ot_meso_fifo.sv']:shutil.copy2(f,d/f.name)
for name in ['ot_sram_1r1w2c_64x546_m1','ot_sram_1r1w_32x546_m1']:
 path=f'physical/asap7_memory_macros/{name}/{name}.v'
 data=subprocess.run(['git','-C',str(r),'show','HEAD:'+path],capture_output=True,check=True).stdout
 (d/(name+'.v')).write_bytes(data)
path='rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv'
gold=subprocess.run(['git','-C',str(r),'show',a.baseline+':'+path],capture_output=True,text=True,check=True).stdout
gold=gold[:gold.index('endmodule')+len('endmodule')].replace('module ot_pdie_serdes_col #','module ot_pdie_serdes_col_gold #',1)
(d/'col_gold.sv').write_text(gold+'\n')
s=(d/'ot_pdie_serdes_col.sv').read_text();top=s[:s.index('endmodule')+len('endmodule')]
mut=top.replace('module ot_pdie_serdes_col #','module ot_pdie_serdes_col_mut #',1).replace('ot_s81_serdes_col_rst_local u_rst_t_local','ot_s81_serdes_col_rst_local_mut u_rst_t_local')
helper=s[s.index('module ot_s81_serdes_col_rst_local ('):];helper=helper[:helper.index('endmodule')+len('endmodule')]
assert helper.count('else q <= {3{first_stage}};')==1
helper=helper.replace('module ot_s81_serdes_col_rst_local (','module ot_s81_serdes_col_rst_local_mut (').replace('else q <= {3{first_stage}};','else q <= {q[1:0],first_stage};')
(d/'col_mut.sv').write_text(mut+'\n'+helper+'\n')
for n in ['tb_col_rst_local.sv','run_col_rst_local.sh']:shutil.copy2(Path(__file__).parent/n,d/n)
profile={'baseline_commit':a.baseline,'mission_added_cycles':0,'reset_calendar_added_edges':0,'rtl_copies':3,'mapped_copies_required':3,'source_first_stage':'rs_t[0]','async_reset_domain':'rst_g from unchanged recovered-clock LOCKSAFE/HOLD64 sequencer','inherited_TX_delta_vs_POR':8,'inherited_RX_delta_vs_vG':0,'inherited_RX_delta_vs_POR':'RM_STAGED +1 remains unadopted','physical_hold':'no P&R before actual vG PLACE and mapped consumer centroid/clock-budget image review','mutant':'same actual COL, RM/status reset delayed1/2clk edges','files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(d.iterdir()) if f.is_file()}}
(d/'PROFILE.json').write_text(json.dumps(profile,indent=2)+'\n')
print(json.dumps({k:v for k,v in profile.items() if k!='files'},indent=2))
