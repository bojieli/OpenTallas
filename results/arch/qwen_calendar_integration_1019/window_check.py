import sys,json,hashlib,copy
from pathlib import Path
root=Path('../src').resolve();sys.path.insert(0,str(root/'tools/qwen_layerbench'))
from table_load_windows import validate
records={}
manifest=json.loads(Path('table_manifest_identity.json').read_text())['manifest_sha256']
consumer=hashlib.sha256((root/'rtl/qwen_dv/qfd_dv_vm.sv').read_bytes()).hexdigest()
for line in Path('table_windows.trace').read_text().splitlines():
    kind,u,s,edge=line.split();u,s,edge=map(int,(u,s,edge))
    w=records.setdefault((u,s),dict(user=u,stage=s,read_slots=88,manifest_sha256=manifest,consumer_sha256=consumer))
    if kind=='LOAD':w['start']=edge
    elif kind=='FIRST':w['first_read']=min(w.get('first_read',edge),edge)
    elif kind=='LAST':w['last_read']=max(w.get('last_read',edge),edge)
windows=list(records.values())
receipt=validate(windows,manifest)
Path('table_windows.json').write_text(json.dumps(dict(receipt=receipt,windows=windows),indent=2)+'\n')
for name in ('collision','lifetime','early'):
    bad=copy.deepcopy(windows)
    if name=='collision':bad[1]['start']=bad[0]['start']+1
    elif name=='lifetime':bad[0]['last_read']=bad[4]['start']+100
    else:bad[0]['first_read']=bad[0]['start']+91
    try:validate(bad,manifest)
    except ValueError as e:print('WINDOW_MUTANT_REJECT',name,str(e))
    else:raise RuntimeError('window mutant admitted '+name)
print('ACTUAL_CALENDAR_WINDOWS_PASS',receipt)
