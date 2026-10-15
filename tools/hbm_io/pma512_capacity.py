#!/usr/bin/env python3
"""Exact capacity/latency model for coded-PMA gearbox; no physical timing claim."""
from fractions import Fraction
import json

def model(phy_hz=1_200_000_000):
    ratio=Fraction(512,544)
    net=487*ratio
    return dict(physical_bits_per_edge=512,coded_bits_per_fec_edge=544,
                coded_words_per_block=16,physical_words_per_block=17,block_bits=8704,
                fec_to_phy_frequency=str(ratio),fec_hz_at_declared_phy=float(phy_hz*ratio),
                phy_hz=phy_hz,user487_bits_per_phy_edge=str(net),
                user487_gbps=float(net*phy_hz/1e9),
                endpoint613_frames_per_phy_edge=str(net/613),
                simultaneous_register_bank_storage_bits=2*4*8704,
                registered_data_output_bits=512+544,bank_clock_roots=8,
                sinks_per_bank_root=8704,read_mux_fanin_tx=4*17,read_mux_fanin_rx=4*16,
                observed_fec_to_window_age_fec_edges=151,previous_same_clock_age_fec_edges=102,
                adapter_added_age_fec_edges=49,
                observed_age_ns=float(Fraction(151*10**9,phy_hz)/ratio),
                adapter_added_age_ns=float(Fraction(49*10**9,phy_hz)/ratio),
                physical_qualification=False,whole_link_price_qualification=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
