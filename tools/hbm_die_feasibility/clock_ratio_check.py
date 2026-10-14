#!/usr/bin/env python3
"""Validate retained actual OpenSTA paths and known-offset sign/unit conservation."""
import argparse,gzip,json,math,re,hashlib
from pathlib import Path

EXPECTED={(a,b,t) for a,b in [('C','V'),('V','C'),('C','VN'),('VN','C')] for t in ['max','min']}
def parse(text,mode):
    if 'time 1ps' not in text or 'PROBE_COMPLETE '+mode not in text:raise ValueError('missing units/completion')
    if 'STA-1010' in text:raise ValueError('no common period warning')
    paths={}
    for a,b,t,body in re.findall(r'PAIR_BEGIN (\S+) (\S+) (\S+)\n(.*?)PAIR_END \1 \2 \3',text,re.S):
        key=(a,b,t);s=re.findall(r'([-+\d.]+)\s+slack \((?:MET|VIOLATED)\)',body)
        if key in paths or len(s)!=1:raise ValueError('ambiguous or missing path')
        val=float(s[0])
        if not math.isfinite(val):raise ValueError('nonfinite path')
        paths[key]=val
    if set(paths)!=EXPECTED:raise ValueError('missing/extra related path coverage')
    return paths

def validate(logs):
    data={m:parse(t,m) for m,t in logs.items()}
    if set(data)!={'ROUNDED','DERIVED','SHIFT100'}:raise ValueError('missing probe mode')
    differences={}
    for key in EXPECTED:
        delta=data['SHIFT100'][key]-data['DERIVED'][key]
        expected=100 if (key[0]=='C')==(key[2]=='max') else -100
        if abs(delta-expected)>0.001:raise ValueError('incorrect source-offset sign/units: '+str(key))
        differences['/'.join(key)]={'actual_delta_ps':delta,'expected_delta_ps':expected}
    return {'paths_ps':{m:{'/'.join(k):v for k,v in sorted(rows.items())} for m,rows in data.items()},'offset_differences':differences,'negative_path_count':sum(v<0 for rows in data.values() for v in rows.values()),'qualified':False,'actual_child_insertion_compensation_proven':False,'only_known_test_offset_proven_ps':-100,'rounding_alone_reproduces_STA_1010':False}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--logs',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args()
    logs={m:gzip.decompress((p.logs/(m+'.log.gz')).read_bytes()).decode() for m in ['ROUNDED','DERIVED','SHIFT100']};d=validate(logs)
    d.update({'schema':'opentallas.actual_clock_ratio_units_probe.v1','image_sha256':'16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','ot_run_units':['3234506-1791980000','3256191-1791980401'],'host':'ot-epyc1tb','memory_gb':2,'threads':1,'exit_codes':[0,0],'actual_clock_source_model':'Synthetic independent 25ps inputs; real inverter-derived falling capture clock, no child source/driver binding','logs_sha256':{m:hashlib.sha256(t.encode()).hexdigest() for m,t in logs.items()}})
    p.output.write_text(json.dumps(d,indent=2)+'\n')
