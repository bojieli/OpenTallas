#!/usr/bin/env python3
"""Emit a source successor from a guarded HG1 native input; never edit its inputs.

This is opt-in preparation. Its receipt explicitly keeps physical and composed
latency qualification open: the context-to-CTL edge is a changed source endpoint.
"""
import argparse
import gzip
import hashlib
import json
import os
import shlex
import shutil
import re
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def once(text, pattern, fn, label):
    result, count = re.subn(pattern, fn, text, flags=re.M)
    if count != 1:
        raise ValueError(f'{label}: expected one match, got {count}')
    return result


def emit(a):
    root = Path(a.root).resolve()
    native = Path(a.native).resolve()
    parent = Path(a.host_parent).resolve()
    ab_path = Path(a.asbuilt).resolve()
    host_files = Path(a.host_files).resolve()
    guard = Path(a.host_guard).resolve()
    gd = json.loads(guard.read_text())
    # The caller supplies the actual successful guard record, never just a file's existence.
    verdict = str(gd.get('verdict', gd.get('status', ''))).upper()
    if verdict not in ('PASS', 'PASSED', 'OK'):
        raise ValueError(f'host parent guard is not PASS: {verdict!r}')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', a.host_module):
        raise ValueError('invalid host module name')
    source = root/'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_rope_ovl.sv'
    raw = source.read_text()
    match = re.search(r'^module qkd_kvs_emb_rope_ovl\s*\(.*?^endmodule\b', raw, re.M | re.S)
    if not match:
        raise ValueError('existing selected RoPE wrapper missing')
    wrapper = match.group().replace('module qkd_kvs_emb_rope_ovl', 'module qkd_kvs_emb_rope')
    for name in ('i_ovl_users', 'i_kvn_fault', 'i_ovl_adm'):
        wrapper = re.sub(r'^\s*input wire[^\n]*\b'+name+r'\b[^\n]*\n', '', wrapper, flags=re.M)
    wrapper = wrapper.replace('.OVL(1)', '.OVL(0)')
    wrapper = wrapper.replace('.ROPE(1),', '.ROPE(1), .FIX_ROPE_SLOT_GUARD(1),')
    ctx = root/'rtl/qwen_sys/static_embedding_20261014/qkd_kvs_emb_ctx.sv'
    rowtx = root/'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_rope.sv'
    if not all('FIX_ROPE_SLOT_GUARD' in p.read_text() for p in (ctx, rowtx)):
        raise ValueError('off-default73-slot guard source dependency absent')
    for old, new in ((".head_rx_user(i_ovl_users[3:2])", ".head_rx_user(2'd0)"),
                     (".emb_tx_user(i_ovl_users[1:0])", ".emb_tx_user(2'd0)"),
                     ('.kvn_ctx_fault(i_kvn_fault)', ".kvn_ctx_fault(1'b0)"),
                     ('.ovl_adm_done(i_ovl_adm)', ".ovl_adm_done(1'b0)")):
        wrapper = wrapper.replace(old, new)
    if any(x in wrapper for x in ('i_ovl_users', 'i_kvn_fault', 'i_ovl_adm', '.OVL(1)')):
        raise ValueError('incomplete ROPE-only derivation')
    if '.ROPE(1)' not in wrapper or '.ROPE_DELAY(1024)' not in wrapper:
        raise ValueError('existing generator timing contract changed')
    text = gzip.decompress(native.read_bytes()).decode() if native.suffix == '.gz' else native.read_text()
    host = re.search(r'^\s*qkd_host_root_admission_obsx_bo1_c45\s*(?:#\(.*?\))?\s+host\s*\((.*)\);\s*$', text, re.M)
    if not host:
        raise ValueError('actual c45 host selection absent or not one-line native form')
    ports = host.group(1)
    native_params = dict(re.findall(r'\.(\w+)\((\d+)\)', host.group().split(' host ', 1)[0]))
    expected_params = dict(D2D_BOOT_ORDER='1',ENABLE_SERVICE='1',ENABLE_NATIVE='1',ENABLE_TOKEN='1',NL='2',REQUIRE_MISSION_START='1')
    if native_params != expected_params:
        raise ValueError(f'actual native HOST context changed: {native_params!r}')
    # Reuse the actual HOST landing, including its existing witness and valid.
    for port, rhs in (('record_send_kind','n_hrec_rx__pinfix1[1:0]'),
                      ('record_witness_slot','n_hrec_rx__pinfix1[2]'),
                      ('record_rx_v','n_hrec_rx__pinfix1[3]'),
                      ('record_rx','n_hrec_rx__pinfix1[551:4]')):
        if f'.{port}({rhs})' not in ports:
            raise ValueError(f'actual accepted context landing changed: {port}')
    fault = re.search(r'\.link_physical_fault\(([^()]*)\)', ports)
    if not fault:
        raise ValueError('real HOST fault collector input absent')
    old_fault = fault.group(1)
    ports = ports.replace(f'.link_physical_fault({old_fault})', '.link_physical_fault(kv_ctx_host_fault)')
    replacement = f'  {a.host_module} host ({ports});'
    text = text[:host.start()] + '\n'+replacement + text[host.end():]
    text = once(text, r'^(\s*)qkd_kvs_emb\s+kvs_emb\s*\((.*)\);\s*$',
                lambda m: m.group(1)+'qkd_kvs_emb_rope kvs_emb ('+m.group(2)+', .i_head_record(n_hrec_rx__pinfix1[551:0]), .o_ctx_svc(kv_ctx_svc), .emb_fault(kv_ctx_fault));', 'embedding provider')
    ctl = re.search(r'^\s*qkd_kvs_ctl\s+kvs_ctl\s*\((.*)\);\s*$', text, re.M)
    if not ctl:
        raise ValueError('actual CTL selection missing')
    old_svc = re.search(r'\.d2d__svc\(([^()]*)\)', ctl.group(1))
    if not old_svc:
        raise ValueError('actual CTL service input missing')
    new_ctl = ctl.group().replace(old_svc.group(), '.d2d__svc(kv_ctx_svc)')
    text = text[:ctl.start()]+new_ctl+text[ctl.end():]
    text = once(text, r'^(\s*wire \[551:0\] n_hrec_rx__pinfix1;)$',
                lambda m: m.group(1)+'\n  wire [173:0] kv_ctx_svc;\n  wire kv_ctx_fault;\n  wire kv_ctx_host_fault;\n  assign kv_ctx_host_fault = '+old_fault+' | kv_ctx_fault;', 'context declarations')
    out = Path(a.out).resolve()
    out.relative_to(root)  # final artifacts must be portable members of this source event
    out.mkdir(parents=True, exist_ok=False)
    (out/'qkd_kvs_emb_rope.sv').write_text(wrapper+'\n')
    with gzip.GzipFile(filename=str(out/'die_bound_native_ctx_hr4.v.gz'), mode='wb', mtime=0) as f:
        f.write(('// Source successor emitted by tools/die_plan/kv_ctx_source_event.py; source_event.json records inputs and pending physical/model qualification.\n// The original generated-input header below is retained as history.\n'+text).encode())
    ab = json.loads(ab_path.read_text())
    new_sources = []
    for line in host_files.read_text().splitlines():
        for token in shlex.split(line, comments=True):
            if token.startswith('-') or token.startswith('+'):
                raise ValueError('host filelist must contain explicit source paths only')
            f = Path(token)
            if not f.is_absolute(): f = root/f
            new_sources.append(str(f.resolve().relative_to(root)))
    parent_rel = str(parent.relative_to(root))
    new_sources += [parent_rel, str((out/'qkd_kvs_emb_rope.sv').relative_to(root)),
        str(ctx.relative_to(root)), str(rowtx.relative_to(root)),
        'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_ctx_start.sv',
        'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_ctx.sv',
        'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_ctx_native32.sv']
    for rel in new_sources:
        if not (root/rel).is_file(): raise ValueError('missing selected source '+rel)
    old_map = Path(ab['map_file'])
    if not old_map.is_absolute(): old_map = ab_path.parent/old_map
    shutil.copy2(old_map, out/'asbuilt_map_base.json')
    ab['base'] = os.path.relpath(root, out)
    ab['map_file'] = 'asbuilt_map_base.json'
    ab['netlist'] = [str((out/'die_bound_native_ctx_hr4.v.gz').relative_to(root))]
    for key in ('files','prefer'):
        ab[key] = list(dict.fromkeys(ab.get(key, [])+new_sources))
    ab['source_event_note'] = 'Explicit opt-in ctx/HR source successor; new CTL source endpoint requires fresh bind/lane composition; HG1B input untouched.'
    (out/'asbuilt_ctx_hr.json').write_text(json.dumps(ab,indent=2)+'\n')
    (out/'selected_additions.f').write_text('\n'.join(new_sources)+'\n')
    receipt = dict(schema='opentallas.kv.ctx_hr_source_event.v1', opt_in=True, adopted=False,
        inputs={str(p):digest(p) for p in (native,parent,guard,source,ctx,rowtx,ab_path,host_files)}, host_module=a.host_module,native_host_parameters=native_params,
        preserves=['SFM/D2D/KVNC/dcal ABI','native user/token identity','HG1B input files'],
        context=dict(source='actual HOST n_hrec_rx__pinfix1 landing',width=552,live_context_bits=99,authority='actual native59 HEAD_PREP1 accepted c_emb descriptor -> qfd_mu_head_context_tx_lctx32, kind12/layer63/stage0/seg0; final selected programme/window still pending',valid='head[3] is qualified SFM rx_event1: ev&&rv&&!slot_bad&&!crc_bad&&!epoch_abort; head[2] is kind14 witness only and must not gate kind12 context',owner='record[60:0]',position='owner[18:6]',rope_delay=1024,rope_delay_scope='per accepted context, second HBM sweep separation',ovl=0,fix_rope_slot_guard=1,guard_effect='accept real73-slot frame, zero added data cycles',packet_slots_per_request=73,rope_payload_words_per_request=8,payload_bits_per_rope_word=512),
        changed_edges=[dict(edge='HOST context landing -> embedding ctx',class_='new local consumer; use actual delivered HOST age'),dict(edge='embedding o_ctx_svc -> CTL d2d__svc',old_source=old_svc.group(1),class_='changed source endpoint; must regenerate physical lane'),dict(edge='embedding fault -> HOST link_physical_fault',old_source=old_fault,class_='local combinational OR into existing real fault collector; timing unqualified')],
        model=dict(aggregate_added_cycles=None,rule='compose1024 against dependent QC preload window; never free boot credit or blind global sum',physical_qualification='PENDING',latency_qualification='PENDING',compute_macs_added=0,new_context_boundary_bits_per_cycle=552,changed_svc_boundary_bits_per_cycle=174,local_fault_bits=1,context_boundary_note='reuse existing HOST landing where actual binder proves shared delivery; otherwise price new branch',minimum_component_proof='owned by TOK-VERIFY-3'),
        outputs={p.name:digest(p) for p in out.iterdir() if p.is_file()})
    (out/'source_event.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','native','asbuilt','host-parent','host-guard','host-files','host-module','out'):
        p.add_argument('--'+name,required=True)
    emit(p.parse_args())

if __name__=='__main__': main()
