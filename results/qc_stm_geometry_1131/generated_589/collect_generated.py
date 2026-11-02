from pathlib import Path
import json, re, sys, tarfile
base = Path('/srv/opentallas-scratch2/claude/codex-qc-stm-count-1131')
run = base / 'private_gen_589'
kit = run / 'phys/slw_stm_v3'
old = base / 'phys/slw_stm_v3'
sys.path.insert(0, str(run / 'source/tools/die_plan'))
import gen_rtl

def width(expr):
    if not expr:
        return 1
    match = re.fullmatch(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', expr)
    assert match, expr
    return abs(int(match[1]) - int(match[2])) + 1

ports = gen_rtl.parse_leaf_ports((kit / 'rtl/qfd_qc_slw_stm.sv').read_text(), 'qfd_qc_slw_stm')
actual = {name: {'direction': value[0], 'width': width(value[1])} for name, value in ports.items()}
frozen = json.load(open(base / 'private_gen_172/native_source_port_census.json'))['ports']
differences = {name: [frozen.get(name), actual.get(name)] for name in set(frozen) | set(actual) if frozen.get(name) != actual.get(name)}
contract = json.load(open(kit / 'bound_native_reset.json'))
reset_text = (kit / 'reset_tree.tcl').read_text()
sites = [line for line in reset_text.splitlines() if line.startswith('rtr_place ')]
receipt = {
    'native_ports': len(actual), 'native_bits': sum(value['width'] for value in actual.values()),
    'exact_native_direction_width_differences': differences,
    'actual_IO_contacts': len(re.findall(r'^place_pin ', (kit / 'io.tcl').read_text(), re.M)),
    'native_reset_entry': contract['tree']['entry'], 'entry_path': contract['entry_path'],
    'native_reset_relays': len(contract['tree']['relays']), 'native_symbols': len(contract['native_paths']),
    'actual_emitted_reset_start_sites': len(sites),
    'no_phantom_root': not any('u_rst_root' in line or 'u_run_root' in line for line in sites),
    'SDC_byte_equal_frozen': (kit / 'constraint.sdc').read_bytes() == (old / 'constraint.sdc').read_bytes(),
    'clock_binding_byte_equal_frozen': (kit / 'clock_binding.json').read_bytes() == (old / 'clock_binding.json').read_bytes(),
    'core_area_line': next(line for line in (kit / 'config.mk').read_text().splitlines() if line.startswith('export CORE_AREA')),
    'fill': {'stdcell_area': 30846.92058, 'macro_area': 30682.301184, 'core_area': 182891.52, 'free_core': 152209.218816, 'std_fill_free': .202661315917334},
    'tool': '58964d6ef', 'native_source': 'd90b109213c6949da87b330ef143d96bbe937934',
    'qualification': 'GEN only. No CAD, actual placement/load/clock-source identity, parent adoption or asset qualification.',
    'nonFF_regional_area_obligation': 10691.5869, 'max_tiny_projected_FF_overlap': .8422200520833125,
    'bank_windows': 'Estimated model intent only; actual generator uses existing emitted ring/FT/reset decks.'
}
(run / 'static_generated_contract.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt), flush=True)
if not (run / 'face_guard.json').is_file():
    print('FACE_PENDING', flush=True)
    raise SystemExit(0)
receipt['port_bind'] = json.load(open(kit / 'port_bind.json'))
receipt['face_guard'] = json.load(open(run / 'face_guard.json'))
(run / 'actual_generated_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
files = ['config.mk', 'io.tcl', 'pins.json', 'port_bind_pins.json', 'port_bind.json', 'macro_place.tcl', 'clock_binding.json', 'constraint.sdc', 'sdc_lint.json', 'landing_contract.json', 'landing_placement.tcl', 'land_slots.json', 'reset_tree.tcl', 'reset_taps.tcl', 'clock_taps.tcl', 'face_flops.tcl', 'ft_stations.txt', 'budget.json', 'bound_native_reset.json']
with tarfile.open(run / 'actual_generated_bundle.tgz', 'w:gz') as archive:
    for name in files:
        archive.add(kit / name, arcname='kit/' + name)
    for name in ['actual_generated_receipt.json', 'face_guard.json', 'port_bind.log', 'face_guard.log', 'gen_receipt.json', 'native_slot_join.json']:
        archive.add(run / name, arcname=name)
print('BUNDLE_READY', flush=True)
