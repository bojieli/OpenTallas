"""Literal source identities and port linkage for the native consumer bridge.

This adapter never creates native completion, reverse or cohort-drain events.
The enclosing actual native issuer/output/reverse endpoints own those signals.
No tick/clock/reset ownership is taken from the enclosing simulator.
"""
COHORTS=('stage','payload_request','payload_return','metadata','RF_commonACK',
         'consumer','request_CDC','reverse_CDC')
FIELDS=(('native_tag',64),('native_generation',64),('source_PC',11),('SM',5),
        ('rank',1),('reader_lease',64),('key',20),('stage',1))


def native_tuple(fields):
    if set(fields)!=set(k for k,_ in FIELDS):raise ValueError('exact native source fields required')
    result=0;offset=0
    for name,width in FIELDS:
        value=fields[name]
        if type(value) is not int or not 0<=value<1<<width:raise ValueError('native '+name+' width')
        result|=value<<offset;offset+=width
    layer=fields['key']>>14;rank=(fields['key']>>13)&1
    if layer>=36 or rank!=fields['rank'] or fields['source_PC']!=48*layer+13+16*rank+2*fields['stage']:
        raise ValueError('actual source SCORES/PV binding, not PC40 or a primitive')
    return result


def unpack_native_tuple(value):
    if type(value) is not int or not 0<=value<1<<230:raise ValueError('native tuple width')
    out={};offset=0
    for name,width in FIELDS:
        out[name]=(value>>offset)&((1<<width)-1);offset+=width
    if native_tuple(out)!=value:raise ValueError('native tuple source map')
    return out


def port_linkage():
    return dict(top='ot_gpu_qwen_kv_native_lifecycle',bridge='ot_gpu_qwen_native_consumer_drain',ENABLE_default=0,
        shared_clock='same actual enclosing streaming edge as KV controller; no adapter tick',
        KV_controller_inputs={p:p for p in ('consumer_valid','consumer_identity','consumer_key',
            'consumer_stage','consumer_accepted','consumer_reverse','drain_done_valid',
            'drain_done_identity','drain_done_key','drain_done_allcopies')},
        KV_controller_outputs={p:p for p in ('consumer_ready','drain_valid','drain_identity',
            'drain_key','drain_done_ready')},
        actual_native_inputs=dict(native_issue='literal opPC.issue accepted by actual issuer',
            native_complete='literal opPC.result_visible AFTER all source tiles/loops/rounding and actual output acceptance',
            native_reverse='literal opPC.credit_return after actual capture/consumer reverse'),
        cohorts=list(COHORTS),
        endpoint_contract='cohort_quiesce closes new same-key admissions; each accepted request must return matching held {key20,id64}/empty from actual owned endpoint; hold quiescence until drain_retained falls',
        reset='por_n cold-only/allcopy discard authority; warm rst_n retains debt and latches fault; no software clear/retry',
        RF38_fragment='r5 PC40 NEG/FMAX/FMIN is partial SILU; cannot satisfy any SCORES/PV fulloperator input',
        result_bytes='none; exact arithmetic and payload remain in original native execution',
        actual_enclosing_binding_required=True)
