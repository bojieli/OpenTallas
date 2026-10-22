#!/usr/bin/env python3
"""Exercise actual compiler A/B images with explicit TEST-only date books.

No native command or runtime descriptor payload is replaced. This checks real
emission and fail-closed gaps while the current stage lowerings remain partial.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import pipeline_boot as P
from ks_descriptor import fixture_word


def run(root):
    root=Path(root)
    calendar=json.loads((root/'calendar.json').read_text())
    meta=json.loads((root/'fixture_meta.json').read_text())
    word=fixture_word(meta,user=0)
    (root/'descriptor.memh').write_text(f'{word:014x}\n')
    windows={x['stage']:x for x in calendar['pipeline_graph']['stages']}
    jobs=[]
    native={}
    for name,stage,first,ks in [('A','R000',10000,10600),('B','R001',30000,38400)]:
        job=P.native_job(root/name);native[name]=job
        H=len(job['words'])
        end_edge=ks+2+4+job['end_issue']
        slots=[dict(head_header_edge=first+16*i-3,head_body_edge=first+16*i+1,
                    receiver_header_edge=first+16*i,receiver_body_capture_edge=first+16*i+4)
               for i in range(H)]
        seq_ks=ks+2; first_command=seq_ks+4+job['first_command_issue']
        jobs.append(dict(stage=stage,user=0,position_index=0,native_programme=name,native_job=0,
            descriptor_file='descriptor.memh',
            context=dict(stage_id=int(stage[1:]),rank=meta['rank'],transaction_id=37,
                user=0,token=meta['token'],position=meta['position'],epoch_identity=0x1021),
            receiver_contract=dict(source_sha256='792f588ad90d481cd70edbc91a0a18b486194d5e4e63e4d08f6d2840bc50d200',
                clock_reset_identity='TEST_COMMON_CLOCK_EXPLICIT_NOT_PRODUCTION',
                host_body_to_seq_capture_edges=4,ks_header_to_seq_capture_edges=2,
                issuer_stage=job['issuer_stage'],host_word_count=417,
                production_lifecycle_bound=False,die_v_sha256=job['native_die_sha256']),
            host_slots=slots,ks_slots=dict(head_edge=ks-3,receiver_edge=ks,deadline=ks,slot=0),
            first_command_edge=first_command,phase_epoch_edge=0,
            issuer_phase_at_epoch=(-seq_ks)%4,issuer_phase_convention='preedge_phase_q',
            graph_epoch_receiver_edge=first_command-windows[stage]['position_windows'][0][0],
            hbc_book=dict(local_epoch_at_config_body_capture=0,boot_header_edge=20,
                boot_commit_edge=30,clock_reset_id64=0x1021,
                prev_return_input_capture=end_edge+1000,local_status_sample=end_edge+4,
                local_return_send=end_edge+6,expected_data_stage=int(stage[1:]),expected_data_rank=meta['rank'])))
    book=dict(tp_ranks=[0,1,2,3],jobs=jobs,scope='TEST_REAL_NATIVE_IMAGES_ONLY')
    (root/'bookings.json').write_text(json.dumps(book,indent=1)+'\n')
    report=P.compile_pipeline(calendar,book,root,root/'emitted')
    assert report['status']=='PARTIAL' and report['emitted']==2
    causes=[x['cause'] for x in report['gaps']]
    assert causes.count('receiver_host_word_count_mismatch')==2
    assert causes.count('full_stage_native_lowerings_incomplete')==2
    assert causes.count('HBC_context_load_commit_lifecycle_not_bound')==2
    assert 'native_commands_or_END_outside_pipeline_window' in causes
    assert native['A']['nops']==8 and len(native['A']['words'])==33
    assert native['B']['nops']==113 and len(native['B']['words'])==515
    caught=[]
    # Actual A image exposes why the old417word fixture's +16KS tail is unsafe:
    # scan is fixed128, even for only8rows. No synthetic programme is introduced.
    short=deepcopy(book);a=short['jobs'][0]
    old=a['ks_slots']['receiver_edge'];new=a['host_slots'][-1]['receiver_body_capture_edge']+16
    a['ks_slots'].update(head_edge=new-3,receiver_edge=new,deadline=new)
    delta=new-old;a['first_command_edge']+=delta;a['graph_epoch_receiver_edge']+=delta
    a['issuer_phase_at_epoch']=(-(new+2))%4
    r=P.compile_pipeline(calendar,short,root,root/'short_scan')
    witness=[g for g in r['gaps'] if g['cause']=='native_seal_scan_not_complete']
    assert witness and witness[0]['earliest_seq_ks']-witness[0]['seq_ks']==22
    caught.append(dict(case='actual_A_old_fixture_KS_gap',gap_edges=22,witness=witness[0]))
    for name,mutate in [
        ('wrong_phase',lambda b:b['jobs'][0].update(issuer_phase_at_epoch=(b['jobs'][0]['issuer_phase_at_epoch']+1)%4)),
        ('wrong_first_command',lambda b:b['jobs'][0].update(first_command_edge=b['jobs'][0]['first_command_edge']+1)),
        ('partial_TP',lambda b:b.update(tp_ranks=[0])),
        ('wrong_issuer_stage',lambda b:b['jobs'][0]['receiver_contract'].update(issuer_stage=(native['A']['issuer_stage']+1)%128)),
        ('duplicate_native_job',lambda b:b['jobs'].append(deepcopy(b['jobs'][0]))),
    ]:
        bad=deepcopy(book);mutate(bad)
        try:P.compile_pipeline(calendar,bad,root,root/name)
        except ValueError as exc:caught.append(dict(case=name,error=str(exc)))
        else:raise AssertionError('missed '+name)
    forged=deepcopy(book)
    forged['jobs'][0]['receiver_contract'].update(host_word_count=33,production_lifecycle_bound=True)
    rr=P.compile_pipeline(calendar,forged,root,root/'forged_capability')
    assert any(g['cause']=='receiver_capability_not_source_bound' for g in rr['gaps'])
    assert sum(g['cause']=='receiver_host_word_count_mismatch' for g in rr['gaps'])==2
    caught.append(dict(case='caller_capability_flags',error='source-bound extension receipt remains required'))
    cap_path=root.parent/'receiver_capability.json'
    if cap_path.exists():
        selected=deepcopy(book)
        for job in selected['jobs']:
            job['receiver_contract'].update(capability_receipt='../receiver_capability.json',
                capability_source_root='../receiver_source', selected_parameters=dict(
                    ENABLE=1,VARIABLE_WORDS=1,ALLOW_RELOAD=1,HOSTB_ENABLE=1,STATIC_KS6=0))
        rr=P.compile_pipeline(calendar,selected,root,root/'selected_receiver')
        assert rr['status']=='PARTIAL'
        assert not any(g['cause'] in ('receiver_host_word_count_mismatch','receiver_capability_not_source_bound')
                       for g in rr['gaps'])
        assert any(g['cause']=='HBC_context_load_commit_lifecycle_not_bound' for g in rr['gaps'])
        caught.append(dict(case='qualified_variable_source',result='33/515 accepted, unbound production remains PARTIAL'))
        fake=root/'altered_capability.json'
        fake.write_text(cap_path.read_text().replace('"die_instance_bound": false','"die_instance_bound": true'))
        bad=deepcopy(selected);bad['jobs'][0]['receiver_contract']['capability_receipt']='altered_capability.json'
        try:P.compile_pipeline(calendar,bad,root,root/'altered_capability')
        except ValueError as exc:caught.append(dict(case='altered_capability_receipt',error=str(exc)))
        else:raise AssertionError('missed altered capability receipt')
        wrong=root/'wrong_receiver';shutil.copytree(root.parent/'receiver_source',wrong)
        f=wrong/'rtl/dsrom_sys/s81_dv/hostb/dsdv_hbc1_loader.sv'
        f.write_text(f.read_text()+'\n// altered source witness\n')
        bad=deepcopy(selected);bad['jobs'][0]['receiver_contract']['capability_source_root']='wrong_receiver'
        try:P.compile_pipeline(calendar,bad,root,root/'altered_receiver_source')
        except ValueError as exc:caught.append(dict(case='altered_receiver_source',error=str(exc)))
        else:raise AssertionError('missed altered receiver source')
    # Corrupt real emitted payload and retain original compiler manifest.
    bad_dir=root/'A_mutated';shutil.copytree(root/'A',bad_dir)
    hp=bad_dir/'prog/host_boot.memh';words=hp.read_text().split();words[3]=f'{int(words[3],16)^2:0129x}'
    hp.write_text('\n'.join(words)+'\n')
    try:P.native_job(bad_dir)
    except ValueError as exc:caught.append(dict(case='mutated_actual_boot',error=str(exc)))
    else:raise AssertionError('missed mutated actual boot')
    result=dict(status='PASS',scope='REAL_NATIVE_PACKET_EMISSION_AND_REFUSAL_NOT_FULL_STAGE_RTL',
        actual_jobs={n:dict(rows=j['nops'],host_words=len(j['words']),END=j['end_issue'],
                           payload_sha256=j['programme_payload_sha256']) for n,j in native.items()},
        emitted_manifest_sha256=P.sha(root/'emitted/manifest.json'),
        fixture_meta_sha256=P.sha(root/'fixture_meta.json'),calendar_sha256=P.sha(root/'calendar.json'),
        producer_sha256=P.sha(P.__file__),caught=caught,production_enabled=False)
    (root/'exercise.json').write_text(json.dumps(result,indent=1)+'\n')
    print('PASS real A/B images emitted;',len(caught),'causal refusals/gaps caught; full-stage/RTL remains open')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();run(a.root)
