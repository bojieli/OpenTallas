"""Capture metadata projections only; no payload, execution, or schedule build."""
import argparse,gzip,hashlib,json,subprocess
from pathlib import Path

def packed(x):return gzip.compress(json.dumps(x,sort_keys=True,separators=(',',':')).encode(),mtime=0)

def capture(out,calendar):
    commit=subprocess.check_output(['git','rev-parse','8fab955']).decode().strip()
    path='results/uarch/h3_qwen_complete_native_20261002/Qwen_native.json.gz'
    raw=subprocess.check_output(['git','show',commit+':'+path]);x=json.loads(gzip.decompress(raw))
    ops=[]
    def wide_symbols(recipe):
        result=set()
        for node in recipe:
            if node['op']=='FOR':result.update(wide_symbols(node['body']))
            elif node['op'] in ('FTOI','SHL64','IADD64'):result.add(node['dst'])
        return sorted(result)
    for o in x['operations']:
        row={k:o[k] for k in ['pc','opcode','participants','temporary_storage','calendar_counts_full_context','dependencies']}
        row['explicit64bit_symbols']=wide_symbols(o['recipe']);ops.append(row)
    native={'source_commit':commit,'source_path':path,'source_SHA256':hashlib.sha256(raw).hexdigest(),
        'provider_binding_pin':x['provider_binding_pin'],'allocation':x['concrete_provider_binding']['allocation'],'operations':ops}
    manifest_raw=(calendar/'manifest.json').read_bytes();manifest=json.loads(manifest_raw)
    raw=(calendar/'Qwen.json.gz').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=manifest['output_sha256']['Qwen.json.gz']:raise ValueError('calendar source digest')
    cal=json.loads(gzip.decompress(raw))
    programs={k:{field:p[field] for field in ['finite_scratch_bytes','scratch_homes','duration']} for k,p in cal['native_programs'].items()}
    events=[{k:e[k] for k in ['pc','rank','native_program_ref']} for e in cal['events'] if 'native_program_ref' in e]
    projection={'observed_calendar_path':str(calendar),'calendar_output_sha256':sha,'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),
        'manifest':manifest,'programs':programs,'native_events':events}
    out.mkdir(parents=True,exist_ok=True)
    (out/'native_workspace_metadata.json.gz').write_bytes(packed(native))
    (out/'calendar_workspace_metadata.json.gz').write_bytes(packed(projection))
    pins={'files':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['native_workspace_metadata.json.gz','calendar_workspace_metadata.json.gz']},
          'input_scope':'Pure source metadata projection; no checkpoint payload','replay':'python3 tools/qwen_native_workspace_capture_r20.py --output /tmp/FRESH --calendar-directory <pinned native_r3 directory>'}
    (out/'input_manifest.json').write_text(json.dumps(pins,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--calendar-directory',type=Path,required=True);a=p.parse_args();capture(a.output,a.calendar_directory)
