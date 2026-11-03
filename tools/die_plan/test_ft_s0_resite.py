"""DIE-HBM-59/G0C: ft_s0_resite helpers (stage positions are real bit sites, never a centroid inside a core)."""
import json
import ft_s0_resite as R


def test_stage_position_is_a_real_site_not_the_centroid():
    # a band split around a core: bits 0-3 at x=0, bits 4-7 at x=100 -> centroid x=50 lies in the core gap
    slot = dict(bit_site_cell_um=[1.0, 0.5], bit_sites_um=[[[0.0, float(y)] for y in range(4)] +
                                                          [[100.0, float(y)] for y in range(4)]])
    (m,) = R.stage_medoids(slot)
    centres = [[x + 0.5, y + 0.25] for x, y in slot['bit_sites_um'][0]]
    assert m in centres and m[0] != 50.5
    assert m == centres[4]          # the middle bit (window order) carries the stage position


def test_medoid_fix_rewrites_only_internal_regs(tmp_path):
    slot = dict(name='L1x1', stations=2, regs_um=[[5.0, 5.0], [50.0, 0.0]], bit_site_cell_um=[1.0, 0.5],
                bit_sites_um=[[[0.0, 0.0], [100.0, 0.0], [101.0, 0.0]]])
    plan = dict(partition_types=dict(t=dict(ft_slots=[slot])))
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    a.write_text(json.dumps(plan))
    R.medoid_fix(str(a), str(b), ['t/L1x1'])
    out = json.loads(b.read_text())['partition_types']['t']['ft_slots'][0]
    assert out['regs_um'][0] == [5.0, 5.0] and out['regs_um'][1] == [100.5, 0.25]
