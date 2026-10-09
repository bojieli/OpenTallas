#!/usr/bin/env python3
"""New SOURCE/STG physical masters using retained full-shape r24/r11 budgets.

Run remotely through measured admission. No old source/view is changed.
"""
import argparse,json
from pathlib import Path
import dsrom_wfc_split_physical as L
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('cmd',choices=['prep','sta','check']);p.add_argument('--inst',choices=['src','stg'],required=True)
 p.add_argument('--case',type=Path,required=True);p.add_argument('--src',type=Path,default=ROOT);p.add_argument('--cores',type=int,default=12);p.add_argument('--need',type=int,default=32)
 a=p.parse_args();basis=json.loads((ROOT/f'physical/dsrom_wfc_tokpipe/{a.inst}_basis.json').read_text())
 L.CTRL='rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv'
 if a.cmd=='sta':return L.cmd_sta(argparse.Namespace(case=a.case,macros=a.inst=='src'))
 if a.cmd=='check':return L.cmd_check(argparse.Namespace(case=a.case))
 # Size before route: retained full-shape basis, same macro count and registered
 # interfaces; SOURCE metadata +1cycle, current-user STAGE tuple +0cycles.
 L.cmd_prep(argparse.Namespace(inst=a.inst,case=a.case,src=a.src,knob=[f'{k}={v}' for k,v in basis['params'].items()],util=50,density=.50,lb_addon=.20,orfs_var=basis['orfs_var'],die_skew=150,link_hold_pad=0,link_hold_abs_min=basis.get('link_hold_abs_min_ps'),route_period=770,ideal_io=False,io_lat=None,cores=a.cores,need=a.need))
 cfg=a.case/'config.mk';s=cfg.read_text().replace('export DESIGN_NAME = ot_rom_pkg_ctrl_wfc\n',f'export DESIGN_NAME = ot_dsrom_wfc_tokpipe_{a.inst}\n')
 s=s.replace('export VERILOG_FILES = ',f'export VERILOG_FILES = /src/rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_{a.inst}.sv ')
 cfg.write_text(s)
 run=a.case/'run.sh';s=run.read_text().replace('tools/dsrom_wfc_split_physical.py sta',f'tools/dsrom_wfc_tokpipe_physical.py sta --inst {a.inst}').replace('tools/dsrom_wfc_split_physical.py check',f'tools/dsrom_wfc_tokpipe_physical.py check --inst {a.inst}')
 # Calibrate stops atCTS; subsequent route keeps the same pinned source and recipe.
 s=s.replace('finish\" > $W/flow.log','${WFC_TARGET:-finish}\" > $W/flow.log')
 s=s.replace('cd $S && python3', 'if [[ "${WFC_TARGET:-finish}" != "finish" ]]; then exit 0; fi\ncd $S && python3',1)
 run.write_text(s)
 print(json.dumps(dict(master=f'ot_dsrom_wfc_tokpipe_{a.inst}',basis=f'physical/dsrom_wfc_tokpipe/{a.inst}_basis.json',source_cycles_added=1 if a.inst=='src' else 0,registered_boundary_unchanged=True)))
if __name__=='__main__':main()
