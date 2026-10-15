#!/usr/bin/env python3
# Independent old-parent reference: unchanged full390-bit TX/register operands.
# Apply ONLY the explicitly priced extra return/node edges, no bank alias codec.
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2];out=root/'rtl/qwen_sys/tile_parent_banked_20261015'
FROZEN_INPUTS={'rtl/hdc/ot_qwen_w12_matvec.sv': '113f17dddbb3986b714cd4e7df04856c9675aa2affea34774b5cf56888b842a5', 'rtl/hdc/ot_qwen_rom_tile_w12.sv': 'cd8200cb36e4273e78d21a66a816a15e5c3b59b7cb678a692e7c8a51956634b2', 'rtl/physical/ot_qwen_rom_tile_nk.sv': '319061d4c2037e4503b7766bd60bfcb91516d36b708d756d8be18f2ace3b8c54', 'rtl/physical/qfd_tile_nk_slot.sv': 'd0f082b2efe651abbec5f093fe92798b8952dbafa01a5c6ea8741c69e5e50893'}
for n,expected in FROZEN_INPUTS.items():
 assert __import__("hashlib").sha256((ROOT/n if "ROOT" in globals() else root/n).read_bytes()).hexdigest()==expected, "original parent source changed: "+n
def mod(p,n):return re.search(r'^module '+n+r'\b.*?^endmodule',(root/p).read_text(),re.M|re.S)[0]
def change(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
logic=mod('rtl/hdc/ot_qwen_rom_tile_w12.sv','ot_qwen_rom_tile_logic_w12')
logic=logic.replace('ot_qwen_rom_tile_logic_w12','ot_qwen_rom_tile_logic_staged_reference')
logic=change(logic,'localparam integer ME_EXTRA = MEM_EXTRA + RX;','localparam integer ME_EXTRA = MEM_EXTRA + RX + 1;')
logic=change(logic,'assign wrom_q = gs_q | gn_q;','reg [1023:0] gs_extra,gn_extra;\n always @(posedge clk)begin gs_extra<=gs_q;gn_extra<=gn_q;end\n assign wrom_q=gs_extra|gn_extra;')
wrap=mod('rtl/hdc/ot_qwen_rom_tile_w12.sv','ot_qwen_rom_tile_w12').replace('ot_qwen_rom_tile_logic_w12','ot_qwen_rom_tile_logic_staged_reference').replace('module ot_qwen_rom_tile_w12','module ot_qwen_rom_tile_staged_reference',1)
nk=mod('rtl/physical/ot_qwen_rom_tile_nk.sv','ot_qwen_rom_tile_nk').replace('ot_qwen_rom_tile_w12','ot_qwen_rom_tile_staged_reference').replace('module ot_qwen_rom_tile_nk','module ot_qwen_rom_tile_nk_staged_reference',1)
top=mod('rtl/physical/qfd_tile_nk_slot.sv','qfd_tile_nk').replace('ot_qwen_rom_tile_nk','ot_qwen_rom_tile_nk_staged_reference').replace('module qfd_tile_nk','module qfd_tile_nk_staged_reference',1)
top=change(top,'    localparam integer IBW =','    reg [513:0] n_a_s,n_b_s;\n always @(posedge ck)begin n_a_s<=n_a_q;n_b_s<=n_b_q;end\n    localparam integer IBW =')
top=top.replace('n_a_q[','n_a_s[').replace('n_b_q[','n_b_s[')
top=change(top,'    (* keep *) reg [513:0] t_out_q;','    reg [513:0] to_extra,ny_extra;\n always @(posedge ck)begin to_extra<={tf,tv,to};ny_extra<={fy_q,nvy,ny};end\n    (* keep *) reg [513:0] t_out_q;')
top=change(top,'t_out_q[511:0]<=to;','t_out_q[511:0]<=to_extra[511:0];')
top=change(top,'reset_q ? {tf,tv} : 2\'d0','reset_q ? to_extra[513:512] : 2\'d0')
top=change(top,'n_y_q[511:0]<=ny;','n_y_q[511:0]<=ny_extra[511:0];')
top=change(top,'reset_q ? {fy_q,nvy} : 2\'d0','reset_q ? ny_extra[513:512] : 2\'d0')
(out/'qfd_tile_nk_staged_reference.sv').write_text('// Numerical reference only: original parent with explicitly priced extra edges.\n'+logic+'\n'+wrap+'\n'+nk+'\n'+top+'\n')
