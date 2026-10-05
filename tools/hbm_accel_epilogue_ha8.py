#!/usr/bin/env python3
"""Forward HA3 clock successors to the actual HA8 installer, without editing it.

This selects the native tensor-core engine, never the guarded RF/SIMD service.
The enclosing installer retains its allocator, pin packing, clock and lifecycle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BOOK = 'rtl/model/qwen_hbm_integrated_20261003/ranked/ports.json'
LIST = 'rtl/model/qwen_hbm_integrated_20261003/ranked/sources.f'
ENGINE = 'rtl/gpu/ot_gpu_sm_q.sv'
ENGINE_SHA = '8e0aa477664f385a8536b1610c508fdd637bb020377adf744671c960d984b06f'
SUCCESSOR = 'rtl/hbm_accel/epilogue/ot_hbm_accel_sm_q.sv'
CLOCK_SOURCES = ('rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv',
                 'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv')
ENGINE_DEPENDENCIES = (
    'rtl/gpu/ot_gpu_issue.sv', 'rtl/gpu/ot_gpu_bulk_copy.sv',
    'rtl/gpu/ot_gpu_xstore.sv', 'rtl/gpu/ot_gpu_tc_col.sv',
    'rtl/gpu/ot_gpu_tree.sv', 'rtl/gpu/ot_gpu_stack.sv', 'rtl/gpu/ot_gpu_fadd.sv',
    'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
    'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_prefix.sv',
    'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
    'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_delay.sv',
    'rtl/hdc/ot_hdc_sfu.sv',
    'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
    'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def original_engine(successor):
    """The only three permitted changes; equality covers arithmetic, memory and ports."""
    substitutions = (
        ('module ot_hbm_accel_sm_q #(\n    parameter integer ENABLE_HA3 = 0,\n',
         'module ot_gpu_sm_q #(\n'),
        ('    ot_hbm_accel_bulk_copy #(.ENABLE(ENABLE_HA3), ', '    ot_gpu_bulk_copy #('),
        ('    ot_hbm_accel_issue #(.ENABLE(ENABLE_HA3), ', '    ot_gpu_issue #('))
    for a, b in substitutions:
        if successor.count(a) != 1:
            raise ValueError('HA3 engine source selection differs: '+a)
        successor = successor.replace(a, b, 1)
    return successor


def select_native_engine(*, enable_ha3_clock_lookahead=False, installer_root=ROOT):
    """Consume in the HA8 native-engine instance emitter; every original port is kept.

    The returned module/parameter selection is an explicit experimental opt-in.
    It is not the guarded SM's module replacement or a numerical fusion flag.
    """
    parent = Path(installer_root)
    if sha(parent / ENGINE) != ENGINE_SHA:
        raise ValueError('Actual HA8 native-engine source pin changed')
    if not enable_ha3_clock_lookahead:
        return dict(module='ot_gpu_sm_q', parameters={}, sources=[str(parent/ENGINE)],
                    source_sha256={ENGINE:ENGINE_SHA}, adopted=False)
    new = (ROOT / SUCCESSOR).read_text()
    if original_engine(new).encode() != (parent / ENGINE).read_bytes():
        raise ValueError('HA3 sibling changes more than engine name and clock children')
    paths = [SUCCESSOR, *CLOCK_SOURCES]
    # Off generate branches retain the actual original implementations.
    originals = ['rtl/gpu/ot_gpu_issue.sv', 'rtl/gpu/ot_gpu_bulk_copy.sv']
    for p in originals:
        if (parent/p).read_bytes() != (ROOT/p).read_bytes():
            raise ValueError('HA8 clock child differs from the 72-case source: '+p)
    return dict(module='ot_hbm_accel_sm_q', parameters={'ENABLE_HA3':1},
        sources=[str(ROOT/p) for p in paths]+[str(parent/p) for p in originals],
        source_sha256={p:sha(ROOT/p) for p in paths+originals},
        original_engine_sha256=ENGINE_SHA, adopted=False,
        port_contract='Exact original ot_gpu_sm_q ports, sizes and directions; enclosing shared clock',
        numerical_fusion=False)


def forward_installer(*, installer_root, enable_ha3_clock_lookahead=False):
    """Return actual installer sources and verified hashes plus the engine selection.

    No clock ticks, owner/grant synthesis, private memory, or pin-direction edits.
    Missing native-engine installation stays explicit; mere dependency inclusion
    cannot turn this into an installed real-SM latency result.
    """
    parent = Path(installer_root).resolve()
    book = json.loads((parent/BOOK).read_text())
    inputs = (parent/LIST).read_text().splitlines()
    paths = list(dict.fromkeys(p.strip() for p in inputs if p.strip()))
    pins = book['source_sha256']
    actual = {p:sha(parent/p) for p in pins}
    if actual != pins:
        raise ValueError('Actual HA8 installer sourcebook hash mismatch')
    if set(paths) - set(pins):
        raise ValueError('Actual HA8 installer source list has unpinned dependencies')
    selected = select_native_engine(enable_ha3_clock_lookahead=enable_ha3_clock_lookahead,
                                    installer_root=parent)
    # An SM engine's scalar pins cannot be substituted for SIMD RF service pins.
    engine_callers = [p for p in paths if re.search(
        r'\bot_gpu_sm_q\s*#\s*\([^;]+\)\s+\w+\s*\(', (parent/p).read_text())]
    # Reuse the actual HA8 definitions of shared arithmetic/macros. Refuse
    # differing definitions rather than silently mix a second FPU/memory version.
    dependencies, shared = [], {}
    for dep in ENGINE_DEPENDENCIES:
        existing = [p for p in paths if Path(p).name == Path(dep).name]
        if len(existing) > 1:
            raise ValueError('Ambiguous HA8 native dependency: '+dep)
        if existing:
            p = existing[0]
            if (parent/p).read_bytes() != (parent/dep).read_bytes():
                raise ValueError('HA8 native dependency differs from shared definition: '+dep)
            shared[dep] = p
        else:
            p = dep
            dependencies.append(str(parent/p))
    candidate = list(dict.fromkeys([str(parent/p) for p in inputs]
                    + selected['sources'] + dependencies))
    # Strip canonical duplicate paths for dependencies already supplied by HA8.
    candidate = [p for p in candidate if p not in {str(parent/d) for d in shared}]
    return dict(schema='opentallas.hbm_accel.ha3.ha8_forward.v1',
        installer_root=str(parent), installer_top=book['top'],
        installer_source_list=str(parent/LIST), installer_source_sha256=actual,
        installer_book_sha256=sha(parent/BOOK), installer_list_sha256=sha(parent/LIST),
        # Forward the real list exactly, including its historical duplicates.
        installer_sources=[str(parent/p) for p in inputs],
        candidate_sources=candidate,
        candidate_source_sha256={p:sha(p) for p in candidate},
        reused_installer_definitions=shared,
        selected_native_engine=selected, original_engine_callers=engine_callers,
        native_engine_installed=bool(engine_callers),
        status='READY_FOR_NATIVE_ENGINE_EMITTER' if not engine_callers else 'CALLER_SELECTION_REQUIRED',
        pending='HA8 native engine emitter must use selected module and parameter on its actual same-clock instance; '
                'current ranked guarded-SM RF/SIMD service is not the native tensor core',
        physical_qualified=False, token_qualified=False, measured_real_sm_cycles=None,
        numerical_fusion=False, adopted=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--installer-root', type=Path, required=True)
    ap.add_argument('--enable-ha3-clock-lookahead', action='store_true')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    record = forward_installer(installer_root=a.installer_root,
                               enable_ha3_clock_lookahead=a.enable_ha3_clock_lookahead)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x') as f:
        json.dump(record, f, indent=2)
        f.write('\n')
