#!/usr/bin/env python3
"""Actual PHY-only 32-PC request mux cost; no on-chip scheduling arbitration."""
import json

def model():
 return dict(schema='opentallas.hbm-svc-phy-mux.v1',pcs=32,request_bits_per_pc=340,
   state_bits=96,mux_bits_upper_bound=32*340,arbitration='round robin only at HBM PHY boundary; held owner until actual acceptance',
   read_response='direct only to prefetch boundary',write_completion='direct only to WB boundary',
   added_request_latency_cycles=0,clock_domain='hbm1024ps',macs_per_cycle=0,
   routing_tracks_needed=32*340,routing_capacity=None,slot_fit=None,physical_closed=False,adopted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
