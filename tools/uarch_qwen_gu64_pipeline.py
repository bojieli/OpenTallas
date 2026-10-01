#!/usr/bin/env python3
"""Size the baseline GU64 phase/credit/scale/L2 pipeline before RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import uarch_model as U

ROOT=Path(__file__).resolve().parents[1]


def compose():
    # Same 16 addressed entries survive raw -> multiply -> ready -> sent ->
    # committed. No second output FIFO is hidden behind the unstallable pipe.
    data_bits=16*(16*32+18+16+16+3)
    control_bits=8*(7+1)+3+2*4+7*4
    bits=data_bits+control_bits
    return dict(schema='opentallas.qwen-gu64-pipeline-sizing.v1',
        status='model_before_RTL',full_token=False,adoption=False,
        physical_columns=16,active_AR_columns=1,SM_replicas=32,
        MACs_per_active_column_fast_cycle=128,weight_Bpc=128,
        x_read_bits_per_active_column=1024,L2_AR_payload_Bpc=4,
        L2_physical_gather_bits_per_SM=256,
        FIFO=dict(entries=16,allocation='Two fixed entries per circulating slot',
            states=['free','reserved','raw','multiplying','ready','sent','committed'],
            release='Only matching actual L2 commit releases credits; a ready handshake is insufficient',
            stored_bits=data_bits,control_bits=control_bits,
            footprint_mm2_per_SM=bits*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6,
            replicated_mm2=32*bits*U.DFF_UM2/U.GPU_LOGIC_UTIL/1e6),
        ports=dict(result_write_rows_per_cycle=2,scale_issue_rows_per_cycle=1,
            scale_return_rows_per_cycle=1,L2_send_rows_per_cycle=1,
            L2_commit_rows_per_cycle=1,scale_store='Reservation captures actual broadcast BF16 scale once per row',
            boundary_metadata_bits=18+16+4,
            mux_cost='16-way addressed raw/ready selection and one active-column row-scale multiply; no global weight broadcast'),
        phase=dict(IL=8,counter='Advances on every actual clock, including bubbles',
            acceptance='Step slot must equal actual clock phase; reserve two row credits before first product',
            products_per_leaf=64,slot_release='Both rows committed; no slot/tag reuse while results are outstanding'),
        latency=dict(product_and_64tree_cycles=56,FIFO_capture_cycles=1,
            last_burst_serialization_bound_cycles=16,row_scale_cycles=7,
            ready_register_cycles=1,unstalled_tail_bound_cycles=81,
            existing_model_drain_cycles=89,
            backend='Memory bubbles, ready stalls and L2 commit waits remain actual clock cycles, with no host replacement or hidden wait subtraction',
            pricing='Keep existing89-cycle drain and GU72 extra-token allowance; no gain credited. Replace only from the matched connected measurement'),
        gates=['Actual circulating phase with bubbles','Two-row result bursts under backpressure',
            'RTL BF16 row scaling and global row/epoch tags','Matching actual L2 commits before credit reuse',
            'Composed hub route and contextual SS/FF before adoption'],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['tools/uarch_model.py','tools/uarch_qwen_gu64_pipeline.py',
             'results/uarch/qwen_hbm_connected_20261001/model_before_RTL.json']})


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(compose(),f,indent=2);f.write('\n')
