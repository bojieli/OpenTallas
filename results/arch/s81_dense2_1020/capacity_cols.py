"""DRIVE-S81-SVCPLAN 10-20: MODEL inventory -- the 8-column dieref with whole cluster columns removed (frames + their two
slices) and optionally every row-0 frame removed (service band).  Env OT_SVCPLAN_COLS (e.g. 7 -> keep columns 0..6),
OT_SVCPLAN_ROW0 (1 = drop all row-0 frames).  Slice sids are re-ranked contiguously (compiler topology).  Never a bind."""
import hashlib, json, os, re, sys
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D / "root/tools/s81_dv/layer_prog"))
import xs_capacity as XC
import xs_topo as TP
NC = int(os.environ.get("OT_SVCPLAN_COLS", "8")); DROPFC = {(int(x[0]), x[1]) for x in os.environ.get("OT_SVCPLAN_DROPFC", "").split(",") if x}; ROW0 = os.environ.get("OT_SVCPLAN_ROW0") == "1"
ORIGINAL = XC._die
def keep_frame(n):
    m = re.fullmatch(r"f_(\d)([LR])(\d)(\d)", n); c, t, r = int(m.group(1)), int(m.group(3)), int(m.group(4))
    return c < NC and (c, m.group(2)) not in DROPFC and not (ROW0 and t == 0 and r == 0)
def cols(src):
    die = ORIGINAL(src)
    gone = {b["name"] for b in die.plan["blocks"] if (b["kind"] == "frame" and not keep_frame(b["name"]))
            or (b["kind"] == "slice" and int(b["name"][2]) >= NC)}
    die.plan["blocks"] = [b for b in die.plan["blocks"] if b["name"] not in gone]
    die.inst = {k: v for k, v in die.inst.items() if k[2:] not in gone}
    orig = die.slices
    def slices():
        s = orig(); order = sorted(s, key=lambda k: (s[k]["sid"] if s[k]["sid"] is not None else 99, k))
        for i, k in enumerate(order): s[k]["sid"] = i
        return s
    die.slices = slices
    TP.set_from_die(die)
    inv = sorted("u_" + b["name"] for b in die.plan["blocks"] if b["kind"] == "frame")
    os.environ["OT_XS_FRAME_INVENTORY_SHA256"] = hashlib.sha256(json.dumps(inv).encode()).hexdigest()
    print("SVCPLAN_INVENTORY", json.dumps(dict(cols=NC, drop_frame_columns=sorted(DROPFC), row0_dropped=ROW0, frames=len(inv), slices=len(die.slices()), topo=TP.describe()["frames_per_slice"])), flush=True)
    return die
XC._die = cols
if __name__ == "__main__":
    sys.exit(XC.main())
