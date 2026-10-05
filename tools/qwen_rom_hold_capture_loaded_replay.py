#!/usr/bin/env python3
"""Verify the immutable full-load packet and replay its six SS/FF reports.

No synthesis, RTL alteration, solver campaign or P&R. Exit zero means the
recorded characterization reproduces, including its blocking failures.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from qwen_rom_hold_capture_loaded_map import worst_slack, consumer_endpoints

def replay(base, sta):
    manifest=json.loads((base/'terminal_manifest_r4.json').read_text())
    record=json.loads((base/manifest['result']).read_text())
    with tempfile.TemporaryDirectory(prefix='qwen-loaded-replay-') as temp:
        work=Path(temp)
        for name,pins in manifest['artifacts'].items():
            raw=(base/'terminal_r4'/name).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==pins['sha256'],name
            data=gzip.decompress(raw)
            assert hashlib.sha256(data).hexdigest()==pins['uncompressed_sha256'],name
            (work/name.removesuffix('.gz')).write_bytes(data)
        net=json.loads((work/'mapped.json').read_text())['modules']['qwen_loaded_capture']
        local={v['bits'][0] for k,v in net['netnames'].items()
               if '.g_direct.g_mask[' in k and k.endswith('.local_sel')}
        assert len(local)==80 and len(consumer_endpoints(net))==512
        counts={}
        for cell in net['cells'].values():
            counts[cell['type']]=counts.get(cell['type'],0)+1
        assert counts==record['mapped_cell_counts']
        for timing in record['timings']:
            key=timing['corner']+'_'+timing['scope']
            tcl=(work/(key+'.tcl')).read_text().replace(manifest['original_workdir'],str(work))
            for corner in ['ss','ff']:
                old=manifest['original_source_root']+f'/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_{corner}.lib'
                tcl=tcl.replace(old,str(work/f'macro_{corner}.lib'))
            script=work/(key+'.tcl');script.write_text(tcl)
            proc=subprocess.run([sta,'-exit',str(script)],capture_output=True,text=True,check=True)
            slack=worst_slack(proc.stdout+proc.stderr)
            assert abs(slack-timing['slack_ps'])<0.001,(key,slack)
            print(key,slack)
    print('PASS_REPLAY_OF_BLOCKED_CHARACTERIZATION:80replicas; no physical closure')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--sta',default='/usr/bin/sta')
    args=parser.parse_args();replay(args.packet,args.sta)
