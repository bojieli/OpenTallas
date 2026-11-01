"""Selector-only repair for the proven native11c config-forward driver names.

No geometry/model/RTL/cycle change and no empty-guide waiver. Input must retain
all seven original logical selectors; the alias/status evidence is kept beside
this finite patch. Do not generalize to another source without mapped evidence.
"""
import copy,json,re,sys
from pathlib import Path
LEAVES=(0,1,3,4,6,8,9)

def patch(doc):
    result=copy.deepcopy(doc);changed={}
    def visit(value):
        if isinstance(value,dict):
            name=value.get('name','')
            match=re.fullmatch(r'pstore_l(0|1|3|4|6|8|9)_cfg_forward',name)
            if match:
                leaf=int(match[1]);old=[f'g_leaf[{leaf}].u_leaf.fwd_addr_q',f'g_leaf[{leaf}].u_leaf.fwd_data_q']
                new=[f'g_leaf[{leaf}].u_leaf.out_addr',f'g_leaf[{leaf}].u_leaf.out_data']
                if value.get('prefixes')!=old or name in changed:
                    raise ValueError('selector input differs from the proved native11c fixture: '+name)
                value['prefixes']=new;changed[name]={'old':old,'new':new,'actual_unique_ff':267,'before_status':'NONE','after_face_status':'NONE'}
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(result)
    if set(changed)!={f'pstore_l{leaf}_cfg_forward' for leaf in LEAVES}:
        raise ValueError('expected exactly seven existing config-forward guides')
    # Reversing just these14 strings must reproduce the complete input object.
    restored=copy.deepcopy(result)
    def reverse(value):
        if isinstance(value,dict):
            if value.get('name') in changed:value['prefixes']=changed[value['name']]['old']
            for child in value.values():reverse(child)
        elif isinstance(value,list):
            for child in value:reverse(child)
    reverse(restored)
    if restored!=doc:raise ValueError('unexpected nonselector mutation')
    return result,changed

if __name__=='__main__':
    source,target=map(Path,sys.argv[1:3]);doc=json.loads(source.read_text());result,delta=patch(doc)
    target.write_text(json.dumps(result,indent=2)+'\n')
    target.with_suffix('.delta.json').write_text(json.dumps({'scope':'SELECTORS_ONLY_NATIVE11C','changes':delta,'geometry_model_source_cycles':'UNCHANGED','mandatory_face_ownership':0,'new_ff':0,'new_cycles':0},indent=2)+'\n')
    print('RETARGET7GUIDES1869PROVEN_UNFIXED_FFS_NO_WAIVER')
