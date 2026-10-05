"""Read-only, portable review of retained historical attention metadata.

Never loads an archive, compiles a design, launches a model or admits runtime.
Verilator digestSymbol is lossy; agreement is metadata evidence, not signed
attestation that an archive was compiled from a particular Git blob.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

EVIDENCE = Path('results/uarch/w17_D1_retained_attention_binding_20261002')
CHILDREN = ('Vot_hdc_v41x_attn_staging_3', 'Vot_hdc_v41x_attn_tile_e',
            'Vot_hdc_v41x_attn_merge_6', 'Vot_hdc_qadd')


def digest_symbol(data):
    return base64.b64encode(hashlib.sha256(data).digest()[:30]).decode().replace('+', 'A').replace('/', 'B')


def source_rows(text):
    result = {}
    for line in text.splitlines():
        if line.startswith('S '):
            m = re.fullmatch(r'S\s+(\d+)\s+(?:\d+\s+){5}"([^"]+)"\s+"([^"]+)"', line)
            if not m:
                raise ValueError('Malformed source metadata row')
            size, digest, name = m.groups()
            if name in result:
                raise ValueError('Repeated source metadata path')
            result[name] = (int(size), digest)
    return result


def validate_source_rows(text, sources, data):
    rows = source_rows(text)
    for item in sources:
        name = '/home/ubuntu/w17work/attnsrc/' + item['recorded_basename']
        content = data[item['path']]
        if rows.get(name) != (len(content), digest_symbol(content)):
            raise ValueError('Historical source digest/size mismatch: ' + name)


def public_widths(text):
    return {name: int(msb) - int(lsb) + 1 for name, msb, lsb in
            re.findall(r'VL_(?:IN|OUT)(?:8|16|64|W)?\(&([a-zA-Z0-9_]+),(\d+),(\d+)(?:,\d+)?\)', text)}


def tile_indices(text):
    return sorted(set(map(int, re.findall(r'g_t__BRA__(\d+)__KET__', text))))


def clock_sample(old_bus, new_bus, propagate_before_rising=False):
    """Negative-control model of host transfer phase, not RTL qualification."""
    return new_bus if propagate_before_rising else old_bus


def attention_method(text):
    start = text.index('    bool att_propagate() override {')
    end = text.index('    bool done() override', start)
    return text[start:end]


def validate_clock_contract(text):
    start = text.index('    auto tick = [&]() {')
    tick = text[start:text.index('    for (int i = 0; i < 8; i++) tick();', start)]
    good = tick[tick.index('if (!wrong) {'):tick.index('} else {')]
    if good.index('dies[i - 4]->att_eval(1, rst)') > good.index('d->att_propagate()'):
        raise ValueError('Transfer before attention rising edge')
    if tick.index('set_inputs(1, rst)') > tick.index('if (!wrong)'):
        raise ValueError('Clock input assigned after rising evaluations')
    if tick.index('set_inputs(0, rst)') > tick.index('dies[i]->att_eval(0, rst)'):
        raise ValueError('Falling evaluation before clock assignment')
    if 'if (n > 64)' not in text:
        raise ValueError('Missing original settle guard')


def verify(root):
    e = Path(root) / EVIDENCE
    def load(name):
        return json.loads((e / name).read_text())
    manifest = load('artifact_manifest.json')
    for item in manifest:
        p = e / item['path']
        if p.is_symlink() or not p.resolve().is_relative_to(e.resolve()):
            raise ValueError('Unsafe artifact path')
        content = p.read_bytes()
        if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ValueError('Artifact mismatch: ' + item['path'])
    sources = load('source_manifest.json')
    content = {s['path']: (e / s['path']).read_bytes() for s in sources}
    records = ['metadata/Vattn__verFiles.dat', 'metadata/Vattn__hier.dir/Vattn__verFiles.dat']
    records += ['metadata/' + c + '/' + c + '__verFiles.dat' for c in CHILDREN]
    for name in records:
        validate_source_rows((e / name).read_text(), sources, content)
    # Match exact generated protectlib wrapper content to the final top record.
    rows = source_rows((e / records[1]).read_text())
    for c in CHILDREN:
        name = c + '/' + c[1:] + '.sv'
        d = (e / ('metadata/' + name)).read_bytes()
        if rows.get('obj/' + name) != (len(d), digest_symbol(d)):
            raise ValueError('Generated child wrapper mismatch')
        syms = (e / ('metadata/' + c + '/protectlib_symbols.txt')).read_text()
        for suffix in ('check_hash', 'create', 'combo_update', 'seq_update'):
            if c[1:] + '_protectlib_' + suffix not in syms:
                raise ValueError('Missing child ABI symbol: ' + suffix)
    widths = public_widths((e / 'metadata/Vattn.h').read_text())
    expected = dict(q_w=8192, kv_w=16960, sc_y=2048, pv_y=32768,
                    pv_f=1024, job_t=16, kv_m=4, p_w=512)
    if any(widths.get(k) != v for k, v in expected.items()):
        raise ValueError('Public ABI width mismatch')
    for item in load('full_engine_header_inventory.json'):
        excerpt = (e / item['excerpt']['path']).read_text()
        if tile_indices(excerpt) != list(range(64)):
            raise ValueError('Incomplete full-engine tile geometry')
    command = (e / 'metadata/Vattn__verFiles.dat').read_text().splitlines()[1]
    for option in ('--hierarchical', '-GH=16', '-GD=512', '-GTD=32', '-GNL=4', '-GTROWS=640', '-GPWORDS=1'):
        if option not in command:
            raise ValueError('Missing top geometry option')
    if [s['recorded_basename'] for s in sources if not s['byte_equal_current']] != ['ot_hdc_v41x_attn.sv']:
        raise ValueError('Current source mismatch record changed')
    record = load('binding_record.json')
    if record['runtime_binding']['original_process_archive_identity'] != 'NOT_PROVEN':
        raise ValueError('Unsupported original-process identity claim')
    if record['limits']['finite_causal_service_bound'] != 'BOUND_MISSING':
        raise ValueError('Unsupported service-bound claim')
    original = (e / 'runtime_source/v41_die_rt.cpp').read_text()
    current = (e / 'runtime_source/w17_current_fastpp_die_rt.cpp').read_text()
    if attention_method(original) != attention_method(current):
        raise ValueError('Driver attention mapping differs')
    validate_clock_contract(original)
    validate_clock_contract(current)
    return dict(status='METADATA_SOURCE_ABI_FULL_ENGINE_REVIEW_PASS',
                artifacts=len(manifest), source_inputs=6, child_records=4,
                tile_instances=64, current_revision_equivalence=False,
                original_process_linkage=False, runtime_admitted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2, sort_keys=True))
