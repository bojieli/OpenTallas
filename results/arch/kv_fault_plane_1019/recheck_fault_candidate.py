"""Read-only strict bind on pinned old case, using newly derived exact relay pads."""
import argparse
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser()
for key in ('run','source_tree','tools_tree','pads','out','die'):
    p.add_argument('--'+key.replace('_','-'), type=Path, required=True)
a=p.parse_args()
for key,value in vars(a).items():setattr(a,key,value.resolve())
r=json.loads((a.run/'port_bind_v2/port_bind_v2.json').read_text())
cmd=['python3',str(a.tools_tree/'tools/die_port_bind.py'),str(a.die),
     '--rtl-root',str(a.source_tree/'rtl'),'--pad-file',str(a.pads),
     '--strap-file',str(a.run/'port_bind_v2/straps.json'),'--out',str(a.out)]
for d in ('physical/qkd_astk_strip/macros','physical/asap7_memory_macros','physical/asap7_memory_macros_v2'):
    if (a.source_tree/d).is_dir():cmd+=['--lib-root',str(a.source_tree/d)]
for f in ('rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv'):
    cmd+=['--prefer',str(a.source_tree/f)]
for f in r['rtl_files']+[str(a.source_tree/'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv')]:
    cmd+=['--rtl-file',str(a.source_tree/f if not Path(f).is_absolute() else Path(f))]
for m in ('qkd_hbm3e_phy_pc','qkd_ckbump','qkd_fwdbump','ot_qkvd_ucie_x64_phy','ot_qkvd_ucie_x64_phy_model',
          'ot_qfd_serdes_112g_x12_phy','qkd_pll_analog_model'):
    cmd+=['--allow-model',m]
result=subprocess.run(cmd,cwd=a.source_tree)
# FAIL is expected until actual functional consumers and all independently proven spare families are resolved.
print('STRICT_RECHECK_RETURN',result.returncode)
