#!/usr/bin/env python3
"""Untrusted loaded-valid hints on the exact retained LN7 lane40..43 AIGs.

No RTL changes and no constant replacement outside its native valid guard.
The entire retained hypothesis profile is re-proved jointly with the hints.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--tool", type=Path, required=True)
    ap.add_argument("--mutant", action="store_true")
    ap.add_argument("--restore-native-profile", action="store_true")
    ap.add_argument("--fresh-correspond", action="store_true")
    ap.add_argument("--restore-keymaps", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, str(a.tool.parent))
    import lec
    lec.PROVE_JOBS = 8
    a.out.mkdir(parents=True, exist_ok=True)
    started = time.time()

    class Log(list):
        def append(self, s):
            super().append(s)
            with (a.out / "proof.log").open("a") as f:
                f.write(s + "\n")
            print(s[:240], flush=True)

    log = Log()
    old = json.loads((a.input / "lec.json").read_text())
    contract = lec.reset_contract_gate(a.kit, old["top"])
    assert contract["used"] == old["reset_contract"]["used"] == 64
    L = lec.Lec(lec.read_aig(a.input / "gold.aig"), lec.read_map(a.input / "gold.map"),
                lec.read_aig(a.input / "gate.aig"), lec.read_map(a.input / "gate.map"))
    L.kit_reset_ports = old["kit_reset_ports"]
    profile = json.loads((a.input / "hyp.json").read_text())
    if a.restore_keymaps or a.fresh_correspond:
        for src in a.input.glob("*aliases.json"):
            shutil.copy2(src, a.out / src.name)
    if a.restore_keymaps:
        # Exact native keymap setup, with retained frontend alias metadata.
        lec.normalize_gold_elements(L, lec.slang_elements(a.out / "gold.aliases.json"), log)
        lec.json_alias_keys(L, log, work=a.out)
        lec.slang_element_keys(L, log, work=a.out)
        lec.alias_arrays(L, log, work=a.out)
        lec.relayout(L, log, packed=lec.slang_packed_vectors(a.out / "gold.aliases.json"))
        lec.renamed(L, log)
    if a.fresh_correspond:
        # Correspondence also rekeys frontend array aliases; hyp.json alone
        # cannot restore those key maps. Re-run the native algorithm on the
        # exact retained AIGs, then add only the new conditional hints.
        lec.correspond(L, a.out, 10000, log)
    hints = []
    groups = collections.Counter()
    pat = re.compile(r"^(ff:u_dut\.u_fcore\.u_core\.u_lane([0-3])\.u_lane\.g_ld3k)"
                     r"\.g_s\[([0-4])\]\.(p0|p2|q2)\[(\d+)\]$")
    for key in L.gonly:
        m = pat.fullmatch(key)
        if not m or int(m[5]) >= 24:
            continue
        lane, kind = int(m[2]), m[4]
        if kind == "p0" and lane != 0:
            continue
        # LN7 G1=3/G2=6: lane40 low3=0, all40..43 bit6=0.
        guard = m[1] + (".ldq_v" if kind == "q2" else ".ldp_v")
        assert guard in L.gp
        hints.append(["gold", key, ["loaded", 0, [[[guard, 1]]]]])
        groups[f"lane{lane}.{kind}"] += 1
    assert len(hints) == 1080, (len(hints), groups)
    assert groups["lane0.p0"] == 120
    for lane in range(4):
        assert groups[f"lane{lane}.p2"] == groups[f"lane{lane}.q2"] == 120
    if a.mutant:
        hints[0][2][1] = 1  # actual source always loads this partial sum with zero
    (a.out / "loaded_hints.json").write_text(json.dumps(hints, indent=1) + "\n")
    log.append(f"Loaded {len(profile)} retained untrusted hypotheses + {len(hints)} loaded hints; mutant={a.mutant}")
    if a.fresh_correspond:
        rec = lec.apply_hints(L, hints, a.out, 10000, log)
    elif a.restore_native_profile:
        # Restore the exact native compare inventory. Generic apply_hints also
        # exposes anonymous state as additional compare points; that is a
        # different proof vehicle from the original no-hint run. The existing
        # transfer API re-sides stale profile roles without assuming them.
        transfer = lec.transfer_profile(L, profile, log)
        rec = lec.apply_hints(L, hints, a.out, 10000, log, propose_only=True)
        assert rec["applied"] == 1080 and not rec["skipped"] and not rec["loaded_refused"]
        lec.noreset_filter(L, log, collections.Counter(), a.out, 10000)
        joint = lec.prove_profile(L, a.out, 10000, log)
        rec["dropped"] = joint["dropped"]
        rec["loaded"] = [dict(register=k, value=h[1], guard=h[2])
                         for (sd, k), h in L.hyp.items() if h[0] == "loaded"]
        rec["profile_transfer"] = transfer
        rec["joint_rounds"] = joint["rounds"]
    else:
        rec = lec.apply_hints(L, profile + hints, a.out, 10000, log)
    # apply_hints proves every retained and new hypothesis together and drops failures.
    (a.out / "proved_hyp.json").write_text(json.dumps([[sd, k, list(h)] for (sd, k), h in sorted(L.hyp.items())]) + "\n")
    miter, _ = L.build(with_compare=True, with_hyp=True)
    status = lec.prove(miter, a.out, 10000, log, tag="native_compare")
    counts = dict(collections.Counter(status.values()))
    bad = {k: v for k, v in status.items() if v != "proved"}
    if a.mutant:
        verdict = "MUTANT_CAUGHT" if rec["dropped"] and bad else "MUTANT_NOT_CAUGHT"
    else:
        verdict = "EQUIVALENT" if not bad and len(rec["loaded"]) == 1080 else "NOT_EQUIVALENT"
    result = dict(verdict=verdict, input=str(a.input), top=old["top"], reset_contract=contract,
                  tool_sha256=hashlib.sha256(a.tool.read_bytes()).hexdigest(),
                  input_hashes={n: hashlib.sha256((a.input / n).read_bytes()).hexdigest()
                                for n in ["gold.aig", "gate.aig", "gold.map", "gate.map", "hyp.json"]},
                  groups=dict(groups), supplied_loaded=len(hints), kept_loaded=len(rec["loaded"]),
                  retained_hypotheses=len(profile), hint_report=rec, counts=counts, bad=bad,
                  restore_native_profile=a.restore_native_profile, fresh_correspond=a.fresh_correspond, restore_keymaps=a.restore_keymaps,
                  added_cycles=0, rtl_changes=0, elapsed_seconds=round(time.time()-started, 2))
    (a.out / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ["verdict", "supplied_loaded", "kept_loaded", "counts", "elapsed_seconds"]}), flush=True)
    return 0 if verdict in ("EQUIVALENT", "MUTANT_CAUGHT") else 1


if __name__ == "__main__":
    sys.exit(main())
