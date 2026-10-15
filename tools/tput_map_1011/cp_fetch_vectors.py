#!/usr/bin/env python3
"""tput-map-1011 / F2: CP.FETCH production-shape vectors for rtl/hbm_accel/generic/tb/tb_hgi_cp_die_seq.sv.

The DS AR 1M token program of record (results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json, the G25 rank-0
program that throughput_budget prices) is encoded by the simulator's own encoder (hgi_sim.records.encode_program), a
CTL.END (wait all units, A = the token word in VM) is appended (the rank-0 export ends at COLL.ARGMAX_MERGE), and the
HGI-1 v1.0 reference sequencer (tools/hgi_seq_vectors.Ref) produces the exact dispatch vectors.  The bench's mem files
are written to --out (the tb reads them by bare name from its run directory), so the committed hgi_seq_*.mem are not
touched.

The CP-alone PRICE of the same records: T.schedule(recs, "S2") with every unit cost 0 (price.S2_zero_unit_cost_cycles,
the number the bench is graded against); also listed, the simulator's S2 CP terms (tools/hgi_sim/timing.py schedule) with
every unit at zero cost and no waits: fetch_ready(k) = fetch_latency + ceil(end_k / fetch_req_bytes) * fetch_issue,
dec = max(dec + dcyc, fetch_ready + dcyc), ready = dec + addr_latency; the price is the last record's ready time.

    python3 tools/tput_map_1011/cp_fetch_vectors.py --out DIR [--pos 1048575] [--rank 0]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import hbm_generic_iface as G  # noqa: E402
import hgi_seq_vectors as V  # noqa: E402
from hgi_sim import ds_native_timing as DT  # noqa: E402
from hgi_sim import records as SR  # noqa: E402
from hgi_sim import timing as T  # noqa: E402

PROG = ROOT / "results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json"
TOK_ADDR, TOK = 0x8001, 4242


def price(recs, nbytes_end):
    cpc = T.CAL["cp"]
    v = lambda k: cpc[k]["value"]  # noqa: E731
    lat, iss, req = v("fetch_latency"), v("fetch_issue_cycles"), v("fetch_req_bytes")
    dh, dpc, al = v("decode_header"), v("decode_per_chunk"), v("addr_latency")
    dec, ready, off = 0.0, 0.0, 0
    for r, e in zip(recs, nbytes_end):
        if r.unit == "CTL" and r.op in ("NOP", "FENCE", "END"):
            pass
        nch = (1 if r.sut is not None else 0) + len(r.descs_in_order())
        dcyc = dh + nch * dpc
        fr = lat + math.ceil(e / req) * iss
        dec = max(dec + dcyc, fr + dcyc)
        ready = dec + al
    return dict(cycles=round(ready, 1), fetch_latency=lat, fetch_issue_cycles=iss, fetch_req_bytes=req,
                decode_header=dh, decode_per_chunk=dpc, addr_latency=al,
                fetch_only_cycles=round(lat + math.ceil(nbytes_end[-1] / req) * iss, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pos", type=int, default=(1 << 20) - 1)
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--nowait", action="store_true", help="diagnostic: clear every record's wait mask (dispatch path alone)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    _, recs = DT.load(PROG)
    recs = T.rebuild_waits(recs)                    # the wait masks the budget's S2 schedule prices (build.py ds_budget)
    if a.nowait:
        for r in recs:
            r.wait = 0
    b = SR.encode_program(recs)
    words = [int.from_bytes(b[q:q + 16], "little") for q in range(0, len(b), 16)]
    words += V.record(V.header("CTL", "END", wait=0xFFFE), descs=dict(A=V.mdesc(space=1, fmt=5, base=TOK_ADDR, n=1)))
    assert len(words) < (1 << 16), len(words)
    ends, o = [], 0
    for r in recs:
        o += SR.rec_bytes(r)
        ends.append(o)
    VM0 = {TOK_ADDR: TOK}
    D = dict(vocab=129280, ctxmax=1 << 20)
    ref = V.Ref(words, 0, 3, a.pos, a.rank, D["vocab"], D["ctxmax"], VM0, lambda k, u, o_: [], ncol=1)
    tr, cpl = ref.run()
    if getattr(ref, "fault", None) or cpl != (TOK, 0):
        raise SystemExit(f"reference fault {getattr(ref, 'fault', None)} cpl {cpl}")
    exp = []
    for d in tr:
        meta_w = d["unit"] | d["L"] << 4 | d["L1"] << 20 | (d["pos1"] & V.M21) << 36 | (d["pslot1"] & V.M21) << 57
        exp += [meta_w, d["hdr"], d["sut"]] + d["eff"] + [sum((n & V.M21) << (21 * j) for j, n in enumerate(d["n"]))]
    O = a.out
    (O / "hgi_seq_image.mem").write_text("\n".join(f"{w:032X}" for w in words) + "\n")
    (O / "hgi_seq_expect.mem").write_text("\n".join(f"{x:064X}" for x in exp) + "\n")
    cfg = [0, 3, a.pos, a.rank, D["vocab"], D["ctxmax"], len(tr), cpl[0], cpl[1], 0xFFFF, 0, 0 | (1 << 8)]
    (O / "hgi_seq_cfg.mem").write_text(" ".join(f"{v:08X}" for v in cfg) + "\n")
    mds = G.d_pack(dict(magic=G.MAGIC, ver_minor=G.D_VERSION[1], ver_major=G.D_VERSION[0], n_words=G.NWORDS,
                        cp_vocab=D["vocab"], cp_ctx_max=D["ctxmax"], coll_group_size=96, entry_ar=0,
                        image_base=0x10, image_pages=1))
    (O / "hgi_seq_md.mem").write_text("\n".join(f"{x:08X}" for x in mds) + "\n")
    (O / "hgi_seq_toks.mem").write_text(" ".join(["0000000000000000"] * 16) + "\n")
    (O / "hgi_seq_vmw.mem").write_text("00000000" * 3 + "\n")
    (O / "hgi_seq_vm0.mem").write_text("\n".join(f"{k:08X}{v:08X}" for k, v in sorted(VM0.items())) + "\n")
    (O / "hgi_seq_sizes.svh").write_text("// GENERATED by tools/tput_map_1011/cp_fetch_vectors.py\n" + "\n".join(
        f"localparam integer {k} = {v};" for k, v in dict(SEQ_NW=len(words), SEQ_NCASE=1, SEQ_NCASE_STALE=1,
                                                         SEQ_NEXP=len(exp), SEQ_NEXP_STALE=1, SEQ_NVM0=len(VM0)).items()) + "\n")
    pr = price(recs, ends)
    # the simulator's CP-alone price: the S2 schedule (fetch, decode, address, wait rule, dispatch / retire wires) with
    # every unit at zero cost -- the same records, the same schedule code throughput_budget prices the token with
    z = T.schedule(recs, DT.POS, "S2", cost_fn=lambda r, dyn, L: (0.0,))
    pr["S2_zero_unit_cost_cycles"] = round(z["total_cycles"], 1)
    man = dict(program=str(PROG.relative_to(ROOT)), records=len(recs), image_bytes=len(b), words128=len(words),
               dispatches=len(tr), pos=a.pos, rank=a.rank, token=TOK, price=pr)
    (O / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man))


if __name__ == "__main__":
    main()
