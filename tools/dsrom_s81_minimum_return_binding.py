"""Bind one existing emitted source phase/CFG and canonical first branch.

Consumes the owner's EXISTING StageProgramJoin and literal PHROM words. Does
not emit programs, reload mappings, read weights, grant GO or fabricate peers.
"""
import hashlib
from pathlib import Path
from dsrom_s81_phase_capture_join import emitted_phase_profile


def bind_return_phase(stage_join, connectivity, fragment, *, pair, positions,
                      phrom0, phrom1, cfg_path, identity, format, output_base,
                      output_position_stride, ME):
    for value in [pair, positions, phrom0, phrom1, identity, format, output_base,
                  output_position_stride]:
        if type(value) is not int:
            raise ValueError('literal integer source ports required')
    if (not 0 <= pair < 2417 or not 1 <= positions <= 8 or
        not 0 <= phrom0 < 1 << 64 or not 0 <= phrom1 < 1 << 64 or
        not 0 <= identity < 1 << 47 or not 0 <= format < 3 or
        not 0 <= output_base < 1 << 19 or not 0 <= output_position_stride < 1 << 19):
        raise ValueError('selected native return port aperture')
    if not connectivity['inventory_bound'] or not connectivity['no_READY']:
        raise ValueError('canonical source return ownership required')
    if (connectivity['RD'], connectivity['ROOTD'], connectivity['QD'],
        connectivity['RST'], connectivity['BYPASS']) != (64,128,128,1,1):
        raise ValueError('retained branch/root parameters changed')
    stage, rank, phase, key = [fragment[k] for k in ['stage','rank','phase','key']]
    if any(type(v) is not int for v in [stage,rank,phase,key]) or not (
        0 <= stage < 81 and 0 <= rank < 4 and 0 <= phase < 1024 and 0 <= key < 1 << 32):
        raise ValueError('actual dispatch owner/key/phase aperture')
    profile = emitted_phase_profile(stage_join, connectivity, stage=stage,
                                   rank=rank, phase=phase, positions=positions,
                                   key=key, ME=ME)
    if profile['source_matrix_sha256'] != fragment['source_matrix_sha256']:
        raise ValueError('source dispatch/matrix mismatch')
    if ((phrom0 >> 46) & 65535) != profile['phase_rows'] or bool(phrom0 & 1) != ME:
        raise ValueError('literal PHROM row count/family differs from emitted phase')
    root = next((r for r in range(128) if
                 connectivity['region_bounds'][r] <= pair < connectivity['region_bounds'][r+1]), None)
    if root is None:
        raise ValueError('pair absent from actual retained region')
    nodes = [n for n in connectivity['nodes'] if
             n['a'] == 2*pair and n['b'] == 2*pair+1 and n['region'] == root]
    if len(nodes) != 1:
        raise ValueError('actual canonical first branch missing/duplicate')
    if not profile['root_return_counts'][root]:
        raise ValueError('selected region has no outputs in actual phase')
    cfg_path = Path(cfg_path)
    cfg_raw = cfg_path.read_bytes()
    words = [int(line,16) for line in cfg_raw.decode().splitlines() if line.strip()]
    if not words or len(words)%25 or any(not 0 <= w < 1 << 48 for w in words):
        raise ValueError('actual CW25/CFG48 initializer required')
    if len(words) < 25*(phase+1):
        raise ValueError('CFG does not contain the accepted phase')
    expected = [stage_join.cfg(stage,rank,pair,phase*25+w) for w in range(25)]
    if words[phase*25:phase*25+25] != expected or not any(expected):
        raise ValueError('source CFG mismatch/inactive selected pair')
    matrix = stage_join.by_stage[stage][phase]['matrix']
    required_segments = set(range(len(matrix['segments'])))
    selected_rows = {}
    for segment, owner_pair, first, count, stride, start, words_per_row in matrix['plans']:
        if owner_pair != pair:
            continue
        for j in range(count):
            for output_row in [2*(first+j*stride),2*(first+j*stride)+1]:
                if output_row < matrix['rows']:
                    selected_rows.setdefault(output_row,set()).add(segment)
    component_rows = sorted(row for row, segments in selected_rows.items()
                            if segments == required_segments)
    if not component_rows or any(row not in profile['root_rows'][root] for row in component_rows):
        raise ValueError('selected pair does not own complete K subtrees in this root')
    return dict(stage=stage,rank=rank,pair=pair,root=root,phase=phase,
                positions_minus_one=positions-1,format=format,identity=identity,
                phrom0=phrom0,phrom1=phrom1,output_base=output_base,
                output_position_stride=output_position_stride,emitted_key=str(key),
                source_matrix_sha256=profile['source_matrix_sha256'],cfg_path=str(cfg_path),
                cfg_sha256=hashlib.sha256(cfg_raw).hexdigest(),
                region_pair_begin=connectivity['region_bounds'][root],
                region_pair_end=connectivity['region_bounds'][root+1],
                branch_a_leaf=nodes[0]['a'],branch_b_leaf=nodes[0]['b'],
                canonical_node_id=nodes[0]['id'],whole_root_quota=profile['root_return_counts'][root],
                component_rows=component_rows,component_quota=len(component_rows)*positions,
                actual_owned_rows=profile['root_rows'][root],
                scope='one actual branch/root; missing K siblings cannot be synthesized',
                field_complete=False,physical_qualified=False)
