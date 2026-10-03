#!/usr/bin/env python3
"""Generate a passive, default-off PHW10 wrapper copy and join retirement facts.

No compiler or runtime launcher. Source checks are structural, not elaboration.
Native root publication is observable; selected capture credits/packet debts are
not implemented by the pinned native engine and cannot be synthesized from idle.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import dsrom_I66_effective_idle_contract as E
import dsrom_I66_existing_ready_fences as F
import dsrom_I66_source_interlock as I
import dsrom_I66_consumer_deadline as D
import dsrom_I66_capture_owner as O

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_I66_native_observer_20261003'
INPUT = ROOT / 'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs'
BEGIN = '// I66_PASSIVE_OBSERVER_BEGIN\n'
END = '// I66_PASSIVE_OBSERVER_END\n'
C = 'dut.u_tile.u_core'
T = 'dut.u_tile'
A = C + '.g_rom.u_radapt'
U = C + '.g_su_x.u_su'
V = U + '.u_vec'
WRITERS = {
    'ww_h': ['ww_h_we', 'ww_h_addr', 'ww_h_mask', 'ww_h_data'],
    'rom': ['rom_we', 'rom_waddr', 'rom_wdata'],
    'vw_me': ['vw_me_we', 'vw_me_addr', 'vw_me_mask', 'vw_me_data'],
    'vw_su': ['vw_su_we', 'vw_su_addr', 'vw_su_data'],
    'vw_rd': ['vw_rd_we', 'vw_rd_addr', 'vw_rd_data'],
    'xs_vm': ['xs_vm_we', 'xs_vm_waddr', 'xs_vm_wdata'],
    'xs_res': ['xs_res_we', 'xs_res_addr', 'xs_res_data'],
    'vw_xe': ['vw_xe_we', 'vw_xe_addr', 'vw_xe_data'],
    'ww_q': ['ww_q_we', 'ww_q_addr', 'ww_q_mask', 'ww_q_data'],
    'ww_x': ['ww_x_we', 'ww_x_addr', 'ww_x_mask', 'ww_x_data'],
    'xa': ['xa_we', 'xa_waddr', 'xa_wdata'],
    'xb': ['xb_we4', 'xb_waddr4', 'xb_wdata4'],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned_sources():
    pins = json.loads((OUT / 'source_pins.json').read_text())
    for path, h in pins.items():
        if sha((ROOT / path).read_bytes()) != h:
            raise ValueError('source pin changed: ' + path)
    return pins


def display(kind, fields, condition='1'):
    # Hex preserves packed source widths; normalizer must use the compiled widths.
    fmt = 'I66HOOK pre %0d %0d ' + kind + ''.join(' ' + k + '=%h' for k in fields)
    args = ', '.join(['i66_edge', 'RANK'] + list(fields.values()))
    return f'        if ({condition}) $display("{fmt}", {args});\n'


def observer_block():
    b = BEGIN + '''// Simulation observation only. No drives, forces or provider completion flags.
    generate if (I66_OBSERVE != 0) begin : g_i66_passive
        longint unsigned i66_edge = 0;
        // Count every clock including reset; never reuse an edge across reset epochs.
        always @(posedge clk) i66_edge <= i66_edge + 1;
        initial if (ROM_PHW != 10 || ROM_R != 128 || ROM_FBW != 1632 || SUN != 256)
            $fatal(1, "I66 observer requires exact full PHW10/SUN256 binding");
        always @(posedge clk) begin
'''
    fields = {'rst_n': 'rst_n', 'pc': C+'.pc', 'st': C+'.st', 'unit': C+'.d_unit',
              'wait_mask': C+'.d_wait', 'skip': C+'.d_skip', 'waited': C+'.waited',
              'unit_ready': C+'.unit_ready', 'q_gate': C+'.q_gate', 'kv_gate': C+'.kv_gate',
              'm0_gate': C+'.m0_gate', 'idles': C+'.idles', 'gos': C+'.gos',
              'coll_busy': 'dut.coll_busy', 'faults': 'dbg_fs', 'user10': 'user',
              'writer_mask': "{" + ','.join('(|'+T+'.'+s[0]+')' for s in WRITERS.values()) + "}"}
    b += display('edge', fields)
    b += display('issue_sample', {'pc': C+'.pc', 'unit': C+'.d_unit',
                       'qe_mode': C+'.qe_mode', 'word': C+'.ir'}, C+'.st == 6')
    b += display('rom_accept', {'pc': C+'.pc', 'key': C+'.qe_wbase', 'stride': C+'.qe_istride',
                    'indexed': C+'.qe_ind', 'ibase': C+'.qe_ibase', 'obase': C+'.qe_obase'},
                    'rst_n && '+C+'.rom_q_go && '+A+'.st == 0')
    b += display('adapter', {'st': A+'.st', 's_go': C+'.g_rom.s_go',
                    's_idle': C+'.g_rom.s_idle', 's_ready': C+'.g_rom.s_ready',
                    'key': A+'.key', 'hit': A+'.hit', 'phase': C+'.g_rom.s_ph',
                    'vi_re': A+'.vi_re', 'vi_addr': A+'.vi_addr', 'vi_q': A+'.vi_q',
                    'fault': A+'.fault'})
    b += display('SU_front', {'pc': C+'.pc', 'seq': U+'.seq', 'abase': C+'.a_base',
                    'cbase': C+'.c_base'}, 'rst_n && '+C+'.su_go && !'+U+'.pend')
    b += display('vector_accept', {'seq': U+'.seq', 'copy': U+'.cp', 'abase': U+'.abase',
                    'cbase': U+'.cbase'}, 'rst_n && '+U+'.v_acc')
    b += display('Xtag', {'cw': V+'.cwx', 'cw_width': '$bits('+V+'.cwx)'},
                    'rst_n && '+V+'.vx')
    for family, signals in WRITERS.items():
        b += display('writer_'+family, {s: T+'.'+s for s in signals}, 'rst_n && (|'+T+'.'+signals[0]+')')
    b += '''        end
        for (genvar r = 0; r < ROM_R; r = r + 1) begin : g_pub
            reg [29:0] saved_addr;
            longint unsigned saved_edge;
            always @(posedge clk) if (rst_n && dut.u_tile.rom_we[r]) begin
                saved_addr = dut.u_tile.rom_waddr[r*30 +: 30];
                saved_edge = i66_edge;
                // $strobe executes after NBA. Full address is logged to reject VM19 alias.
                $strobe("I66HOOK post %0d %0d VM root=%h address=%h value=%h",
                        saved_edge, RANK, r, saved_addr, dut.u_tile.vm[saved_addr[18:0]]);
            end
        end
        for (genvar p = 0; p < 4*SUN; p = p + 1) begin : g_read
            always @(posedge clk) if (rst_n && dut.u_tile.xs_rd_re[p] && dut.u_tile.xs_rd_src[p*2 +: 2] == 0)
                $display("I66HOOK pre %0d %0d read port=%h src=%h address=%h value=%h",
                    i66_edge, RANK, p, dut.u_tile.xs_rd_src[p*2 +: 2],
                    dut.u_tile.xs_rd_addr[p*30 +: 30],
                    dut.u_tile.vm[dut.u_tile.xs_rd_addr[p*30 +: 19]]);
        end
    end endgenerate
''' + END
    return b


def generate():
    pinned_sources()
    wrapper = (INPUT/'runtime_wrapper.sv.txt').read_text()
    if wrapper.count('module ot_v41_rt_die #(') != 1 or wrapper.count('endmodule') != 1:
        raise ValueError('unexpected wrapper shape')
    result = wrapper.replace('module ot_v41_rt_die #(', 'module ot_v41_rt_die_i66_observer #(\n    parameter integer I66_OBSERVE = 0,', 1)
    return result.replace('endmodule', observer_block() + 'endmodule', 1)


def inverse(text):
    start, end = text.index(BEGIN), text.index(END) + len(END)
    result = (text[:start] + text[end:]).replace(
        'module ot_v41_rt_die_i66_observer #(\n    parameter integer I66_OBSERVE = 0,',
        'module ot_v41_rt_die #(', 1)
    if result != (INPUT/'runtime_wrapper.sv.txt').read_text():
        raise ValueError('observer inverse differs from protected wrapper')
    if text[start:end] != observer_block():
        raise ValueError('unreviewed observer body')
    return sha(result.encode())


def retirement_join(context, publications, credits, packet, wait_exit, next_issue, read):
    """Concrete normalized SAME-phase callback join; no actual-enrollment credit.

    Transitive fences of other phases require separate records, never alias a
    captured producer's context to W2. Actual entry delegates existing enrollment.
    """
    context = copy.deepcopy(context)
    O.identity(context)
    source = D.source_model()
    demand = dict(node='L0.I'+str(context['pc']), expert=context['expert'], rank=context['rank'],
                  generation=context['generation'], user=context['user'], xversion=context['xversion'],
                  owner_stage=context['stage'], phase=context['phase'], key_word=context['key_word'])
    obligation = D.operation_id(demand, source)
    base = obligation['output_VM_elements'][0]
    def same(record):
        if record['context'] != context:
            raise ValueError('stale or aliased retirement context')
        O.identity(record['context'])
    if len(publications) != 576 or len(credits) != 576:
        raise ValueError('all576 concrete publication and credit callbacks required')
    pub, credit = {}, {}
    for records, dest in [(publications, pub), (credits, credit)]:
        for r in records:
            same(r); row = I.uint(r['row'], 16); edge = I.uint(r['postNBA_edge'])
            if row >= 576 or row in dest:
                raise ValueError('duplicate or foreign row')
            if I.uint(r['physical_shard'], 1) != ((row % 256)//2)//64:
                raise ValueError('wrong physical shard')
            if dest is pub:
                if I.uint(r['address'], 30) != base+row:
                    raise ValueError('resolved source frame/address mismatch')
                I.uint(r['value'], 32)
            dest[row] = edge
    for row in pub:
        if credit[row] <= pub[row]:
            raise ValueError('positive captured credit return after VM visibility required')
    same(packet); same(wait_exit); same(next_issue); same(read)
    if I.uint(packet['outstanding_after'], 32) != 0:
        raise ValueError('wire packet debt remains')
    sent, returned = {}, {}
    for record in packet['accepted_packets']:
        ident=I.uint(record['id'],32)
        if ident in sent: raise ValueError('duplicate sent packet')
        sent[ident]=I.uint(record['edge'])
    for record in packet['captured_ACKs']:
        ident=I.uint(record['id'],32)
        if ident in returned: raise ValueError('duplicate ACK')
        returned[ident]=I.uint(record['postNBA_edge'])
    if not sent or set(sent)!=set(returned) or any(returned[k]<=sent[k] for k in sent):
        raise ValueError('actual complete positive packet ACK ledger required')
    ack=max(returned.values())
    sample = {k: wait_exit[k] for k in ['edge','adapter_st','s_go','native_idle',
               'phase_active','qualified_retired','effective_idle','healthy_reset_epoch']}
    for name in ['adapter_fault','spine_fault']:
        if I.uint(wait_exit[name],1)!=0: raise ValueError('faulted source cannot retire healthy')
    E.validate_wait_exit(sample)
    edge = sample['edge']
    if max(max(pub.values()), max(credit.values()), ack) >= edge:
        raise ValueError('all concrete retirement facts must precede F sample')
    if I.uint(next_issue['edge']) < edge+1 or I.uint(next_issue['registered_accept_edge']) != next_issue['edge']+1:
        raise ValueError('later source issue/registered acceptance relation')
    rom = [d['pc'] for d in F.descriptors() if d['unit']==3 and d['decoded_fields']['qe_mode']==0]
    later = next((pc for pc in rom if pc>context['pc']), None)
    if I.uint(next_issue['pc'],14) != later:
        raise ValueError('must follow the next real QE phase, not alias adjacent W2 to producer')
    for k in ['waited','unit_ready','q_gate','kv_gate','m0_gate','healthy_reset_epoch']:
        if I.uint(next_issue[k],1)!=1: raise ValueError('source admission gate false')
    if I.uint(next_issue['d_skip'],1)!=0: raise ValueError('skipped instruction is not admission')
    if I.uint(read['edge']) <= max(pub.values()) or I.uint(read['observed_tag_edge']) != read['edge']+2:
        raise ValueError('actual read/postNBA visibility/R+2 relation')
    if I.uint(read['address'],30) not in range(base,base+576):
        raise ValueError('read outside retained source VM version')
    I.uint(read['source_seq'],8); I.uint(read['observed_tag_seq'],8)
    if read['source_seq'] != read['observed_tag_seq']:
        raise ValueError('stale R+2 sequence tag')
    return dict(status='PASS_NORMALIZED_CALLBACK_RELATIONS_ONLY', F=edge,
                last_VM_visible=max(pub.values()), last_credit=max(credit.values()),
                actual_current_enrollment=False, physical_deadline_proved=False,
                absolute_service_bound=None)


def parse_native(lines):
    """Lossless raw hooks: packed words are hex, edges/rank decimal.

    These are source observations, not full169 identities. No PC/busy event is
    converted to causal progress. Missing provider fields remain unavailable.
    """
    kinds={'edge','issue_sample','rom_accept','adapter','SU_front','vector_accept','Xtag',
           'VM','read'} | {'writer_'+k for k in WRITERS}
    result=[]; last={}
    for line in lines:
        if not line.startswith('I66HOOK '): continue
        parts=line.split()
        if len(parts)<6 or parts[1] not in ['pre','post'] or parts[4] not in kinds:
            raise ValueError('malformed native callback')
        if not parts[2].isdigit() or not parts[3].isdigit(): raise ValueError('nondecimal edge/rank')
        edge,rank=int(parts[2]),int(parts[3]); I.uint(edge,64); I.uint(rank,2)
        if edge<last.get(rank,0): raise ValueError('backward actual edge')
        last[rank]=edge; fields={}
        for token in parts[5:]:
            if token.count('=')!=1: raise ValueError('malformed field')
            key,value=token.split('=')
            if not key or key in fields or not value or any(c not in '0123456789abcdefABCDEF' for c in value):
                raise ValueError('unknown/duplicate/malformed source value')
            fields[key]=int(value,16)
        if (parts[4]=='VM') != (parts[1]=='post'):
            raise ValueError('wrong source NBA region')
        result.append(dict(edge=edge,rank=rank,region=parts[1],kind=parts[4],fields=fields))
    if not result: raise ValueError('no actual hook events')
    return result


def calendar(enrollment):
    """Strict actual enrollment before reading raw current-program journal.
    Reports measured callback extents; does not make a worst-case guarantee.
    """
    enrolled = D.J.current_enrollment(enrollment)
    compiled=json.loads(Path(enrollment['compile_manifest_path']).read_text())
    if compiled.get('selected_wrapper')!='ot_v41_rt_die_i66_observer' or enrollment['parameters'].get('I66_OBSERVE')!=1:
        raise ValueError('enabled observer top must be selected by actual compile receipt')
    binding=enrollment['native_observer_binding']
    hook=D.J.file_pin(binding['source_path'],binding['source_sha256'])
    if compiled['source_files'].get(str(hook))!=binding['source_sha256']:
        raise ValueError('observer source not compiled in enrolled executable')
    inverse(hook.read_text())
    events=parse_native(Path(enrollment['journal_path']).read_text().splitlines())
    extents={}
    for event in events:
        key=str(event['rank'])+':'+event['kind']
        x=extents.setdefault(key,dict(count=0,first_edge=event['edge'],last_edge=event['edge']))
        x['count']+=1; x['last_edge']=event['edge']
    return dict(status='ENROLLED_NATIVE_CALLBACK_EXTENTS_ONLY', enrollment=enrolled,
                measured_extents=extents, actual169_provider_identity=False,
                F_qualified=False, causal_service_upper_bound=None, fulltoken=False)


def model():
    generated = generate(); inverse(generated)
    # Exact structural checks only, not a substitute for Verilator hierarchy admission.
    sources = [(INPUT/'core.sv.txt').read_text(), (INPUT/'tile.sv.txt').read_text(),
               (OUT/'inputs/su_adapt.sv.txt').read_text(),
               (ROOT/'results/uarch/dsrom_I66_consumer_deadline_20261002/inputs/vec.sv.txt').read_text()]
    for signals in WRITERS.values():
        if any(s not in sources[1] for s in signals): raise ValueError('writer source absent')
    for name in ['v_acc','seq','cp','abase','cbase']:
        if name not in sources[2]: raise ValueError('SU source absent')
    if 'reg [INSTR_BITS-1:0] ir' not in sources[0]:
        # Declaration whitespace may vary, but must be source-confirmed.
        import re
        if not re.search(r'reg\s+\[INSTR_BITS-1:0\]\s+ir\b', sources[0]): raise ValueError('instruction register absent')
    peer=json.loads((OUT/'inputs/Maxwell_parent_review.json').read_text())
    return dict(scope='PASSIVE_CURRENT_SOURCE_HOOK_COPY_AND_RETIREMENT_JOIN_MODEL_ONLY',
        source_pins=pinned_sources(), generated_sha256=sha(generated.encode()),
        inverse_sha256=inverse(generated), default_off=True, engine_edits=0,
        native_events=['everyedge reset/PC/gates/allwriter presence','issue sample (not admission)',
            'registered ROM accept','adapter EID VM read/key/phase','SU front/vector accept',
            'all12 active writer families','ROM postNBA VM value','actual operand read','raw Xtag controlword'],
        unavailable_native_fields=['capture generation/user32/Xversion/physical shard association',
            'selected bank row credit capture','wire packet ACK/outstanding debt',
            'effective-idle hook active/qualified retirement','selected c9 physical root/CDC phase'],
        no_identity_fabrication='Wrapper user10 is raw source input, never promoted to full169 user32. No generation inferred from PC or busy.',
        edge_contract='pre $display reads source before NBA; post $strobe reads VM after NBA; edge counts include reset, actual rank source clock only.',
        observer_state_bits=64+128*(30+64), observer_state_bytes=1512,
        per_native_edge_max_records=1+1+1+1+1+1+1+12+128+1024,
        logging_cost='No measured runtime/compile cost. Packed writer records have source $bits, no bit or address truncation except VM19 indexing disclosed with full AW30 address.',
        elaboration_pass=False, frontend_required_for_new_SV_copy=True,
        reuse_policy='Source-matched disabled original objects can be retained as baseline only; enabling new wrapper hooks requires regenerated affected frontend and dependency/ABI verification. No hand-paired native translation credit.',
        earliest_run=dict(kind='CURRENT_PHW10_NATIVE_BASELINE_OBSERVATION_AFTER_ENROLLMENT_AND_BUILD_REVIEW',
            launch_ready=False, binary=None, actual_journal=None,
            required=['source-matched complete PHW10 full configuration binary/closure (not PHW6)',
                'four exact +DIR/prog.hex and separate +OT_ROM_DIR field bundle identities',
                'actual wrapper hierarchy/elaboration and regenerated/native object ABI review',
                'measured frontend/output inventory and fresh host capacity, preserve incremental outputs',
                'selected provider callbacks and completion hook implementation for candidate calibration']),
        selected_candidate_run_ready=False,
        relative_consumer_contract=E.model()['edge_names'],
        absolute_service_deadline=None, C=None, physical_stations=None,
        provider_retirement_emulated=False, jobs_launched=0,
        physical_review=dict(target=peer['target'],verdict=peer['verdict'],
            tests=peer['tests'],existing_gross_hook_with_local_clock_reset_body_um2=2.42028,
            hook_cost_readded=False,stage0_rank0_shard0_only=True,
            loaded_routes_SSFF_qualified=False,source_RTL_hook_implemented=False),
        historical_origin_transferred=False, hardware_admission=False, fulltoken=False)


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--generate',type=Path); p.add_argument('--model',type=Path)
    p.add_argument('--calendar',type=Path)
    a=p.parse_args()
    if a.generate: a.generate.write_text(generate())
    if a.model: a.model.write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
    if a.calendar: print(json.dumps(calendar(json.loads(a.calendar.read_text())),sort_keys=True,indent=2))
    if not a.generate and not a.model and not a.calendar: print(json.dumps(model(),sort_keys=True,indent=2))
