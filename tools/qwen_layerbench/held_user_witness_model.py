"""Source-derived finite held-user and all-slice witness MODEL, before RTL choice."""
import argparse,copy,hashlib,json
from collections import defaultdict
from pathlib import Path
class ContractError(ValueError):pass

def groups(events):
    g=defaultdict(list)
    for e in events:
        label=e['label'];family=label.split(':')[0] if ':' in label else label.split()[0]
        g[(family,e['local_pidx'])].append(e)
    out=[]
    for (family,pc),es in g.items():
        slices=[e['target_slice'] for e in es]
        if len(set(slices))!=len(slices):raise ContractError('source group needs repeated-slice ordinal')
        first=min(e['edge_w5'] for e in es)
        ds={e['target_slice']:e['edge_w5']-first for e in es}
        if max(ds.values())>255:raise ContractError('8bit within-family delta does not fit')
        out.append(dict(family=family,local_pidx=pc,required_mask=sum(1<<s for s in slices),
          first_w5=first,last_w5=max(e['edge_w5'] for e in es),delta_by_slice=ds,
          source_indices=[e['source_index'] for e in es]))
    return out

class HeldUser:
    def __init__(self):self.user=None;self.me_live=False;self.xpf_live=False
    def start(self,user,*,authenticated,profile,base,epoch):
        if self.me_live or self.xpf_live:raise ContractError('replacement during live ME/XPF span')
        if not authenticated or profile!='canonical-fused25-cap1-model' or base!=0 or user not in range(4) or not 0<=epoch<65536:
            raise ContractError('unauthenticated/profile/base/user/epoch')
        self.user=user;self.me_live=self.xpf_live=True
    def address(self,canonical,expected):
        if not self.me_live or canonical!=expected or canonical not in (4096,16384,32768):
            raise ContractError('unqualified canonical ME base or lifetime')
        if canonical & (3<<16):raise ContractError('canonical user bits occupied')
        return canonical|(self.user<<16)
    def retire(self,which,*,all_native_reads_complete,all_slice_witnesses_complete):
        if not all_native_reads_complete or not all_slice_witnesses_complete:raise ContractError('early retirement')
        if which=='me':self.me_live=False
        elif which=='xpf':self.xpf_live=False
        else:raise ContractError('retirement class')

class AllWitnesses:
    def __init__(self,events,user,stage,generation):
        self.expected={(e['edge_w5'],e['target_slice'],e['local_pidx']+128*user) for e in events}
        self.seen=set();self.user=user;self.stage=stage;self.generation=generation
    def observe(self,event):
        edge,sl,pc,user,stage,gen=event
        key=(edge,sl,pc)
        if (user,stage,gen)!=(self.user,self.stage,self.generation) or key not in self.expected or key in self.seen:
            raise ContractError('wrong/late/duplicate/user/stage/generation producer witness')
        self.seen.add(key)
    def finish(self):
        if self.seen!=self.expected:raise ContractError('missing slice witness')

def must_reject(name,fn):
    try:fn()
    except ContractError:return dict(name=name,rejected=True)
    raise AssertionError('mutant accepted: '+name)

