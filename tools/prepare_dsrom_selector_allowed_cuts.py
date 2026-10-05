"""Cross-bound literal-cell station preparation, not numerical/physical launch."""
import argparse
import json
from pathlib import Path
import prepare_dsrom_balanced_selector_candidate as C
import prepare_dsrom_full_selector_dma_fixture as V
ROOT=V.ROOT;BASE=ROOT/'results/rtl/dsrom_selector_allowed_cut_prepare_20261002'

def prepare(out):
    if out.exists():raise ValueError('fresh allowedcut package required')
    model=json.loads((BASE/'model.json').read_text())
    for p,e in model['source_context_pins'].items():
        if V.sha((BASE/'inputs'/p).read_bytes())!=e['sha256']:raise ValueError('current context pin changed')
    if json.loads((BASE/'inputs/capture_timing_FAIL.json').read_text())['verdict']!='FAIL_ONE_BALANCED_CUT_CONDITIONAL_SS':raise ValueError('capture FAIL context changed')
    out.mkdir(parents=True)
    C.prepare(out/'candidate')
    caller=(out/'candidate/ot_w15_coll_dma_balanced_station_prepare.sv').read_text()
    caller=C.replace(caller,'module ot_w15_coll_dma_balanced_station_prepare #(','module ot_w15_coll_dma_balanced_allowed_cut_prepare #(')
    caller=C.replace(caller,'    parameter integer TK_BALANCED = 0,','    parameter integer TK_CELL_MAP = 0,\n    parameter integer TK_BALANCED = 0,')
    if caller.count('ot_topk_fixed_packet_delay_prepare #(')!=3:raise ValueError('actual three caller cut interfaces changed')
    caller=caller.replace('ot_topk_fixed_packet_delay_prepare #(', 'ot_topk_allowed_cut_packet_prepare #(.CELL_MAP(TK_CELL_MAP),')
    (out/'candidate/ot_w15_coll_dma_balanced_allowed_cut_prepare.sv').write_text(caller)
    (out/'candidate/ot_topk_allowed_cut_packet_prepare.sv').write_bytes((ROOT/'tools/rtl_templates/ot_topk_allowed_cut_packet_prepare.sv').read_bytes())
    (out/'library_sources').mkdir()
    for p in (BASE/'inputs').glob('*.v'):(out/'library_sources'/p.name).write_bytes(p.read_bytes())
    V.write_json(out/'sourceplan.json',dict(model_sha256=V.sha((BASE/'model.json').read_bytes()),default_off=True,
        caller_public_ports_unchanged=True,cut_modules=3,helper_edges=[99,99,28],
        cell_ports_source_checked=True,installed_TT_model_files_functional_provenance_only=True,
        official_SEQ_UDP_and_specify_backend_compatibility_unverified=True,
        no_unreviewed_functional_cell_standins=True,component_545_behavioral_source_gate_retained=True,
        current_capture_FAIL_blocks_parent_admission=True,consumer_deadline=None,
        compile_admitted=False,physical_admitted=False,integrated_parent_runtime_admitted=False,
        source_G0_pending=['Literal-cell primitive backend and complete terminal/present port review','Priced226SETN tie and core35ASR tie/root/reset union','Actual widened terminal sites and parent capture accepteddeadline admission']))
    V.write_json(out/'artifact_manifest.json',{str(p.relative_to(out)):V.sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
    print(json.dumps({'status':'literalallowedcut_source_prepared','compile_admitted':False,'integrated_parent_admitted':False}))
