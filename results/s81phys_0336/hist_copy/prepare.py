import json
import hashlib
import re
import subprocess
from pathlib import Path

W = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
O.mkdir(parents=True, exist_ok=True)
bank_path = 'rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv'
parts_path = 'rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_parts.sv'
prefix_path = 'rtl/hdc/ot_hdc_prefix.sv'
bank = (W / bank_path).read_text()
old = subprocess.check_output(['git', '-C', str(W), 'show', '65902f47b3a:' + bank_path])
assert bank.encode() == old, 'current child differs from signed kit source revision'
prefix = (W / prefix_path).read_bytes()
assert prefix == subprocess.check_output(['git', '-C', str(W), 'show', '65902f47b3a:' + prefix_path])
parts = (W / parts_path).read_text()
parent = re.search(r'\bmodule ot_s81ph_hq_hist\b[\s\S]*?\bendmodule\b', parts).group()
modules = re.findall(r'\bmodule\s+(\w+)', bank)
assert modules == ['ot_s81ph_native_sel_hist_bank', 'ot_s81ph_hist32_popc']
for suffix, define in [('ref', False), ('copy', True)]:
    text = bank
    for name in modules:
        text = re.sub(r'\b' + name + r'\b', name + '_' + suffix, text)
    pp = parent.replace('ot_s81ph_hq_hist', 'hist_' + suffix).replace(
        'ot_s81ph_native_sel_hist_bank', 'ot_s81ph_native_sel_hist_bank_' + suffix)
    (O / (suffix + '.sv')).write_text(
        '`undef OT_HARD_CHILDREN\n' + ('`define' if define else '`undef') + ' OT_HB_PINCOPY\n' +
        text + '\n' + pp + '\n`undef OT_HB_PINCOPY\n')
mut = parent.replace('ot_s81ph_hq_hist', 'hist_mut').replace(
    'ot_s81ph_native_sel_hist_bank', 'ot_s81ph_native_sel_hist_bank_copy')
assert mut.count('.gsel({16{ng}})') == 1
mut = mut.replace('.gsel({16{ng}})', ".gsel({{15{ng}}, (ng ^ 4'h1)})")
(O / 'mut.sv').write_text('`undef OT_HARD_CHILDREN\n`define OT_HB_PINCOPY\n' + mut + '\n`undef OT_HB_PINCOPY\n')
(O / 'prefix.sv').write_bytes(prefix)
(O / 'source.json').write_text(json.dumps({
    'scope': 'parent multicast qualification only; no parent P&R or view adoption',
    'signed_child_revision': '65902f47b3a',
    'child_matches_signed_revision': True,
    'prefix_matches_signed_revision': True,
    'child_sha256': hashlib.sha256(bank.encode()).hexdigest(),
    'parent_source': parts_path,
    'parent_sha256': hashlib.sha256(parts.encode()).hexdigest(),
    'fixed_child_parameters': {'W': 16, 'CB': 11, 'BANK': 0, 'NB': 32, 'HPIPE': 1},
    'multicast': {'clr': '17 equal copies per bank', 'gsel': '16 equal 4-bit copies per bank'},
    'added_cycles': 0,
}, indent=2))
