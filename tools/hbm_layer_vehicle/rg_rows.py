#!/usr/bin/env python3
"""VEH-FMT-SFU / ROW_GATHER (10-19): regenerate the REAL compressed-KV rows a COLL.ROW_GATHER record moves (the fixture
holds only (addr, bytes, sha256) of its HBM operands) from the released-checkpoint reference state, and the row list a
rank contributes.

Source of the rows (no placeholders): w19_hbm_tp96_isa.State(m, ctx 1,048,576, seed 20260930, {L}) -- the W17 reference
decode state: every compressed row of KV source s = qdq_fp4_e4m3(LC._gained(rng[seed, ctx, 1, s], ..., gain =
attn.compressor.norm.weight of layer s from the released checkpoint)), plus this token's appended row (refs
ctx1048576_L<s>.npz ckv<s>, the golden's own KVWB value).  Ownership / HBM placement exactly as ds_native: row i lives on
rank (i // 8) % 96 at local row (i // 768) * 8 + i % 8 of source slot SOURCES.index(s) of the per-die CKSTORE, byte
address A.base + local * 2048 (A.base = the record's A descriptor = local row 0 of slot s).
Checks (each must hold or the script fails): sha256(row 0 of rank 0's slot) == the fixture's A input sha; the fixture's
I words == the record's selection; the fixture's O sha is matched against the gathered row list (reported).
Out: <out>/<name>.npz (sel, owner, local, addr, rows FP32 [512 x 512]) + <name>.json (shas, rank-0 owned rows).

    HDC_V41_ARITH=chunk8 OT_V41_FLASH_SNAPSHOT=<ckpt> python3 tools/hbm_layer_vehicle/rg_rows.py \
        --fixtures <fix>/L02 <fix>/L03 <fix>/L14 --refs <refs> --out <out>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hgi_sim"))

import w19_hbm_tp96_isa as W  # noqa: E402

SOURCES = [2, 8, 14, 20]          # hgi_sim/ds_native.SOURCES (CKSTORE slot order)
ROW_B = 2048


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", nargs="+", type=Path, required=True)
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rank", type=int, default=0)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    ref = json.loads(W.REF_RECORD.read_text())
    ctx, seed = ref["context"], ref["seed"]
    ck = W.LC.Checkpoint()
    m, _ = W.LC.build_model(ck, engram=False)
    todo = []
    for fd in a.fixtures:
        r = json.loads((fd / "records.json").read_text())
        z = np.load(fd / "operands.npz")
        for _, rr in sorted(r["records"].items()):
            for x in rr:
                if x["op"] == "COLL.ROW_GATHER" and x.get("family") == "kv_gather":
                    todo.append((fd, x, z))
                elif x["op"] == "COLL.ROW_GATHER":
                    print(f"SKIP {fd.name} k{x['k']} {x['tag']} family {x.get('family')}: not a compressed-KV gather")
    srcs = sorted({m.kv_of[x["layer"]] for _, x, _ in todo})
    st = W.State(m, ctx, seed, {L for L in {x["layer"] for _, x, _ in todo}})
    for s in srcs:                                # this token's appended row (the golden's KVWB value)
        zf = a.refs / f"ctx{ctx}_L{s:02d}.npz"
        zz = np.load(zf)
        if f"ckv{s}" in zz.files:
            st.ckv[s][st.n[s]] = zz[f"ckv{s}"]
    ok = True
    for fd, x, z in todo:
        L, s, k = x["layer"], m.kv_of[x["layer"]], x["k"]
        sel = z[f"r0.k{k}.I"].astype(np.int64)
        assert sha(z[f"r0.k{k}.I"]) == x["inputs"]["I"]["sha256"]
        rows = st.ckv[s][sel].astype(np.float32)
        if np.isnan(rows).any():
            raise SystemExit(f"{fd.name} k{k}: a selected row was never written (sel max {sel.max()}, n {st.n[s]})")
        owner = W.key_owner(sel)
        local = (sel // (W.KEY_BLOCK * W.TP)) * W.KEY_BLOCK + sel % W.KEY_BLOCK
        base = x["desc"]["A"][0]
        addr = base + local * ROW_B
        a0 = sha(st.ckv[s][0].astype(np.float32))          # rank 0, local row 0 of slot s
        a_ok = a0 == x["inputs"]["A"]["sha256"]
        o_sha = x["outputs"]["O"]["sha256"]
        o_hit = [int(i) for i in range(len(sel)) if sha(rows[i]) == o_sha]
        mine = owner == a.rank
        name = f"ds_l{L}_k{k}_rg"
        np.savez_compressed(a.out / f"{name}.npz", sel=sel.astype(np.uint32), owner=owner.astype(np.uint8),
                            local=local.astype(np.uint32), addr=addr.astype(np.uint64), rows=rows.view(np.uint32))
        info = dict(name=name, layer=L, k=k, source=s, tag=x["tag"], n_sel=len(sel), rows_sha256=sha(rows),
                    a_row0_sha256=a0, fixture_a_sha256=x["inputs"]["A"]["sha256"], a_match=a_ok,
                    fixture_o_sha256=o_sha, o_matches_sel_index=o_hit, state_sha=st.sha.get(f"ckv{s}"),
                    rank=a.rank, rank_owned=int(mine.sum()), rank_owned_sel=sel[mine].tolist(),
                    rank_owned_local=local[mine].tolist(), rank_owned_addr=[int(v) for v in addr[mine]],
                    rank_owned_rows_sha256=sha(rows[mine]),
                    provenance="w19_hbm_tp96_isa.State (released checkpoint gains + seeded reference state) + refs appended row")
        (a.out / f"{name}.json").write_text(json.dumps(info, indent=1) + "\n")
        print(f"{name}: A row0 {'MATCH' if a_ok else 'MISMATCH'}  O first-row hit {o_hit[:4]}  rank{a.rank} owns "
              f"{int(mine.sum())}/{len(sel)}")
        ok &= a_ok
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
