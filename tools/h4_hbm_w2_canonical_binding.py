#!/usr/bin/env python3
"""Wire the actual full219 controller, not the older raw/codec fixture.

No compiler/run is launched. Source qualification stays with Nash/Hubble and
Russell's one fixture. The actual system owns all fences and visibility events.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENDPOINT='rtl/experimental/hbm_canonical_transport_20261003/ot_gpu_w2_canonical_endpoint.sv'
FILES={
    'primary':'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv',
    'secondary':'rtl/experimental/w2_nc6_secondary_20261003/ot_w2_nc6_coded_secondary.sv',
    'codec':'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv',
    'helper':'rtl/experimental/w2_nc6_correction_control_20261003/ot_w2_nc6_correction_control.sv',
}
MODULES={'primary':'ot_w2_nc6_protected_completion','secondary':'ot_w2_nc6_coded_secondary',
         'codec':'ot_w2_sealed_secded72','helper':'ot_w2_nc6_correction_control'}
MODEL='results/uarch/w2_nc6_count_utility_closure_20261003/model.json'


def ports(source):
    header=source.split(')(\n',1)[1].split(');',1)[0]
    out=[]
    for m in re.finditer(r'\b(?:input|output)\s+(?:wire|reg)\s*(?:\[[^]]+\])?\s*([^\n]*?)(?=\binput|\boutput|\n|$)',header):
        out.extend(n.strip() for n in m.group(1).rstrip(',').split(',') if n.strip())
    return out


def validate_wiring(primary, endpoint):
    """Source-port enrollment, deliberately not HDL syntax/runtime proof."""
    actual=ports(primary)
    selected=endpoint.split(' controller(',1)[1].split(');',1)[0]
    connections=dict(re.findall(r'\.(\w+)\(([^()]*)\)',selected))
    if set(connections)!=set(actual) or any(connections[n]!=n for n in actual):
        raise ValueError('actual full primary ports must connect without stubs or truncation')
    if 'OPT_EXACT=0' not in endpoint or 'ot_w2_nc6_protected_completion #' not in endpoint:
        raise ValueError('default-off full219 source required')
    for field in ('p_wr_done_ready','reverse_fenced','repair_busy','provider_fenced','reset_fenced'):
        if connections.get(field)!=field:raise ValueError('real authority required '+field)
    if 'ot_hdc_qwen_pc_exact_completion' in endpoint:
        raise ValueError('raw controller cannot substitute for full219')
    return actual


def binding(primary_root, helper_root):
    primary_root=Path(primary_root);helper_root=Path(helper_root)
    paths={k:(helper_root if k=='helper' else primary_root)/v for k,v in FILES.items()}
    raw={k:p.read_bytes() for k,p in paths.items()}
    for k,b in raw.items():
        if ('module '+MODULES[k]).encode() not in b:raise ValueError('actual module '+k)
    actual=validate_wiring(raw['primary'].decode(),(ROOT/ENDPOINT).read_text())
    if 'localparam integer NW=182' not in raw['primary'].decode():raise ValueError('primary182 required')
    if '[0:218]' not in raw['primary'].decode():raise ValueError('combined219 current truth required')
    if re.search(rb'always_ff|always\s*@\s*\([^)]*(?:posedge|negedge)',raw['helper']):
        raise ValueError('helper must reuse actual context, not add state')
    model=json.loads((primary_root/MODEL).read_text())
    # Reject a concurrent generator rewrite rather than silently consuming half
    # of an evolving source enrollment. Caller may select a later exact snapshot.
    for k,p in paths.items():
        if p.read_bytes()!=raw[k]:raise ValueError('source changed during binding '+k)
    sources=[dict(role=k,path=str(paths[k]),sha256=hashlib.sha256(raw[k]).hexdigest())
             for k in ('codec','helper','secondary','primary')]
    sources.append(dict(role='canonical_endpoint',path=str(ROOT/ENDPOINT),
                        sha256=hashlib.sha256((ROOT/ENDPOINT).read_bytes()).hexdigest()))
    return dict(schema='opentallas.W2.canonical-full219-source-binding.v1',
        sources=sources,primary_ports=actual,
        selection=dict(NC=6,MAX_OUT=16,AW=34,CTAG32=32,GEN4=4,PTAG35=35,DW=256,
                       OPT_EXACT_default=0,PC_ID_width=7,PC_ID='actual mapper-selected PC within DIE/STACK'),
        owner46='PC_ID7 || scoped_PT​AG35 || source_generation4'.replace('\u200b',''),
        transport=dict(address_unit='32-byte sector, actual home translation upstream',
                       source_tag_echo='full35 plus separate4; never truncate to16',
                       physical16_ticket='requires separately priced reversible live source-owner mapping',
                       requests='all six actual clients; client5 remains KV',
                       response='full tag32/gen4 returned to original client',
                       write_done='held provider terminal until p_wr_done_ready; not request acceptance',
                       namespace='DIE/STACK; external route scope retained'),
        authorities=dict(provider_fenced='actual provider accepted/queued/inflight/held-return debt',
                         reverse_fenced='actual consumer/reverse/allcopies tracker, not offer snapshot drain',
                         reset_fenced='actual cross-domain reset/drain controller',
                         repair_busy='actual secondary/helper aggregate to system admission/rearm owner',
                         p_wr_done_ready='actual full primary receiver to held backend write-completion source'),
        callee_model=model,callee_model_source_sha256=hashlib.sha256((primary_root/MODEL).read_bytes()).hexdigest(),
        sizing=dict(codewords=219,protected_bits=15768,primary_CW=182,secondary_CW=37,
                    added_endpoint_FF=0,added_endpoint_FF_reason='port wires, constant PC/client concatenations and combinational hold OR only',
                    hold_OR_gate_eq_ASSUMED=3,hold_OR_cell_um2_ASSUMED=3*.0648,
                    hold_OR_128PC_50pct_mm2_ASSUMED=128*3*.0648/500000,
                    added_owner_boundary_bits=13*46,
                    actual_hold_OR_cell_and_loaded_fanout=None,
                    correction_boundary_bits=1232,old_boundary_bits_not_selected=656,
                    loaded_read_mux_fanout_closed=False,
                    provider_request_boundary_bits=332,provider_read_boundary_bits=297,
                    provider_write_done_boundary_bits=41,MACs_per_cycle=0,
                    provider_sector_bytes_per_accept=32,
                    routing_capacity=None,slot_fit=None,whole_token_latency_ns=None),
        calendar=dict(cost_key='W2.NC6.full219',replacement_only=True,
                      source_same_client_II_edges=19,different_client_II_edges_prospective=10,
                      measured=False,leaf_8_8_9_not_full_controller_supply=True,
                      exceptional_CAP4_FIX4_min_edges=8,
                      eligible_service_upper_bound=None,
                      ready_backpressure='real downstream holds extend service; no fabricated upper bound'),
        status='WIRED_SOURCE_FUNCTIONAL_QUALIFICATION_PENDING',
        full_controller_runtime_pass=False,physical_admission=False,compile_launched=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--primary-root',type=Path,required=True)
    ap.add_argument('--helper-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();report=binding(a.primary_root,a.helper_root)
    with a.out.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
