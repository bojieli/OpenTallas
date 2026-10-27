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


def test_interleaved_groups_respread_pin_by_pin_no_stack(tmp_path):
 # S81-CORE-LAT-R6: l0r W face, buses alternate bit by bit; the block shift stacked 321/737 pins (GRT-0080)
 pins=[]
 for i in range(300):
  pins.append({'name':('wr_bd[%d]' if i%2 else 'r_d[%d]')%(i//2),'layer':'M4','x':0.042,'y':round(6.3+0.192*i,4)})
 pins.append({'name':'clk','layer':'M4','x':0.042,'y':64.668})
 p=tmp_path/'pins.json';p.write_text(json.dumps({'pins':pins}))
 assert m.xfin_pins(p,(267.84,267.84),old_outline=172.8)
 out=json.loads(p.read_text())['pins']
 ys=sorted(q['y'] for q in out)
 assert len(set(ys))==len(ys) and min(b-a for a,b in zip(ys,ys[1:]))>=0.192-1e-6 and ys[-1]<=267.84-0.5
 assert all(abs((q['y']-0.012)/0.048-round((q['y']-0.012)/0.048))<1e-3 for q in out)
 o=sorted(pins,key=lambda q:(q['y'],q['name']));n=sorted(out,key=lambda q:q['y']);assert [q['name'] for q in o]==[q['name'] for q in n]


def test_plan_l0r_table_has_no_stacked_pins():
 import subprocess,sys
 g=Path(__file__).resolve().parents[3]/'tools/die_plan/core_pin_sites_gate.py'
 r=subprocess.run([sys.executable,'-I',str(g),'--pins',str(Path(__file__).with_name('inputs')/'core_pins/dsdv_gunit_l0r.json'),'--outline','267.84','267.84'],capture_output=True)
 assert r.returncode==0
