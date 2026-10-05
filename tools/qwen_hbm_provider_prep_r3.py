#!/usr/bin/env python3
"""Prepare a pinned actual-source observation experiment; NEVER compile/run RTL.

Observer inserts are reversible textual journal hooks, not controller fixes.
The future bench exercises actual ports and the source's actual state updates.
Logical ACT/PRE/REF reservations are distinguished from emitted commands.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from qwen_hbm_controller_calendar_r2 import (ROOT,REV,SOURCE,BASE,PROGRAM,kv_rows,weight_ranges,bankmap,pinned,source_timing)

R2='71bda6e916d183e0d86e6206b0550edc55285043'
FIXTURE='tools/fixtures/qwen_hbm_provider_r3/tb_actual_controller.sv'
BEGIN='// QHP_BEGIN\n'
END='// QHP_END\n'

def block(text):return BEGIN+text+'\n'+END

def strip_observer(text):
    return re.sub(r'// QHP_BEGIN\n.*?// QHP_END\n','',text,flags=re.S)

def observed_source(raw):
    """Boundaries are exact-source anchors; core bytes are recoverable verbatim."""
    text=raw.decode();hooks=[]
    def before(anchor,extra,name):
        nonlocal text
        if text.count(anchor)!=1:raise ValueError('observer anchor not unique: '+name)
        text=text.replace(anchor,block(extra)+anchor);hooks.append(name)
    def after(anchor,extra,name):
        nonlocal text
        if text.count(anchor)!=1:raise ValueError('observer anchor not unique: '+name)
        text=text.replace(anchor,anchor+block(extra));hooks.append(name)
    before('    localparam integer LPC =',r'''    // Passive journal; no assignments to DUT state or ports.
    integer qhp_fd;
    string qhp_path;
    initial begin
        if (!$value$plusargs("QHP_JOURNAL=%s",qhp_path))
            $fatal(1,"QHP_JOURNAL path required");
        qhp_fd=$fopen(qhp_path,"w");
        if (!qhp_fd) $fatal(1,"cannot open observation journal");
        $fdisplay(qhp_fd,"kind|sim_ps|observe_ps|logical_ps|pc|bank|row|sector|tag|beat|arrival_ps|q_n|r_n");
    end
    function automatic void qhp_log(input string kind,
        input longint observe_ps, logical_ps,
        input integer pc, bank, input longint row,
        input longint sector, tag, beat, arrival_ps);
        $fdisplay(qhp_fd,"%s|%0d|%0d|%0d|%0d|%0d|%0d|%0d|%0d|%0d|%0d|%0d|%0d",
            kind,longint'($realtime*1000.0),observe_ps,logical_ps,
            pc,bank,row,sector,tag,beat,arrival_ps,
            pc>=0 ? q_n[pc] : -1, pc>=0 ? r_n[pc] : -1);
    endfunction
    final $fclose(qhp_fd);''','journal_definition')
    # Every request acceptance and every beat expansion, before scheduler swap.
    after('            if (req_v && req_rdy) begin\n',
          '                qhp_log(req_we ? "ACCEPT_WR" : "ACCEPT_RD",now,now,-1,-1,-1,req_addr,req_tag,req_len,now);','accept')
    after('                    q_n[p] = q_n[p] + 1;\n',
          '                    qhp_log(q_we[p][slot] ? "ENQUEUE_WR" : "ENQUEUE_RD",now,now,p,bank_of(q_addr[p][slot]),row_of(q_addr[p][slot]),q_addr[p][slot],q_tag[p][slot],q_beat[p][slot],q_arr[p][slot]);','beat_enqueue')
    before('                            h_tcol[p] = schedule(',
          '                            qhp_log("SCHEDULE",now,now,p,bank_of(q_addr[p][q_rp[p]]),row_of(q_addr[p][q_rp[p]]),q_addr[p][q_rp[p]],q_tag[p][q_rp[p]],q_beat[p][q_rp[p]],q_arr[p][q_rp[p]]);','schedule_entry')
    before('                if (any_open) tr = tr + RP_PS;\n',
          '                if (any_open) qhp_log("PREALL_RESERVATION",tnow,tr,p,-1,-1,s,q_tag[p][q_rp[p]],q_beat[p][q_rp[p]],arr);','refresh_PREall')
    after('                st_ref[p] = st_ref[p] + 1;\n',
          '                qhp_log("REF_RESERVATION",tnow,tr,p,-1,-1,s,q_tag[p][q_rp[p]],q_beat[p][q_rp[p]],arr);','refresh_reservation')
    after('                    tact = max2(tmin, b_preok[p][bk]) + RP_PS;      // PRE, then ACT\n',
          '                    qhp_log("PRE_RESERVATION",tnow,tact-RP_PS,p,bk,row,s,q_tag[p][q_rp[p]],q_beat[p][q_rp[p]],arr);','PRE_reservation')
    after('                st_act[p] = st_act[p] + 1;\n',
          '                qhp_log("ACT_RESERVATION",tnow,tact,p,bk,row,s,q_tag[p][q_rp[p]],q_beat[p][q_rp[p]],arr);','ACT_reservation')
    before('            schedule = tcol;\n',
          '            qhp_log(we ? "WR_COLUMN_RESERVATION" : "RD_COLUMN_RESERVATION",tnow,tcol,p,bk,row,s,q_tag[p][q_rp[p]],q_beat[p][q_rp[p]],arr);','column_reservation')
    before('                                mem[q_addr[p][slot] % MEM_WORDS] = q_data[p][slot];\n',
          '                                qhp_log("WR_POP",now,h_tcol[p],p,bank_of(q_addr[p][slot]),row_of(q_addr[p][slot]),q_addr[p][slot],q_tag[p][slot],q_beat[p][slot],q_arr[p][slot]);','WR_pop')
    after('                                mem[q_addr[p][slot] % MEM_WORDS] = q_data[p][slot];\n',
          '                                qhp_log("BACKING_STORE",now,now,p,bank_of(q_addr[p][slot]),row_of(q_addr[p][slot]),q_addr[p][slot],q_tag[p][slot],q_beat[p][slot],q_arr[p][slot]);','backing_store')
    after('                                r_n[p] = r_n[p] + 1;\n',
          '                                qhp_log("RETURN_ENQUEUE",now,r_t[p][k],p,bank_of(q_addr[p][slot]),row_of(q_addr[p][slot]),q_addr[p][slot],q_tag[p][slot],q_beat[p][slot],q_arr[p][slot]);','return_enqueue')
    before('                    r_rp[p] = (r_rp[p] + 1) % RQD; r_n[p] = r_n[p] - 1;\n',
          '                    qhp_log("READ_TAKE",now,r_t[p][r_rp[p]],p,-1,-1,-1,r_tag[p][r_rp[p]],r_beat[p][r_rp[p]],-1);','read_handshake')
    after('                                e = q_rp[p];\n',
          '                                qhp_log("REORDER",now,now,p,bank_of(t_addr),row_of(t_addr),t_addr,t_tag,t_beat,t_arr);','reorder_identity')
    assert strip_observer(text).encode()==raw
    return text,hooks


def read_journal(path):
    lines=Path(path).read_text().splitlines()
    names=lines[0].split('|')
    expected=['kind','sim_ps','observe_ps','logical_ps','pc','bank','row','sector','tag','beat','arrival_ps','q_n','r_n']
    if names!=expected:raise ValueError('journal schema')
    rows=[]
    for line in lines[1:]:
        fields=line.split('|')
        if len(fields)!=len(names):raise ValueError('journal field count')
        rows.append(dict(zip(names,[fields[0]]+[int(x) for x in fields[1:]])))
    return rows


def audit_journal(events,timing):
    """Actual source projection: classify reservations; do not invent WRvisible.

    No negative is a DUT result until a pinned compile/run supplies a journal.
    Interface/return inequality checks can pass while command causality fails.
    """
    checks=[];reservations={};enqueued={};pops={};responses=set();accepted={}
    for e in events:
        key=(e['tag'],e['beat'])
        if e['kind'] in ('ACCEPT_RD','ACCEPT_WR'):
            if e['tag'] in accepted or not 1<=e['beat']<=32 or (e['kind']=='ACCEPT_WR' and e['beat']!=1):
                checks.append(dict(verdict='FAIL',rule='accept_identity_length',key=key))
            accepted[e['tag']]=e
        if e['kind'] in ('ENQUEUE','ENQUEUE_RD','ENQUEUE_WR'):
            if e['kind']!='ENQUEUE':
                origin=accepted.get(e['tag'])
                if origin is None or not 0<=e['beat']<origin['beat'] or e['sector']!=origin['sector']+e['beat'] or e['arrival_ps']!=origin['observe_ps'] or e['kind'].replace('ENQUEUE','ACCEPT')!=origin['kind']:
                    checks.append(dict(verdict='FAIL',rule='accept_to_beat_identity',key=key))
            if key in enqueued:checks.append(dict(verdict='FAIL',rule='unique_no_reuse_identity',key=key))
            enqueued[key]=e
        if e['kind'] in ('SCHEDULE','REORDER'):
            origin=enqueued.get(key)
            if origin is None or e['sector']!=origin['sector'] or e['arrival_ps']!=origin['arrival_ps']:
                checks.append(dict(verdict='FAIL',rule='queue_reorder_origin',key=key))
        if e['kind'] in ('ACT_RESERVATION','PRE_RESERVATION','REF_RESERVATION','PREALL_RESERVATION'):
            if e['logical_ps']<e['observe_ps']:
                checks.append(dict(verdict='FAIL_AS_EMITTED_COMMAND',rule='causal_command_time',kind=e['kind'],key=key,logical_ps=e['logical_ps'],observe_ps=e['observe_ps']))
        if e['kind'] in ('RD_COLUMN_RESERVATION','WR_COLUMN_RESERVATION'):
            reservations[key]=e
            if e['logical_ps']<max(e['observe_ps'],e['arrival_ps']+timing['REQ_PS']):
                checks.append(dict(verdict='FAIL',rule='column_request_head_time',key=key))
        if e['kind']=='WR_POP':
            pops[key]=e
            if key not in reservations or e['observe_ps']<reservations[key]['logical_ps']:
                checks.append(dict(verdict='FAIL',rule='pop_before_reserved_column',key=key))
        if e['kind']=='BACKING_STORE':
            if key not in pops:checks.append(dict(verdict='FAIL',rule='backing_without_WR_pop',key=key));continue
            earliest=pops[key]['observe_ps']+timing['CWL_PS']+timing['BURST_PS']
            if e['observe_ps']<earliest:
                checks.append(dict(verdict='FAIL_AS_WR_VISIBLE_PROVIDER',rule='column_to_backing_visibility',key=key,store_ps=e['observe_ps'],earliest_visible_ps=earliest))
        if e['kind']=='RETURN_ENQUEUE':
            if key not in reservations or e['logical_ps'] != reservations[key]['logical_ps']+timing['CL_PS']+timing['BURST_PS']+timing['RSP_PS']:
                checks.append(dict(verdict='FAIL',rule='read_due_equation',key=key))
        if e['kind']=='READ_TAKE':
            if key not in enqueued or key in responses or e['observe_ps']<e['logical_ps']:
                checks.append(dict(verdict='FAIL',rule='read_identity_due',key=key))
            responses.add(key)
    return dict(status='SOURCE_JOURNAL_AUDIT_NOT_HARDWARE_QUALIFICATION',events=len(events),findings=checks,
        WR_visible_hook_present=False,logical_reservations_are_actual_command_outputs=False,hardware_build_ready=False)


def audit_reservation_projection(events,timing):
    """Reuse inequality verifier only; input timestamps must come from SV hooks.

    This is a projection of the behavioral model, not physical commands and
    not the r2 causal fixture. No latency/rate transfers from r2 are allowed.
    """
    from qwen_hbm_controller_calendar_r2 import audit_bank_events
    kinds=dict(ACT_RESERVATION='ACT',PRE_RESERVATION='PRE',
        PREALL_RESERVATION='PREall',REF_RESERVATION='REF',
        RD_COLUMN_RESERVATION='RD',WR_COLUMN_RESERVATION='WR')
    projected=[dict(kind=kinds[e['kind']],ps=e['logical_ps'],pc=e['pc'],
                    bank=e['bank'] if e['bank']>=0 else None,sector=e['sector'])
               for e in events if e['kind'] in kinds]
    result=audit_bank_events(projected,timing)
    result['scope']='actual source logical reservation projection only, no command emitter/PHY closure'
    return result


def stimulus(repo=ROOT):
    graph=json.loads(pinned(repo,BASE,PROGRAM));rows=kv_rows(graph,graph['instructions'][10],1)
    selected=rows[:4]
    weight=next(w for w in weight_ranges(graph) if w['weight']=='L0.o.d0')['ranges'][0]['stacks'][0]
    return dict(writer=10,position=1,read=12,next_matrix=17,WR_rows=selected,
        weight_start_sector=weight['first_local_sector'],weight_LEN32_requests=4,
        weight_policy='Controlled prefetch stimulus from next matrix address range; not recorded concurrent opcode issue',
        payload='Synthetic zero/marker only, never checkpoint bytes',
        blocked_PC_probe=dict(PC=0,reads_same_sector=32,queued_new_bank_sector=1,release_ready_model_cycle=4100,MAX_OUT=34),
        clocks=dict(controller_CLK_PS=1000,scope='source CLK_PS preset, explicitly instantiated; no universal/target clock claim'))


def stimulus_header(s):
    lines=['// Generated address metadata only; four exact L0 position1 K sectors.']
    for i,r in enumerate(s['WR_rows']):lines.append(f"localparam logic [33:0] QHP_KV{i}=34'd{r['sector']};")
    lines.append(f"localparam logic [33:0] QHP_WEIGHT=34'd{s['weight_start_sector']};")
    return '\n'.join(lines)+'\n'


def prepare_sources(destination,repo=ROOT):
    """Source materialization only, for review before GO. No subprocess build."""
    destination=Path(destination)
    raw=pinned(repo,REV,SOURCE)
    observed,_=observed_source(raw)
    assert strip_observer(observed).encode()==raw
    destination.mkdir(parents=True,exist_ok=False)
    files={'controller_observed.sv':observed.encode(),
           'tb_actual_controller.sv':(ROOT/FIXTURE).read_bytes(),
           'stimulus_r3.svh':stimulus_header(stimulus(repo)).encode()}
    for name,data in files.items():
        with (destination/name).open('xb') as f:f.write(data)
    return {name:hashlib.sha256(data).hexdigest() for name,data in files.items()}


def plan(repo=ROOT):
    raw=pinned(repo,REV,SOURCE);observed,hooks=observed_source(raw);s=stimulus(repo)
    pins={}
    for rev,path in [(REV,SOURCE),(BASE,PROGRAM),(R2,'tools/qwen_hbm_controller_calendar_r2.py'),
        ('bb51403bff27fc648be92a8b183199f7f8f2ba5e','rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv'),
        (BASE,'rtl/test/tb_hdc_qwen_hbm_mixed_service.sv')]:
        b=pinned(repo,rev,path);pins[path]=dict(commit=subprocess.check_output(['git','rev-parse',rev],cwd=repo,text=True).strip(),sha256=hashlib.sha256(b).hexdigest())
    t=source_timing(repo)
    # Direct source equation, no r2 causal fixture imported as source behavior.
    delayed=dict(arrival_ps=34000,schedule_call_ps=4100000,REQ_ps=t['REQ_PS'],
        inactive_bank_ACT_logical_ps=34000+t['REQ_PS'],previous_column_ps=100000,
        next_ref_ps=3900000,source_refresh_loop_runs=3900000<=max(34000+t['REQ_PS'],100000))
    return dict(schema='Qwen_actual_source_finite_provider_preparation_r3',source_pins=pins,
        status='PREPARED_NOT_COMPILED_PARENT_GO_REQUIRED',source_classification='SIMULATION_ARCHITECTURAL_CALENDAR_ABSTRACTION',
        classification_evidence=[
            'Header explicitly says simulation only; no ACT/PRE/REF/column command pins or command valid/ready interface.',
            'schedule() writes b_open,b_act,b_actok,last_col and future h_tcol immediately in one host simulation edge.',
            'ACT lookahead is computed retrospectively from arrival+REQ; no independent acceptance-time ACT emitter or command reservation arbiter exists.',
            'REF is demand-driven by max(arr+REQ,last_col), not a current-time autonomous refresh service; no refresh output.',
            'WR writes mem at head pop using modulo MEM_WORDS; no CWL-delayed backing commit or WRdone/WRvisible/epoch output.',
            'Read response is real registered valid/ready with a retained return queue and due timestamp; r_data is captured at RD pop.'
        ],source_equation_counterexample=delayed,
        observer=dict(hooks=hooks,core_byte_restore_sha256=hashlib.sha256(strip_observer(observed).encode()).hexdigest(),
            observed_preview_sha256=hashlib.sha256(observed.encode()).hexdigest(),
            path_policy='Materialize only in a new clean pinned experiment worktree/output directory. Pinned RTL is never edited.',
            passive_only=True,semantic_source_restore_byte_identical=True,
            fields=['kind','sim_ps','observe_ps','logical_ps','pc','bank','row','sector','tag','beat','arrival_ps','q_n','r_n'],
            limits='Function hooks observe calculated reservations, not physical commands. Timestamps retain model-cycle vs simulation-wall distinction. READ_TAKE has no address in source queue; join unique acceptance tag/beat ledger.'),
        source_projection_validation='audit_reservation_projection reuses only the independent timing-inequality checker. All experiment times will be captured from original source hooks; no r2 fixture times/behavior/latency are transferred.',
        existing_service_binding=dict(NC3_CTAGW14_SIDW2_PTAGW16='fits only restricted client tags; not common36 namespace or epoch ABI',
            read_port_mismatch='PC service has one response input; NPC32 source has32 held ports; requires separately finite locked arbiter/landing adapter.',
            WR_completion='PC service expects externally supplied p_wr_done_v/tag pulse without ready. Source has neither. Existing mixed-service test fabricates due=cycle+24+(seq%3); it is not a WR-visible provider.',
            selected_probe='Direct finite TB clients with immutable unique tag/beat ledger; no service-module shim or fabricated WRdone. Four WR slots remain live through termination, explicitly not drain/retirement.'),
        finite_experiment=dict(geometry=dict(NPC=32,AW=34,TAGW=16,LENW=6,BEATW=5,QD=64,RQD=32,MEM_WORDS=4096),stimulus=s,
            cases=[
                dict(name='metadata_ports',case=0,requests=12,read_beats=132,write_requests=4,front_READ_transaction_cap=4,WR_cap=4,scope='Actual-address subset plus controlled LEN32 weight reads; WR producer delay is a TB stimulus, not actual RMW arithmetic.'),
                dict(name='blocked_PC_backdated_ACT_refresh',case=1,requests=34,read_beats=34,front_READ_transaction_cap=34,scope='Source-only QD64/RQD32 pressure isolation; deliberately exceeds common36 four-per-die admission, gives no whole-system capacity credit.'),
                dict(name='fullAW_alias',case=2,requests=4,read_beats=2,write_requests=2,scope='Synthetic distinct fullAW34 addresses0 and2^32 collide modulo4096; expected source identity/storage failure, no encoded payload.')],
            bounds=dict(max_controller_edges=8000,cores=1,compile_memory_budget_GiB=4,simulation_memory='bounded queues +4096x256 backing +64 ledger entries; no checkpoint load'),
            termination='Only after exact accepted/read counts and source queues/held read outputs empty; report SOURCE_TRACE_COMPLETE_NOT_WR_PROVIDER_DONE. WR-visible/consumer/CDC drain remains absent.',
            preparation_files=dict(bench=FIXTURE,stimulus_header='tools/fixtures/qwen_hbm_provider_r3/stimulus_r3.svh',
                generated_observed_source='Passively generated by observed_source(pin4535bytes); must restore exact source SHA before compiling'),
            mutations=[
                'observer journal ACT logical time before observation -> must flag emitted-command causality',
                'journal RD due minus1ps -> must flag exact source tail equation',
                'logical reservation projection RD moved before ACT+tRCD or REF+tRFC -> independent inequality checker must reject',
                'journal READ_TAKE before due -> must flag early response',
                'wrong tag/duplicate tag-beat -> must flag identity/uniqueness',
                'source-observer anchor mismatch or byte restoration mismatch -> refuse preparation',
                'source BACKING_STORE at WR pop -> expected baseline FAIL_AS_WR_VISIBLE_PROVIDER, never mask as PASS'],
            post_GO_commands=[['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_actual_controller','-Mdir','<new-output>/obj','-I<new-output>','<new-output>/controller_observed.sv','<new-output>/tb_actual_controller.sv'],
                ['<new-output>/obj/Vtb_actual_controller','+CASE=0','+QHP_JOURNAL=<new-output>/case0.tsv','+QHP_CLIENT_JOURNAL=<new-output>/case0_client.tsv'],
                ['<new-output>/obj/Vtb_actual_controller','+CASE=1','+QHP_JOURNAL=<new-output>/case1.tsv','+QHP_CLIENT_JOURNAL=<new-output>/case1_client.tsv'],
                ['<new-output>/obj/Vtb_actual_controller','+CASE=2','+QHP_JOURNAL=<new-output>/case2.tsv','+QHP_CLIENT_JOURNAL=<new-output>/case2_client.tsv']],
            journal_audit_command=['python3','tools/qwen_hbm_provider_prep_r3.py','--audit-journal','<new-output>/case1.tsv','--output','<new-output>/case1_audit.json'],
            actual_source_pins_must_be_verified_before_GO=True,
            review_before_GO='Review observer core restoration and bench bounds first. Then create a clean worktree pinned to preparation commit, check measured CPU/memory/disk headroom, and run only listed source-model cases. No engine, checkpoint, or whole-program build.'),
        hook_feasibility=dict(acceptance='direct req_v&&req_rdy port monitor plus per-beat q-array hook',
            column='internal WR/RD pop and h_tcol observation, no public command pin',
            bank='instrument schedule() calculations; no external bank commands exist',
            read_completion='public registered rsp_v&&rsp_rdy; finite tag/beat ledger and immutable-held check',
            WR_visible='absent; BACKING_STORE is earlier source array assignment, not a visibility/ACK contract. A delayed commit plus finite held completion is a future source change, never an observer-generated completion.',
            epochs='absent source fields; external unique-tag ledger is only a no-reuse experiment identity, not epoch proof',
            CDC='existing ot_async_fifo can carry finite ready/valid records, but no actual source WR-visible producer is connected; no CDC provider claim'),
        remaining_source_changes_after_experiment=['actual legal command interface/scheduler policy and timer ports','producer epoch through every accepted beat/reorder/return','precolumn pending-WR reservation and delayed fullAW backing commit','held WR-visible completion plus finite CDC/consumer/drain binding','18..35 hardware scan/shift and finite32PC return arbiter lowering'],
        compile_GO=False,RTL_compiled=False,RTL_executed=False,hardware_build_ready=False,hardware_rate_credit=0,token_cycles=None)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    # Preparation only; intentionally no build/run option.
    p.add_argument('--prepare-dir',type=Path,help='Materialize source-only review bundle in a new directory; never compile')
    p.add_argument('--audit-journal',type=Path,help='Audit supplied journal; provenance/compile receipt must be bound separately')
    a=p.parse_args()
    if a.audit_journal is not None:
        if a.prepare_dir is not None:p.error('audit and preparation are separate steps')
        events=read_journal(a.audit_journal);record=audit_journal(events,source_timing())
        record['journal_sha256']=hashlib.sha256(a.audit_journal.read_bytes()).hexdigest()
        record['provenance']='Supplied journal: bind source/binary/run receipt independently before claiming actual execution.'
        try:record['reservation_projection']=audit_reservation_projection(events,source_timing())
        except AssertionError as failure:record['reservation_projection']=dict(status='FAIL_LOGICAL_RESERVATION_INEQUALITY',reason=str(failure))
    else:
        record=plan()
        if a.prepare_dir is not None:record['prepared_sources_sha256']=prepare_sources(a.prepare_dir)
    with a.output.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
