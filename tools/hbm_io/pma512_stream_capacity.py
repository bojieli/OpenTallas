#!/usr/bin/env python3
"""Prebuild streaming alternative model, exact average16/17 rate unchanged."""
import json
if __name__=='__main__':
 print(json.dumps(dict(slot_count_each_direction=16,tx_slot_bits=544,rx_slot_bits=512,
 storage_bits=16*(544+512),output_bits=544+512,max_slot_storage_sinks_per_root=16*544,
 read_mux_slots=2,phase_step_bits=32,clock_ratio_fec_to_phy='16/17',
 proposed_test_latency_fec_edges=13,physical_qualified=False,
 mechanism='write full source words; read one or two immutable occupied slots; synchronized per-slot completion/release toggles observe ownership only; fixed epochs issue every clock edge'),indent=2))
