"""Read-only preflight of a source-bound terminal owner snapshot plan; no replay."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.w17_D1_root_header_layout import parse_layout,check_anchors


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def verify_schema(plan):
    if plan['binary']['SHA256']!='dcbb334df6bd62990f7731c2254cd59aa33aeff0c20b61641edf8345d81e2482':
        raise ValueError('wrong experimental binary')
    if plan['header']['SHA256']!='c66d1ceb7ab3cbf289d9a88822ad6a1cf114cbb29fa37469752d89aa57f70042':
        raise ValueError('wrong root ABI')
    if plan['program']['SHA256']!='dc93faea61a95d04d0a157d09e9c962d7f863bb9559ab92532aed61d7856d1c6':
        raise ValueError('wrong original program')
    if plan['replay_executed'] or plan['new_frontend_or_build'] or plan['fulltoken']:
        raise ValueError('incorrect scope credit')
    if plan['first_return_deadline'] is not None or not plan['no_cap_extension']:
        raise ValueError('unpriced deadline/cap change')
    expected=[plan['binary']['path'],'+DIR=/tmp/w17-D1-native-diagnostic-result-20261002-r1/input']
    if plan['actual_run_argv_gap']['required_argv']!=expected:raise ValueError('program argv binding')
    if plan['capture_hook']['symbol']!='_Z40Vtb_D1_scope_core___024root___eval_finalP27Vtb_D1_scope_core___024root':
        raise ValueError('wrong terminal phase')
    if len(plan['fields'])!=79:raise ValueError('field cardinality')


def validate(plan_path):
    p=Path(plan_path);plan=json.loads(p.read_text());verify_schema(plan)
    for key in ['binary','header','program','GDB']:
        item=plan[key]
        if Path(item['path']).stat().st_size!=item['bytes'] or sha(item['path'])!=item['SHA256']:
            raise ValueError('input hash mismatch '+key)
    root=p.resolve().parents[3]
    for name,expected in plan['source_authority_SHA256'].items():
        if sha(root/name)!=expected:raise ValueError('source authority hash '+name)
    parsed=parse_layout(Path(plan['header']['path']).read_text())['fields'];check_anchors(parsed)
    for name,field in plan['fields'].items():
        if 'control_mask_word' in field:
            base=name.rsplit('[',1)[0];word=field['control_mask_word']
            if type(word) is not int or not 0<=word<4 or parsed[base]['type']!='VlWide<4>':
                raise ValueError('mask word schema')
            expected={**parsed[base],'offset':parsed[base]['offset']+4*word,'bytes':4,'type':'IData','control_mask_word':word}
        else:expected=parsed[name]
        if expected!=field:raise ValueError('field layout mismatch '+name)
    script=(p.parent/'capture_terminal.gdb').read_text()
    prohibited=('run','attach','call','shell','python','start','set variable')
    for line in script.splitlines():
        if any(line==x or line.startswith(x+' ') for x in prohibited):raise ValueError('unsafe script command')
        if line.startswith('set ') and not (line.startswith('set $root = ') or line in ('set pagination off','set confirm off','set args +DIR=/tmp/w17-D1-native-diagnostic-result-20261002-r1/input')):
            raise ValueError('unexpected debugger set command')
    for name,value in json.loads((p.parent/'artifact_SHA256.json').read_text()).items():
        if sha(p.parent/name)!=value:raise ValueError('artifact hash '+name)
    # Defines breakpoint/commands only. No inferior starts, reads, calls or writes.
    r=subprocess.run([plan['GDB']['path'],'-batch','-nx','-x',str(p.parent/'capture_terminal.gdb')],capture_output=True,text=True)
    if r.returncode:raise ValueError('offline GDB definitions failed: '+r.stderr)
    return {'status':'PASS_OFFLINE_PREFLIGHT_ONLY','fields':len(plan['fields']),'inferior_started':False,
            'runtime_admitted':False,'first_return_deadline':None,'fulltoken':False}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');args=a.parse_args()
    print(json.dumps(validate(args.plan),indent=2))
