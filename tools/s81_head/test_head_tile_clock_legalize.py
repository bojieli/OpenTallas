from pathlib import Path
import importlib.util

p=Path(__file__).with_name('head_tile_clock_legalize.py')
s=importlib.util.spec_from_file_location('clocklegal',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_fixed_row_bucket_survives_written_decimal_vs_snapped_binary(tmp_path):
    d=tmp_path/'blk.tsv'
    d.write_text('W\t350\t717.12\t370\t717.39\nF\t355.104\t717.12\t356.184\t717.39\tDFFHQNx1_ASAP7_75t_R\tstate\n')
    g=m.Geometry(d)
    assert g.bad((356.022,717.1200000000001,357.642,717.3900000000001)) == 'fixed'
    assert g.bad((358.0,717.1200000000001,359.62,717.3900000000001)) is None

def test_geometry_source_moves_preserve_whole_group_and_are_idempotent(tmp_path):
    d=tmp_path/'blk.tsv'
    d.write_text('W\t4.32\t4.32\t100\t4.59\nW\t4.32\t4.59\t100\t4.86\nF\t10.26\t4.32\t10.368\t4.59\tTAPCELL_ASAP7_75t_R\ttap\n')
    g=m.Geometry(d);spec=dict(root_split_xy=[30.,4.32],trunk=[['R',30.,4.32,'-'],['A',10.,4.32,'CLK']],core_taps=[])
    plan=dict(trunk=spec['trunk'],taps=[])
    fixed,built,moves=m.legalize(spec,plan,g)
    assert moves and not m.audit(fixed,built,g)
    again,built2,moves2=m.legalize(fixed,built,g)
    assert not moves2 and again==fixed and built2==built
    assert len(m.groups(spec,plan))==len(m.groups(fixed,built))
