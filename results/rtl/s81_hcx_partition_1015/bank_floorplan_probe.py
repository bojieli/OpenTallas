#!/usr/bin/env python3
"""Use actual production geometry functions, not a halo substitute, to size one bank."""
import sys,json,copy,pathlib
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tools/ref_tile'))
import ref_tile as RT

def probe(W,H,stack):
 s={'kind':'tile','pins':{'W':['stage_d','stage_v_q','stage_word_q','wr','wa','xr','xa'],'E':['wd','xd'],'S':['clk'],'N':[]},'macros':[],'children':[]}
 pitch=62.928 if stack else 84.24
 for c in range(2):
  for r in range(4):
   s['macros'].append({'inst':f'g_rom[{c*2+r//2}].g_page[{r%2}].rom','view':'physical/asap7_memory_macros/ot_rom_4096x266_m8','at':[25.92+c*146.88,25.92+r*pitch],'at_exact':stack,'orient':'R0'})
 for c in range(2):
  s['macros'].append({'inst':f'g_x[{c}].ram','view':'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2','at':[25.92+c*119.232,300.24 if stack else 362.88],'orient':'R0'})
 blocks=RT.blocks_of(s);RT.place_blocks(s,W,H,blocks);findings=RT.floorplan_checks(s,W,H,blocks,1381.58622)
 return {'outline_um':[W,H],'macro_policy':{'channel_um':RT.CHANNEL_UM,'pin_edge_um':RT.PIN_EDGE_UM,'core_margin_um':RT.CORE_MARGIN,'abutted_ROM_stack':stack},'PASS':not any(f[0]=='FAIL' for f in findings),'findings':findings,'blocks':[{k:b[k] for k in ['inst','x','y','w','h','offtrack']} for b in blocks]}
r={'scope':'Actual ref_tile place_blocks/floorplan_checks geometry only; pin face assignment illustrative, no slotgrant/CTS/route/timing qualification','rows':[probe(280,340,False),probe(324,432,False),probe(324,367.2,True),probe(324,324,True)]}
pathlib.Path(__file__).with_name('bank_floorplan_probe.json').write_text(json.dumps(r,indent=2)+'\n')
for row in r['rows']:print(row['outline_um'],row['macro_policy']['abutted_ROM_stack'],row['PASS'],row['findings'])
