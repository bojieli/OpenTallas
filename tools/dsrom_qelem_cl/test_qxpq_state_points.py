"""State normalization must preserve clocks/state/ports and reject incomplete maps."""
import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import qxpq_cgr_lec as Q


def pair(tmp_path):
    paths=[]
    for side,offset in (("gold",0),("gate",10)):
        m={"ports":{"clk":{"direction":"input","bits":[2+offset]},
                    "d":{"direction":"input","bits":[3+offset]},
                    "q":{"direction":"output","bits":[4+offset,5+offset]}},
           "netnames":{"state":{"bits":[4+offset,5+offset],"attributes":{"init":"01"}},
                       "dead_clock_alias":{"bits":[100+offset],"attributes":{}}},
           "cells":{"reg":{"type":"$dff","parameters":{"WIDTH":"10","CLK_POLARITY":"1"},
                             "connections":{"CLK":[2+offset],"D":[3+offset,3+offset],"Q":[4+offset,5+offset]},
                             "port_directions":{"CLK":"input","D":"input","Q":"output"}}}}
        p=tmp_path/(side+".json");p.write_text(json.dumps({"modules":{side:m}}));paths.append(p)
    return paths


def mutate(path,fn):
    data=json.loads(path.read_text());fn(next(iter(data["modules"].values())));path.write_text(json.dumps(data))


def test_normalization_preserves_every_cell_clock_port_and_initial_bit(tmp_path):
    paths=pair(tmp_path);before=[json.loads(p.read_text()) for p in paths]
    g,t,scope=Q.normalize_state_points(*paths,str(tmp_path))
    assert scope["state_bits"]==2 and scope["primary_and_rom_ports"]==3
    for old,path,side in zip(before,(g,t),("gold","gate")):
        old=old["modules"][side];new=json.load(open(path))["modules"][side]
        assert new["cells"]==old["cells"] and new["ports"]==old["ports"]
        assert "dead_clock_alias" not in new["netnames"]
        assert [new["netnames"][f"lec_state_{i}"]["attributes"]["init"] for i in range(2)]==["1","0"]


@pytest.mark.parametrize("change,error",[
    (lambda m:m["ports"]["d"]["bits"].append(99),"interface differs"),
    (lambda m:m["netnames"].pop("state"),"unmatched FF bits"),
    (lambda m:m["netnames"].update(alias={"bits":[15,14],"attributes":{}}),"ambiguous FF aliases"),
    (lambda m:m["netnames"]["state"]["attributes"].update(init="10"),"initial values differ"),
    (lambda m:m["cells"]["reg"]["parameters"].update(CLK_POLARITY="0"),"semantics differ"),
    (lambda m:m["cells"]["reg"]["connections"].update(CLK=[13]),"unproved derived clock"),
])
def test_bad_normalization_inputs_fail_closed(tmp_path,change,error):
    paths=pair(tmp_path)
    if error=="ambiguous FF aliases":
        mutate(paths[0],lambda m:m["netnames"].update(alias={"bits":[4,5],"attributes":{}}))
    mutate(paths[1],change)
    with pytest.raises(ValueError,match=error):Q.normalize_state_points(*paths,str(tmp_path))
