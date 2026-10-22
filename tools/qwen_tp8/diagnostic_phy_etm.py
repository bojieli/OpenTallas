"""Exact input-boundary PHY ETM admission for failed-case diagnosis only.

A null reference is an unmeasured model input boundary, never native insertion R.
"""
import hashlib
import json
import os
from pathlib import Path
import re

FLAG = 'OT_DIAG_KPHY_INPUT_ETM'
MASTER = 'ot_qkvd_ucie_x64_phy'
DIRECTORY = 'physical/qwen_kv_die_phy/' + MASTER
SCHEMA = 'opentallas.qwen-kv-die.link-phy-abstract.v1'
APPROVED = {
    '.json': 'a1d77cc57a6a1010e3d40e735a1ca9f9d38be102bb5041487d9eaf7acecf973c',
    '.lef': 'f4a2b22a7479ebcbca2a9dbe676e36b20d933d28ae13aff4b15f8b66c7280f66',
    '_bb.v': 'c9699325c5e7134940f41f21b9c8c5d2a65f396f4201ca2d148b1b4d9204c7be',
    '_model.sv': '2b14efcc89a0841eddae12d1ca3c8f5ab7944773b2460887fe7496fd10500066',
    '_tt.lib': '4537813c653458ff6a9c35be6f3fb4671dc98c124e49be2de00910341c6347dc',
    '_ff.lib': 'a93f474f35cc1b3a72a0e99c6473196d5c30a65c8448230a820861be4585e262',
    '_ss.lib': '3a2cff90556b744aa79d7564e47fe1560c8fd5ad1a921a5f99b2a798eafac954',
}
ROLES = {'clk':'input', 'rst_n':'input', 'tx_v':'input', 'tx_flit':'input',
         'tx_up':'output', 'rx_v':'output', 'rx_flit':'output'}


def groups(text, kind):
    """Read balanced groups in this exact hash-pinned generated profile."""
    pattern = r'(?m)^\s*' + kind + r'\s*\(\s*([^)]*)\s*\)\s*\{'
    for match in re.finditer(pattern, text):
        start = match.end(); depth = 1; end = start
        while depth and end < len(text):
            depth += (text[end] == '{') - (text[end] == '}'); end += 1
        if depth: raise ValueError('unterminated exact PHY Liberty group')
        yield match[1].strip(), text[start:end-1]


def validate_lib_roles(text):
    cells = list(groups(text, 'cell'))
    if len(cells) != 1 or cells[0][0] != MASTER:
        raise ValueError('exact K PHY Liberty cell required')
    rows = list(groups(cells[0][1], 'pin')) + list(groups(cells[0][1], 'bus'))
    if len(rows) != len({name for name, _ in rows}):
        raise ValueError('duplicate boundary pin/bus')
    pins = dict(rows)
    if set(pins) != set(ROLES):
        raise ValueError('exact K PHY scalar/bus roles required')
    for name, body in pins.items():
        directions = re.findall(r'\bdirection\s*:\s*(\w+)\s*;', body)
        if directions != [ROLES[name]]:
            raise ValueError('K PHY boundary direction differs: ' + name)
        clock = re.findall(r'\bclock\s*:\s*(\w+)\s*;', body)
        if clock != (['true'] if name == 'clk' else []):
            raise ValueError('only input clk may be a clock: ' + name)
        arcs = list(groups(body, 'timing'))
        expected = [] if name == 'clk' else (['setup_rising','hold_rising'] if ROLES[name]=='input' else ['rising_edge'])
        types = []
        for _, arc in arcs:
            typ = re.findall(r'\btiming_type\s*:\s*(\w+)\s*;', arc)
            related = re.findall(r'\brelated_pin\s*:\s*"([^"]+)"\s*;', arc)
            if len(typ)!=1 or related != ['clk']:
                raise ValueError('boundary timing must reference sole input clk')
            tables = ('cell_rise','cell_fall') if typ[0]=='rising_edge' else ('rise_constraint','fall_constraint')
            if any(not re.search(r'\b'+t+r'\s*\(',arc) for t in tables):
                raise ValueError('boundary timing tables missing')
            types.append(typ[0])
        if sorted(types) != sorted(expected):
            raise ValueError('boundary timing arc roles differ: ' + name)
    return {'clock':'clk', 'clock_direction':'input', 'generated_clock_outputs':[],
            'arcs':{'setup_rising':3,'hold_rising':3,'rising_edge':3}}


