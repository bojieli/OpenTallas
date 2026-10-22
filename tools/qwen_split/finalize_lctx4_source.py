#!/usr/bin/env python3
"""Add the exact specialized profile and original ROM model bindings to emitted RTL."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--construction',required=True);p.add_argument('--out',required=True);a=p.parse_args()
s=Path(a.raw).read_text();d=json.loads(Path(a.construction).read_text())
s=s.replace('module qfd_sys_face_lctx4_bounded(','''// Fixed production profile; parent selects this master explicitly.
// Header constants remain bound by construction.json; ROM image path is not header authority.
module qfd_sys_face_lctx4_bounded #(
 parameter integer L_CONTEXTS=1,MU=1,MU_HEAD=1,ROPE=1,MUT=0,GO_OFS=3,
 parameter [719:0] START_ADJ='0,
 parameter OVL_ROM_DIR="rtl/qwen_sys/d2d_static_20261015/ovl_release_rope",
 parameter ROM_VIAMAP="",ROM_INSTANCE="sys_face_cfg"
)(''',1)
count=0
for idx,(name,c) in enumerate(d['graph']['cells'].items()):
 if c['type']!='ot_rom_4096x72_m8':continue
 start=f'ot_rom_4096x72_m8 hard_rom_{idx}('
 line=next(x for x in s.splitlines() if x.startswith(start));count+=1
 if name.endswith('.u_cseq.u_rx_rom'):params='.VIAMAP({OVL_ROM_DIR,"/ovl_c_rx.viamap.hex"}),.INSTANCE("ovl_c_rx")'
 elif name.endswith('.u_cseq.u_tx_rom'):params='.VIAMAP({OVL_ROM_DIR,"/ovl_c_tx.viamap.hex"}),.INSTANCE("ovl_c_tx")'
 else:
  assert name.endswith('.u_rom'),name
  params='.VIAMAP(ROM_VIAMAP),.INSTANCE(ROM_INSTANCE)'
 sim=line.replace('ot_rom_4096x72_m8 ',f'ot_rom_4096x72_m8 #({params}) ',1)
 s=s.replace(line,'`ifdef SYNTHESIS\n'+line+'\n`else\n'+sim+'\n`endif',1)
assert count==3
s=s.replace('endmodule','initial if(L_CONTEXTS!=1 || MU!=1 || MU_HEAD!=1 || ROPE!=1 || MUT!=0 || GO_OFS!=3 || START_ADJ!=0) $fatal(1,"LCTX4 is fixed to its bound production profile");\nendmodule',1)
Path(a.out).write_text(s)
