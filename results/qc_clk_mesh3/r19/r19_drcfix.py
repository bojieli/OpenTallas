"""R19: regenerate the encoder Tcl of the R17 nets that carry Min Step @ M8 markers with the NEW and the OLD
clock_routed.py, diff, and write a replay Tcl (routed.odb -> re-encode those nets -> drt::check_drc on their boxes)."""
import glob, importlib.util, json, re, sys
from pathlib import Path
T = Path(sys.argv[1]); NEW = Path(sys.argv[2]); OLD = Path(sys.argv[3]); OUT = Path(sys.argv[4])
sys.path.insert(0, str(NEW))
def load(p, nm):
    s = importlib.util.spec_from_file_location(nm, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
CRn = load(NEW / "clock_routed.py", "crn"); CRo = load(OLD / "clock_routed.py", "cro")
import die_clock_mesh as D
M = json.loads((T / "mesh.json").read_text()); cells = json.loads((T / "place.json").read_text())
W = {w["name"]: w for w in M["fixed_wires"]}
bad, boxes = {}, []
for f in sorted(glob.glob(str(T / "drc" / "*.rpt"))):
    t = Path(f).read_text()
    for net in re.findall(r"srcs: net:(\S+)", t):
        bad.setdefault(net, set()).add(int(Path(f).stem.split("_")[1]))
allbox = (T / "drc_boxes.txt").read_text().split("\n")
ids = sorted({b for v in bad.values() for b in v})
ports_ = {t_["port"]: dict(layer=t_.get("layer", M["meta"].get("tap_layer", "M7")), xy=t_["xy"]) for t_ in M["taps"]}
ports_["root"] = dict(layer="M9", xy=list(M["meta"]["root_um"]))
ws = [W[n] for n in sorted(bad)]
via89 = D.NDR["16w"]["via89"]
Ln, _ = CRn.routed_tcl(json.loads(json.dumps(ws)), cells, ports_, D.BUF, "ot_mesh_ndr", via89=via89)
Lo, _ = CRo.routed_tcl(json.loads(json.dumps(ws)), cells, ports_, D.BUF, "ot_mesh_ndr", via89=via89)
diff = [(a, b) for a, b in zip(Lo, Ln) if a != b]
print(json.dumps(dict(nets=len(ws), boxes=len(ids), lines_old=len(Lo), lines_new=len(Ln), changed=len(diff), sample=diff[:3])))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "boxes.txt").write_text("\n".join(allbox[i] for i in ids) + "\n")
for tag, L in (("new", Ln), ("old", Lo)):
    (OUT / f"replay_{tag}.tcl").write_text("\n".join([
        "read_db /t/routed.odb", "set blk [ord::get_db_block]; set tech [ord::get_db_tech]",
        "foreach l {M1 M2 M3} { set tg [$blk findTrackGrid [$tech findLayer $l]]; if {$tg != \"NULL\"} { odb::dbTrackGrid_destroy $tg } }",
        "make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036",
        "foreach yo {0.045 0.081 0.117 0.153 0.189 0.225 0.270} { make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset $yo -y_pitch 0.270 }",
        "make_tracks M3 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036"] + L + [
        f"set fh [open /o/boxes.txt r]; set k 0; file mkdir /o/drc_{tag}",
        "foreach ln [split [string trim [read $fh]] \"\\n\"] { lassign $ln x0 y0 x1 y1; "
        f"drt::check_drc -box [list $x0 $y0 $x1 $y1] -output_file /o/drc_{tag}/box_$k.rpt; incr k }}",
        "puts \"OT_DRC_BOXES $k\"", "puts OT_DONE"]) + "\n")
