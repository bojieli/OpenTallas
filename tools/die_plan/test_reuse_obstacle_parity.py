"""Actual HBM su11 reuse overlap and the permitted split-container controls."""
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import check
import gen_phys
import ft_full_stage
import placement_obstacles
import g2


def run(t, sites, size, monkeypatch):
    t = dict(t, ft_slots=[dict(name="repro", width=len(sites)-1, stations=2,
        in_face="W", out_face="E", bit_site_cell_um=size, bit_sites_um=[sites])])
    pins = [("repro_"+side, i, "M6", x, 0., face)
            for side,x,face in [("i",0.,"W"),("o",t["outline_um"][0],"E")]
            for i in range(len(sites))]
    monkeypatch.setattr(gen_phys,"type_pins",lambda *_:pins)
    monkeypatch.setattr(ft_full_stage,"load",lambda *_:{})
    report=check.Report()
    hits=check.check_ft_macro_sites(SimpleNamespace(types={"actual":t}),report)
    return hits,report


def test_actual_su11_1323_cells_rejected(monkeypatch):
    with gzip.open(Path(__file__).with_name("test_data")/"hbm_su11_reuse_overlap_1101.json.gz","rt") as f:
        d=json.load(f)
    assert len(d["hits"])==1323
    sizes={tuple(r["size"]) for r in d["hits"]}; assert len(sizes)==1
    sites=[r["xy"] for r in d["hits"]]
    hits,report=run(d,sites,list(sizes.pop()),monkeypatch)
    assert hits==1323 and report.errors()
    # Omitting the G2-only reuse leaves recreates the previous false PASS.
    monkeypatch.setattr(placement_obstacles,"probe_blockages",lambda *_:[])
    hits,report=run(d,sites,d["hits"][0]["size"],monkeypatch)
    assert hits==0 and not report.errors()


def test_touching_leaf_edge_and_split_container_stay_legal(monkeypatch):
    t=dict(outline_um=[100.,100.],contents=[
        dict(inst="leaf",origin_um=[10.,10.],outline_um=[5.,5.]),
        dict(inst="bank",origin_um=[20.,20.],outline_um=[50.,50.])],hard_cores=[
        dict(inst="bank.left",origin_um=[20.,20.],outline_um=[10.,50.]),
        dict(inst="bank.right",origin_um=[60.,20.],outline_um=[10.,50.])])
    assert g2.probe_blockages is placement_obstacles.probe_blockages
    assert {r["inst"] for r in g2.probe_blockages(t)}=={"leaf","bank.left","bank.right"}
    # Whole cell touches the leaf edge; another cell occupies the valid glue corridor.
    hits,report=run(t,[[8.596,11.],[40.,40.]],[1.404,.27],monkeypatch)
    assert hits==0 and not report.errors()
