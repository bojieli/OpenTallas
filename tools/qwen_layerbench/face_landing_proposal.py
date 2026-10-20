#!/usr/bin/env python3
"""Private opt-in proposal ledger, never an executable deployment programme."""
import argparse,hashlib,json
from pathlib import Path

def load(p):return json.loads(Path(p).read_text())
def compile_proposal(stages_path, model_path, ownership_path):
    d=load(stages_path);m=load(model_path);o=load(ownership_path)
    if d['design']!='qwen_compute' or d['role']!='die_plan' or d['coverage']!='complete':raise ValueError('complete actual compute die-plan required')
    cohort=m['coherent_cohort'];rows=[]
    ownership={(r['src_port'],r['dst_port']):r for r in o['rows'] if r['corner']=='tt'}
    for (sp,rp),own in ownership.items():
        hit=[b for b in d['buses'] if b['src']['inst']=='dvs_E1' and b['src']['port']==sp and b['dst']['inst']=='dvs_E2' and b['dst']['port']==rp]
        if len(hit)!=1:raise ValueError('missing or ambiguous actual bus '+sp+'->'+rp)
        b=hit[0]
        if b['width']!=own['bits']:raise ValueError('actual width mismatch '+sp)
        old=b.get('age_edges')
        if not isinstance(old,int):raise ValueError('actual edge age missing '+sp)
        rows.append(dict(actual_id=b['id'],src=b['src'],dst=b['dst'],bits=b['width'],old_age_edges=old,
          added_receiver_edges=5,proposed_age_edges=old+5,source_clock_candidate=own['source_candidate_tx'],
          receiver_clock_candidate=own['source_candidate_rx'],clock_ownership_bound=own['consumed_owner_qualified']))
    if len(rows)!=10 or sum(r['bits'] for r in rows)!=2743:raise ValueError('incomplete actual cohort')
    ages={r['proposed_age_edges'] for r in rows}
    if len(ages)!=1:raise ValueError('torn proposed input cohort; source ages must be reconciled explicitly')
    return dict(schema='opentallas.qwen.face_landing_schedule_proposal.v1',role='proposal_only',
      inputs={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [stages_path,model_path,ownership_path]},
      source_plan=d['plan'],physical_qualification_eligible=False,deployment_programme_emitted=False,
      actual_source_ownership_bound=False,rows=rows,
      producer_interface=dict(required_event_fields=['source_programme_sha256','event_id','user','stage','cohort_id','producer_issue_edge','receiver_consume_edge','source_leaf_clock','receiver_leaf_clock','reset_G','reset_R0'],
       contract='For every real issued tuple, all ten receiver_consume_edges must equal producer_issue_edge+proposed_age_edges. Recompute dependent ME/XPF/status retire and reset windows from these actual events.',
       unresolved='No actual production event stream supplied; do not use sys_face bench_program filler'),
      reviewed_scopes=['lanes/QW-CCTL-MU-CODEX.md: queued preparation, no implementation',
       'lanes/QW-F16PROG4.md: witness/CALR loader and face source; GEN and regional-parent binding open',
       'lanes/QW-PROGSTORE.md: immutable store/window component; fullbody+BOOT/INIT producer explicitly open'],
      blockers=['native per-port clock ownership and measured phases unbound','actual deployment ME/XPF/DV producer events not supplied','dependent consumer/lifetime calendars not compiled','parent physical face placement and mapped census absent'])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stages',required=True);ap.add_argument('--model',required=True);ap.add_argument('--ownership',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 r=compile_proposal(a.stages,a.model,a.ownership);Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print('FACE_PROPOSAL_ONLY 10 ports 2743 bits ages +5; deployment/physical eligibility FALSE')
if __name__=='__main__':main()
