"""Bounded source extraction/ledger generation; no simulation or synthesis."""
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def blob(rev, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{rev}:{path}'])
def sha(data):
    return hashlib.sha256(data).hexdigest()
def load(rev, path):
    return json.loads(blob(rev, path))

prior = load('dee8d6b3a', 'results/arch/qwen_d8_hybrid_model_1019/model.json')
age = load('f68bd657b', 'results/arch/qw_109_age_model_1019/ledger.json')
die_bytes = blob('7cda48173', 'results/arch/qw_source_age_1019/die.v')
die = die_bytes.decode()
def binding(inst):
    match = re.search(r'\b' + re.escape(inst) + r'\s*\((.*?)\);', die, re.S)
    assert match, inst
    return dict(re.findall(r'\.([\w]+)\s*\(([^()]*)\)', match.group(1)))

files = ['050_qfd_dv_slice2.sv', '109_qfd_dv_slice2_faces.sv',
         '110_qfd_tt_ctlm_dv.sv', '114_qfd_native59_dv_service.sv',
         '115_qfd_sys_face.sv', '107_ot_qfd_collective_static_io_production.sv',
         '032_ot_qfd_io_collective_static.sv', '099_ot_coll_tp8_static.sv',
         '059_qfd_fwd_lane.sv']
sources = {}
for name in files:
    data = blob('7cda48173', 'results/arch/qw_source_age_1019/source/' + name)
    (HERE / 'source').mkdir(exist_ok=True)
    (HERE / 'source' / name).write_bytes(data)
    sources[name] = sha(data)

rows = []
for old in prior['rows']:
    row = dict(old)
    bus = old['bus']
    a = next(x for x in age['buses'] if x['bus'] == bus)
    chain = old['historical']['chain']
    source, destination = bus.split(' -> ')
    row['actual_bindings'] = {name: binding(name) for name in
        [source.split('.')[0], chain[0], chain[-1], destination.split('.')[0]]}
    row['actual_ordered_instances'] = a['actual_ordered_instances']
    row['actual_chain_instances'] = len(chain)
    row['historical_n_is_not_recounted_chain_length'] = old['historical']['n'] != len(chain)
    row['source_origin_and_consumer'] = a
    row['clock_reset_verdict'] = 'NET_BINDINGS_KNOWN_NATIVE_PHASE_AND_RESET_EPOCH_UNPROVEN'
    row['D8_adoptable_K_mod16'] = None
    row['first_legal_payload_read_edge'] = None
    row['same_address_cross_clock_collision_exclusion'] = None
    row['absolute_token_delta'] = None
    rows.append(row)

out = {'schema': 'opentallas.qwen.hybrid.source_ledger.v1',
       'verdict': 'MODEL_ONLY_SOURCE_CONTRACT_HOLD',
       'pins': {'source_age_commit': '7cda48173', 'age_commit': 'f68bd657b',
                'hybrid_commit': 'dee8d6b3a', 'native_input_audit': 'a6343c77a',
                'die_sha256': sha(die_bytes), 'source_sha256': sources},
       'rows': rows,
       'D8_record_ABI': {
           'order_low_to_high': ['complete original W-bit bus', 'wc[3:0] epoch', 'written-valid'],
           'payload_semantic_valid_is_preserved': True,
           'external_valid': '8 separately asynchronously cleared bits; not SRAM power-up state',
           'write': ['wclk=last forwarded ck_o', 'address={00,wc[2:0]}',
                     'record={1,wc[3:0],payload[W-1:0]}', 'all corresponding write masks enabled'],
           'read': ['rclk=actual receiver root', 'expected=(rc-k_q) mod16',
                    'slot=expected[2:0]', 'address={00,slot}',
                    'read-enable only with qualified read-run; no backpressure'],
           'SRAM_word_map': 'bank b stores complete record[64*b +: min(64,record_bits-64*b)]; unused high bits are explicit padding, not removed semantic fields',
           'controls': ['k_q[3:0]', 'write and read face resets', 'read-enable/address',
                        'aligned expected/slot/run/valid', 'fill/warm/ready', 'sticky fault'],
           'same_slot_epoch_repeats_after_16_writes': 'valid plus mod16 does not detect every stale history; reset/refill/lifetime and bounded age still required'},
       'architecture_edges': {
           'production_D4': 'W: bank[wc[1:0]]<=i; R: o<=preedge bank[(rc-k)[1:0]] conditional warm/valid',
           'FF_D8': 'W: selected bank payload/epoch capture; R: 8:1 direct mux into output FF; no readbank stage; timing unqualified',
           'SRAM_D8': 'W: selected native word storage write; R: synchronous macro read; R+1: external output and aligned fault publication',
           'receiver_pin_FF': 'destination captures old external o at its edge by NBA semantics; do not silently count this as the same R+1 macro output edge',
           'source_first_hop': 'source NBA publication is observed only by a later eligible capture; forwarded half-cycle stages retain original source-pinned ordering',
           'startup': '8 actual writes (+4 source edges versus D4) only fills storage; first legal read also needs both reset epochs, selected valid, expected epoch, read clock phase and source first-use proof',
           'read_advance': 'no R-1 substitution: prior gross 0.25T minus210ps=-1.667ps before macro setup',
           'extra_write_FF': 'native wclk storage inputs have audited setup/hold; no evidence mandates +1521FF/W+1; any inserted source register would need a new age/calendar price'},
       'physical_hold': 'Current exact macro pin contacts have0.096um pitch=10.4167/um; no replacement views/prototype/gate authorized',
       'preserved': ['109 historical schedule failures', 'nine D4 E_sta6/7 failures',
                     'HR low73 observed16 expected20 FAIL512/512',
                     'crossclock same-address R/W forbidden; no OLD assumption'],
       'qualification': {'simulation': None, 'native_timing': None, 'production_K': None,
                         'whole_reset_startup': None, 'schedule_compile': None, 'token': None}}
assert len(rows) == 9 and sum(r['width'] for r in rows) == 1757
assert sum(r['macros'] for r in rows) == 26
assert sum(r['selected_declared_soft_FF'] for r in rows) == 4672
for r in rows:
    assert r['actual_bindings'][r['actual_ordered_instances'][0]]
    assert r['record_order'][-1]['hi'] == r['width'] + 4
(HERE / 'ledger.json').write_text(json.dumps(out, indent=2) + '\n')
print('SOURCE_EXTRACTION_INTEGRITY_PASS nine lanes,1757 payload bits,26 banks,4672 declared softFF; semantic/timing qualification HOLD')
