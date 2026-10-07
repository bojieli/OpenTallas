#!/usr/bin/env python3
"""Prepare native caller sources + literal child map; never dispatch or replay ABC."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--synth-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--caller-only',action='store_true',
                    help='prepare the new caller independently while child ABC remains live')
    a=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    terminal=a.synth_root/'result.json'
    if not terminal.is_file() and not a.caller_only:
        raise SystemExit('Live child map has no terminal receipt; preserve ABC. Native caller sources are prepared independently.')
    gate=json.loads((root/'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r2/result.json').read_text())
    assert gate['verdict']=='PASS_CHANGED_HA2_FULL16_GOLDEN'
    for f,h in gate['source_sha256'].items():
        assert sha(root/f)==h,f
    mapped=None;text=None
    if not a.caller_only:
        r=json.loads(terminal.read_text())
        assert r['exit']==0 and r['synthesis_only']
        assert r['shape']==dict(CUTS=1,NC=8,NOG=8,PFMAX=384,LANES=16,BF16=1,INJ=2,NPT=8,LAT=7,SLOTREG=1)
        for f,h in r['sources_sha256'].items():
            assert sha(root/f)==h==gate['source_sha256'][f],f
        mapped,=a.synth_root.glob('work/orfs/results/asap7/*/base/1_2_yosys.v')
        assert sha(mapped)==r['artifacts'][str(mapped.relative_to(a.synth_root))]['sha256']
        text=mapped.read_text()
        text,n=re.subn(r'(?m)^(module\s+)ot_ha2_tu_owner_adapter_item9_cuts(?=\s*\()',
                       r'\1ot_hbm_item9_ha2_cached_map',text)
        assert n==1,'exact top rename only; never reoptimise child'
    assert a.out.is_absolute() and not a.out.exists()
    a.out.mkdir(parents=True)
    if text is not None:
        (a.out/'cached_adapter.v').write_text(text)
    # A blackbox is ONLY for the independent caller synthesis stage. Physical
    # link must use cached_adapter.v, never this declaration as a macro view.
    (a.out/'child_for_caller_synth_only.v').write_text(
        '(* blackbox *) module ot_hbm_item9_ha2_cached_map(input clk,rst_n,active,arm,'
        'input[7:0]rank,input[15:0]pf,input[1:0]h_v,input[1087:0]h_d,'
        'input[7:0]p_v,input[4359:0]p_flit,output r_v,output[15:0]r_m,'
        'output[511:0]r_d,output dupe,issue_o,quiet);endmodule\n')
    sources=['rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv',
             'rtl/hbm_accel/ha2_ar/ot_ha2_parent_quiet_prims.sv',
             'physical/hbm_die_abstracts_20261006/integration/ot_hbm_item9_ha2_native_boundary_context.sv']
    (a.out/'caller_sources.f').write_text('\n'.join(str(root/f) for f in sources)+'\n'+str(a.out/'child_for_caller_synth_only.v')+'\n')
    for name in ['ha2_native_boundary_internal.sdc','ha2_native_boundary_pins.tcl']:
        shutil.copy2(root/'physical/hbm_die_abstracts_20261006/integration'/name,a.out/name)
    rec=dict(phase='NATIVE_CALLER_SOURCE_READY_NOT_ADMITTED',
             top='ot_hbm_item9_ha2_native_boundary_context',ENABLE=1,
             evidence_class='CONDITIONAL_NATIVE_CALLER_CONTEXT',
             child_original_map_sha256=sha(mapped) if mapped else None,
             child_link_map_sha256=sha(a.out/'cached_adapter.v') if mapped else None,
             child_map_pending=mapped is None,
             child_edit='one module-header rename; body byte-identical',
             caller_source_sha256={f:sha(root/f) for f in sources},
             parent_source='rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_item9_owner.sv',
             parent_source_sha256=sha(root/'rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_item9_owner.sv'),
             model='hbm_item9_ha2_native_boundary_context_model',
             caller_synthesis_required=True,child_synthesis_replay=False,
             instructions=['Synthesise caller_sources.f with ENABLE=1; preserve attributes through all intermediate exports.',
                           'After caller mapping, link its mapped Verilog with cached_adapter.v, not the synthesis-only blackbox.',
                           'Use measured total cell/macro/PG/CTS inventory to check the finite r16g slot; resize explicitly if it fails 55% final cap.',
                           'Kant owns actual memory inventory and fresh E1 CPU/RAM/disk pre/post unchanged admission; no guessed inherited64GiB.',
                           'Route conditional internal paths with propagated CTS and named-corner SPEF; report external unconstrained I/O/reset.',
                           'Extract core-clock hub read-mux/dispatch-to-child and child-to-dqo/qr paths and SS/FF caps from the resulting caller archive.'],
             source_clock_qualified=False,external_IO_qualified=False,
             numerical_gate_reused=str(root/'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r2/result.json'),
             new_edges=0,physical_signoff=False,adopted=False)
    (a.out/'packet.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))


if __name__=='__main__':
    main()
