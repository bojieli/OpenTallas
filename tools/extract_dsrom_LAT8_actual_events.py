#!/usr/bin/env python3
"""Extract existing source-pinned LAT8 log; never launches HDL or a build."""
import argparse
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1] / 'results/rtl/dsrom_LAT8_actual_event_profile_20261002'
SCHEMAS = {
    'EDGE': 'cycle adapt spine smpos smi have0 have1 sok adv cfg go xs u b pos sv cnt npush pop issue hazard gate'.split(),
    'LOADER': 'cycle valid addr ld_run ld_k'.split(),
    'EMITTED': 'cycle p b pos q0 e0 q1 e1'.split(),
    'PUBLIC': 'row seg nseg pos value err'.split(),
}
HEX = {'q0':64, 'q1':64, 'e0':3, 'e1':3, 'value':8}
PASS = 'PASS_EXISTING_FAST_PROFILE rows=2 emitted=16 pushes=16 pops=16 issues=16'

def parse(text):
    groups = {k: [] for k in SCHEMAS}
    current = None
    passes = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if 'FATAL' in line.upper() or 'Error' in line or 'OTHER_FAULT' in line:
            raise ValueError('failed log')
        kind = line.split(' ', 1)[0]
        if kind.startswith('PASS'):
            if line != PASS:
                raise ValueError('foreign PASS')
            passes.append(line_number)
            continue
        if kind not in SCHEMAS:
            if any(marker in line for marker in SCHEMAS):
                raise ValueError('malformed event')
            continue
        tokens = line.split()[1:]
        if len(tokens) != len(SCHEMAS[kind]):
            raise ValueError('event field count')
        row = {'line':line_number}
        for key, token in zip(SCHEMAS[kind], tokens):
            pattern = f'{key}=([0-9a-fA-F]{{{HEX[key]}}})' if key in HEX else f'{key}=([0-9]+)'
            match = re.fullmatch(pattern, token)
            if not match:
                raise ValueError('malformed event field')
            row[key] = match[1].lower() if key in HEX else int(match[1])
        if kind == 'EDGE':
            current = row['cycle']
        elif kind == 'PUBLIC':
            if current is None or not groups['LOADER'] or groups['LOADER'][-1]['cycle'] != current:
                raise ValueError('unbound PUBLIC')
            row['cycle'] = current
            row['cycle_binding'] = 'preceding EDGE/LOADER in same bench tick, PUBLIC after posedge settle'
        elif current != row['cycle']:
            raise ValueError('event cycle context')
        groups[kind].append(row)
    if len(passes) != 1:
        raise ValueError('terminal PASS count')
    edges, loaders = groups['EDGE'], groups['LOADER']
    if [r['cycle'] for r in edges] != list(range(3,1032)) or [r['cycle'] for r in loaders] != list(range(3,1032)):
        raise ValueError('edge/loader coverage or duplicate')
    if passes[0] <= max(r['line'] for rows in groups.values() for r in rows):
        raise ValueError('terminal ordering')
    emissions = groups['EMITTED']
    if [(r['cycle'],r['p'],r['b'],r['pos']) for r in emissions] != [(62+8*i,0,i%8,i//8) for i in range(16)]:
        raise ValueError('emitted order')
    bycycle = {r['cycle']:r for r in edges}
    for r in emissions:
        e = bycycle[r['cycle']]
        if (e['xs'],e['u'],e['b'],e['pos'],e['sv']) != (1,r['p'],r['b'],r['pos'],3):
            raise ValueError('emission/EDGE mismatch')
    for key, start in [('npush',64),('pop',65),('issue',65)]:
        actual = [e['cycle'] for e in edges if e['gate'] and e[key]]
        if actual != list(range(start,start+8*16,8)) or any(e[key]>1 for e in edges):
            raise ValueError('accept/issue coverage')
    if any((e['hazard'] and e['issue']) or e['cnt']+e['npush'] > 4+e['pop'] for e in edges):
        raise ValueError('hazard/overflow')
    if [e['cycle'] for e in edges if e['cfg']] != [13] or [e['cycle'] for e in edges if e['go']] != [40]:
        raise ValueError('cfg/go pulse binding')
    if [(r['cycle'],r['addr']) for r in loaders if r['valid']] != [(15+i,i) for i in range(25)]:
        raise ValueError('config coverage')
    if [(r['cycle'],r['row'],r['seg'],r['nseg'],r['pos'],r['value'],r['err']) for r in groups['PUBLIC']] != [(155,256,0,1,0,'44000000',0),(219,256,0,1,1,'44000000',0)]:
        raise ValueError('public output coverage')
    return groups, passes[0]

def generate(base=BASE):
    base = Path(base)
    pins = json.loads((base/'sourcepins.json').read_text())
    for name, expected in pins['extraction_inputs_sha256'].items():
        if hashlib.sha256((base/name).read_bytes()).hexdigest() != expected:
            raise ValueError('source pin mismatch: '+name)
    g, passline = parse((base/'inputs/existing_fast8_simulate.log').read_text())
    cfg = [int(x,16) for x in (base/'inputs/existing_fast8/e1.cfg.hex').read_text().split()]
    samples = []
    events = []
    def event(kind, sample, phase='pre_rising_edge', **extra):
        c=sample['cycle']
        return {'kind':kind, 'basis':'observed_log', 'cycle':c, 'sample_phase':phase,
                'source_derived_fixture_time_ps':c*833000+(419000 if phase=='post_rising_settle' else 418000),
                'log_line':sample['line'], **extra}
    for e,l in zip(g['EDGE'],g['LOADER']):
        samples.append({'cycle':e['cycle'],'edge':e,'loader':l,'basis':'observed_log','sample_phase':'pre_rising_edge'})
        for field,kind in [('cfg','configuration_start'),('go','pair_go')]:
            if e[field]: events.append(event(kind,e))
        for field,kind in [('npush','fifo_accepted_push'),('pop','fifo_pop'),('issue','walker_issue')]:
            if e['gate'] and e[field]:events.append(event(kind,e,pre_count=e['cnt'],count=e[field]))
        if not samples[:-1] or e['gate'] != samples[-2]['edge']['gate']:
            events.append(event('leaf_enable_sample_transition',e,enabled=e['gate'],meaning='low-phase latched enable, not clock signoff'))
        if l['valid']:
            address=l['addr']; word=cfg[address] | (8 if address==16 else 0)
            events.append(event('accepted_configuration_write',l,address=address,
                data_observed=False,source_derived_word_hex=f'{word:012x}',
                data_derivation='phase0 immutable cfg word; addr16 OR (np=1 <<3) by pair loader'))
    for row in g['EMITTED']:
        events.append(event('input_emitted',row,position=row['pos'],slice=row['b'],pair=row['p'],q0=row['q0'],e0=row['e0'],q1=row['q1'],e1=row['e1']))
    for row in g['PUBLIC']:
        events.append(event('pair_public_partial',row,phase='post_rising_settle',row=row['row'],segment=row['seg'],nseg=row['nseg'],position=row['pos'],value_hex=row['value'],error=row['err'],root_return=False))
    events.append({'kind':'terminal_pair_quiet_assertion','basis':'bench PASS inference, flags not separately logged','cycle':1032,'log_line':passline,'pair_busy':False,'pair_quiet':True,'controller_drain_complete':False})
    events.sort(key=lambda r:(r['cycle'],r['log_line'],r['kind']))
    joins=[]
    for i,row in enumerate(g['EMITTED']):
        joins.append({'input_ordinal':i,'position':row['pos'],'slice':row['b'],'emit_cycle':row['cycle'],
            'fifo_accept_cycle':64+8*i,'issue_pop_cycle':65+8*i,'public_partial_cycle':155 if i<8 else 219,
            'tag_binding':'source FIFO order + strict emitted bench order; walker tags not individually logged'})
    geometry={'NP':8192,'R':128,'NBF':1024,'selected_pairs':1,'NSEG':8,'NCH':16,'NCHB':8,'XF':4,'NB':2,'positions':2,'MTP_parameter':1,'K':512,'configured_phase_rows':257,'selected_public_row':256,'FAST':1,'PP':1,'BP':0,'FRONT_PAR':0,'CUT':379,'LAT':8,'PHW':6,'BST':2,'WAKE_REG':1,'FIX_SECOND_ROW_INDEX':1,'GRADUAL_RNE':1,'DRAIN':127}
    profile={'status':'EXTRACTED_EXISTING_PASS_SELECTED_PAIR_ONLY','geometry':geometry,'sourcepins':'sourcepins.json',
        'counts':{'edge_samples':1029,'loader_samples':1029,'accepted_configuration_writes':25,'emitted_inputs':16,'accepted_fifo_pushes':16,'pops':16,'issues':16,'pair_public_partials':2,'observed_root_returns':0,'observed_writes':0},
        'cfg_cycles':[15,39],'cfg_addresses':[0,24],'cfg_start_cycle':13,'pair_go_cycle':40,
        'emit_interval_cycles':8,'emit_to_fifo_cycles':2,'fifo_to_issue_cycles':1,'last_issue_to_public_cycles':34,
        'maximum_observed_preedge_fifo_count':max(e['cnt'] for e in g['EDGE']),
        'hazard_samples':sum(e['hazard'] for e in g['EDGE']), 'issues_during_hazard':sum(e['issue'] for e in g['EDGE'] if e['hazard']),
        'leaf_enable_transitions':[{'cycle':e['cycle'],'enabled':e['enabled']} for e in events if e['kind']=='leaf_enable_sample_transition'],
        'last_issue_cycle':185,'last_public_cycle':219,'first_disabled_after_run_cycle':317,
        'last_issue_to_gate_off_cycles':132,'last_public_to_gate_off_cycles':98,
        'fixture_clock':{'tick_ps':833000,'unit':'1ns','precision':'1ps','high_phase_ns':416,'low_phase_ns':417,'post_rising_settle_ns':1,'post_falling_settle_ns':1,
                         'comment_discrepancy':'bench comment says 833ps; literal delays/generated C++ prove 833ns','frequency_credit':False,'timestamps':'source-derived scheduling offsets, not printed timestamps'},
        'final_observed_controller':g['EDGE'][-1],
        'coverage_limit':'single synthetic-ROM selected pair, two FP4 positions; not complete resident phases, full field or full token',
        'unknowns':['actual root-return events','actual write payload/ACK/retirement','drain counter and walker-stop trace','original consumer deadlines','observed VM read request/address trace'],
        'claims':{'fullfield':False,'fulltoken':False,'physical':False,'SS_FF_clock':False,'PAR2':False,'adoption':False}}
    contract={'original_consumer_deadline_cycles':None,'deadline_reason':'spine uses completion/count barrier; no original downstream deadline observed or specified in these pinned source paths',
        'root_returns':{'connection':'bench r_v/r_row/r_pos/r_fp32/r_bf16/r_e tied zero','observed_events':[],'pair_partials_are_root_returns':False},
        'writes':{'connection':'bench leaves w_we/w_addr/w_data unconnected','observed_events':[],
            'source_contract':'on each r_v[kr], w_we[kr]<=1; w_addr=obase+r_row+r_pos*ops; w_data chosen from fp32/bf16 per format',
            'source_implied_zero_write_enables':'r_v=0 throughout fixture, except initialization also clears w_we',
            'conditional_unobserved_addresses':[{'row':256,'position':0,'address':4352},{'row':256,'position':1,'address':4609}],
            'address_constants':{'obase':4096,'ops':257},'consumer_ACK_contract':None},
        'retirement_drain':{'complete_observed':False,'terminal_pair_quiet':True,'spine_final_state':'RUN (3)','adapter_final_state':'WAIT (5)',
            'source_rows_left_initial':514,'source_rows_left_rule':'nrow*(np+1)=257*2; subtract countones(r_v); r_v tied0 so remains514',
            'idle_rule':'S_RUN exits iff rows_left==0 && !sm_run && !ld_run',
            'element_tail_rule':'go_e or walk_busy reloads DRAIN127; else decrement; registered wake=go|go_e|walk_busy|(drain!=0)',
            'observed_gate_off_cycle':317,'observed_drain_counter':None,'last_leaf_to_root_retire_bound':None},
        'source_locations':{'bench':'inputs/tb_dsrom_upstream_pair_cadence.sv:99-125,171-230','write_and_retire':'inputs/ot_v41_spine_w17w10.sv:250-271,308-315','loader':'inputs/ot_v41_pair_w17w10.sv:113-140','tail':'inputs/ot_v41_rom_elem_w10.sv:174-203'},
        'composition_owner':'Maxwell; parent owns PAR2 config/root static edges, Nash parity; this record supplies selected-pair observed cadence only'}
    offered = json.loads((base/'inputs/offered_r3_first_fp4.json').read_text())
    offered_model = json.loads((base/'inputs/offered_r3_model.json').read_text())
    if offered_model['source_sha256']['rtl/v41die/ot_v41_spine_w17w10.sv'] != pins['original_package_artifact_hashes']['ot_v41_spine_w17w10.sv']:
        raise ValueError('offered spine source mismatch')
    stream = [int(x,16) for x in (base/'inputs/existing_fast8/spine_stream.hex').read_text().split()]
    bycycle = {e['cycle']:e for e in g['EDGE']}
    beat_matches=[]
    for row in g['EMITTED']:
        c=row['cycle']-3; e=bycycle[c]; w=stream[e['smi']]
        u=(w>>1)&255; b=(w>>9)&7; sv=(w>>12)&3
        need_q=(((u<<9)|((1 if sv&2 else 0)<<8)|(b<<5))+32)&32767
        have=e['have1'] if row['pos']&1 else e['have0']
        if not (w&1 and e['adv'] and e['sok'] and e['smpos']==row['pos'] and need_q<=have and u==row['p'] and b==row['b']):
            raise ValueError('stream acceptance join mismatch')
        matches=[o for o in offered['offered_beats'] if o['word48']==w]
        if len(matches)!=1 or matches[0]['required_loaded_elements']!=need_q:
            raise ValueError('offered word/need_q mismatch')
        beat_matches.append({'position':row['pos'],'slice':row['b'],'fixture_stream_index':e['smi'],
            'word48_hex':f'{w:012x}','source_derived_need_q':need_q,'observed_have':have,
            'observed_stream_advance_cycle':c,'observed_pair_emit_cycle':row['cycle'],
            'broadcast_latency_cycles':3,'advance_line':e['line'],'emit_line':row['line'],
            'offered_profile':offered['name'],'offered_index':matches[0]['offered_index'],
            'match_scope':'same literal word and source need_q, not full offered-program acceptance'})
    offered_join={'matches':beat_matches,'source_literal_need_q':"sv[1] ? ({u, 1'b1, b, 5'd0} + 15'd32) : ({u, 1'b0, b, 5'd0} + 15'd32)",
        'selected_fixture_K':512,'offered_profile_K':offered['K'],'selected_fixture_nbeat':64,
        'offered_profile_beats':len(offered['offered_beats']),'selected_valid_beats_per_position':8,
        'config_binding':{'observed_pair_cfg_cycle':13,'observed_pair_go_cycle':40,'observed_go_relative_cfg':27,
            'offered_safe_GO_relative_cfg':offered['config_source_safe_GO_edge'],
            'observed_last_valid_loader_cycle':39,'observed_last_loader_relative_cfg':26,
            'capture_semantics':'LOADER samples c_v/c_a before this rising edge; element free-clock config captures this edge'},
        'first_loaded_data_admission':{'blocked_cycle':58,'observed_have':bycycle[58]['have0'],'source_need_q':288,'observed_s_ok':bycycle[58]['sok'],'observed_s_adv':bycycle[58]['adv'],'accepted_cycle':59,'accepted_have':bycycle[59]['have0']},
        'broadcast_binding':'bt_xs_v captures s_adv && sw[0]; BST2 delays two more edges; preedge emitted sample is advance cycle+3',
        'full_program_acceptance_proven':False,'return_write_drain_deadlines_proven':False}
    products={'offered_word_join.json':offered_join,'edge_samples.jsonl':samples,'events.jsonl':events,'input_issue_relationships.json':joins,'profile.json':profile,'consumer_contract.json':contract}
    return products

def write(base=BASE):
    products=generate(base)
    for name,data in products.items():
        content=''.join(json.dumps(row,sort_keys=True)+'\n' for row in data) if name.endswith('.jsonl') else json.dumps(data,indent=2,sort_keys=True)+'\n'
        (Path(base)/name).write_text(content)
    return products

if __name__ == '__main__':
    a=argparse.ArgumentParser();a.add_argument('--base',type=Path,default=BASE);args=a.parse_args()
    p=write(args.base);print(json.dumps(p['profile.json']['counts'],sort_keys=True))
