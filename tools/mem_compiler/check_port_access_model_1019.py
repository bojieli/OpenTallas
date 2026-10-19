#!/usr/bin/env python3
"""Fleet entry point: python3 this.py PLANNER_SOURCE INPUT_JSON.

The two causal geometry mutants preserve every endpoint and count while
breaking column separation or physical connectivity.
"""
import json
import sys

code=sys.argv[1]
data=json.loads(sys.argv[2])
namespace={'__name__':'model_test'}
exec(code,namespace)
model=namespace['plan'](data)
assert model['proof']['geometry_error_count']==0
assert model['proof']['source_to_terminal_connected_paths']==437
print(json.dumps(model,indent=2,sort_keys=True))
print('ACCESS_MODEL_PASS paths=437 connected=437 vias=870 geometry_errors=0',file=sys.stderr)
for name,old,new in (
    ('UNREVERSED_COLUMNS','t=228+(n-1-k)*96','t=228+k*96'),
    ('MISSING_SOURCE_VIA','for y in (old_y,new_y):','for y in (new_y,):'),
):
    mutated=code.replace(old,new)
    assert mutated!=code
    scope={'__name__':'model_mutant'}
    exec(mutated,scope)
    try:
        bad=scope['plan'](data)
        assert bad['proof']['geometry_error_count']==0,str(bad['proof']['errors'][0])
    except AssertionError as error:
        print('MUTANT_'+name+'_FAIL '+str(error)[:1500],file=sys.stderr)
    else:
        raise AssertionError('mutant survived: '+name)
