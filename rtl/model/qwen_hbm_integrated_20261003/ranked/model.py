"""Source-priced rank hierarchy correction; never physical or token credit.

Replay the CURRENT 219-word utility price, using its archived antecedent price
as the original function does. Git blobs make sparse checkout omissions explicit
without copying or changing pinned inputs. No unified baseline is overwritten.
"""
import hashlib, json, math, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'tools'))


def blob(path):
    return subprocess.check_output(['git','show','HEAD:'+path], cwd=ROOT)


def model():
    import w2_nc6_count_utility_closure as current
    price_path='results/uarch/w2_nc6_mutable_protection_20261003/model.json'
    facts_path='results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'
    prior=json.loads(blob(price_path)); rawfacts=blob(facts_path)
    facts=json.loads(rawfacts)['facts']
    old_model,old_D=current.c.model,current.c.D
    try:
        with tempfile.TemporaryDirectory(prefix='qwen-ranked-model-') as td:
            current.c.D=Path(td)
            dst=current.c.D/'inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'
            dst.parent.mkdir(parents=True);dst.write_bytes(rawfacts)
            current.c.model=lambda:prior
            pricing=current.price(current.layout())
    finally:
        current.c.model,current.c.D=old_model,old_D
    book=json.loads((BASE/'ports.json').read_text())
    widths={p:book['pins']['w2_'+p]['leaf_bits'] for p in (
      'c_req_v','c_req_we','c_req_addr','c_req_tag','c_req_gen','c_rsp_rdy','c_wr_done_rdy',
      'c_rsp_v','c_wr_done_v','c_rsp_tag','c_wr_done_tag','c_rsp_gen','c_wr_done_gen','c_req_rdy')}
    mux_bits=sum(widths.values())
    A=lambda cell:facts[cell]['SS']['area_um2']
    N='NAND2x1_ASAP7_75t_R';B='BUFx4_ASAP7_75t_R';I='INVx1_ASAP7_75t_R'
    # Two rank-local128 trees plus the explicit rank2 mux. Every extra tree
    # node is charged. Two-input mux =3 NAND2 plus select inversion budget.
    mux_delta_nodes=128*mux_bits
    select_fanout=mux_bits+256*24
    buffers=math.ceil(select_fanout/8)
    comparator_nands=256*8*4+32
    outer_um2=(3*mux_delta_nodes+comparator_nands)*A(N)+buffers*A(B)+256*A(I)
    inputs=[price_path,facts_path,'tools/uarch_model.py','tools/qwen_hbm_provider_bindings_r17.py',
            'tools/w2_nc6_count_utility_closure.py','tools/w2_nc6_mutable_protection_model.py',
            'rtl/model/qwen_hbm_integrated_20261003/generate.py',
            'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_w2_authority.sv',
            'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_sector_authority.sv',
            'tools/gpu_sys/canonical_qwen_kv_controller.py',
            'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv']
    inputs+= [x for x in json.loads((BASE/'ports.json').read_text())['source_sha256'] if 'w2_nc6_' in x or 'ot_w2_sealed' in x]
    unified=blob('tools/uarch_model.py').decode()
    assert 'HBM_PCS_DIE = 4 * 32' in unified or 'HBM_PCS_DIE = 4*32' in unified
    return dict(schema='qwen.canonical.rank-banks.prospective.v1',
      inventory=dict(rank_count=2,stacks_per_rank=4,PC_per_stack=32,W2_PC_per_rank=128,W2_total=256,NC=6,SM_per_rank=32),
      correction='Prior enclosing128TOTAL is incomplete for adopted2x4stack recipe; inventory already in unified model. No new stacks/bandwidth credit.',
      source_sha256={p:hashlib.sha256(blob(p)).hexdigest() for p in inputs},
      current_W2_price=pricing,
      storage=dict(coded_bits_per_PC=15768,total_coded_bits=256*15768,delta_vs_old_top_bits=128*15768,
        rank_retain='Existing207bit retained grant key20 rankbit13; no extra rank register',added_rank_FF=0,added_SRAM_bytes=0,existing_root_mutable_protection='source root owner/phase/rmw/fault are ordinary registers; no SECDED protection credit, contextual protection unresolved'),
      ports=dict(inner_PC_bits=7,rank_bits=1,outer_reverse_bits=81,inner_reverse_bits=80,
        selected_bus_widths=widths,selected_bits=mux_bits,maximum_bytes_per_PC_edge=32,
        request_bytes_per_edge_256PC_upper_bound=256*32,actual_composed_bandwidth_unknown=True,
        owner46_unchanged=True,PTAG35_unchanged=True,gen4_unchanged=True),
      outer_price=dict(delta_mux_nodes=mux_delta_nodes,mux_NAND2=3*mux_delta_nodes,
        comparator_NAND2_budget=comparator_nands,rank_select_buffer_fanout8_budget=buffers,
        area_body_um2_ASSUMED=outer_um2,area_gross_50pct_um2_ASSUMED=2*outer_um2,
        W2_gross256PC_50pct_mm2_ASSUMED=2*pricing['gross128PC_50pct_mm2_ASSUMED'],
        net_baseline_replacement_unknown=True,clock_and_reset_W2_delta='one additional existing128-PC die inventory; current219word clock/reset replicated, no root flipflop added'),
      routing=dict(outer_rank_and_reverse_min_tracks=82,selected_mux_bits=mux_bits,
        physical_channel_capacity=None,wire_RC=None,loaded_clock_skew=None,slot_fit=None,fulltile_SSFF=None),
      latency=dict(target_period_ps='2500/3',setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        measured_W2_same_client_II_edges=19,extra_logic_levels=2,
        rank_mux_prospective_added_pipeline_edges=[0,1,2],
        no_installed_zero_cycle_claim=True,added_edge_sensitivity_ps=[0,2500/3,5000/3],
        actual_outer_mux_latency_edges=None,CDC_latency_edges=None,full1737_latency=None),
      admission=dict(existing_engine_source_composition=True,new_engine=False,source_qualified_elaboration_allowed=True,
        PnR=False,physical=False,token=False,headline=False),
      refusals=['allocation map rank must equal source key rank','reverse sender rank must equal retained grant key rank',
        'wrong-rank identical inner route must not capture/ACK/advance/release','no PC truncation/hash/restripe'])


if __name__=='__main__':
    text=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(text)
    else:print(text,end='')
