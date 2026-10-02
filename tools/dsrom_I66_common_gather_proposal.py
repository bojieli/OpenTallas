"""One conditional common-owner proposal; no stations, C, or RTL selected."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_I66_common_gather_proposal_20261002'


def route(row):
    if type(row) is not int or not 0 <= row < 576:
        raise ValueError('exact source row')
    root = (row % 256) // 2
    return {'row': row, 'root': root, 'physical_shard': root // 64, 'local_root': root % 64}


def source_wire_user(user, domain_qualified=False):
    """No implicit user32 -> fff6 user16 alias; no hardware adapter supplied."""
    if type(domain_qualified) is not bool or not domain_qualified:
        raise ValueError('source user domain not qualified')
    if type(user) is not int or not 0 <= user < 65536:
        raise ValueError('source packet user16 cannot represent context user32')
    return user


def validate_itinerary(rows):
    if not isinstance(rows, list) or len(rows) != 576:
        raise ValueError('all576 source rows required')
    for row, packet in enumerate(rows):
        if not isinstance(packet, dict) or set(packet) != {'row', 'root', 'physical_shard', 'local_root'}:
            raise ValueError('exact routing identity')
        if any(type(v) is not int for v in packet.values()) or packet != route(row):
            raise ValueError('source order or physical owner mismatch')
    return [sum(p['physical_shard'] == s for p in rows) for s in (0, 1)]


def proposal():
    rows = [route(r) for r in range(576)]
    seats = validate_itinerary(rows)
    base = ROOT / 'results/uarch/dsrom_I66_consumer_deadline_20261002/source_model.json'
    consumer = json.loads(base.read_text())
    home = ROOT / 'results/uarch/dsrom_I66_R49_service_join_20261002/inputs/home.json'
    provider = ROOT / 'results/uarch/dsrom_I66_R49_service_join_20261002/inputs/provider.json'
    p = json.loads(provider.read_text())
    return {
        'scope': 'ONE_CONDITIONAL_COMMON_OWNER_PROPOSAL_NOT_HARDWARE_SELECTION',
        'source_pins': {str(x.relative_to(ROOT)): hashlib.sha256(x.read_bytes()).hexdigest()
                        for x in (base, home, provider)},
        'common_control_owner_proposed': {'physical_shard': 0, 'reason': 'one phase lease and larger320-seat shard',
                                         'adopted': False},
        'per_shard_controls': 'Each die owns its local bank read/selector and captured credit endpoint; shard1 endpoint state must be separately priced',
        'gather_owner_proposed': 'one owner in HUB_GATHER region; actual endpoint pin/clock/route and exclusive VM lease unbound',
        'arbitration': {
            'source_read_request': 'next source-ordered row chooses physical shard; issue only after gather seat and complete return route reserved',
            'grant_limit': 'at most one scalar request per qualified gather edge; local bank grants may require greater II',
            'returns': 'route-bound return may arrive out of order only into its previously reserved row/context seat',
            'delivery': 'only lowest unretired row may consume one accepted formatter/home-write grant',
            'sink_hold': 'refused consumer holds its seat, identity and debt; does not backpressure no-ready field capture',
            'credit_release': 'actual home visibility followed by positive captured credit-return/CDC; no same-edge source reuse',
            'wire_ACK': 'fresh matching sequence/CRC-qualified last packet-delivery ACK is a separate packet debt',
            'rearm': 'all576 home-visible, healthy source idle, every wire debt and credit-return fence, then explicit old-context drain'},
        'physical_shard_seats': seats,
        'ordered_shard_runs': [[0, 127, 0], [128, 255, 1], [256, 383, 0], [384, 511, 1], [512, 575, 0]],
        'capacity_and_register_gate': {
            'C': None, 'stations': None, 'calendar': None,
            'needed': 'source-owned rational clocks and request/read/reply/visibility/credit-return latencies plus finite accepted sink grants',
            'capacity_rule': 'maximum accepted reservations minus source-observed returned credits; return at edgeT cannot fund issue atT',
            'arbitrary_sink_hold_has_no_finite_successful_bound': True,
            'VM512': 'exclusive full-block lease, assembly and writer arbitration must be priced; existing xa/xb ports are not free',
            'native_one_clock_is_not_planned_3_to_4_CDC': True},
        'wire_identity_gap': {
            'candidate_context_user_bits': 32,
            'fff6_packet_header_user_bits': p['ports']['packet_header_fields']['user'],
            'projection_selected': False,
            'required_choice': 'qualify source domain<=65535 with no alias, or price header widening, CRC/framing and resulting packet/calendar changes'},
        'accepted_consumer_endpoints': {
            'enrollment': 'CURRENT_PHW10/X_ROM1/SUN256; exact source/binary, four program SHAs, +DIR and separate +OT_ROM_DIR',
            'core_sha256': consumer['core_sha256'],
            'producer_owner': 'actual accepted producer PC and registered phase/EID/key, frozen generation/user/Xversion',
            'vector_owner': 'dut.u_tile.u_core.g_su_x.u_su.u_vec accepted vector sequence/context, not latest PC',
            'read': 'xs_rd_re[port] && xs_rd_src[2*port+:2]==0; resolved VM address and old read data',
            'tag': 'accepted VM read atR matched actual vx/cwx source X tag atR+2',
            'publication': 'same-identity writer/address/data postNBA strictly BEFORE read edge',
            'static_consumers': [{'producer': o['producer_node'], 'consumer': o['first_static_consumer']}
                                 for o in consumer['obligations']],
            'actual_current_journal': None, 'actual_consumer_deadline': None},
        'state_accounting': {'core_gross': 698354, 'core_increment_already_in_gross': 127140,
                             'disjoint_transport': 476180, 'union': 1174534,
                             'new_shard_endpoint_gather_CDC_VM_state': None},
        'typed_timing': 'feedback and forward hold repairs are distinct typed lower bounds; no SS/FF routed qualification or station selection',
        'new_jobs': False, 'RTL_GO': False, 'finite_actual_service': 'BOUND_MISSING',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(proposal(), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
