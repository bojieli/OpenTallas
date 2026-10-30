import copy,json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');D0=Path('/srv/opentallas-scratch2/claude/codex-ds-native-1029')
sys.path[:0]=[str(R/'code'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.entry_page_protocol import encode,validate_rows,decode_check
from native_boot import compile_boot
import dv_layer_compile as D
read=lambda p:json.loads(p.read_text())
t=read(D0/'timing_current.json');phase=read(D0/'seqhost_current.json')
assert all(t['source_sha256'].get(n)==v for n,v in phase['source_sha256'].items())
t.update(seqhost_input_clock=phase.get('seqhost_input_clock',phase.get('input_clock')),edge_convention=phase['edge_convention'])
out=R/'protocol_pages_L14';out.mkdir();jobs=[]
for path in sorted((R/'load_pages_L14').glob('job*.json')):
 j,words=encode(read(path),t,stage=0,start_phase=0)
 (out/path.name).write_text(json.dumps(j,indent=1)+'\n');(out/(path.stem+'.host_boot.memh')).write_text(D.memh(words,515));jobs.append(j)
checks=[]
def refuse(name,fn):
 try:fn()
 except ValueError:checks.append(name)
 else:raise AssertionError('missed '+name)
page=read(next((R/'load_pages_L14').glob('job*.json')));j,w=encode(page,t,stage=0,start_phase=0)
wrong=copy.deepcopy(j);wrong['rows'][-2]['issue']=0;refuse('KIT_before_store_commit',lambda:validate_rows(wrong))
wrong=copy.deepcopy(j);wrong['rows'][-1]['issue']=wrong['rows'][-2]['issue']+1;wrong['rows'][-1]['row76']=f'{D.pack_row(0,wrong["rows"][-1]["issue"],15,0):019x}';refuse('END_before_KIT_return',lambda:validate_rows(wrong))
wrong=list(w);index=next(i for i,z in enumerate(wrong)if((z>>1)&255)==0x13);wrong[index]^=1<<17;refuse('actual_HOST_payload_mutant',lambda:decode_check(j,wrong))
wrong=list(w);index=next(i for i,z in enumerate(wrong)if((z>>1)&255)==0x10 and(((z>>1)>>32)&(1<<25))and(((z>>1)>>32)>>26)==3);wrong[index]^=1<<40;refuse('SEAL_header_phase_mutant',lambda:decode_check(j,wrong))
refuse('unbooked_launch_default_still_refused',lambda:compile_boot(j['local_mux_config'],t))
refuse('unqualified_header_phase',lambda:encode(page,t,stage=0,start_phase=1))
summary=dict(status='PASS_LOCAL_NATIVE_ENTRY_PROTOCOL_ENCODING',pages=len(jobs),row_count=104,templates=102,HOST_words=sum(j['host_word_count']for j in jobs),local_HOST_reservation_edges=sum(j['local_HOST_reservation_edges']for j in jobs),KIT_issue_range=[min(j['local_KIT_issue']for j in jobs),max(j['local_KIT_issue']for j in jobs)],END_issue_range=[min(j['local_END_issue']for j in jobs),max(j['local_END_issue']for j in jobs)],KIT_return_from_age0_delta=3,selected_header_stage=0,selected_local_header_phase=0,KS_pin_offset_from_reset_mod4=t['seqhost_input_clock']['accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4'],explicit_MU_words_per_page=35,all8events_disabled_replay=True,controls_caught=checks,BEGIN_SEAL_KIT_END_emitted=True,actual_global_HOST_KS_pin_bookings=None,actual_incoming_descriptors=None,actual_local_SEAL_runtime_executed=False,native_job_sealed=False,physical_START_qualified=False,full_token=False)
(R/'entry_protocol_L14.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
