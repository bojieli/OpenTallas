import copy
import pytest
import die_clock_mesh as D
import die_clock_128 as C
import die_trial as T
import json


def test_directional_pin_bars_and_inventory(tmp_path):
    cells = {"a": dict(x=10.8,y=1.08), "b": dict(x=5.4,y=1.08)}
    sites = {k: dict(origin_um=[v["x"],v["y"]], xy_um=[v["x"]+.81,v["y"]+.135], part="p") for k,v in cells.items()}
    nets = [dict(drv="a",loads=["b"]), dict(drv="b", loads=["port:o"])]
    D.apply_lattice_cell_sites(cells,nets,[dict(port="o",xy=[20,1])],sites,lambda xy:("p",None))
    assert cells["a"]["orient"] == "MY" and cells["b"]["orient"] == "R0"
    assert C.pin_xy(cells,"a","Y",.27)[0] == 10.827
    assert C.pin_xy(cells,"a","A",.27)[0] == 12.393
    p=tmp_path/"plan.json"
    p.write_text(json.dumps(dict(lattice=dict(nodes=[dict(tag="ignored",xy_um=[0,0])],cell_sites=sites))))
    loaded=T.load_island_sites([p])
    assert len(loaded)==2 and loaded[0][0]==tuple(sites["a"]["xy_um"])


def test_missing_or_illegal_sites_fail():
    cells={"a":dict(x=0,y=0)}
    with pytest.raises(C.PlanError,match="cell_site_inventory"):
        D.apply_lattice_cell_sites(copy.deepcopy(cells),[],[],{},lambda xy:("p",None))
    with pytest.raises(C.PlanError,match="cell_site_off_row"):
        D.apply_lattice_cell_sites(copy.deepcopy(cells),[],[],{"a":dict(origin_um=[.001,0],part="p")},lambda xy:("p",None))
    with pytest.raises(C.PlanError,match="cell_site_host"):
        D.apply_lattice_cell_sites(copy.deepcopy(cells),[],[],{"a":dict(origin_um=[0,0],part="p")},lambda xy:(None,"on_hard_keepout"))


def test_cell_body_cannot_cross_partition_seam():
    with pytest.raises(C.PlanError,match="cell_site_seam"):
        D.apply_lattice_cell_sites({"a":dict(x=0,y=0)},[],[],
            {"a":dict(origin_um=[0,0],part="p")},lambda xy:("p",None),{"p":(0,0,1,1)})


def test_short_stack_has_real_min_area_pads_on_both_riser_ends():
    import clock_routed as R
    st=dict(xy=[1.,2.],riser_from=[1.,2.005],short_stack=True)
    p=R.stack_pad_layers(st)
    assert "M7" in p[(1.,2.)] and "M8" in p[(1.,2.005)]
    lines=[]
    R._emit_stack(lines,R.stack_down(st),p,split_down=True)
    i=next(i for i,l in enumerate(lines) if "VIA78" in l)
    assert "addRect" in lines[i-1]
    j=next(i for i,l in enumerate(lines) if "VIA67" in l)
    assert "addRect" in lines[j-1]
    assert C.SHORT_STACK_PAD["M7"][0]*C.SHORT_STACK_PAD["M7"][1]*4 >= .0021875
    assert C.SHORT_STACK_PAD["M8"][0]*C.SHORT_STACK_PAD["M8"][1]*4 >= .00752
