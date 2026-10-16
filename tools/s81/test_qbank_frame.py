#!/usr/bin/env python3
"""Source-only regressions on the actual128-frame canonical record."""
import ast, copy, json, math, subprocess, sys
from pathlib import Path
from s81.qbank_frame import canonical, slot_extra, EXTRA, require_replan, require_bank_views

def extract(source,name,ctx):
    tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual-source-function>','exec'),ctx)
    return ctx[name]

def main():
    layout=json.loads(Path(sys.argv[1]).read_text());before=copy.deepcopy(layout)
    candidate=canonical(layout,cfifo_h=95.04)
    assert before==layout,'immutable canonical mutated'
    assert candidate['pair_count']==1973 and candidate['q_pairs']==1549 and candidate['bf_pairs']==424
    assert len(candidate['placements'])==128
    assert min(s['available_um'] for s in candidate['qbank_hard_frame']['streets'])==108.0
    assert candidate['qbank_hard_frame']['bank_nominal_height_um']==dict(S=25.92,N=8.64)
    for name,call in [('double_apply',lambda:canonical(candidate,cfifo_h=95.04)),('insufficient_real_stack',lambda:canonical(layout,cfifo_h=130))]:
        try:call()
        except AssertionError:pass
        else:raise AssertionError(name+' incorrectly admitted')
    gates=dict(hop_fix=True,hop_iter=2,col_reset_tree=32,rly_face_pins=True,reset_leaf=True)
    require_replan(**gates)
    for key,bad in [('hop_fix',False),('hop_iter',1),('col_reset_tree',0),('rly_face_pins',False),('reset_leaf',False)]:
        invalid=dict(gates);invalid[key]=bad
        try:require_replan(**invalid)
        except AssertionError:pass
        else:raise AssertionError('old source/glue admitted: '+key)
    try:require_bank_views({})
    except AssertionError:pass
    else:raise AssertionError('missing actual banks admitted')
    source=Path('tools/dsrom_s81_fulldie.py').read_text()
    base=subprocess.check_output(['git','show','17b13fb06:tools/dsrom_s81_fulldie.py'],text=True)
    common=dict(ELEM_DY=77.76,ELEM_FRAME_H=207.36,Q_ELEM_FRAME_H=221.4,GY=2.16,
                up=lambda v,g:round(math.ceil(v/g-1e-8)*g,6))
    oldctx=dict(common);newctx=dict(common,qbank_slot_extra=lambda k:slot_extra(k,False))
    old=extract(base,'pack_frame',oldctx);new=extract(source,'pack_frame',newctx)
    bf={p for f in layout['placements'] for p,k,s,l in f['packed_elements'] if k=='BF'}
    for f in layout['placements']:
        args=(list(range(*f['pairs'])),bf,set())
        assert old(*args)==new(*args),'default pack changed'
    newctx['qbank_slot_extra']=lambda k:slot_extra(k,True)
    for f in candidate['placements']:
        elems,off,h=new(list(range(*f['pairs'])),bf,set())
        assert off==f['slot_offsets_um'] and h==f['slot_heights_um'],('source/canonical row disagreement',f['root'])
        assert [list(e) for e in elems]==f['packed_elements'],'pair/lane identity changed'
    print('QBANK_FRAME PASS:128 default source rows byte-value-identical;128 candidate rows agree;1973pair IDs/lanes; both bank sizes; immutable input; two fail-closed negatives')
if __name__=='__main__':main()
