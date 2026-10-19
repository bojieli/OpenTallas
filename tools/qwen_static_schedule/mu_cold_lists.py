"""Legacy32-bit once-only prefix plus recurring WRAP_BASE list encoder.

All times are explicit list-go-domain edges supplied by a launch binding. This
module does not choose a physical FIRST or cancel unknown pin/clock stages.
"""
import hashlib, json
from .mu_cold_prefix import ContractError
CALS=('C_tx','C_rx','K_tx','K_rx')
MIN_DT=4
MAX_DT=(1<<20)-1

def _append(words,dt,flags=0):
    if dt<MIN_DT:raise ContractError(f'list prefetch gap {dt}<4')
    while dt>MAX_DT:
        piece=min(MAX_DT,dt-MIN_DT)
        words.append(piece<<12);dt-=piece
    words.append((dt<<12)|flags)

def encode(*,steady,H,loop_anchor,prefix=(),capacity=4096):
    """Events are (edge,segment,user), steady edges relative to loop anchor.

    The prefix wait NOP establishes exactly the same loop-anchor reference used
    by the final wrap NOP. Halt/reload must rewind0; wrap jumps WRAP_BASE.
    """
    words=[];prev=0
    for t,seg,user in sorted(prefix):
        if not 0<=seg<2 or not 0<=user<4:raise ContractError('legacy list segment/user width')
        _append(words,t-prev,(1<<11)|(seg<<10)|(user<<8));prev=t
    _append(words,loop_anchor-prev)
    wrap_base=len(words);prev=0
    for t,seg,user in sorted(steady):
        if not 0<=seg<2 or not 0<=user<4:raise ContractError('legacy list segment/user width')
        _append(words,t-prev,(1<<11)|(seg<<10)|(user<<8));prev=t
    _append(words,H-prev,1<<7)
    if len(words)>capacity:raise ContractError('expanded cold list exceeds4096-word SRAM/ROM capacity')
    return dict(words=words,wrap_base=wrap_base,period=H,prefix_words=wrap_base,total_words=len(words),AW=12)

def played(table,cycles=2):
    """Independent event-level playback, including literal wrap address."""
    t=0;addr=0;wraps=0;out=[]
    while wraps<cycles:
        w=table['words'][addr];dt=w>>12
        if dt<4 or w&127:raise ContractError('bad legacy list word')
        t+=dt
        if w&(1<<11):out.append((t,(w>>10)&1,(w>>8)&3))
        if w&128:addr=table['wrap_base'];wraps+=1
        else:addr+=1
    return out

def admission_constraint(receipt_path, *, offset, length):
    """Bind only the exact measured admission parameters, not a free guard.

    This component receipt establishes list go acceptance. It does not establish
    the FACE/die launch phase needed to encode a production prefix.
    """
    raw=receipt_path.read_bytes();r=json.loads(raw);p=r['params'];m=r['measured']
    if (offset,length)!=(p['ADM_OFS'],p['ADM_LEN']):
        raise ContractError('admission parameters differ from measured source')
    done=m['adm_done_relative_epoch'];go=m['minimum_go_relative_epoch']
    if done!=m['adm_done_sample']-m['epoch_sample'] or go!=m['legal_go_sample']-m['epoch_sample']:
        raise ContractError('inconsistent admission sample reference')
    if go!=done or m['early_go_sample']!=m['legal_go_sample']-1:
        raise ContractError('receipt does not prove same-edge admission acceptance')
    return dict(schema='opentallas.mu.admission-launch-constraint.v1',
                admission_done_sample=done,earliest_go_sample=go,
                admission_done_to_go_guard=0,minimum_list_delta=p['MIN_DT'],
                first_core_publication_delta=m['go_to_core_publication'],
                first_core_pin_sample_delta=m['go_to_core_pin_sample'],
                source_commit=r['source_commit'],source_sha256=r['source_hashes'],
                receipt_sha256=hashlib.sha256(raw).hexdigest(),production_bound=False,
                scope=r['scope'])

def compile_bound(manifest,admission,binding):
    """Require an explicit source/phase ledger; absence is not a zero age."""
    if not binding or binding.get('schema')!='opentallas.mu.list-launch-binding.v1':
        raise ContractError('explicit source-bound list launch ledger required')
    required=('list_go_reference','raw_L0_minus_steady_anchor','reference_start_minus_core_start','admission_done_sample','earliest_go_sample','source_sha256','qualified')
    if any(k not in binding for k in required):raise ContractError('incomplete list launch ledger')
    go=binding['list_go_reference'];a=manifest['admission']
    if binding['earliest_go_sample']<binding['admission_done_sample']:
        raise ContractError('earliest go predates measured admission completion')
    if go<binding['earliest_go_sample']+binding.get('admission_done_to_go_guard',0):
        raise ContractError('list go precedes admission completion/guard')
    anchor=manifest['plan']['first_L0_external_pin']-binding['raw_L0_minus_steady_anchor']-go
    delays=binding['reference_start_minus_core_start']
    if set(delays)!=set(CALS):raise ContractError('every calendar needs an explicit launch age')
    tables={}
    for c in CALS:
        prefix=[]
        if c in manifest['player_prefix']:
            e=manifest['player_prefix'][c]
            prefix=[(e['start']-delays[c]-go,e['segment'],e['user'])]
        steady=[(e['time']+admission['D0'],e['segment'],e['user']) for e in admission['link_starts'][c]]
        tables[c]=encode(steady=steady,H=admission['H'],loop_anchor=anchor,prefix=prefix)
    return dict(schema='opentallas.mu.cold-list-tables.v1',production_bound=False,
                launch_binding=binding,tables=tables,absolute_FIRST_selected=False)
