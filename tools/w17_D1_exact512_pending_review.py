"""Review a final-point snapshot; no descriptor history inferred from final state."""
import hashlib,re
from tools.w17_D1_reset_qualified_runtime_verify import verify_priming

def review(text, receipt, plan):
    if receipt.get('GDB_exit') != 0 or not receipt.get('input_postchecks') or not all(receipt['input_postchecks'].values()):
        raise ValueError('execution/input failure')
    if receipt['actual_argv'] != plan['actual_argv'] or receipt['cwd'] != plan['cwd'] or not receipt['default_prog_still_absent']:
        raise ValueError('different program/working directory')
    if receipt['log_SHA256'] != hashlib.sha256(text.encode()).hexdigest():
        raise ValueError('raw hash mismatch')
    if re.findall(r'^D1_INFERIOR_EXIT code=(\d+)$',text,re.M) != ['0']:
        raise ValueError('inferior failed')
    if any(s in text for s in ['D1_SOURCE_OR_LEDGER_FAULT','D1_SOURCE_ADMISSION_MISMATCH','%Error']):
        raise ValueError('fault takes priority')
    expected = plan['expected_stop']
    if re.findall(r'^D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=(\d+)$',text,re.M) != [str(expected['cycles'])]:
        raise ValueError('not original prefix stop')
    if re.findall(r'^D1_TERMINAL_PREFIX_ONLY evals=(\d+) time_ps=(\d+) cycles=(\d+)$',text,re.M) != [tuple(str(expected[k]) for k in ['evals','time_ps','cycles'])]:
        raise ValueError('terminal eval/time/cycle mismatch')
    if text.count('D1_TERMINAL_OWNER_CAPTURE_BEGIN') != 1 or text.count('D1_TERMINAL_OWNER_CAPTURE_END') != 1:
        raise ValueError('missing/extra capture')
    section=text.split('D1_TERMINAL_OWNER_CAPTURE_BEGIN\n')[1].split('D1_TERMINAL_OWNER_CAPTURE_END')[0]
    fields=re.findall(r'^D1_OWNER_(\d{3}) value=(\d+)$',section,re.M)
    if len(section.strip().splitlines())!=79 or [int(i) for i,v in fields]!=list(range(79)):
        raise ValueError('capture shape/type/order')
    values={}
    for (name,meta),(_,v) in zip(plan['fields'].items(),fields):
        value=int(v)
        if value >= 2**(8*meta['bytes']):raise ValueError('capture width')
        values[name]=value
    prime=verify_priming(text)
    P='tb_D1_scope_core__DOT__';D=P+'probe__DOT__dut__DOT__';C=D+'u_tile__DOT__u_core__DOT__'
    Q=P+'probe__DOT__g_D1_current__DOT__';W=D+'g_packed_kv__DOT__g_window_hbm_attention__DOT__u_source__DOT__';L=D+'g_packed_kv__DOT__u_desc_life__DOT__'
    for name in [D+'fault_r',D+'att_packed_desc_fault',D+'win_service_fault',C+'e_fault',Q+'violations']:
        if values[name]:raise ValueError('captured sticky fault')
    if values[P+'diag_cycle'] != 512 or values[P+'rst_n'] != 1 or values[D+'rst_s'] != 3:
        raise ValueError('final reset/clock count mismatch')
    for name,meta in plan['fields'].items():
        if 'control_mask_word' in meta:
            want=0 if 'stage_valid' in name else 0xffffffff
            if values[name] != want:raise ValueError('final priming/staging mask mismatch')
    controls={k:values[C+k] for k in ['pc','st','d_unit','d_skip','me_cls','idles','waited','q_gate','me_ready','me_go','win_admit']}
    provider={k:values[D+k] for k in ['kv_ok','kvd_v','coll_busy','att_packed_desc_gen','att_packed_desc_rows','att_packed_issue','win_service_staged','win_service_v']}
    state={name:values[name] for name in values if name.startswith((W,L))}
    ledger={k:values[Q+k] for k in ['reads','returns','writes','acks','pending']}
    outputs={k:values[P+k] for k in ['sc_v','sc_row','sc_m','pv_v','pv_c']}
    markers={k:len(re.findall('^'+k+r'\b',text,re.M)) for k in ['D1_REAL_DESCRIPTOR','D1_REAL_ACCEPT','D1_REAL_RESPONSE']}
    return dict(status='ACTUAL_EXACT512_PENDING_SNAPSHOT_NOT_COMPLETION',priming=prime,core=controls,
        provider=provider,owner_state=state,ledger=ledger,outputs=outputs,marker_counts=markers,owner_values=values,
        program_binding='Original parent no-DIR/default prog.hex absent; source loader bypassed file read. Program contents not dumped.',
        first_return_bound='BOUND_MISSING',first_return_deadline=None,
        first_return_reason='Need accepted descriptor and qualified request before any source-composed reply bound. Final state is not transaction history.',
        fulltoken=False,RTL_fidelity='UNPROVEN_HAND_PAIRED_NATIVE_FIXTURE',original_PC24_cause='UNOBSERVED',
        I66_origin=None,cap_extended=False,new_frontend=False,new_compile=False)
