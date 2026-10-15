#!/usr/bin/env python3
"""Pre-build exact landing-bank layout model; no PHY timing or price changes."""
import json
from pathlib import Path

def bank(j):return (j&31)^((j>>5)&3)
def inverse(b,row):return (row<<5)|(b^(row&3))
assert len({(bank(j),j>>5) for j in range(2048)})==2048
for j in range(2048):assert inverse(bank(j),j>>5)==j
counts=[0]*32
for total in range(1,2049):
    counts[bank(total-1)]+=1
    for b in range(32):
        expected=(total>>5)+int((total&31)>(b^((total>>5)&3)))
        assert counts[b]==expected
        assert (counts[b]==0)==(total<=b)
for row in range(64):
    for group in range(4):
        assert {bank(row*32+group*8+lane) for lane in range(8)}==set(range(group*8,group*8+8))
# For every synchronized physicalbeat and fixed column/row hash, four PC
# groups differing only in ordinalbits[6:5] hit distinct low2 landingbanks.
for beat in range(4):assert len({bank((pcgroup<<5)|beat) for pcgroup in range(4)})==4
r=dict(scope='prebuild static response landing swizzle; qualified=False',
    mapping='bank=ordinal[4:0] XOR {3b0,ordinal[6:5]}; SRAM row=ordinal[10:5]',
    inverse='ordinal={SRAMrow,BANK XOR {3b0,SRAMrow[1:0]}}',
    capacity_exact_vectors=2048,tail_count_checks=2048*32,fixed8lane_group_checks=64*4,
    actual_SRAM_count_delta=0,payload_FIFO_count_delta=0,clock_root_delta=0,
    physical_capacity_delta_bits=0,read_phase_metadata_FF_delta=2,
    response_target_XOR_gates=64,bank_identity_XOR_gates=64,
    extra_read_data_mux_2to1_equivalents=8*256*3,
    read_wiring='Existing4-way8bank group select followed by local4-lane XOR permutation; no new intergroup data crossbar',
    fixed_stream_delivery_sectors_per_cycle=8,stream_first_word_latency_delta_cycles=0,
    response_fairness='Existing per-bank round-robin over32PC responses unchanged',
    full_native_immutable_limits_HBM_cycles={'640':84.7,'2048':134.2},
    physical_slot_fit=False,CTS_qualified=False,full_PF_latency_gate_pending=True,
    note='Swizzle only changes real landing layout, inverse output mux and exact tail count. Original sector identity/tag/epoch stay intact; shared native DRAM controller and all refresh/column timing unchanged.')
out=Path(__file__).resolve().parents[1]/'results/arch/hbm_die_v15/prefetch_swizzle';out.mkdir(parents=True,exist_ok=True)
(out/'prebuild_model.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
