#!/usr/bin/env python3
"""Conditional source-order proof using existing later ROM ready fences.

This is NOT a newly selected SU admission guard, current callback calibration,
numeric latency bound, or evidence of wrong data/deadlock in an actual run.
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path
import dsrom_I66_consumer_deadline as D
import dsrom_I66_source_interlock as I

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/uarch/dsrom_I66_existing_ready_fences_20261003'


def layout():
    text=(ROOT/'results/uarch/dsrom_I66_stage_provider_20261002/inputs/isa_full.svh.txt').read_text()
    fields={}
    for name, offset in re.findall(r'^localparam integer O_(\w+) = (\d+);', text, re.M):
        width=re.search(r'^localparam integer W_'+name+r' = (\d+);', text, re.M)
        if width is None:raise ValueError('ISA field width absent')
        fields[name.lower()]=(int(offset),int(width[1]))
    return fields


def encode(fields, instruction):
    word=0
    for name, value in instruction.items():
        if name.startswith('_'):continue
        if name not in fields:raise ValueError('unknown source ISA field')
        off,width=fields[name];I.uint(value,width)
        word|=value<<off
    return word


def descriptors():
    fields=layout()
    demand=json.loads(gzip.decompress((D.OUT/'inputs/demand-r5.json.gz').read_bytes()))
    nodes={n['instruction_index']:n for n in demand['nodes']
           if n.get('kind')=='instruction' and n.get('scope')==0 and 66<=n['instruction_index']<=98}
    words={w['node']:w for w in json.loads((OUT/'inputs/selected_range_QE_words.json').read_text())}
    if set(nodes)!=set(range(66,99)) or len(words)!=17:
        raise ValueError('complete I66..I98 source descriptor range required')
    result=[]
    for pc,n in sorted(nodes.items()):
        raw=encode(fields,n['instruction'])
        if hashlib.sha256(raw.to_bytes(256,'little')).hexdigest()!=n['template_word_sha256']:
            raise ValueError('source template word mismatch')
        intended=raw; evidence='source_template_word'
        if n['instruction']['unit']==3:
            record=words[n['id']];intended=int(record['word_hex'],16)
            I.uint(intended,2048)
            allowed=0
            for f in ['qe_wbase','qe_istride']:
                off,width=fields[f];allowed|=((1<<width)-1)<<off
            if (raw^intended)&~allowed:
                raise ValueError('patched QE descriptor changed control/arithmetic outside address fields')
            evidence='source_address_patched_QE_word; native_execution_qualified=false'
        decoded={name:(intended>>off)&((1<<width)-1) for name,(off,width) in fields.items()}
        if decoded['unit'] not in (2,3,4,6) or decoded['pred']!=0:
            raise ValueError('source range has unexpected branch/predicate')
        if decoded['unit']==3 and decoded['qe_mode']!=0:
            raise ValueError('later QE is not ROM LINQ')
        result.append(dict(pc=pc,node=n['id'],unit=decoded['unit'],wait=decoded['wait'],
                           predicate=decoded['pred'],decoded_fields=decoded,
                           source_instruction=n['instruction'],evidence=evidence,
                           intended_word_hex=f'{intended:0512x}',
                           intended_word_sha256=hashlib.sha256(intended.to_bytes(256,'little')).hexdigest(),
                           template_word_sha256=n['template_word_sha256']))
    calls=json.loads((D.OUT/'inputs/selected_six_calls.json').read_text())['calls']
    mapped={r['node']:r for r in result}
    if any(mapped[c['binding']['node']]['intended_word_hex'] != c['word']['word_hex'] for c in calls):
        raise ValueError('twelve captured source words differ from pinned current calls')
    wanted=json.loads((D.J.P.OUT/'inputs/I66_current_patched_word.json').read_text())
    if mapped['L0.I66']['intended_word_sha256']!=wanted['patched_word_sha256_little_endian']:
        raise ValueError('current patched I66 source word differs')
    return result


def find_fences(desc):
    result=[]
    for obligation in D.source_model()['obligations']:
        producer=int(obligation['producer_node'].split('I')[1])
        target=obligation['first_static_consumer'][0]
        consumer=int(target['consumer_node'].split('I')[1])
        between=[d for d in desc if producer<d['pc']<consumer]
        later=[d['pc'] for d in between if d['unit']==3 and d['decoded_fields']['qe_mode']==0 and d['predicate']==0]
        collective=[d['pc'] for d in between if d['unit']==6 and d['wait']==31]
        if not later:raise ValueError('no existing later ROM-ready fence before consumer')
        result.append(dict(producer_pc=producer,first_consumer_pc=consumer,operand=target['operand'],
                           consumer_wait_mask=target['wait_mask'],first_later_ROM_ready_fence_pc=later[0],
                           all_later_ROM_ready_fences_before_consumer=later,
                           alternate_collective_all_idle_fences=collective))
    return result


def reachable(edges,start,end):
    seen=set();todo=[start]
    while todo:
        here=todo.pop()
        if here==end:return True
        if here in seen:continue
        seen.add(here);todo += [b for a,b in edges if a==here]
    return False


def proof(*, ready_holds_visibility_credit, idle_holds_visibility_credit,
          separate_VM_lease=True):
    for value in [ready_holds_visibility_credit,idle_holds_visibility_credit,separate_VM_lease]:
        if type(value) is not bool:raise ValueError('exact policy boolean required')
    desc=descriptors();chains=find_fences(desc);certificates=[]
    for f in chains:
        p,c,n=f['producer_pc'],f['first_consumer_pc'],f['first_later_ROM_ready_fence_pc']
        visible=f'{p}.all_VM_visible';credits=f'{p}.all_positive_credit_returns';rearm=f'{p}.bank_rearm'
        issue=f'{c}.consumer_issue';read=f'{c}.owned_VM_read';tag=f'{c}.observed_Xtag';release=f'{p}.VM_lease_release'
        # Graph reachability establishes order. Credit/rearm may share an edge;
        # rearm postNBA must strictly precede next core admission preedge.
        # No arbitrary dispatch cycles imply completion.
        edges=[(visible,credits),(credits,rearm),(issue,read),(read,tag),(tag,release)]
        ready=f'{n}.core_ROM_issue';registered=f'{n}.registered_ROM_accept'
        edges += [(ready,registered),(registered,issue)]
        if ready_holds_visibility_credit:edges.append((rearm,ready))
        for pc in f['alternate_collective_all_idle_fences']:
            collective=f'{pc}.collective_issue'
            edges.append((collective,issue))
            if idle_holds_visibility_credit:edges.append((rearm,collective))
        if not separate_VM_lease:edges.append((release,rearm))
        circular=any(reachable(edges,b,a) for a,b in edges)
        relations=[dict(before=a,after=b,edge_relation='<=' if (a,b) in [(credits,rearm),(tag,release)] else '<') for a,b in edges]
        certificates.append(dict(f,ordering_edges=relations,
            visibility_before_read_proved=reachable(edges,visible,read) and not circular,
            captured_credit_before_consumer_proved=reachable(edges,credits,issue) and not circular,
            circular_policy=circular))
    return dict(certificates=certificates,
                all_twelve_visibility_before_read=all(c['visibility_before_read_proved'] for c in certificates),
                all_twelve_bank_credit_before_consumer=all(c['captured_credit_before_consumer_proved'] for c in certificates),
                circular_policy=any(c['circular_policy'] for c in certificates),
                actual_source_guard_implemented=False, numerical_service_upper_bound=None,
                actual_hazard_or_deadlock_observed=False)


def check_previous_owner_release(previous_identity, release):
    """Guard input must be the previous phase, not the next selected stage.

    Proposed source callback schema only. Source-row count/value provenance
    and packet debts must be joined by the preceding lifecycle checker.
    """
    D.operation_id(previous_identity,D.source_model())
    if release['identity']!=previous_identity:
        raise ValueError('guard belongs to a stale/different previous owner')
    D.operation_id(release['identity'],D.source_model())
    for bit in ['all_VM_visible','all_captured_credits','all_packet_ACKs','source_retired']:
        if I.uint(release[bit],1)!=1:raise ValueError('previous phase not fully retired: '+bit)
    if I.uint(release['rearm_postNBA_edge'])>=I.uint(release['later_ROM_core_issue_preedge']):
        raise ValueError('same-edge rearm cannot authorize preedge admission')
    return True


def model():
    I.sources()
    pins=json.loads((OUT/'source_pins.json').read_text())
    for path,sha in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=sha:raise ValueError('source pin changed: '+path)
    core=(D.J.P.OUT/'inputs/core.sv.txt').read_text()
    for needle in ['assign qe_ready = qe_rom ? rom_ready_w : qe_ready_e;',
                   'assign qe_idle = qe_idle_e && ((X_ROM == 0) || rom_idle_w);',
                   'if (waited && (&idles) && !coll_busy)',
                   'S_COLL_WAIT: if (!coll_busy)',
                   'wire qe_rom = (X_ROM != 0) && qe_mode == 2\'d0;']:
        if needle not in core:raise ValueError('source dispatch/collective contract changed')
    direct=proof(ready_holds_visibility_credit=True,idle_holds_visibility_credit=False)
    alternatives=proof(ready_holds_visibility_credit=False,idle_holds_visibility_credit=True)
    desc=descriptors()
    return dict(scope='CONDITIONAL_EXISTING_READY_FENCE_SOURCE_PROOF',source_pins=pins,
        descriptors=desc,source_ready_guard_only=direct,alternate_idle_guard_only=alternatives,
        unit_counts=dict(collections.Counter(str(d['unit']) for d in desc)),
        final_sequence=[dict(pc=d['pc'],unit=d['unit'],wait=d['wait'],qe_mode=d['decoded_fields']['qe_mode']) for d in desc if 92<=d['pc']<=98],
        constructive_result='All twelve first-consumer operands have an intervening later QE ROM-ready admission. A correctly associated previous-phase visibility/credit rearm fence on existing shared ready suffices for ordering without a new SU guard.',
        existing_source_vs_candidate='Original ready=adapterIDLE&&spine_ready does not implement remote visibility/credit qualification. The proof is conditional on that candidate binding, not a claim of implementation.',
        ready_association='Keep previous full169/user32 phase ownership until all owned visibility/positive credits/packet/source retirements; gate shared ready monotonically until registered next acceptance. Do not substitute next stage idle or stale phase credits.',
        required_binding='FULL_SHAPE=1/X_ROM=1/ROM_PHW10, nonskipped enrolled intended words and source-ordered accepted front/registered events; bank release before next ROM admission is separate from VM address/version lease through SU R+2.',
        collective_alternative='wait31 and &idles include QE/ROM; collective arm/wait holds PC until coll_busy retires. It is a publication fence only if ROM idle itself includes candidate owned visibility/credit. Ready-only proof does not require this alternative.',
        no_explicit_WAIT_instruction='No unit0 WAIT/control instruction in I66..I98. S_WAIT is instruction-fetch state, not a producer-completion fence.',
        source_minimum_dispatch_gap_not_deadline=True,
        consumer_read_relation='After actual owned emit E: read E+BCAST+2 linear or +4 gathered; tag R+2. No numeric origin/emit bound inferred.',
        source_predicates='Range source words pred0; core zero-skip predicate excludes QE. Actual d_skip=0/healthy epoch still required in enrollment.',
        full_word_enrollment_missing='17 intended patched QE source words and16 exact source template words are supplied, not actual four-rank compiled program files.',
        bank_VM_lease_join_prerequisite='bfce21b139e3b6b97d53ca7a4de3b6abb09b2d56',
        additional_SU_guard_selected=False, additional_SU_guard_priced=False,
        four_frame_floor=4,actual_peak_with_tags=None,
        finite_successful_provider_bound=None,current_accepted_journal=None,
        c9_phase_reset_positive_credit_CDC_qualified=False,
        status='CONDITIONAL_ORDER_PROVED_RUNTIME_AND_BOUND_MISSING',
        actual_wrong_data_or_deadlock_claim=False,RTL_GO=False,new_job=False,fulltoken=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true')
    a=p.parse_args();text=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.verify:
        if (OUT/'model.json').read_text()!=text:raise SystemExit('model mismatch')
        print('all12 conditional ready-fence chains PASS; actual runtime/service bound unavailable')
    elif a.out:a.out.write_text(text)
    else:print(text,end='')
