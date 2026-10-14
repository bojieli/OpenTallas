#!/usr/bin/env python3
"""Compare a bound literal FrontC manifest to existing die geometry, without grants."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from report import area

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_child(candidate, bound, actual, overlaps):
    expected=bound['view']['hashes']['lef']
    if sha(actual)!=expected:
        raise ValueError('bound LEF hash mismatch: '+bound['instance'])
    if [candidate['w_um'],candidate['h_um']] != [bound['view']['w_um'],bound['view']['h_um']]:
        raise ValueError('actual outline mismatch: '+bound['instance'])
    return {'instance':bound['instance'],'logical_instance':candidate['logical_instance'],
            'master':bound['master'],'xy_um':candidate['xy_um'],'orientation':candidate['orientation'],
            'outline_um':[candidate['w_um'],candidate['h_um']],
            'actual_LEF_sha256':expected,'candidate_recorded_LEF_sha256':candidate['view_sha256'],
            'candidate_recorded_hash_matches_actual':candidate['view_sha256']==expected,
            'clock_port':bound['clock_port'],'reset_port':bound['reset_port'],
            'actual_clock_source_driver':None,'actual_reset_source_driver':None,
            'overlapping_other_children':overlaps,'assigned':False}

def build(repo, revision, producer, manifest):
    raw=manifest.read_bytes();m=json.loads(raw)
    def blob(path,rev=revision):
        return subprocess.check_output(['git','show',rev+':'+path],cwd=repo)
    if sha(blob(m['source_file'],m['source_commit']))!=m['source_sha256']:
        raise ValueError('committed parent source hash mismatch')
    path='results/arch/hbm_native_1013/die_v13/candidate.json';cr=blob(path);d=json.loads(cr)
    rows=[]
    for child in m['children']:
        logical='hb_sm_SW_0/g_fd.u_fc.'+child['instance']
        matches=[c for c in d['children'] if c.get('logical_instance')==logical]
        if len(matches)!=1:raise ValueError('exact child association missing/ambiguous: '+logical)
        c=matches[0];actual=(producer/child['view']['bound_view_dir']/(child['master']+'.lef')).read_bytes()
        if blob(c['view_lef'])!=actual:raise ValueError('candidate and bound LEF bytes differ: '+logical)
        x,y=c['xy_um'];box=[x,y,x+c['w_um'],y+c['h_um']]
        overlaps=[]
        for peer in d['children']:
            if peer['instance']==c['instance']:continue
            px,py=peer['xy_um'];a=area(box,[px,py,px+peer['w_um'],py+peer['h_um']])
            if a>1e-6:overlaps.append({'instance':peer['instance'],'area_um2':a})
        row=check_child(c,child,actual,overlaps)
        ir=(producer/child['view']['bound_view_dir']/'insertion.json').read_bytes()
        if sha(ir)!=child['view']['hashes']['insertion.json']:raise ValueError('insertion hash mismatch: '+logical)
        ins=json.loads(ir)
        row['bound_insertion_sha256']=sha(ir)
        row['insertion_reported_clock_label']=ins.get('clock')
        row['raw_corner_clock_measurements']={corner:{'boundary':ins[corner]['boundary'],'all':ins[corner]['all'],'errors':ins[corner].get('errors',[])} for corner in ('tt','ff','ss')}
        row['measured_parent_entry_wire_ps']=None
        row['fixed_TT_source_phase_ps']=None
        row['reference_context_revalidation_required']=True
        rows.append(row)
    return {'schema':'opentallas.frontc_geometry_binding_audit.v1','candidate_revision':revision,
            'candidate_sha256':sha(cr),'manifest_sha256':sha(raw),'parent_source_commit':m['source_commit'],
            'parent_source_sha256':m['source_sha256'],'children':rows,'exact_bound_LEF_count':len(rows),
            'stale_candidate_hash_count':sum(not r['candidate_recorded_hash_matches_actual'] for r in rows),
            'geometry_overlap_count':sum(len(r['overlapping_other_children']) for r in rows),
            'qualified':False,'source_clock_reset_assignment':None,
            'required_next_actions':['refresh stale candidate metadata against exact bound bytes',
                'SM geometry owner confirms current compaction adoption or replacement',
                'bind actual nine source clock/reset producers, routed entries and corner timing',
                'prove native seams and full parent before physical adoption']}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--repo',type=Path,required=True);a.add_argument('--revision',required=True);a.add_argument('--producer',type=Path,required=True);a.add_argument('--manifest',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    p=a.parse_args();p.output.write_text(json.dumps(build(p.repo,p.revision,p.producer,p.manifest),indent=2)+'\n')
