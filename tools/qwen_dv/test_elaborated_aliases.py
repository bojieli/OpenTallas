"""Retained-module output aliases must canonicalize exact parent consumers."""
from copy import deepcopy
from soft_cone_inventory import expand_hierarchy
def main():
    child={'ports':{'d':{'direction':'input','bits':[2]},'q':{'direction':'output','bits':[2]},
        'zero':{'direction':'output','bits':['0','0']}},'netnames':{},'cells':{}}
    top={'ports':{'i':{'direction':'input','bits':[10]}},'netnames':{},'cells':{
        'child':{'type':'child','connections':{'d':[10],'q':[11],'zero':[12,13]}},
        'use':{'type':'$_AND_','port_directions':{'A':'input','B':'input','Y':'output'},'connections':{'A':[11],'B':[12],'Y':[14]}}}}
    design={'modules':{'top':top,'child':child}}
    result=expand_hierarchy(design,'top')['modules']['top'];con=result['cells']['use']['connections']
    assert con['A']==result['ports']['i']['bits'] and con['B']==['0']
    bad=deepcopy(design);bad['modules']['child']['ports']['other']={'direction':'input','bits':[2]}
    bad['modules']['top']['cells']['child']['connections']['other']=[15]
    try:expand_hierarchy(bad,'top')
    except ValueError as e:assert 'port alias conflict' in str(e)
    else:raise AssertionError('two different inputs accepted as the same child net')
    print('PASS exact passthrough/repeatedconstant aliases and conflictinginput rejection')
if __name__=='__main__':main()
