"""Legacy32-bit once-only prefix plus recurring WRAP_BASE list encoder.

All times are explicit list-go-domain edges supplied by a launch binding. This
module does not choose a physical FIRST or cancel unknown pin/clock stages.
"""
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

def compile_bound(manifest,admission,binding):
    """Require an explicit source/phase ledger; absence is not a zero age."""
    if not binding or binding.get('schema')!='opentallas.mu.list-launch-binding.v1':
        raise ContractError('explicit source-bound list launch ledger required')
    required=('list_go_reference','raw_L0_minus_steady_anchor','reference_start_minus_core_start','admission_done_to_go_guard','source_sha256','qualified')
    if any(k not in binding for k in required):raise ContractError('incomplete list launch ledger')
    go=binding['list_go_reference'];a=manifest['admission']
    if go<a['offset']+a['length']+binding['admission_done_to_go_guard']:
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
