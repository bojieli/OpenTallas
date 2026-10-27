"""QC-CORES-4 10-27: su_exact pin tables for the QC plan event (COORD 12:48: R28 owns the event, QC-CORES-4 supplies data).
Source: the 16 Codex su_exact tables (backup/wt-1026/codex-qc-su-wrapper-1026 @ 6db53f3977, physical/die_plan/qwen_compute/
cores/su_exact/*_pins.json, 302 c_o each).  COORD 06:16: NARROW the 24 RTL-constant outputs c_o[49..68] (kv_wdata[0..19])
and c_o[297..300] (wrom_addr[20..23] = '{4'h0, cura[23:4]}' top nibble), value 0.  Output per table: narrowed pins
(c_o renumbered 0..277 in original order, physical slots of kept bits unchanged, the 24 slots freed) + old->new map."""
import json, re, subprocess, sys
from pathlib import Path
repo, src, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
CONST = list(range(49, 69)) + list(range(297, 301))
out.mkdir(parents=True, exist_ok=True)
names = subprocess.run(["git", "-C", repo, "ls-tree", "--name-only", src, "physical/die_plan/qwen_compute/cores/su_exact/"],
                       capture_output=True, text=True, check=True).stdout.split()
summary = dict(source=f"{src}:physical/die_plan/qwen_compute/cores/su_exact", const_bits=CONST, const_value=0,
               const_roles={"c_o[49..68]": "kv_wdata[0..19]", "c_o[297..300]": "wrom_addr[20..23]"}, tables={})
for n in sorted(names):
    d = json.loads(subprocess.run(["git", "-C", repo, "show", f"{src}:{n}"], capture_output=True, text=True, check=True).stdout)
    co = sorted((int(re.fullmatch(r"c_o\[(\d+)\]", p["name"])[1]), p) for p in d["pins"] if p["name"].startswith("c_o["))
    assert [i for i, _ in co] == list(range(len(co))), n
    if len(co) != 302:      # lanes 1..7 (248 c_o) carry no kv_wdata / wrom_addr port bits: copied unchanged
        (out / Path(n).name).write_text(json.dumps(d, indent=1) + "\n")
        summary["tables"][Path(n).name] = dict(core=d["core"], pins_old=len(d["pins"]), pins_new=len(d["pins"]),
                                               c_o_new=len(co), narrowed=False)
        continue
    keep = [i for i, _ in co if i not in CONST]
    mp = {i: k for k, i in enumerate(keep)}
    freed = [dict(old=f"c_o[{i}]", layer=p["layer"], x=p["x"], y=p["y"]) for i, p in co if i in CONST]
    pins = []
    for p in d["pins"]:
        m = re.fullmatch(r"c_o\[(\d+)\]", p["name"])
        if m and int(m[1]) in CONST:
            continue
        q = dict(p)
        if m:
            q["name"] = f"c_o[{mp[int(m[1])]}]"
        pins.append(q)
    nd = dict(schema=d.get("schema"), core=d["core"], pins=pins,
              source=f"{d.get('source')}; QC-CORES-4 narrowed 24 constant c_o (COORD 06:16) from {src}",
              narrowing=dict(c_o_width_old=302, c_o_width_new=len(keep), removed=[f"c_o[{i}]" for i in CONST],
                             removed_value=0, freed_slots=freed, old_to_new={f"c_o[{i}]": f"c_o[{k}]" for i, k in mp.items()}))
    (out / Path(n).name).write_text(json.dumps(nd, indent=1) + "\n")
    summary["tables"][Path(n).name] = dict(core=d["core"], pins_old=len(d["pins"]), pins_new=len(pins), c_o_new=len(keep), narrowed=True)
(out / "su_exact_narrow_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
print(json.dumps({k: v["pins_old"] - v["pins_new"] for k, v in summary["tables"].items()}))
