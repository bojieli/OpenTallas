#!/usr/bin/env python3
"""Opt-in added-only D2 source preparation; no HDL execution entrypoint."""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_source_bound_image_admission as A
import prepare_dsrom_upstream_pair_cadence as OLD
import analyze_dsrom_cadence_r3_terminal as TRACE

BASE = 'results/rtl/dsrom_cadence_admission_prepare_20261002'
BENCH = 'rtl/test/tb_dsrom_upstream_pair_cadence_admission_prepare.sv'


def admission(profile):
    if profile != 'existing_fast8':
        raise ValueError('STALE_IMAGE_ADMISSION: SMIN5 unsupported for compiled FAST1 CUT379 LAT8')
    binding = A.actual_binding()
    if binding['CUT'] != 379 or binding['actual_add_LAT'] != 8:
        raise ValueError('new CUT/LAT requires fresh reviewed model')
    # The image provider is the SAME existing source implementation used by
    # the passing control, rather than an independently rewritten scheduler.
    files, ph, rom = OLD.images(profile)
    if ph['nbeat'] != 64:
        raise ValueError('STALE_IMAGE_ADMISSION: selected schedule is not 8x8')
    return files, ph, rom, dict(status='SOURCE_BOUND_BEFORE_COMPILE',binding=binding,
        image_provider='tools/v41_die_images_w17w10.py',profile=profile,nbeat=ph['nbeat'],
        stale_profile_refused='production5',geometry= dict(NP=8192,R=128,NBF=1024,selected_pair=1,NSEG=8,NCH=16,NCHB=8,XF=4,NB=2,MTP=2,K=512,rows=257),
        golden_and_ROM='unchanged existing_fast8 source implementation and immutable inputs')


def package(profile='existing_fast8'):
    images, ph, rom, receipt = admission(profile) # Refuse before any output.
    sources = OLD.sources()
    files = {Path(p).name:t for p,t in sources.items()}
    files['tb_dsrom_upstream_pair_cadence.sv'] = (ROOT / BENCH).read_text()
    files.update({profile+'/'+name:text for name,text in images.items()})
    files['dsrom_upstream_pair_ROM.cpp'] = OLD.input_cpp(rom)
    files['source_image_admission.json'] = json.dumps(receipt,indent=2,sort_keys=True)+'\n'
    return files


def expected():
    return OLD.expected()


def completion(text, plan, rc):
    """Keep prior exact control checks AND bind every loader event to source."""
    pattern = r'LOADER cycle=(\d+) valid=(\d+) addr=(\d+) ld_run=(\d+) ld_k=(\d+)'
    entries = []
    filtered = []
    errors = []
    for line in text.splitlines():
        if 'LOADER' in line:
            match = re.fullmatch(pattern,line)
            if match is None:
                errors.append('malformed loader marker')
            else:
                entries.append(tuple(map(int,match.groups())))
        else:
            filtered.append(line)
    spec = importlib.util.spec_from_file_location('pinned_r3',ROOT/'tools/run_dsrom_upstream_pair_cadence_r3.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    result = old.completion('\n'.join(filtered),'existing_fast8',plan,rc)
    edges = [dict((k,int(v)) for k,v in re.findall(r'(\w+)=(\d+)',line))
             for line in filtered if line.startswith('EDGE ')]
    cfg = [e['cycle'] for e in edges if e['cfg']]
    if len(cfg) != 1:
        errors.append('missing/duplicate config start')
    elif entries:
        # Bench snapshots are BEFORE the edge: prior cycle's NBA port values.
        trace = TRACE.loader_trace(cfg[0],max(e['cycle'] for e in edges))
        wanted = [(e['cycle'],trace[e['cycle']-1]['c_v'],trace[e['cycle']-1]['c_a'],
                   trace[e['cycle']-1]['ld_run'],trace[e['cycle']-1]['ld_k']) for e in edges]
        if entries != wanted:
            errors.append('loader source recurrence/count/order mismatch')
    else:
        errors.append('missing loader observations')
    result['errors'].extend(errors)
    result['loader_samples'] = len(entries)
    result['valid_config_writes'] = sum(e[1] for e in entries)
    result['valid'] = result['valid'] and not errors
    return result


def prepare(out, profile='existing_fast8'):
    plan = json.loads((ROOT/BASE/'sourceplan.json').read_text())
    for path,digest in plan['input_source_sha256'].items():
        if A.digest((ROOT/path).read_bytes()) != digest:
            raise ValueError('source changed '+path)
    files = package(profile)
    pins = {name:A.digest(text.encode()) for name,text in files.items()}
    if pins != plan['generated_files_sha256']:
        raise ValueError('package changed')
    out.mkdir(parents=True,exist_ok=False)
    for name,text in files.items():
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    receipt = dict(status='PREPARED_NOT_COMPILED',compile_authorized=False,simulation_authorized=False,
        sourceplan_sha256=A.digest((ROOT/BASE/'sourceplan.json').read_bytes()),files_sha256=pins)
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare-lat8',action='store_true',required=True)
    ap.add_argument('--profile',default='existing_fast8')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    prepare(args.out,args.profile)
