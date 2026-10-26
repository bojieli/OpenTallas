#!/usr/bin/env python3
"""Expose each exact native compiler calendar job as a minimum control replay.

A multi-job layer stores boots in prog/jobN/host_boot.memh. This adapter consumes
those actual bytes and their decoded PW rows, deriving the CTL checks from each
job's real local template table. It qualifies control only, never layer arithmetic.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'layer_prog')]
import dv_layer_compile as D
from pipeline_boot import native_job
from entry_boot import write_replay_prog


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--tree',type=Path,required=True);a.add_argument('--program',type=Path,required=True)
    a.add_argument('--fixture-meta',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    x=a.parse_args();x.out.mkdir(parents=True,exist_ok=False)
    die=D.Die(x.tree);cal=json.loads((x.program/'prog/calendar.json').read_text())
    manifest=json.loads((x.program/'manifest.json').read_text())
    if die.timing_contract.get('transport_sources') != manifest['timing_contract'].get('transport_sources'):
        raise ValueError('selected transport configuration differs from compiler; set matching OT_S81_SELECTED_DEFINES/SOURCE_ROOT')
    templates=json.loads((x.program/'prog/ctl_templates.json').read_text())['templates']
    tab={t['i']:t for t in templates};report=[]
    for i,row in enumerate(cal['job']):
        native=native_job(x.program,i)
        if native['native_die_sha256']!=die.die_sha:
            raise ValueError('native calendar and replay die differ')
        p=D.Prog(die);indices=row['templates'];p.templates=[int(tab[k]['payload186'],16) for k in indices]
        p.tnames=[tab[k]['name'] for k in indices]
        p.rows=[dict(issue=r['issue'],done=r['done'],eng=r['engine'],arg=r['arg'],what=f"native job{i} row{r['i']}") for r in native['rows']]
        # Decode every non-V command from the same checked native PW bytes.
        # These producer events keep strict checks on configuration and SVC job lanes.
        for r in native['rows']:
            if r['engine'] == D.ENG['GUNIT']:
                ti=r['arg'] & 127; kind=(r['arg'] >> 7) & 1
                value=1 | (0x200 | kind) << 1 | (p.templates[ti] & ((1 << 42)-1)) << 11
                ports=['cw_v','cw_a','cw_d']; width=267; delay=D.SEQ['gunit_to_cw']
            elif r['engine'] == D.ENG['SVC']:
                value=(1 << 32) | r['arg'] << 8 | (i & 1) << 7 | r['i']
                for lane, inst in [('jw_W_l0','u_rsv_05'),('jw_E_l0','u_rsv_11')]:
                    cycle=r['issue']+D.SEQ['svc_to_sj']+die.links[lane]['age_edges']
                    p.events.append(dict(cycle=cycle,inst=inst,port='j',dir='in',kind='SVCJ',
                        tag=f"native job{i} row{r['i']} {lane}",payload=f'{value:x}'))
                continue
            else:
                continue
            cycle=r['issue']+delay
            p.events.append(dict(cycle=cycle,inst='u_seqhost',port=ports[0],ports=ports,
                dir='out',kind='NATIVE_COMMAND',tag=f"native job{i} row{r['i']}",valid_bit=0 if width==267 else 32,
                words=[[cycle,f'{value:x}',f'{(1 << width)-1:x}']]))
        pd=x.out/f'replay_job{i}'
        write_replay_prog(die,p,p.rows,native['words'],pd,
                          dict(input_sources={},fixture_meta_sha256=hashlib.sha256(x.fixture_meta.read_bytes()).hexdigest()))
        report.append(dict(job=i,host_words=len(native['words']),nops=native['nops'],
                           ctl_events=sum(e['kind']=='CTL' for e in p.events),native_boot_sha256=native['host_file_sha256'],
                           layer_issue0=row['layer_issue0'],all_stage_ops_lowered=native['all_stage_ops_lowered'],
                           seal_phase=native['seal_phase'],scope='native job control only; no arithmetic/full layer claim'))
    (x.out/'split_control.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
