"""Prospective one-slot canonical payload authority, before RTL implementation.

Uses pinned unified analytical constants; does not edit its preset or outputs.
Local lifecycle edges compose with the existing serialized KV/W2 calendar.
External loaded route/CDC bounds remain required for full-token qualification.
"""
import ast
from pathlib import Path


def unified_constant(name):
    # Read analytical constants without running the unified model's headline
    # imports, which require unrelated archived physical products in checkout.
    tree = ast.parse((Path(__file__).parents[1] / 'uarch_model.py').read_text())
    found = [s.value for s in tree.body if isinstance(s, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in s.targets)]
    if len(found) != 1:
        raise ValueError('pinned unified constant missing/ambiguous: ' + name)
    return ast.literal_eval(found[0])


def model():
    identity = 64 + 20 + 9 + 34 + 34 + 7 + 3 + 32 + 4
    bits = identity + 3 + 1 + 1  # root, phase, RMW, sticky fault
    return dict(slots=1, replicas=1, identity_bits=identity,
                raw_control_bits=bits, added_SRAM_bytes=0,
                MACs_per_cycle=0, payload_bytes_per_cycle=0,
                boundary_bits_per_cycle=dict(allocate=identity + 1,
                    issue=identity + 1, capture=identity + 1,
                    reverse=identity + 1, release=identity),
                routing_tracks_per_unshared_boundary=identity + 1,
                routing_capacity=None, route_screen='external placement required',
                identity_comparators=4, physical_sector_guard_bits=34+46,
                caller_guard_replicas=6,
                selected_client_exclusive_until_release=True,
                prior_selected_client_and_sector_drain_required=True,
                other_clients_progress='different sectors only; existing authorities retained',
                root_mux_inputs=1, root_read_ports=1, root_write_ports=1,
                state_decode_fanout=6, control_bits_fanout_max=4,
                storage_area_proxy_mm2=bits * unified_constant('DFF_UM2') / .5 / 1e6,
                comparator_gate_equivalents=6*(4*identity+6*80),
                comparator_area_proxy_mm2=6*(4*identity+6*80)*unified_constant('DFF_UM2')/1e6,
                comparator_proxy='six DFF-area gate equivalents per compared bit; conservative unplaced proxy',
                floorplan_slot_fit=None,
                clock_GHz=1.2, setup_uncertainty_ps=unified_constant('UNCERTAINTY_PS'),
                hold_uncertainty_ps=25,
                local_K_lifecycle_edges=8, local_V_lifecycle_edges=5,
                added_nonoverlapped_edges_per_sector=2,
                total_local_commit_overhead_edges=272*2,
                total_local_commit_overhead_ns=272*2/1.2,
                reused_W2_same_client_II_edges=19,
                CDC_latency=None, external_reverse_latency=None,
                physical_qualified=False, headline_adopted=False,
                scope='finite authority integration; no new arithmetic or payload memory')


def compose_commit(existing_commit_edges, allocation_release_CDC_edges):
    if any(type(v) is not int or v < 0 for v in
           (existing_commit_edges, allocation_release_CDC_edges)):
        raise ValueError('finite composed edge bounds required')
    return existing_commit_edges + 272 * (2 + allocation_release_CDC_edges)
