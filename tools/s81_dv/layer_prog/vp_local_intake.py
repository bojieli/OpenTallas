#!/usr/bin/env python3
"""Attach an unchanged, qualified VP local body to exact bound entry transports.

This is source-relative stage composition, not real-clock die readiness.
HLOAD/GAIN last VP output is explicitly separate from the VN's capture/store.
"""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE.parent.parent/'die_plan')]
VP='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv'
MEM='physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v'
PARAMS=dict(ML=7,AL=6,HPL=33,CS_HI_D=0,CS_HI_GS=0,CS_HO_D=0,CS_HO_GS=0,CS_H_G=4,HQX=0)


def attach(transport,inventory,proof,source_root,manifest):
    if transport.get('verdict')!='PASS_BOUND_TRANSPORT':raise ValueError('passing actual entry transport required')
    if transport['die_sha256']!=inventory['source_top_sha256'] or transport['source_asbuilt_sha256']!=inventory['source_asbuilt_sha256']:
        raise ValueError('bound transport/inventory source differs')
    if (proof.get('schema')!='opentallas.s81.vp_local_gate.v1' or proof.get('status')!='PASS'
        or proof.get('parameters')!=PARAMS or proof.get('clock_period_ps')!=833):
        raise ValueError('qualified exact default VP body required')
    checks=proof.get('checks',{});positive=checks.get('positive',{});negative=checks.get('negative_payload',{})
    if not(positive.get('passed') and positive.get('exit_code')==0 and negative.get('passed') and negative.get('exit_code')not in(0,None)):
        raise ValueError('actual positive and caught payload control required')
    root=Path(source_root).resolve();hashes=proof.get('source_sha256',{})
    if not{VP,MEM}<=set(hashes):raise ValueError('VP and real SRAM identities required')
    for name,wanted in hashes.items():
        path=root/name
        if not path.resolve().is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:
            raise ValueError('measured local source changed: '+name)
    from layer_prog.slice_source import manifest_selection
    import bind_elab
    selected=manifest_selection(root,manifest)
    for master,path in [('ot_s81sl_vp',VP),('ot_sram_1r1w_512x128_m4_r0c0',MEM)]:
        picked,ambiguous=bind_elab.pick(selected[2],master,selected[3])
        if ambiguous or not picked or Path(picked).resolve()!=root/path:
            raise ValueError('selected local implementation differs: '+master)
    # The qualified gate has no command-line defines. Reject activated guards
    # in any measured dependency; preserve the reset/clock adoption hold.
    guards=set()
    for name in hashes:guards.update(re.findall(r'^\s*`(?:ifdef|ifndef)\s+(\w+)',(root/name).read_text(),re.M))
    if guards&set(selected[1].get('defines',[])):
        raise ValueError('selected measured dependency conditional changed')
    commits=proof.get('commit_edges',[]);outputs=proof.get('output_edges',{})
    if len(commits)!=49 or any(type(v)is not int or v<0 for v in commits):raise ValueError('actual49row commit proof required')
    if any(type(outputs.get(k))is not int or outputs[k]<0 for k in('HLOAD','GAIN')):
        raise ValueError('actual HLOAD/GAIN last-output ages required')
    rows=transport.get('leaves',[])
    if len(rows)!=80 or len({(r['slice'],r['leaf'])for r in rows})!=80:
        raise ValueError('all80 distinct actual VP destinations required')
    out=copy.deepcopy(transport)
    for row in out['leaves']:
        u=inventory['units'].get(row['vp'],{})
        if row.get('status')!='PASS' or u.get('master')!='ot_s81sl_vp' or u.get('params')!={}:
            raise ValueError('actual VP no longer has the measured unoverridden defaults: '+row['vp'])
        ages=[row['target5_transport_edges'],row['command_transport_edges']]
        if any(type(a)is not int or a<0 for a in ages):raise ValueError('missing actual bound field ages')
        for fields,age in [(('sw_v','sw_a','sw_m','sw_d'),ages[0]),(('c_v','c_d'),ages[1])]:
            if any(row.get('fields',{}).get(f,{}).get('age_edges')!=age for f in fields):
                raise ValueError('reported bound field group ages disagree')
        row.update(local_vp_store_commit_edges=max(commits),local_vp_hload_last_output_edges=outputs['HLOAD'],
            local_vp_gain_last_output_edges=outputs['GAIN'],
            from_xr_target5_output_to_vp_store_commit_edges=ages[0]+max(commits),
            from_xr_command_output_to_vp_hload_last_output_edges=ages[1]+outputs['HLOAD'],
            from_xr_command_output_to_vp_gain_last_output_edges=ages[1]+outputs['GAIN'])
    out['vp_local_intake']=dict(verdict='PASS_UNCHANGED_LOCAL_BODY_INTAKE',instances=80,
        proof_source_asbuilt_sha256=proof['source_asbuilt_sha256'],proof_source_top_sha256=proof['source_top_sha256'],
        current_source_identity_preserved=True,source_sha256=hashes,selected_manifest=str(selected[0].relative_to(root)),
        selected_manifest_sha256=hashlib.sha256(selected[0].read_bytes()).hexdigest(),effective_params=PARAMS,
        same_nominal_clock_period_ps=833,source_event=proof['source_event'],
        scope='existing source-relative VP store commit/last output only; no XR target5 decode, VN store, physical clocks or actual programme start')
    out.update(readiness_qualified=False,native_job_sealed=False,full_token=False)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('transport','inventory','proof','source-root','manifest','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous result; choose fresh output')
    result=attach(json.loads(a.transport.read_text()),json.loads(a.inventory.read_text()),json.loads(a.proof.read_text()),a.source_root,a.manifest)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print('VP_LOCAL_INTAKE PASS',len(result['leaves']),'leaves; physical/VN/START readiness held')
if __name__=='__main__':main()