def build(source,certificate):
    events=source['actual_SU_issue_events'];gs=groups(events)
    accepted=0
    for stage in range(1,37):
      for user in range(4):
        c=AllWitnesses(events,user,stage,7)
        for e in events:
            c.observe((e['edge_w5'],e['target_slice'],e['local_pidx']+128*user,user,stage,7));accepted+=1
        c.finish()
    mutants=[];e=events[0];good=(e['edge_w5'],e['target_slice'],e['local_pidx']+128,1,1,7)
    for name,index,val in [('late',0,good[0]+1),('wrong_slice',1,12),('wrong_pc',2,511),('wrong_user',3,2),('wrong_stage',4,2),('stale_generation',5,6)]:
        bad=list(good);bad[index]=val
        mutants.append(must_reject(name,lambda b=bad:AllWitnesses(events,1,1,7).observe(b)))
    def duplicate():
        c=AllWitnesses(events,1,1,7);c.observe(good);c.observe(good)
    mutants.append(must_reject('duplicate',duplicate))
    mutants.append(must_reject('missing',lambda:AllWitnesses(events,1,1,7).finish()))
    held_checks=0
    bases={'qkv':4096,'o':16384,'gu':4096,'down':32768}
    for user in range(4):
        h=HeldUser();h.start(user,authenticated=True,profile='canonical-fused25-cap1-model',base=0,epoch=7)
        for x in certificate['templates'][user]['xpf_records']:
            base=bases[x['epoch']];expect=(int(x['xpf72'],16)>>1)&((1<<24)-1)
            assert h.address(base,base)==expect;held_checks+=1
        # A live host identity change does not alter either held source identity.
        for live_host in range(4):assert h.address(4096,4096)==4096+(user<<16);held_checks+=1
        h.retire('me',all_native_reads_complete=True,all_slice_witnesses_complete=True)
        h.retire('xpf',all_native_reads_complete=True,all_slice_witnesses_complete=True)
    def start_bad(**changes):
        args=dict(user=1,authenticated=True,profile='canonical-fused25-cap1-model',base=0,epoch=7);args.update(changes);HeldUser().start(**args)
    for name,change in [('unauthenticated',dict(authenticated=False)),('wrong_profile',dict(profile='cap0')),('wrong_programme_base',dict(base=25)),('user_overflow',dict(user=4)),('epoch_overflow',dict(epoch=65536))]:
        mutants.append(must_reject(name,lambda c=change:start_bad(**c)))
    def replacement():
        h=HeldUser();h.start(1,authenticated=True,profile='canonical-fused25-cap1-model',base=0,epoch=7);h.start(2,authenticated=True,profile='canonical-fused25-cap1-model',base=0,epoch=7)
    mutants.append(must_reject('replace_before_ME_XPF_retirement',replacement))
    def early():
        h=HeldUser();h.start(1,authenticated=True,profile='canonical-fused25-cap1-model',base=0,epoch=7);h.retire('me',all_native_reads_complete=False,all_slice_witnesses_complete=True)
    mutants.append(must_reject('retire_before_final_native_read',early))
    def noncanonical():
        h=HeldUser();h.start(1,authenticated=True,profile='canonical-fused25-cap1-model',base=0,epoch=7);h.address(4097,4096)
    mutants.append(must_reject('noncanonical_base',noncanonical))
    return dict(schema='opentallas.qwen.held-user-all-witness-model.v1',production_bound=False,RTL_implemented=False,
      source_SU_events=len(events),source_groups=gs,diagnostic_replays=144,accepted_typed_witnesses=accepted,
      held_user_address_checks=held_checks,mutants=mutants,
      source_axis='actual lowerer W5 pin edges only, repeated as diagnostic per-user/stage cases; no production launch times',
      held_user=dict(existing_GI_publication='hu updates at s_me/c_seg with st register',
        existing_native_output='u_thru ORs live hu into native_pos[17:16]; not a ME/XPF snapshot',
        current_shared_retirement_guard=False,candidate_snapshot_bits=4,candidate_valid_bits_if_not_reused=2,
        required_guard='no next publication until both ME last read and XPF last use have source-bound static retirement',
        authentication='same immutable programme/profile/epoch/base and complete physical-copy digest before launch',
        current_all_ME_XPF_copy_authentication_bound=False,publication_sample=None,retirement_sample=None),
      options=[dict(id='typed-slice-observation',wire_bits=16,
        layout='valid1,user2,slice4,pidx9; SU unit implicit in dedicated producer port',
        existing_wire_bits=16,ABI_changed=True,source='GI cmd[115:112],cmd_user,c_su,c_pidx',
        checks='all compiled tuples at exact source-relative edge; missing/late/duplicate/wrong user/stage/generation fault',
        source_clock_component_ages=dict(cal_output_publication_to_GI_obs_publication=1,
          GI_obs_to_monitor_publication=1,monitor_publication_to_XPF_sample=1),
        physical_age_bound=False),
        dict(id='fixed-family-completion',validates_all_required_slices=True,
          required_masks={g['family']+'_'+str(g['local_pidx']):g['required_mask'] for g in gs},
          completion='only after every tuple independently validated at its compiled edge',
          last_issue_to_completion_register_edges=1,physical_age_bound=False,
          first_payload_age='separate source calibration per slice; never replace with completion edge',
          producer_gating=False,XPF_current_scalar_issue_contract_changed=True)],
      finite_storage=dict(template_groups=len(gs),bits_per_group=134,
        group_fields='first13,pidx9,required_mask12,delta_by_slice12x8,family4',
        immutable_expected_template_bits=len(gs)*134,
        state_seen_bits_4users=4*len(gs)*12,state_cycle13x4=52,state_stage6x4=24,
        state_generation16x4=64,state_active4=4,state_fault1=1,held_ME_XPF_user_bits=4,held_snapshot_valid_bits=2,
        total_candidate_state_lower_bound_bits=4*len(gs)*12+52+24+64+4+1+4+2,
        excludes_state=['native ROM return/capture and service arbitration','clock-domain landing','producer buffering if required by physical assignment'],
        existing_XPF_four188bit_records=752,
        expected_template_fits_existing_XPF_records=len(gs)*134<=752,
        possible_native_ROMs4096x266=1,physical_template_ROM_bits=4096*266,
        native_ROM_read_port_age_bound=False,existing_calendar_ROM_extra_read_port_available=False,
        expected_template_storage_and_capture_placement='unselected; no indexed flop/ROM/port implementation approved',
        area_timing_admission=False),
      predecessor_binding=dict(XS3_resid1='candidate gu producer; actual source/read landing must join',
        XS3_resid2='candidate next-stage qkv producer; interstage lifetime must join',
        first_qkv='embedding/INIT predecessor still unbound',production_consumer_epoch_times=None))
def main():
    a=argparse.ArgumentParser()
    for key in ('source','certificate','out'):a.add_argument('--'+key,type=Path,required=True)
    v=a.parse_args();out=build(json.loads(v.source.read_bytes()),json.loads(v.certificate.read_bytes()))
    out['sources']={k:dict(path=str(getattr(v,k)),sha256=hashlib.sha256(getattr(v,k).read_bytes()).hexdigest()) for k in ('source','certificate')}
    v.out.write_text(json.dumps(out,indent=2)+'\n')
    print('HELD_USER_ALL_WITNESS_MODEL_PASS',out['accepted_typed_witnesses'],'typed events',len(out['mutants']),'mutants rejected; production false')
if __name__=='__main__':main()
