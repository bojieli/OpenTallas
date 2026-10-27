#!/usr/bin/env python3
"""PATH-KV 2026-10-26: the bind composition spec follows main's TYPE-REDUCE-2 odd head ID strap masters
(g3/head_master_odd_tr2.py, OWNER 10-25 07:01 option B): e1 = {e1, e3}, e5 = {e5, e7}, strap_bsel[1:0] tied at the parent.

The rebased KV plan (main) declares hard cores head*_e3 / head*_e7 as kv3_head_eighth_e1 / _e5 with straps
strap_bsel = (e-1)//2, but the composition spec (head_clk_merge.py output) still built four odd composites with the
.bsel constants inside, so the strict bind stopped at 'parent ID kv3_hg: declarations do not match bound known strap
inputs (head*_e{1,3,5,7}, strap_bsel)'.  Same mechanism the even composites already use (strap_hid / strap_bsel):
  * every odd composite core: module -> its master (MASTER), composite port names mapped to the master's lane prefixes
    (head_master_odd_tr2.portmap: e3 g_t_6/7 -> g_t_2/3, e7 g_t_14/15 -> g_t_10/11; the plan's core_conns use the same);
  * new composite input strap_bsel[1:0] = the exact .bsel terminals of the core's ot_qkh_lane8 members (*__u_l8);
    the as-built constants stay endpoint constants, so the bind's ID-strap check proves value == declared bsel.
bind_compose then requires e1/e3 (e5/e7) composites to be textually identical ('same module ... use explicit variants'),
which is the structural proof that the master + strap IS each old variant.
usage: head_odd_strap_compose_0150.py SPEC_IN.json.gz SPEC_OUT.json.gz REPORT.json"""
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "g3"))
from head_master_odd_tr2 import MASTER, portmap  # noqa: E402


def main(spec_in, spec_out, rep):
    spec = json.loads(gzip.decompress(Path(spec_in).read_bytes()))
    recs = []
    for c in spec["cores"]:
        m = re.fullmatch(r"kv3_head_eighth_e([1357])", c["module"])
        if not m:
            continue
        e = int(m.group(1))
        if "strap_bsel" in c["ports"]:
            raise SystemExit(f"{c['inst']}: already has strap_bsel")
        ports = {portmap(k, e): v for k, v in c["ports"].items()}
        if len(ports) != len(c["ports"]):
            raise SystemExit(f"{c['inst']}: port rename collision")
        l8 = [x for x in c["members"] if x.endswith("__u_l8")]
        if len(l8) != 2:
            raise SystemExit(f"{c['inst']}: expected 2 ot_qkh_lane8 members, got {l8}")
        ports["strap_bsel"] = dict(dir="input", bits=[[dict(member=x, port="bsel", bit=b) for x in l8] for b in (0, 1)],
                                   indices=[0, 1])
        recs.append(dict(inst=c["inst"], was=c["module"], master=f"kv3_head_eighth_e{MASTER[e]}", bsel=f"{(e - 1) // 2:02b}",
                         ports_renamed=sum(1 for k in c["ports"] if portmap(k, e) != k)))
        c["module"] = f"kv3_head_eighth_e{MASTER[e]}"
        c["ports"] = ports
    raw = json.dumps(spec).encode()
    Path(spec_out).write_bytes(gzip.compress(raw, mtime=0))
    import hashlib
    Path(rep).write_text(json.dumps(dict(schema="opentallas.kv.head_odd_strap_compose.v1", cores=len(recs),
                                         by_master={k: sum(1 for r in recs if r["master"] == k) for k in sorted({r["master"] for r in recs})},
                                         json_sha256=hashlib.sha256(raw).hexdigest(), first=recs[:8]), indent=1) + "\n")
    print(f"{len(recs)} odd composites -> masters e1/e5 with strap_bsel")


if __name__ == "__main__":
    main(*sys.argv[1:])
