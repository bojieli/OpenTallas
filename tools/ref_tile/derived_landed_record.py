"""Fail-closed provenance for the explicitly reviewed AHUB6 LP derivative.

This profile changes implementation partitioning, never clock/timing contracts.
No script named by a record is executed. Canonical LP is regenerated in memory;
all parent instances/connections and assignments are checked against that base.
Private controller behavior still requires the gate's golden/mutation benches.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

SCHEMA = "opentallas.derived_lp.ahub6.v1"
GENERATOR = "tools/qwen_kv_die/ahub6/mk_source.py"
REGIONS = ('c', 'w', 'e', 'z0', 'z1', 'z2', 'z3')


def _require(ok, message):
    if not ok:
        raise ValueError('derived LP: ' + message)


def _number(expression):
    _require(bool(re.fullmatch(r'[0-9()+*/ -]+', expression)), 'nonconstant cost expression')
    return eval(expression.replace('/', '//'), {'__builtins__': {}})


def expected_record(canonical):
    """Complete record transformation; unknown fields remain immutable."""
    d = copy.deepcopy(canonical)
    _require(d['landing_implementation']['chunk_bits'] == 8, 'profile needs canonical CHUNK8')
    _require(tuple(d['regions']) == REGIONS and d['D'] == 4 and d['E'] == 2,
             'profile needs seven AHUB D4/E2 regions')
    d.update(lane='KV-AHUB6', generator=GENERATOR)
    d['landing_implementation']['chunk_bits'] = 2
    forest = d['reset']['same_depth_forest']
    _require(forest['regional_stages'] == 2, 'profile cannot add a reset edge')
    leaves = branches = 0
    for r in forest['regions'].values():
        r['terms'] = [s.replace('+8-1)/8', '+2-1)/2') for s in r['terms']]
        r['leaves'] = sum(_number(s) for s in r['terms'])
        r['branches'] = (r['leaves'] + 31) // 32
        _require(r['leaves'] <= 1024 and r['branches'] <= 32, 'regional reset capacity')
        r['FFs'] = r['leaves'] + r['branches']
        leaves += r['leaves']; branches += r['branches']
        for b in r['bindings']:
            for k in ('first_expr', 'chunks_expr'):
                b[k] = b[k].replace('+8-1)/8', '+2-1)/2')
            b['first_leaf'] = _number(b['first_expr']); b['chunks'] = _number(b['chunks_expr'])
    forest['root_D_loads'] = 7
    forest['regional_root_copies'] = 7
    # This count changes with the partition, too; do not inherit the base count.
    forest['incremental_FFs'] = leaves + branches - 2 * len(REGIONS)
    d['reset']['note'] = 'Seven same-edge root copies; per-region branches <=32; child/reset and D4/K2 ages unchanged.'
    widths = [l['width'] for l in d['landings']]
    _require(all(type(w) is int and w > 0 for w in widths), 'nonconstant landing width')
    # Outer IO reset pad has four copies of the original seven stages (+21 FF).
    d['flops'].update(landing=5*sum(widths)+33*sum((w+1)//2 for w in widths),
                      reset=leaves+branches+7+52+3*7,
                      model_scope='Outer LP implementation; private core/io copies counted separately in mapped native census.',
                      kept_epoch_ports_included=True)
    d['regions']['c']['children'].extend('u_lpr_root_r'+str(i) for i in range(7))
    d['warnings'] = ['Native admission and current physical review required; no old gate/closure is inherited.']
    return d


def _load_lp(root):
    loader = importlib.util.spec_from_file_location('_derived_canonical_lp', root/'tools/landed_parent/lp.py')
    lp = importlib.util.module_from_spec(loader); loader.loader.exec_module(lp)
    lp.ROOT = root
    return lp


def _identity(root, item):
    _require(type(item) is dict and set(item) == {'path', 'sha256'}, 'artifact identity fields')
    path = Path(item['path'])
    _require(not path.is_absolute() and '..' not in path.parts, 'artifact must stay inside source root')
    blob = (root/path).read_bytes()
    _require(hashlib.sha256(blob).hexdigest() == item['sha256'], 'artifact hash mismatch: '+str(path))
    return blob


def _norm(value):
    if isinstance(value, dict): return {k:_norm(v) for k,v in value.items()}
    return re.sub(r'\s+', '', value)


def _instances(lp, text, top):
    mod = lp.parse_module(lp.preprocess(text, []), top)
    _, assigns, instances = lp.parse_body(mod['body'])
    return mod, assigns, {i['inst']:{k:i[k] for k in ('module','params','conns')} for i in instances}


def _topology(lp, base, actual, top):
    bm, ba, before = _instances(lp, base, top)
    am, aa, after = _instances(lp, actual, top)
    _require(bm['ports'] == am['ports'] and ba == aa, 'parent ports/assignments changed')
    _require(bm['params_txt'] == am['params_txt'], 'parent parameter defaults changed')
    expected = copy.deepcopy(before)
    del expected['u_lpr_root']
    for i,r in enumerate(REGIONS):
        expected['u_lpr_root_r'+str(i)] = dict(module='ot_pl_land_field_copy_bit',
            params=f'#(.ID({8192+i}))', conns=dict(ck='ck_c', d='rst_n', q=f'lpr_root_region[{i}]'))
        inst = expected['u_lpr_'+r]
        inst['params'] = f'#(.DEPTH(2), .LEAVES(LPR_LEAVES_{r}), .ROOT_LOADS((LPR_LEAVES_{r}+31)/32))'
        inst['conns']['d'] = f'lpr_root_region[{i}]'
    for inst in expected.values():
        inst['params'] = inst['params'].replace('.CHUNK_BITS(8)', '.CHUNK_BITS(2)')
        inst['conns'] = {k:v.replace('+8-1)/8', '+2-1)/2') for k,v in inst['conns'].items()}
    expected['u_lprc_u_io'].update(module='ot_ahub6_reset_pad', params='#(.N(7), .COPIES(4))')
    io = expected['u_io']; io['module'] = 'qkd_ahub6_static_io_safe'
    io['conns']['rst_group'] = io['conns'].pop('rst_n')
    io['conns']['start_all'] = 'start_all'
    core = expected['u_core']; core['module'] = 'qkd_ahub6_static_core_la_safe'
    core['conns']['start_all'] = 'start_all'
    _require(_norm(expected) == _norm(after), 'actual parent instance/clock/landing topology changed')
    # Localparam values define real leaf widths/offsets, beyond connection spelling.
    wanted = {k:v.replace('+8-1)/8', '+2-1)/2') for k,v in bm['params'].items()}
    _require(_norm(wanted) == _norm(am['params']), 'actual landing/reset parameter expressions changed')


def validate(spec, root, record):
    root = Path(root).resolve()
    provenance = record.get('derived_lp')
    fields = {'schema','canonical_record','canonical_rtl','canonical_spec','canonical_generator',
              'postprocessor','inputs','outputs','params'}
    _require(type(provenance) is dict and set(provenance) == fields, 'provenance fields')
    _require(provenance['schema'] == SCHEMA and record.get('generator') == GENERATOR, 'unsupported typed profile')
    _require(provenance['params'] == spec.get('params', {}), 'effective parameters changed')
    blobs = {k:_identity(root,provenance[k]) for k in
             ('canonical_record','canonical_rtl','canonical_spec','canonical_generator','postprocessor')}
    _require(provenance['canonical_generator']['path'] == 'tools/landed_parent/lp.py' and
             provenance['postprocessor']['path'] == GENERATOR, 'generator identities')
    canonical = json.loads(blobs['canonical_record'])
    cs = json.loads(blobs['canonical_spec'])
    _require(canonical['generator'] == 'tools/landed_parent/lp.py' and canonical['top'] == spec['top'],
             'canonical generator/top identity')
    _require(cs.get('params', {}) == spec.get('params', {}), 'canonical parameters changed')
    for entry in provenance['inputs']+provenance['outputs']: _identity(root,entry)
    needed = set(cs['sources']+cs.get('child_sources',[]))
    provided = {x['path'] for x in provenance['inputs']}
    _require(needed <= provided, 'missing canonical source identity')
    _require({x['path'] for x in provenance['outputs']} == set(spec['sources']), 'missing/extra actual source identity')
    lp = _load_lp(root)
    try:
        model = lp.Parent(cs); plan = model.plan(); rtl, rt = model.emit(plan,spec['top'])
        regenerated = model.record(plan,spec['top'],rt); regenerated['audit'] = lp.audit(cs,rtl)
        _require(rtl.encode() == blobs['canonical_rtl'] and regenerated == canonical,
                 'canonical deterministic replay differs')
        expected = expected_record(canonical)
        actual_record = {k:v for k,v in record.items() if k != 'derived_lp'}
        _require(actual_record == expected, 'full canonical contract delta differs')
        actual_rtl = root/spec['sources'][0]
        _topology(lp,rtl,actual_rtl.read_text(),spec['top'])
        audit_spec = copy.deepcopy(cs)
        audit_spec['child_sources'] = list(dict.fromkeys(spec['sources'][1:]+cs.get('child_sources',[])))
        audit = lp.audit(audit_spec,actual_rtl.read_text())
        _require(audit['ok'] and audit['landings'] == len(canonical['landings']), 'actual LP audit failed: '+str(audit))
    except (SystemExit, KeyError, IndexError) as e:
        raise ValueError('derived LP source/contract validation failed: '+str(e)) from e
    return record
