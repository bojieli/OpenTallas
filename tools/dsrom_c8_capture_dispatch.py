"""Join Nash's canonical per-root profiles to emitted native C8 phase offers.

Reuse the parent's loaded StageProgramJoin and existing dispatch manifest.
No map constructor, program emission, acceptance decision or numerical oracle.
"""
import copy
import hashlib
import json
from pathlib import Path
from dsrom_s81_capture_profile import compile_profile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def attach(parent_dispatch, join, connectivity, positions_by_offer, out):
    """Emit a fresh successor manifest and count ROMs for selected real offers.

    positions_by_offer maps (physical_die_id, entry, saved_identity) to the
    SOURCE caller's position count. Native i_np is positions-1, not positions.
    Arch threads lookup(i_ph,i_np) and retained identity at actual GO acceptance.
    Unselected phases have invalid ROM entries, never valid zero-count debt.
    """
    require(connectivity['region_bounds'] == join.stage_map['region_bounds'] and
            connectivity['BF_site_IDs'] == join.stage_map['BF_site_IDs'],
            'capture/source physical connectivity mismatch')
    result = copy.deepcopy(parent_dispatch)
    require(result['offers'], 'actual parent dispatch offers required')
    profiles, banks, seen = {}, {}, set()
    for offer in result['offers']:
        key = (offer['die_id'], offer['entry'], offer['identity'])
        require(key not in seen, 'ambiguous accepted offer identity/entry')
        seen.add(key)
        require(key in positions_by_offer, 'source position count missing')
        positions = positions_by_offer[key]
        require(type(positions) is int and 1 <= positions <= 8, 'source positions 1..8')
        stage, rank, phase = offer['stage'], offer['rank'], offer['phase']
        require(offer['die_id'] == 4*stage+rank, 'actual stage/rank die binding')
        rows = join.by_stage[stage]
        require(type(phase) is int and 0 <= phase < len(rows), 'unallocated phase')
        row = rows[phase]
        matrix_sha = hashlib.sha256(json.dumps(row['matrix'],sort_keys=True,
            separators=(',', ':')).encode()).hexdigest()
        require(rank in row['owners'] and row['key'] == offer['key'] and
                matrix_sha == row['matrix_sha256'] == offer['source_matrix_sha256'],
                'phase/matrix/key/physical owner changed')
        profile_id = f's{stage}_r{rank}_ph{phase}_np{positions-1}'
        if profile_id not in profiles:
            profile = compile_profile(row['matrix'], connectivity, positions)
            counts = profile['root_return_counts']
            require(len(counts) == 128 and all(type(c) is int and 0 <= c < 1<<19 for c in counts),
                    'actual capture R128/count19 port')
            packed = sum(c << (19*r) for r,c in enumerate(counts))
            profiles[profile_id] = dict(profile, stage=stage, rank=rank, phase=phase,
                key=row['key'], source_matrix_sha256=row['matrix_sha256'],
                root_count_word_hex=f'{packed:0608x}', count_bits=2432)
            bank = banks.setdefault((stage,rank,positions-1), {})
            require(phase not in bank, 'duplicate phase count ROM word')
            bank[phase] = packed
        offer['capture'] = dict(profile=profile_id, phase=phase, native_i_np=positions-1,
            saved_identity=offer['identity'], saved_token=offer['token'], saved_entry=offer['entry'],
            root_return_counts=profiles[profile_id]['root_return_counts'],
            total_returns=profiles[profile_id]['total_returns'])
    out = Path(out); require(not out.exists(), 'fresh capture output required')
    out.mkdir(parents=True)
    artifacts, roms = {}, []
    for (stage,rank,np), bank in sorted(banks.items()):
        depth = 1 << join.stage_map['PHW_required_by_stage'][stage]
        # [2432] valid, root r occupies [19*r +:19]. Invalid words are zero
        # only with valid=0; the parent MUST refuse GO on invalid/missing np.
        name = f's{stage}_r{rank}_np{np}.capture.hex'
        raw = ''.join(f'{((1<<2432)|bank[p]) if p in bank else 0:0609x}\n'
                      for p in range(depth)).encode()
        (out/name).write_bytes(raw)
        artifacts[name] = hashlib.sha256(raw).hexdigest()
        roms.append(dict(stage=stage, rank=rank, native_i_np=np, path=name,
            address='actual i_ph before GO', depth=depth, word_bits=2433,
            valid_bit=2432, root_count_lsb_stride=19, selected_phases=sorted(bank),
            logical_storage_bits=depth*2433))
    result['capture_profiles'] = profiles
    result['capture_count_roms'] = roms
    result['capture_artifacts'] = artifacts
    result['capture_binding'] = dict(
        selection='actual accepted i_ph/i_np and saved identity/token/entry',
        native_np_encoding='positions-1', logical_storage_bits=sum(r['logical_storage_bits'] for r in roms),
        count_rom_hardware_installed=False, ports_routes_area_latency_admitted=False,
        actual_VM_acceptance_required=True, reset_debt_authority_required=True)
    (out/'parent_dispatch.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def accepted_phase(manifest, *, accepted, die_id, identity, token, entry, i_ph, i_np):
    """Bind an OBSERVED native acceptance to its immutable debt configuration.

    Caller samples accepted GO/ready and retained C8 context at the same edge.
    This supplies no GO, READY, VM write ACK, restoration or drain signal.
    """
    require(accepted is True, 'actual native phase acceptance required')
    matches = [o for o in manifest['offers'] if
               (o['die_id'],o['identity'],o['token'],o['entry'],o['phase']) ==
               (die_id,identity,token,entry,i_ph) and
               o['capture']['native_i_np'] == i_np]
    require(len(matches) == 1, 'unbound/ambiguous accepted phase/context')
    offer = matches[0]
    return copy.deepcopy(dict(offer['capture'], die_id=die_id,
        source_matrix_sha256=offer['source_matrix_sha256']))
