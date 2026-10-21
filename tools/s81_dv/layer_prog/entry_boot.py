#!/usr/bin/env python3
"""Native entry input jobs through the existing host CSR/walker/CTL APIs.

Requires a source-qualified local target5/HLOAD/GAIN mechanism receipt. Jobs
contain no fabricated KS descriptor: the actual host must supply an incoming
matching descriptor. Global transport/clock adoption stays explicitly held.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools/s81_dv'), str(Path(__file__).parent)]
import dv_layer_compile as D
from entry_inputs import compile_inputs


def compile_jobs(die, entry, mechanism, out):
    if 'retire_not_before' not in D.finish.__code__.co_names:
        raise ValueError('entry jobs require current native compiler static-END fence support')
    if mechanism.get('status') != 'PASS':
        raise ValueError('actual entry mechanism PASS receipt required')
    keys = ('target5_pin_to_store_commit_edges', 'hload_pin_to_last_hw_edges', 'gain_pin_to_last_wl_edges')
    measured = mechanism.get('inputs') or {}
    ages = {}
    for sl in {w['slice'] for w in entry['writes']}:
        port = D.ctl_path(die, sl)['entry_port']
        proof = measured.get(port) or {}
        if proof.get('status') != 'PASS':
            raise ValueError('actual local source input proof missing for '+sl+' '+port)
        if port not in ages:
            ages[port] = {}
            for key in keys:
                value = proof.get(key)
                if type(value) is not int or value < 0:
                    raise ValueError('required measured local source age missing: '+port+' '+key)
                ages[port][key] = value
    expected = mechanism.get('source_sha256')
    if not isinstance(expected, dict) or not expected:
        raise ValueError('mechanism receipt requires exact compiled production source hashes')
    for name, digest in expected.items():
        path = ROOT/name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('entry mechanism source identity differs: '+name)
    # Retain complete source/row identity; pair two leaves per real 128-row job.
    leaves = {}
    for write in entry['writes']:
        leaves.setdefault((write['slice'], write['leaf']), []).append(write)
    groups = list(leaves.items())
    jobs = []
    out.mkdir(parents=True, exist_ok=False)
    for index in range(0, len(groups), 2):
        selected = groups[index:index+2]
        prog = D.Prog(die)
        records = []
        edge = 20
        for (sl, leaf), writes in selected:
            cp = D.ctl_path(die, sl)
            raw_pin_age = cp['edges']-D.RSTOP_HOP
            local = ages[cp['entry_port']]
            for write in writes:
                ti = prog.template('entry.'+write['region']+'.'+str(write['sid'])+'.'+str(leaf)+'.'+str(write['row']),
                                   int(write['ctl_payload186'], 16))
                engine = D.ENG['VN'] if sl.endswith('N') else D.ENG['VS']
                prog.vrow(engine, edge, ti, what='entry XRtarget5 '+sl+' leaf'+str(leaf)+' row'+str(write['row']))
                records.append(dict(kind='target5', slice=sl, leaf=leaf, row=write['row'], issue=edge,
                                    model_store_commit=edge+raw_pin_age+local[keys[0]]))
                edge += 2  # match the qualified two-edge target5 source cadence
        # A common conservative source-pin gap covers every preceding write;
        # it never changes the hardware V ACK or waits on a completion signal.
        edge += max(ages[D.ctl_path(die,sl)['entry_port']][keys[0]] for (sl,_),_ in selected)+1
        hload = []
        for (sl, leaf), _ in selected:
            sid = die.slices()[sl]['sid'];engine=D.ENG['VN'] if sl.endswith('N') else D.ENG['VS']
            ti=prog.template('entry.HLOAD.'+sl+'.'+str(leaf), D.ctl_payload(1<<sid,0,1<<leaf,D.vp_cmd(D.VP['HLOAD'],a0=0)))
            prog.vrow(engine,edge,ti,what='entry actual VP HLOAD '+sl+' leaf'+str(leaf))
            hload.append(edge+D.ctl_path(die,sl)['edges']-D.RSTOP_HOP+ages[D.ctl_path(die,sl)['entry_port']][keys[1]])
            records.append(dict(kind='HLOAD',slice=sl,leaf=leaf,issue=edge));edge+=1
        edge += max(ages[D.ctl_path(die,sl)['entry_port']][keys[1]] for (sl,_),_ in selected)+1
        gain = []
        for (sl, leaf), _ in selected:
            sid=die.slices()[sl]['sid'];engine=D.ENG['VN'] if sl.endswith('N') else D.ENG['VS']
            ti=prog.template('entry.GAIN.'+sl+'.'+str(leaf),D.ctl_payload(1<<sid,0,1<<leaf,D.vp_cmd(D.VP['GAIN'],a0=64)))
            prog.vrow(engine,edge,ti,what='entry actual VP GAIN '+sl+' leaf'+str(leaf))
            gain.append(edge+D.ctl_path(die,sl)['edges']-D.RSTOP_HOP+ages[D.ctl_path(die,sl)['entry_port']][keys[2]])
            records.append(dict(kind='GAIN',slice=sl,leaf=leaf,issue=edge));edge+=1
        # Exact local mechanism ages plus explicitly conditional die route model.
        # END is a separate fixed timestamp; ACK remains the real issue+5.
        prog.retire_not_before = int(math.ceil(max(hload+gain)+1))
        rows, host, end = D.finish(prog)
        prefix='job'+str(len(jobs))
        (out/(prefix+'.host_boot.memh')).write_text(D.memh(host,515))
        jobs.append(dict(job=len(jobs), native_commands=len(prog.rows), nops=len(rows),
                         end_age=end, retire_not_before=prog.retire_not_before,
                         commands=records, rows=rows, host_words=len(host),
                         host_reload_edges=len(host)*D.HOST_SLOT,
                         host_boot_file=prefix+'.host_boot.memh',
                         launch='ACTUAL_MATCHING_INCOMING_DESCRIPTOR_REQUIRED'))
    manifest=dict(schema='opentallas.s81.entry_native_jobs.v1', status='PARTIAL',
        source_input_provenance=entry['input_sources'], die_sha256=die.die_sha,
        measured_local_ages=ages, mechanism_receipt_sha256=hashlib.sha256(json.dumps(mechanism,sort_keys=True).encode()).hexdigest(),
        jobs=jobs, sealed_programme_held=True, runtime_program_bound=False,
        global_clock_transport_qualified=False, full_stage=False, full_token=False,
        initial_state='single fixture entry; no fabricated KS/user/token/position descriptor',
        obligations=['actual host adopts these jobs and matching incoming descriptor',
                     'bind die route phases/current clocks and whole entry row lifetimes; local proofs use common bench clocks',
                     'actual NORMR/XFIN sixteen-slice NX/XQ schedule after all entry loads'])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree',type=Path,required=True)
    ap.add_argument('--fixtures',type=Path,required=True)
    ap.add_argument('--mechanism-receipt',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();die=D.Die(a.tree)
    data=compile_jobs(die,compile_inputs(die,a.fixtures),json.loads(a.mechanism_receipt.read_text()),a.out)
    print('ENTRY_NATIVE_JOBS',len(data['jobs']),'PARTIAL: real host/global route adoption held')


if __name__=='__main__':
    main()
