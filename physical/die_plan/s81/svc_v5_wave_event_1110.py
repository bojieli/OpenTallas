#!/usr/bin/env python3
"""S81 svc_rs plan event: form A v5 rebased onto the kit-wave plan (S81-SVCRS-3, COORD 11-10).

Three-way: base = main plan (== v5 event base on every non-svc type), ours = wave plan, theirs = v5.
 - die / partitions / ports / reset / clock: v5 changed them, the wave did not -> take v5.
 - lanes / latency / note and the 191 non-svc_rs types: wave -> kept as is (keys unchanged).
 - the 14 svc_rs blocks: v5 block + the wave's only edit (clock.tap_pair_affinity) + port_buf_at_pin.
Every precondition is asserted; any mismatch stops the event.
usage: svc_v5_wave_event_1110.py WAVE_PLAN V5_PLAN_GZ MAIN_PLAN OUT_PLAN OUT_RECORD
"""
import copy, gzip, hashlib, json, sys

DIE_KEYS = ("die", "partitions", "ports", "reset", "clock")
WAVE_KEYS = ("lanes", "latency", "note", "budgets", "census", "schema")


def fp(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode()).hexdigest()


def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))


def main(wave_p, v5_p, main_p, out_p, rec_p):
    wave, v5, base = load(wave_p), load(v5_p), load(main_p)
    names = sorted(n for n in v5["partition_types"] if "svc_rs" in n)
    assert len(names) == 14, names
    assert set(wave["partition_types"]) == set(v5["partition_types"]) == set(base["partition_types"])
    for k in DIE_KEYS:
        assert fp(wave[k]) == fp(base[k]), f"wave changed {k}: not a clean three-way"
    for n in v5["partition_types"]:
        if n not in names:
            assert fp(v5["partition_types"][n]) == fp(base["partition_types"][n]), f"v5 changed non-svc type {n}"
    out = copy.deepcopy(wave)
    for k in DIE_KEYS:
        out[k] = copy.deepcopy(v5[k])
    rows = {}
    for n in names:
        w, b, v = wave["partition_types"][n], base["partition_types"][n], v5["partition_types"][n]
        # the wave's only edit on these blocks vs main must be clock.tap_pair_affinity (+ port_buf_at_pin)
        wc, bc = copy.deepcopy(w), copy.deepcopy(b)
        tpa = wc["clock"].pop("tap_pair_affinity", None)
        bc["clock"].pop("tap_pair_affinity", None)
        wc.pop("port_buf_at_pin", None); bc.pop("port_buf_at_pin", None)
        assert fp(wc) == fp(bc), f"{n}: wave block differs from main beyond tap_pair_affinity"
        nb = copy.deepcopy(v)
        assert "tap_pair_affinity" not in nb["clock"], n
        if tpa is not None:
            nb["clock"]["tap_pair_affinity"] = tpa
        nb["port_buf_at_pin"] = True
        out["partition_types"][n] = nb
        cnt = lambda blk: {m: sum(1 for x in blk["hard_cores"] if x["module"] == m)
                           for m in sorted({x["module"] for x in blk["hard_cores"]})}
        rows[n] = dict(old_block_sha=fp(w), new_block_sha=fp(nb), old_outline_um=w["outline_um"],
                       new_outline_um=nb["outline_um"], old_hard_cores=cnt(w), new_hard_cores=cnt(nb),
                       views=sorted({(x["module"], x.get("lef"), x.get("lib")) for x in nb["hard_cores"]}))
    for n in out["partition_types"]:
        if n not in names:
            assert fp(out["partition_types"][n]) == fp(wave["partition_types"][n]), n
    for k in WAVE_KEYS:
        assert fp(out.get(k)) == fp(wave.get(k)), k
    s = json.dumps(out, indent=1) + "\n"
    open(out_p, "w").write(s)
    rec = dict(schema="opentallas.s81_svc_v5_wave_event.v1", tool="svc_v5_wave_event_1110.py",
               lane="S81-SVCRS-3", ruling="COORD 11-10: one batch plan event, v5 as the svc_rs binding",
               inputs=dict(wave=dict(path=wave_p, sha256=hashlib.sha256(open(wave_p, "rb").read()).hexdigest()),
                           v5=dict(path=v5_p, sha256=hashlib.sha256(open(v5_p, "rb").read()).hexdigest()),
                           main=dict(path=main_p, sha256=hashlib.sha256(open(main_p, "rb").read()).hexdigest())),
               output=dict(path=out_p, sha256=hashlib.sha256(s.encode()).hexdigest()),
               taken_from_v5=list(DIE_KEYS), kept_from_wave=list(WAVE_KEYS) + ["191 non-svc_rs partition_types"],
               unchanged_other_types=len(out["partition_types"]) - len(names), rows=rows)
    json.dump(rec, open(rec_p, "w"), indent=1)
    print("OK", rec["output"]["sha256"][:16], "rows", len(rows), "others unchanged", rec["unchanged_other_types"])


if __name__ == "__main__":
    main(*sys.argv[1:6])