def admit(master, root, case, view, libs):
    if master != MASTER or os.environ.get(FLAG) != '1':
        return None
    for flag in ('OT_CHAIN_DIAGNOSTIC','OT_SAVED_CASE_PHYSICAL_DIAGNOSTIC'):
        if os.environ.get(flag) != '1': raise ValueError('input-boundary ETM requires ' + flag)
    saved = Path(os.environ.get('OT_SAVED_CASE_ROOT','')).resolve()
    if saved/'src' != root.resolve() or case.resolve()!=saved/'out/case':
        raise ValueError('input-boundary ETM requires exact saved Q diagnostic context')
    for marker in ('DIAGNOSTIC_ONLY','NOT_A_DIE_RESULT'):
        path=saved/'chain'/marker
        if not path.is_file() or 'ORIGINAL_GEN_EXIT=1' not in path.read_text():
            raise ValueError('permanent failed-case diagnostic marker required')
    manifest=Path(os.environ.get('OT_SAVED_CASE_MANIFEST','')).resolve()
    if manifest!=saved/'saved_case_diagnostic_manifest.json':
        raise ValueError('exact saved-case manifest required')
    frozen=json.loads(manifest.read_text())
    if frozen.get('schema')!='opentallas.saved_case_physical_diagnostic.v1' or frozen.get('original_gen_exit')!=1 or frozen.get('compiler_verdict')!='FAIL' or frozen.get('qualification_eligible') is not False:
        raise ValueError('failed GEN/compiler and no qualification must remain explicit')
    expected=(root/DIRECTORY).resolve()
    if view.resolve()!=expected or set(libs)!= {'tt','ff','ss'}:
        raise ValueError('exact same-master full K source profile required')
    hashes={}
    for suffix,digest in APPROVED.items():
        path=view/(MASTER+suffix); actual=hashlib.sha256(path.read_bytes()).hexdigest()
        relative=str(path.resolve().relative_to(saved))
        if actual!=digest or frozen.get('sha256',{}).get(relative)!=digest:
            raise ValueError('unapproved or unfrozen exact K source profile: ' + suffix)
        hashes[suffix]=actual
    sheet=json.loads((view/(MASTER+'.json')).read_text())
    if sheet.get('schema')!=SCHEMA or sheet.get('name')!=MASTER:
        raise ValueError('exact licensed K boundary schema/name required')
    bb=(view/(MASTER+'_bb.v')).read_text()
    declarations=re.findall(r'\b(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)',bb)
    ports={name:(direction,abs(int(a)-int(b))+1 if a else 1)for direction,a,b,name in declarations}
    expected_ports={p:(d,583 if p.endswith('_flit') else 1)for p,d in ROLES.items()}
    if ports!=expected_ports:raise ValueError('exact K source RTL ports required')
    for corner,rel in libs.items():
        if (root/rel).resolve()!=view/(MASTER+'_'+corner+'.lib'):
            raise ValueError('corner library differs from exact source profile')
        validate_lib_roles((root/rel).read_text())
    return dict(schema='opentallas.diagnostic.input-boundary-etm.v1',master=MASTER,
                physical_qualification_eligible=False,qualification={'scope':'MODEL_ONLY','status':'UNMEASURED'},
                reference_kind='UNMEASURED_INPUT_BOUNDARY',native_insertion_ps=None,
                internal_tree='UNPROVEN',source_sha256=hashes['.json'],profile_sha256=hashes,
                clock='clk',clock_direction='input',generated_clock_outputs=[],
                scope='ASSUMED licensed input-boundary ETM only; no internal tree, PLL phase, package, native R or release qualification')


def is_unmeasured_reference(master, pin, value):
    if value is not None: return False
    if master!=MASTER or pin!='clk' or any(os.environ.get(k)!='1' for k in (FLAG,'OT_CHAIN_DIAGNOSTIC','OT_SAVED_CASE_PHYSICAL_DIAGNOSTIC')):
        raise ValueError('unmeasured reference requires exact diagnostic K input boundary')
    return True


def annotate(views, models):
    if not models: return
    views.update(physical_qualification_eligible=False,clock_qualification='UNMEASURED',
                 sta_qualification='UNMEASURED',region_qualification='UNMEASURED',
                 unmeasured_input_boundaries=models,
                 input_boundary_note='Null native insertion; no source-latency compensation; native clock-target construction must refuse')
