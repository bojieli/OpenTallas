#!/usr/bin/env python3
"""Model extension for source-owned credit/session composition, before gate."""
import json
from hbm_collective_native_link_model import model as storage_model
from hbm_collective_link_session_model import model as session_model


def model():
    return {
        'status': 'NATIVE_COMPOSITION_NOT_ADOPTED',
        'storage_and_data_paths': storage_model(),
        'session': session_model(),
        'session_provider_stored_bits': 11102,
        'provider_count': 1,
        'session_scope': 'One source coordinator plus two local agents managing all8 ports only when their actual debt/quiet/initialACK fences are ANDed. Physical peer topology may require additional independently priced sessions.',
        'credit_pair_encoded_plus_rails_bits': 436,
        'source_debt_and_initial_ACK_observer_bits': 148,
        'receiver_initial_ACK_observer_bits': 74,
        'eight_pair_credit_and_observer_bits': 8*(436+148+74),
        'provider_plus_eight_pair_credit_observer_bits': 11102+8*(436+148+74),
        'accounting_scope': 'Eight source/receiver protocol pairs; a full duplex8port native has8local sources and8local receivers whose peers reside outside the TU. Count every real remote replica in die/network composition. Management provider includes4CDC crossings; grant/ACK data-session transports are additional, enumerated by actual composed source hierarchy.',
        'grant_ACK_CDC_bits_per_W72_AW3_crossing': 2574,
        'grant_ACK_CDC_crossing_count': None,
        'startup': 'Initial zero debt is quiet before initial grant. InitialACK seen is a separate lifecycle START-to-RUN gate, never a prerequisite for pre-reset quiet. Each endpoint reset clears its ACK observer; reset_entry releases after two local edges.',
        'reserve': 'session_admit must be generated/synchronized in the native clk domain; no raw coordinator-running crossing. Source observer guard gates both reserve and grant before effects. Already reserved flits continue through flight/CDC/PHY after new-admission closes.',
        'retirement': 'RX protected ingress out_v incorporates credit_rx.final_retire_ready; native dispatch uses that permission before partial consume or result delivery. No post-effect credit counter observation.',
        'transmit_pacing': 'Protected native variant currently requires BITS_X100>=PWB*100 and emits at most one complete flit per pclk. In this sized contract the fractional accumulator is unnecessary and omitted; unsupported lower-bandwidth variants fail elaboration instead of using unprotected pacing state.',
        'actual_control_transport_latency_cycles': None,
        'actual_forward_PHY_flight_cycles': None,
        'actual_return_PHY_flight_cycles': None,
        'full_PF384_endpoint_cycles': None,
        'single_user_latency_delta_ns': None,
        'residual_holds': ['native PF384 exactness/negative gate', 'data-reset and management-reset composition across domains', 'physical source/receiver quarantine ACK provider', 'asynchronous fault distribution', 'remaining inherited hub/delivery/context mutable-state protection census', 'actual source-pinned generic/standard-cell inventories', 'boundary clock budgets and SS/FF physical closure', 'token calendar recomposition']
    }

if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
