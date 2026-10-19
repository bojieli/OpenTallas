#!/usr/bin/env python3
"""LAYERBENCH-HBM (10-18): DeepSeek-V4.1 per-layer, per-RECORD golden fixtures for the d4g layer bench.

Runs the bit-exact native HGI-1 DeepSeek programme (tools/hgi_sim/ds_native.py: the released checkpoint at 1M context,
each layer entered from the W17 reference shards and checked bit for bit against them) for ONE representative layer
(or the head) and captures, on the chosen ranks, for every dispatched record k:
  * the effective operand descriptors the dispatcher hands the unit (ds_native._eff_trace);
  * every VM operand read by the record BEFORE it executes (raw u32 words, so FP32 / BF16 / U32 are bit exact);
  * the VM output O AFTER it executes (raw u32 words);
  * HBM operands as (address, bytes, sha256) of the bytes the record reads (the weights / tables / KV live in the
    die's HBM image, which ds_native --export-images and the image manifest place; a bench loads them into the DRAM
    model behind the PHY, it does not carry them per record);
  * STREAM operands as descriptors (their values are the producer's O / the consumer's operand).
Records are then matched to the d4g price of record (priced_layers.json segments[L].records, the schedule contract)
by (unit.op, tag, occurrence): each fixture entry carries the priced record index i, start / end (commit-cycle
assertion targets) and d4g placement class.

PLACEMENT (stated, not hidden): the bit-exact DeepSeek programme that exists is TP-96 (32-SM die, 96 dies,
w19_hbm_tp96_isa Compiler variant oreduce).  The d4g price (16 SM / 2 stacks, TP-192) is that programme under the
ds_die_split SPLIT TRANSFORM; no native TP-192 DeepSeek programme exists yet.  The per-record fixtures are therefore
the TP-96 rank-r records.  Row-split records (SM.MATVEC by output rows, ROW_NORM, element-wise SU templates) map onto
d4g dies 2r and 2r+1 by halving the row range (same arithmetic); K-split / reduction-tree records (wo_a K-split,
COLL.GROUP_REDUCE_MCAST o-groups, ALL_REDUCE, COLL merges) need the TP-192 programme (the DS analogue of Qwen's
D4G8 mapping) before a d4g fixture can claim the golden's tree; they are flagged needs_tp192_programme.

    HDC_V41_ARITH=chunk8 NPY_DISABLE_CPU_FEATURES=... OT_V41_FLASH_SNAPSHOT=CKPT python3 \
        tools/hbm_next/vehicle/ds_layer_fixtures.py --layer 0 --ranks 0 --refs REFS --out FIXDIR
    (--layer head for the LM head; writes FIXDIR/<L>/{records.json, operands.npz, images/, ds_native.json,
     manifest.json}; manifest = sha256 of every file and of every operand array)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[2]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
from hgi_sim import ds_native as DN  # noqa: E402

PRICED = ROOT / "results/rtl/hbm_ds_layer_tput_1018/priced_layers.json"
ROW_SPLIT = {"SM.MATVEC", "ROW_NORM.ROW_NORM", "SU.VOP", "SFU.GLU", "FUSED.QDQ_FP8", "DMA.LOAD", "DMA.KVWB_DS",
             "DMA.STORE", "IDX.INDEX_Q", "ATT.QK", "ATT.PV", "FUSED.HC_PRE_NORM", "FUSED.HC_POST", "HC.HC_MIX"}
TREE = {"COLL.GROUP_REDUCE_MCAST", "COLL.ALL_REDUCE_SUM", "COLL.TOPK_MERGE", "COLL.ARGMAX_MERGE"}


def sha(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


class Capture:
    """wraps the unit handlers: VM operands before, O after, on the capture ranks"""

    def __init__(self, ranks):
        self.ranks = set(ranks)
        self.rows = {r: [] for r in ranks}
        self.arrays = {}
        self.n = Counter()

    def wrap(self, units):
        out = {}
        for key, fn in units.items():
            def w(M, r, L, _fn=fn, _key=key):
                dies = [d for d in M.dies if d.rank in self.ranks]
                pre = {d.rank: self._operands(M, d, r, L, before=True) for d in dies}
                res = _fn(M, r, L)
                for d in dies:
                    self._commit(M, d, r, L, pre[d.rank])
                return res
            out[key] = w
        return out

    def _operands(self, M, die, r, L, before):
        cur, dies = M.cur, M.dies
        M.cur, M.dies = r, [die]
        got = {}
        try:
            for k, d in r.desc.items():
                if (k == "O") == before:
                    continue
                if d.space == "VM":
                    try:
                        got[k] = ("VM", die.vm[M.vm_addrs(d, die, L)].copy())
                    except Exception as e:      # noqa: BLE001 -- an operand the dispatcher would fault on is recorded
                        got[k] = ("ERR", str(e))
                elif d.space == "HBM":
                    base, n, m, st, ist = M.eff(d, die, L)
                    try:
                        raw = M.hbm_rows_raw(d, die, L)
                        got[k] = ("HBM", dict(addr=int(base), bytes=int(np.asarray(raw).nbytes), sha256=sha(raw)))
                    except Exception as e:      # noqa: BLE001
                        got[k] = ("HBM", dict(addr=int(base), n=int(n), m=int(m), stride=int(st), err=str(e)))
                else:
                    got[k] = (d.space, None)
            return got
        finally:
            M.cur, M.dies = cur, dies

    def _commit(self, M, die, r, L, pre):
        post = self._operands(M, die, r, L, before=False)
        rk = die.rank
        k = len(self.rows[rk])
        name = f"{r.unit}.{r.op}"
        occ = self.n[(rk, name, r.tag)]
        self.n[(rk, name, r.tag)] += 1
        ent = dict(k=k, L=int(L), layer=DN.CUR_LAYER[0], op=name, tag=r.tag, family=getattr(r, "family", None), occ=occ,
                   desc=DN._eff_trace(M, die, r, L), inputs={}, outputs={})
        for side, dd in (("inputs", pre), ("outputs", post)):
            for opn, (space, v) in dd.items():
                if space == "VM":
                    key = f"r{rk}.k{k}.{opn}"
                    self.arrays[key] = v
                    ent[side][opn] = dict(space="VM", array=key, words=int(v.size), sha256=sha(v))
                else:
                    ent[side][opn] = dict(space=space, **(v if isinstance(v, dict) else {"value": v}))
        self.rows[rk].append(ent)


def match_priced(rows, layer):
    """priced record i <- native record (by unit.op, tag, occurrence)"""
    pl = json.loads(PRICED.read_text())
    seg = pl["segments"].get(str(layer))
    if seg is None:
        return None, []
    idx, seen = {}, Counter()
    for e in rows:
        idx[(e["op"], e["tag"], e["occ"])] = e
    out, miss = [], []
    for rec in seg["records"]:
        key = (rec["orig_op"], rec["tag"])
        o = seen[key]
        seen[key] += 1
        e = idx.get((rec["orig_op"], rec["tag"], o))
        if e is None:
            miss.append(dict(i=rec["i"], op=rec["orig_op"], tag=rec["tag"]))
            continue
        e.setdefault("priced", []).append(dict(i=rec["i"], start=rec["start"], end=rec["end"], cls=rec["cls"],
                                               unit=rec["unit"], base_cost=rec["base_cost"]))
        out.append(rec["i"])
    for e in rows:
        e["d4g_placement"] = ("needs_tp192_programme" if e["op"] in TREE or "K" in str(e.get("family") or "")
                              and e["op"] == "SM.MATVEC" and "wo_a" in e["tag"] else
                              "row_split_halves_on_dies_2r_2r+1" if e["op"] in ROW_SPLIT else "rank_local_or_tbd")
    return seg["cycles"], miss


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layer", required=True, help="0..42 or head")
    ap.add_argument("--ranks", default="0")
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ranks = [int(x) for x in a.ranks.split(",")]
    lay = a.layer
    out = a.out / (lay if lay == "head" else f"L{int(lay):02d}")
    out.mkdir(parents=True, exist_ok=True)
    cap = Capture(ranks)
    orig = DN.ds_units
    DN.ds_units = lambda *x, **k: cap.wrap(orig(*x, **k))
    argv = ["ds_native", "--refs", str(a.refs), "--out", str(out / "ds_native.json"),
            "--export-images", str(out / "images"), "--export-layers", lay]
    last = max(int(p.stem.split("_L")[1]) for p in a.refs.glob("ctx*_L*.npz"))
    argv += (["--layers", str(last), "--head"] if lay == "head" else ["--layers", str(int(lay))])
    sys.argv = argv
    rc = DN.main()
    rec = json.loads((out / "ds_native.json").read_text())
    verdicts = [dict(layer=r.get("layer"), verdict=r.get("verdict"), fault=r.get("fault")) for r in rec.get("results", [])]
    keep_L = "head" if lay == "head" else int(lay)
    tgt = max(e["layer"] for e in cap.rows[ranks[0]]) if lay == "head" else int(lay)
    rows = {rk: [e for e in v if e["layer"] == tgt] for rk, v in cap.rows.items()}
    for rk, v in rows.items():                     # k = dispatch index within the layer
        for j, e in enumerate(v):
            e["k_layer"] = j
    cyc, miss = match_priced(rows[ranks[0]], keep_L)
    np.savez(out / "operands.npz", **cap.arrays)
    doc = dict(schema="opentallas.hbm_ds_layer_fixture.v1", layer=keep_L, ranks=ranks, tp=DN.TP,
               placement=("TP-96 native programme (the only bit-exact DS programme); d4g TP-192 = SPLIT TRANSFORM: "
                          "row-split records map to d4g dies 2r / 2r+1 by row halves, tree/K-split records need a "
                          "TP-192 programme (d4g_placement per record)"),
               golden="released DeepSeek-V4.1-Flash checkpoint, 1M context (pos 1,048,575), W17 reference shards; "
                      "ds_native layer verdict below is the bit-exact check of the layer output",
               ds_native_verdicts=verdicts, priced_layer_cycles=cyc, priced_records_unmatched=miss,
               records={str(rk): v for rk, v in rows.items()})
    (out / "records.json").write_text(json.dumps(doc, indent=1, default=int) + "\n")
    man = dict(schema="opentallas.hbm_ds_layer_fixture_manifest.v1", layer=keep_L, files={}, arrays={})
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = dict(bytes=p.stat().st_size,
                                                        sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    man["arrays"] = {k: dict(n=int(v.size), dtype=str(v.dtype), sha256=sha(v)) for k, v in cap.arrays.items()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    ok = all(v["verdict"] == "pass" for v in verdicts)
    print(f"DS_LAYER_FIXTURE {'PASS' if ok else 'FAIL'} layer={keep_L} records={len(rows[ranks[0]])} "
          f"priced_unmatched={len(miss)} arrays={len(cap.arrays)} -> {out}")
    return 0 if ok and not rc else 1


if __name__ == "__main__":
    raise SystemExit(main())
