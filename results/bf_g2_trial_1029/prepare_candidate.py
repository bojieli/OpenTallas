import json,pathlib,re,sys
R=pathlib.Path(__file__).resolve().parent;root=R.parents[1];s81=root/'physical/die_plan/s81';sys.path.insert(0,str(root/'tools/die_plan'))
import master_slice as M
sl=json.load(open(R/'slice/ot_v41_bf_col.json'));layer,x,y,(w,h)=M.slice_placements(R,sl,'clk')['clk']
p=json.load(open(s81/'die_plan.json'));pcs=[]
for t in p['partition_types'].values():
 for c in t.get('hard_cores',[]):
  if c.get('module')=='ot_v41_bf_col':pcs.append(c)
c=pcs[0];q=json.load(open(s81/c['pins_file']));text=(root/c['lef']).read_text()
for pin in q['pins']:
 if pin['name']=='clk':pin.update(layer=layer,x=x,y=y)
block=re.search(r'(?ms)^\s*PIN clk\s*\n.*?^\s*END clk\s*$',text);assert block
b=f'  PIN clk\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER {layer} ;\n        RECT {x-w/2:.4f} {y-h/2:.4f} {x+w/2:.4f} {y+h/2:.4f} ;\n    END\n  END clk'
text=text[:block.start()]+b+text[block.end():]
lef=R/'input/ot_v41_bf_col_centroid.lef';lef.write_text(text);q['lef']=str(lef.relative_to(root));pins=R/'input/ot_v41_bf_col_centroid_pins.json';pins.write_text(json.dumps(q,indent=1))
for c in pcs:c.update(lef=str(lef.relative_to(root)),pins_file='../../../'+str(pins.relative_to(root)))
(R/'input/plan_centroid.json').write_text(json.dumps(p));print('CENTROID_EXPLICIT_CLOCK',layer,x,y,w,h)

# This trial was planned and reviewed against the wider two-ROM gap. Carry it
# explicitly into generation; the shared default recipe has a different gap.
recipes=json.load(open(s81/'cores/legacy/recipes.json'))
recipe=recipes['ot_v41_bf_col']
recipe['macro_sites']={'ot_rom_4096x274_m8':[[42.12,30.960,'R180'],[42.12,104.784,'MY']]}
recipe['_why']='BF G2 trial only: restore the exact approved native 10.872um ROM gap; all5558 planned clock cells remain unchanged.'
(R/'input/recipes_g2.json').write_text(json.dumps({'ot_v41_bf_col':recipe},indent=1)+'\n')
