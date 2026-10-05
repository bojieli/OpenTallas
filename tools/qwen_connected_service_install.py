"""Additive same-clock service install. Does not regenerate pinned originals.

Emits actual64 range-owner instances and joins their issuer/RF event ports.
All remaining producer session/claim/input census/query/retirement/fence ports
stay explicit. This is not a runnable native factory or a build admission.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'rtl/model/qwen_hbm_integrated_20261003/ranked'
OUT = ROOT / 'rtl/model/qwen_hbm_installed_services_20261003'
MODEL = ROOT / 'results/uarch/qwen_connected_service_install_20261003/model.json'
OWNER = 'rtl/experimental/canonical_qwen_range_owner_20261003/ot_gpu_qwen_native_range_owner.sv'
ABI = 'results/uarch/canonical_qwen_range_owner_20261003/ports_r2.json'

# Source-owner inputs observed from actual issuer/SM handshakes.
FROM = {
    'inputs_bound_ready': 'issuer_inputs_bound_ready',
    'go_accepted': '(issuer_backend_go_valid[i] && issuer_backend_go_ready[i])',
    'go_tuple': 'issuer_backend_go_tuple',
    'next_source_PC': 'issuer_issue_tuple[i*239+164 +: 11]',
    'page_ack_valid': 'sm_rf_ack_accept', 'page_ack_owner': 'sm_rf_ack_owner55',
    'rf_range_ack_ready': 'issuer_rf_range_ack_ready',
    'producer_visible_valid': '(issuer_producer_visible_valid[i] && issuer_producer_visible_ready[i])',
    'producer_visible_tuple': 'issuer_producer_visible_tuple',
    'publish_valid': 'issuer_publish_valid', 'publish_tuple': 'issuer_publish_tuple',
    'publish_owner': 'issuer_publish_owner', 'publish_page_mask': 'issuer_publish_page_mask',
    'input_terminal_valid': 'issuer_input_terminal_valid',
    'input_terminal_tuple': 'issuer_input_terminal_tuple', 'input_terminal_mask': 'issuer_input_terminal_mask',
    'input_reverse_valid': 'issuer_input_reverse_valid',
    'input_reverse_tuple': 'issuer_input_reverse_tuple', 'input_reverse_mask': 'issuer_input_reverse_mask',
    'frame_retire_valid': 'issuer_frame_retire_valid',
    'frame_retire_tuple': 'issuer_frame_retire_tuple', 'frame_retire_owner': 'issuer_frame_retire_owner',
}
# These owner outputs replace external issuer inputs. No constant positive flags.
TO = {
    'inputs_bound_valid': 'issuer_inputs_bound_valid', 'inputs_bound_tuple': 'issuer_inputs_bound_tuple',
    'inputs_bound_mask': 'issuer_inputs_bound_mask', 'row_barrier_ready': 'issuer_row_barrier_ready',
    'expected_output_page_mask': 'issuer_issue_output_page_mask',
    'rf_range_ack_valid': 'issuer_rf_range_ack_valid', 'rf_range_ack_tuple': 'issuer_rf_range_ack_tuple',
    'rf_range_ack_owner': 'issuer_rf_range_ack_owner', 'rf_range_ack_page_mask': 'issuer_rf_range_ack_page_mask',
    'publish_ready': 'issuer_publish_ready', 'frame_retire_ready': 'issuer_frame_retire_ready',
    'input_terminal_ready': 'issuer_input_terminal_ready', 'input_reverse_ready': 'issuer_input_reverse_ready',
}


def replace_once(text, old, new):
    if text.count(old) != 1: raise ValueError('source join changed: ' + old[:100])
    return text.replace(old, new)


def slice_signal(signal, width):
    if '[' in signal: return signal
    return signal + ('[i]' if width == 1 else f'[i*{width} +: {width}]')


def generate(out=OUT, *, base=BASE, model_path=MODEL, top_name='ot_gpu_qwen_hbm_integrated_ranked'):
    base, model_path = Path(base), Path(model_path)
    model = json.loads(model_path.read_text())
    for path, digest in model['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise ValueError('priced install source changed: ' + path)
    abi = json.loads((ROOT/ABI).read_text())
    book = json.loads((base/'ports.json').read_text())
    sv = (base/(top_name+'.sv')).read_text()
    cpp = (base/'pin_driver.cpp').read_text()
    declarations, connections, assignments, get, set_ = [], [], [], [], []
    for name, spec in abi['ports'].items():
        if name == 'clk':
            connections.append('.clk(stream_clk)'); continue
        width, direction = spec['width'], spec['direction']
        target = 'source_owner_' + name
        bits = width * 64
        book['pins'][target] = dict(direction='output' if name in FROM else direction,
                                   bits=bits, count=64, leaf_bits=width, leaf=name, block='source_owner')
        declarations.append(f" {book['pins'][target]['direction']} wire [{bits-1}:0] {target}")
        connections.append(f'.{name}({slice_signal(target,width)})')
        if name in FROM:
            expression = slice_signal(FROM[name], width)
            assignments.append(f' assign {slice_signal(target,width)}={expression};')
        if name in TO:
            dest = TO[name]
            if book['pins'][dest]['direction'] != 'input' or book['pins'][dest]['bits'] != bits:
                raise ValueError('issuer source width/direction changed: ' + dest)
            book['pins'][dest]['direction'] = 'output'
            sv = replace_once(sv, f' input wire [{bits-1}:0] {dest}', f' output wire [{bits-1}:0] {dest}')
            assignments.append(f' assign {slice_signal(dest,width)}={slice_signal(target,width)};')
        getter = f'word(uint32_t(dut.{target}>>32));word(uint32_t(dut.{target}));' if bits == 64 else f'for(int i={(bits+31)//32-1};i>=0;i--)word(dut.{target}[i]);'
        get.append(f' if(name=="{target}"){{{getter}}} else')
        if book['pins'][target]['direction'] == 'input':
            setter = f'dut.{target}=uint64_t(v[0])|(uint64_t(v[1])<<32);' if bits == 64 else f'for(unsigned i=0;i<v.size();i++)dut.{target}[i]=v[i];'
            set_.append(f' if(name=="{target}"){{auto v=unpack(value,{bits});{setter}std::cout<<"OK";}} else')
    # A joined issuer pin is observed, never written by the host driver.
    lines = cpp.splitlines()
    lines = [line for line in lines if not any(f'if(name=="{dest}"){{auto v=' in line for dest in TO.values())]
    cpp = '\n'.join(lines)+'\n'
    cpp = replace_once(cpp, ' throw std::runtime_error("unknown pin");}', '\n'.join(get)+'\n throw std::runtime_error("unknown pin");}')
    cpp = replace_once(cpp, ' throw std::runtime_error("unknown/output pin");}', '\n'.join(set_)+'\n throw std::runtime_error("unknown/output pin");}')
    sv = replace_once(sv, '\n);\nassign assembly_enabled', ',\n'+',\n'.join(declarations)+'\n);\nassign assembly_enabled')
    instance = '\nfor(genvar i=0;i<64;i=i+1)begin:g_source_owner\n'+ '\n'.join(assignments)+'\n ot_gpu_qwen_native_range_owner #(.ENABLE(ENABLE),.SM_INDEX(i)) u_source_owner(\n '+',\n '.join(connections)+'\n );\nend\n'
    sv = replace_once(sv, '\nendmodule', instance+'\nendmodule')
    sv = replace_once(sv, '|| state_rpc_fault)', '|| state_rpc_fault || (|source_owner_fault))')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    top = out/(top_name+'.sv')
    top.write_text(sv); (out/'pin_driver.cpp').write_text(cpp)
    deps = (base/'sources.f').read_text().splitlines()
    if deps[-1] != str((base/(top_name+'.sv')).relative_to(ROOT)):
        raise ValueError('unexpected sourcebook top ordering')
    deps[-1:] = [OWNER, str(top.relative_to(ROOT))]
    (out/'sources.f').write_text('\n'.join(deps)+'\n')
    book['inventory']['source_owner_count'] = 64
    book['source_sha256'][OWNER] = model['source_sha256'][OWNER]
    book['source_sha256'][str(top.relative_to(ROOT))] = hashlib.sha256(top.read_bytes()).hexdigest()
    book['source_sha256'].pop(str((base/(top_name+'.sv')).relative_to(ROOT)))
    book['service_install_model'] = str(model_path.relative_to(ROOT))
    book['unresolved'] += model['pending']
    book['native_scratch_input_namespace'] = 'kv_native_* routed by existing shared_router; SM outputs remain readonly'
    (out/'ports.json').write_text(json.dumps(book,indent=2)+'\n')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    print(generate(parser.parse_args().out))
