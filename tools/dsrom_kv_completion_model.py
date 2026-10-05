"""DS ROM completion wiring price. No inference or memory authority."""
import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def model(packages=None):
    nodes=ast.parse((ROOT/'tools/uarch_model.py').read_text()).body
    dff=next(ast.literal_eval(n.value) for n in nodes if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in n.targets))
    journal=128*(64*(47+28+2+17+1)+7+47+28+2+1)+8
    return dict(schema='dsrom.kv.accepted_completion.v1',status='ESTIMATE_NOT_ADOPTED',
      source='1bfb4b6e855b723c06f8885ee1de4de950158c5a',reuse='Arch C8 journal/backend metadata/mux, no new lifecycle engine',
      MACs_per_cycle=0,packages=packages,new_journal_raw_bits_per_package=journal,
      added_identity_raw_bits=16+47,added_prefetch_reset_quarantine_bits=1,added_mux_reset_quarantine_bits=1,existing_pending_mux_raw_bits=4*2,
      new_SRAM_bytes=0,journal_storage_mapping='existing register arrays, no hardened macro abstract',
      gross_cell_floor_mm2_per_package=(journal+63+8+2)*dff/1e6,
      physical_area_mm2=None,slot_fit=None,route_capacity=None,
      bytes_per_cycle=dict(backend_write_peak=128*32,K_client_peak=4*32),
      boundaries_bits=dict(accepted_identity=47,backend_done_address=128*28,backend_done_tag=128*17,backend_done_valid=128,matched_visibility=128*(47+28+2+1)),
      replicas_per_package=dict(stack_backend=4,journal_ports=128,journal_seats_per_port=64,K_pending_owner=4),
      mux_cost='reuse actual K/B arbiter and C8 write/read ownership mux',fanout=128,
      latency=dict(journal_visibility_edges=1,next_position='actual core done AND queued-write quiet AND mux accepted pending quiet AND all matching ACK journals quiet',
        K_write_II_edges='actual backend ACK roundtrip + pending release edge, not original grant-only II1',
        extra_K_write_latency_per_token_edges=None,full_token_latency=None,readback='next position uses actual tagged backend reads; no memory-peek completion'),
      CKV_credit_successor=dict(extra_raw_bits=1+47+1,own_sectors=9,advance='actual c_wr_done after accepted sector',job_done='held merge completion AND actual own-write drained'),
      reset='C8 journals retain/quarantine accepted debt; reset does not certify retirement',
      mutable_protection_qualified=False,SS60_FF25=False,adopt=False,
      applicability=dict(deepseek_v41_rom='actual reduced system / credit CKV source join',qwen3_8b_rom='none',deepseek_v41_hbm='none',qwen3_8b_hbm='none'))
if __name__=='__main__':print(json.dumps(model(),indent=2))
