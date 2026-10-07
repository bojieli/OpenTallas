#!/usr/bin/env python3
"""Prepare one full protected numerical frontend against retained 5.050 leaves.

This prepares commands only. The genuine numerical top/provider must already
exist; the owner launches through Kant's fresh unchanged host guard. Neither
the retained authority nor the live PVE1 parent is modified or rebuilt.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess

from emit import emit

# Actual owner protected implementation, separate from the raw source gate.
# R6/R7/R8 unconditional held-output reload is invalid.
OWNER_CDC_LEAF_CANDIDATE = dict(
    commit='c8ba43664', revision='r9', RSEL=1,
    source_sha256='67d30ee4c889cad1bc65eaf37e93fc35152eab2de4ffedb9c5c580d832fa71a8',
    held_output='per-group kept valid copy; capture only when !vg || l_pop',
    invalid_route_families=['r6', 'r7', 'r8'],
    protected_source_commit='3f3c2b790', protected_source_main='23c3731e6',
    protected_read='full504 r9_read.column[0..17] -> existing u_d0.EN=advance; read_select_fault -> rd_fault',
    protected_source_agreement=True, physical_qualified=False)


def prepare(job, source, numerical_top, provider, output,
            consumer_prefix=None, backing_member=None, backend_dependencies=(),
            cdc_consumer_join=False, landing_rsel=0, parallel_transport=False):
    if not numerical_top.is_file() or not provider.is_file():
        raise ValueError('genuine owner numerical top and provider source required')
    module = re.search(r'^module\s+(\w+)', numerical_top.read_text(), re.M)
    if not module:
        raise ValueError('owner numerical top has no literal module declaration')
    top = module[1]
    mk = (job/'die/Vdie.mk').read_text()
    runtime = Path(re.search(r'^VERILATOR_ROOT\s*=\s*(\S+)', mk, re.M)[1])
    verilator = runtime.parent.parent/'bin/verilator'
    version = subprocess.check_output([str(verilator), '--version'], text=True).strip()
    if not version.startswith('Verilator 5.050 '):
        raise ValueError('retained engine runtime must be canonical 5.050')
    text = (job/'top.args.f').read_text()
    paths = []
    replacement = {
        'ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv': numerical_top,
        'ot_hbm_r14_stream_pc.sv': source/'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv',
        'ot_hbm_r14_stream_stack.sv': source/'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv',
    }
    for line in text.splitlines():
        if line.startswith('--top-module'):
            break
        path = Path(line)
        if path.name == 'ot_qwen_hbm_stream4_tagged.sv':
            continue
        path = replacement.get(path.name, path)
        paths.append(path if path.is_absolute() else job/'die'/path)
    exp = source/'rtl/experimental/qwen_rom_combined_p0_20261005'
    deps = [source/p for p in (
        'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/lib/ot_reset_sync.sv',
        'rtl/hdc/kv/ot_qwen_s4_checked_state.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_pc.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_cdc_consumer_join.sv',
        'rtl/hdc/kv/ot_qwen_s4_protected_control.sv',
        'rtl/hdc/kv/ot_qwen_s4_packet_link.sv',
        'rtl/hdc/kv/ot_qwen_s4_stack_transport.sv',
        'rtl/hdc/kv/ot_qwen_s4_transport_context.sv')]
    deps += [exp/'ot_qwen_p0_full_consumer_exports.sv',
             exp/'ot_qwen_p0_full_transport_join.sv', provider]
    # Owner CDC handoff may have a different literal hierarchy/backing. Use
    # its actual source files and explicit access names, not an ABI alias or
    # the completed numerical transport model in place of the CDC element.
    deps += list(backend_dependencies)
    paths = list(dict.fromkeys(deps+paths))
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    hierarchy = []
    for line in text.splitlines():
        if line.startswith('--hierarchical-block'):
            hierarchy += shlex.split(line)
    params = json.loads((job/'selection.json').read_text())['parameters']['die']
    params = [v for v in params if not v.startswith('-GHBM_PULLIN=')]
    params += ['-GHBM_PULLIN=0', '-GPROTECTED_STREAM4=1']
    if cdc_consumer_join:
        params = [v for v in params if not v.startswith('-GCDC_CONSUMER_JOIN=')]
        params += ['-GCDC_CONSUMER_JOIN=1']
    if landing_rsel:
        if not cdc_consumer_join:
            raise ValueError('selected protected r9 requires the actual CDC consumer join')
        ring = (source/'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv').read_text()
        if 'READ_RSEL' not in ring or 'begin:r9_read' not in ring or 'read_select_fault' not in ring:
            raise ValueError('actual owner protected READ_RSEL implementation missing')
        params = [v for v in params if not v.startswith('-GLANDING_RSEL=')]
        params += ['-GLANDING_RSEL=1']
    if parallel_transport:
        if not cdc_consumer_join or landing_rsel != 1:
            raise ValueError('parallel protected P0 requires explicit corrected owner RSEL1 join')
        params = [v for v in params if not v.startswith('-GSAME_CYCLE_GO=')]
        params += ['-GSAME_CYCLE_GO=1']  # early-go: GO accepted with its own descriptor
        parallel_leaf = source/'rtl/hdc/kv/ot_qwen_s4_parallel_protected_pc.sv'
        if not parallel_leaf.is_file():
            raise FileNotFoundError('actual owner sector-protected RSEL1 leaf required: '+str(parallel_leaf))
        paths = list(dict.fromkeys([*paths, parallel_leaf,
            exp/'ot_qwen_p0_parallel_bank.sv', exp/'ot_qwen_p0_parallel_transport_context.sv']))
        params = [v for v in params if not v.startswith('-GPARALLEL_TRANSPORT=')]
        params += ['-GPARALLEL_TRANSPORT=1']
    # The authority's literal public macro and hierarchy directives are retained.
    configs = [job/'reuse/gen/public.vlt', job/'reuse/gen/hier.vlt']
    for path in configs:
        if not path.is_file():
            raise FileNotFoundError(path)
    old_link = json.loads((job/'link.command.json').read_text())
    group = old_link[old_link.index('-Wl,--start-group')+1:old_link.index('-Wl,--end-group')]
    retained = [Path(p) for p in group if p != str(job/'die/Vdie__ALL.a')]
    # The authoritative link compiled these exact 5.050 runtime sources
    # directly; it retained no separate runtime .o files. Keep that setup.
    runtime_sources = [runtime/'include'/name for name in
                       ('verilated.cpp', 'verilated_threads.cpp', 'verilated_dpi.cpp')]
    for path in retained+runtime_sources:
        if not path.is_file():
            raise FileNotFoundError(path)
    output.mkdir(parents=True, exist_ok=False)
    emit(job/'qwen_plain_ar_fulltoken_guarded_v2.cpp', output/'host', top, True)
    obj = output/'die'
    frontend = [str(verilator), '--cc', '-O3', '--top-module', top,
                '--prefix', 'Vdie', '--mod-prefix', 'Vdie', '--threads', '1',
                '--Mdir', str(obj), '-Wno-fatal', '-Wno-TIMESCALEMOD',
                '-I/srv/opentallas-scratch/claude/fullbw-hbm/src4/rtl/hdc',
                '-I'+str(source/'rtl/hdc/kv'),  # ot_qwen_kv_map_m.svh (KV_MAP option M, default off)
                *hierarchy, *params, *map(str, paths+configs)]
    # Compile this top only. VM_HIER_LIBS is supplied on make's command line,
    # pointing to completed archives, so no retained leaf Makefile is invoked.
    leaves = [p for p in retained if p.name.startswith('libot_')]
    compile_top = ['make', '-C', str(obj), '-f', 'Vdie.mk', 'Vdie__ALL.a',
                   'VM_HIER_LIBS='+' '.join(map(str, leaves))]
    host_index = old_link.index(str(job/'qwen_plain_ar_fulltoken_guarded_v2.cpp'))
    flags = old_link[:host_index]
    flags = [('-I'+str(obj)) if f == '-I'+str(job/'die') else f for f in flags]
    flags += ['-I'+str(output/'host')]
    link = [*flags, str(output/'host/fulltoken.cpp'), '-Wl,--start-group',
            str(obj/'Vdie__ALL.a'), *map(str, retained), '-Wl,--end-group',
            *map(str, runtime_sources), '-o', str(output/'fulltoken')]
    runtime_command = json.loads((job/'runtime.command.json').read_text())
    runtime_command[0] = str(output/'fulltoken')
    runtime_command[3] = str(output/'run')
    record = dict(status='PREPARED_ONLY_NOT_DISPATCHED', top=top,
                  canonical_runtime=str(runtime), version=version,
                  frontend=frontend, compile_top=compile_top, link=link,
                  runtime=runtime_command,
                  consumer_prefix=consumer_prefix or top+'__DOT__u_join__DOT__u_consumer__DOT__',
                  backing_member=backing_member or top+'__DOT__u_numeric__DOT__mem',
                  backend_dependencies=list(map(str, backend_dependencies)),
                  parallel_transport=bool(parallel_transport),
                  transport_rate_scope=('parallel protected source candidate; exact gate/physical context pending' if parallel_transport else 'serialized protected numerical vehicle only; publish no P0 rate'),
                  cdc_consumer_join=bool(cdc_consumer_join),
                  landing_rsel=int(landing_rsel),
                  cdc_binding_scope=('Implemented protected full504 r9 read with actual warm/ACK ports; parent physical route unqualified'
                                     if landing_rsel else 'Descartes protected port adapter only; raw RSEL CDC and protected parent route unqualified'),
                  owner_cdc_leaf_candidate=OWNER_CDC_LEAF_CANDIDATE if cdc_consumer_join else None,
                  access_generation='Run access.py on genuine generated header with exact consumer-prefix/backing-member before driver TU',
                  reused_archives=list(map(str, retained)),
                  matching_runtime_sources=list(map(str, runtime_sources)),
                  full_token_run=False, physical_qualified=False,
                  required_admission='Kant fresh E2 load<128, actual CPU/RAM/disk fit, unchanged admit.sh; one frontend then one final smoke')
    (output/'prepared.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authority-job', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--numerical-top', type=Path, required=True)
    p.add_argument('--provider', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--consumer-prefix', help='Exact owner top consumer hierarchy from generated header')
    p.add_argument('--backing-member', help='Exact owner full36 backing member; no MEM1 substitution')
    p.add_argument('--backend-dependency', type=Path, action='append', default=[],
                   help='Actual additional owner source (e.g. qualified CDC element); preparation only')
    p.add_argument('--cdc-consumer-join', action='store_true',
                   help='Prepare explicit protected port adapter option; does not qualify raw owner CDC')
    p.add_argument('--landing-rsel', type=int, choices=[0, 1], default=0,
                   help='Actual implemented protected full504 owner r9 read option; physical qualification separate')
    p.add_argument('--parallel-transport', action='store_true', help='Actual32 independent protectedPC return lanes/stack; no full build before mechanism gate')
    a = p.parse_args()
    r = prepare(a.authority_job, a.source_root, a.numerical_top, a.provider, a.output,
                a.consumer_prefix, a.backing_member, a.backend_dependency, a.cdc_consumer_join, a.landing_rsel, a.parallel_transport)
    print(json.dumps(dict(status=r['status'], top=r['top'], version=r['version'])))
