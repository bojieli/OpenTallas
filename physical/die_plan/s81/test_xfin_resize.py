import importlib.util, json
from pathlib import Path
spec=importlib.util.spec_from_file_location("delta_cconn",Path(__file__).with_name("delta_cconn_1025.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_existing_345_square_resize_and_idempotence(tmp_path):
 p=tmp_path/"pins.json"
 d={"pins":[{"name":"a[0]","x":345.558,"y":100.0},{"name":"a[1]","x":345.558,"y":100.192},{"name":"b","x":100.0,"y":345.558}]}
 p.write_text(json.dumps(d));assert m.xfin_pins(p,(362.88,362.88))
 out=json.loads(p.read_text());assert all(abs(q["x"]-362.838)<1e-6 for q in out["pins"][:2])
 assert abs(out["pins"][1]["y"]-out["pins"][0]["y"]-0.192)<1e-6
 text=p.read_bytes();assert not m.xfin_pins(p,(362.88,362.88));assert p.read_bytes()==text

def test_all_candidate_outlines_fit_measured_cells():
 assert all(w*h>=75438.654/0.6 for w,h in m.xfin_sizes())


def test_explicit_old_outline_for_single_face_table(tmp_path):
 p=tmp_path/"pins.json"
 p.write_text(json.dumps({"pins":[{"name":"a[0]","x":0.042,"y":153.372},{"name":"a[1]","x":0.042,"y":153.564}]}))
 assert m.xfin_pins(p,(267.84,267.84),old_outline=172.8)
 out=json.loads(p.read_text())["pins"]
 assert all(q["x"]==0.042 and 0<q["y"]<267.84 for q in out)
 assert abs(out[1]["y"]-out[0]["y"]-0.192)<1e-6
