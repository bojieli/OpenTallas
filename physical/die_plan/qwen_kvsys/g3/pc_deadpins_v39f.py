#!/usr/bin/env python3
"""KV-PLAN3F 10-25: kvs_pc / kvs_pc_h_head_p dead-pin drop (KV-CORE-RTL 07:09 boundary recut, claude/kv-core-rtl-pc-1025
@4c6e890d93, DEAD-PIN DROP LIST) as an explicit plan pin correction, not keep attributes.
  both cores: drop pc__land_er[258:1], hck[0], pc__front_hbm_data[3:0], pc__return_hbm_data[3:0]
  head_p:     also drop pc__ki[30:21], pc__ki[14:1]
  live remnants become separate ports (same pin site, new port name):
              both pc__land_er[0] stays; pc__land_er[260:259] -> pc__land_er_259[260:259]
              head_p pc__ki[0] stays; pc__ki[20:15] -> pc__ki_15[20:15]; pc__ki[32:31] -> pc__ki_31[32:31]
Pins: qkd_kvs_pc 4396 -> 4129, qkd_kvs_pc_h_head_p 3278 -> 2987 (one clock: ck).  core_conns.json: ports whose every bit
is dropped lose their key (hck, front/return_hbm_data); the split remnants inherit the conns of their old port.
    pc_deadpins_v39f.py PLAN.json CORES_DIR CORE_CONNS.json --report R.json
"""
import argparse
import json
import re
from pathlib import Path

DROP = {"qkd_kvs_pc": [("pc__land_er", 1, 258), ("hck", 0, 0), ("pc__front_hbm_data", 0, 3),
                       ("pc__return_hbm_data", 0, 3)]}
DROP["qkd_kvs_pc_h_head_p"] = DROP["qkd_kvs_pc"] + [("pc__ki", 21, 30), ("pc__ki", 1, 14)]
SPLIT = {"qkd_kvs_pc": [("pc__land_er", 259, 260, "pc__land_er_259")]}
SPLIT["qkd_kvs_pc_h_head_p"] = SPLIT["qkd_kvs_pc"] + [("pc__ki", 15, 20, "pc__ki_15"), ("pc__ki", 31, 32, "pc__ki_31")]
GONE = ("hck", "pc__front_hbm_data", "pc__return_hbm_data")
WANT = {"qkd_kvs_pc": 4129, "qkd_kvs_pc_h_head_p": 2987}


def nb(q):
    n = q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]"
    m = re.fullmatch(r"(.+)\[(\d+)\]", n)
    return (m.group(1), int(m.group(2))) if m else (n, None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("cores")
    ap.add_argument("core_conns")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    rep = {}
    for mod in DROP:
        f = Path(a.cores) / f"{mod}_pins.json"
        js = json.loads(f.read_text())
        pins = js["pins"] if isinstance(js, dict) else js
        keep, dropped, renamed = [], 0, 0
        for q in pins:
            b, i = nb(q)
            if i is not None and any(b == p and lo <= i <= hi for p, lo, hi in DROP[mod]):
                dropped += 1
                continue
            for p, lo, hi, new in SPLIT[mod]:
                if i is not None and b == p and lo <= i <= hi:
                    q = dict(q, name=f"{new}[{i}]")
                    q.pop("bus", None)
                    q.pop("bit", None)
                    renamed += 1
            keep.append(q)
        if len(keep) != WANT[mod]:
            raise SystemExit(f"{mod}: {len(pins)} -> {len(keep)} pins, KV-CORE-RTL posted {WANT[mod]}")
        if isinstance(js, dict):
            js["pins"] = keep
            js["source"] = js.get("source", "") + " | KV-PLAN3F v3.9f: KV-CORE-RTL 07:09 dead-pin drop + split remnants"
        f.write_text(json.dumps(js if isinstance(js, dict) else keep, indent=1) + "\n")
        rep[mod] = dict(pins=[len(pins), len(keep)], dropped=dropped, renamed=renamed)
    cc = json.loads(Path(a.core_conns).read_text())
    raw = json.loads(Path(a.plan).read_text())
    mod_of = {(tn, h["inst"]): h.get("module") for tn, t in raw["partition_types"].items()
              for h in t.get("hard_cores") or []}
    plan_ref = rep.setdefault("core_conns", dict(keys_removed=0, keys_added=0))
    for tn, insts in cc.items():
        for inst, d in insts.items():
            mod = mod_of.get((tn, inst))
            if mod not in DROP or not isinstance(d, dict):
                continue
            for g in GONE:
                if g in d:
                    del d[g]
                    plan_ref["keys_removed"] += 1
            for old, _, _, new in SPLIT[mod]:
                if old in d and new not in d:
                    d[new] = list(d[old])
                    plan_ref["keys_added"] += 1
    Path(a.core_conns).write_text(json.dumps(cc, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"pc_deadpins: {rep}")


if __name__ == "__main__":
    main()
