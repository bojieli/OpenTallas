#!/usr/bin/env python3
"""S81 SU / HC slab transport budget (stream s81-suhc-1011, 2026-10-11).

The token path prices every critical SU / HC job on a fused full-width unit (ot_dsrom_su_norm N 1024, su_hcpost
NG 256, su_swiglu W 1024, su_qbank NB 32) fed at its full lane width: a vector of N binary32 words a cycle at
1.2 GHz behind the 33 / 23 stage hub traverse.  The S81 die gives each SU half one 1024-b bus from the VM and one
512-b bus to HC.  The VM row is 512 b = 16 binary32 words (ot_s81ph_vm_mem), so a die bus of S row slots
moves 16*S words a cycle.

Per job: T(S_in, S_out) = price + max(0, ceil(rows_in / S_in) - beats_in) + max(0, ceil(rows_out / S_out) - beats_out),
where beats are the unit's own input / output beats already inside the price (the extra cycles are the transport
that the narrow bus serialises in front of / behind the unit).  Qualification: T <= 1.10 x price.
Writes the minimum S_in / S_out per job and the token-path cost of the die's current buses.

    python3 tools/s81_suhc/transport_model.py --out results/arch/s81_suhc_20261011/transport_model.json
"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TP = ROOT / "results/arch/token_path_20261009/ds_rom.json"
W = 16                                  # binary32 words per VM row

# job op -> (engine, words in, words out, unit beats in, unit beats out, unit) ; shapes from the unit benches
JOBS = {
    "attn.quant":     ("su", 4 * 5120, 5120 // 4 + 160, 5, 5, "ot_dsrom_su_norm HC=1 N1024 D5120 QUANT (FP8 codes 4/word + 160 exps)"),
    "ffn.norm.scale": ("su", 4 * 5120, 5120, 5, 5, "ot_dsrom_su_norm HC=1 N1024 D5120 (BF16 y as binary32)"),
    "attn.q_quant":   ("su", 1280, 1280 // 4 + 40, 5, 5, "ot_dsrom_su_norm HC=0 N256 D1280 QUANT"),
    "attn.kv_rope_qdq": ("su", 512, 512, 1, 1, "ot_dsrom_su_norm HC=0 N512 D512 RD64 QDQ"),
    "ffn.quant2":     ("su", 2 * 4096, 4096 // 4 + 128, 4, 4, "ot_dsrom_su_swiglu W1024, 4 vectors (g,u in; codes out)"),
    "attn.z_quant":   ("su", 2048, 2048 // 4 + 64, 2, 2, "ot_dsrom_su_qbank NB32, 2 beats"),
    "attn.hc_post":   ("hc", 5 * 5120, 4 * 5120, 20, 20, "ot_dsrom_su_hcpost NG256 (r0..r3 + y in, 4x5120 out)"),
    "ffn.hc_post":    ("hc", 5 * 5120, 4 * 5120, 20, 20, "ot_dsrom_su_hcpost NG256"),
}
DIE = dict(su=dict(s_in=2 * 2, s_out=2 * 1), hc=dict(s_in=2, s_out=2))   # SU: two halves x (1024 in, 512 out); HC: f_vm 1024 / t_vm 1024


def t(price, rin, rout, bin_, bout, s_in, s_out):
    return price + max(0, math.ceil(rin / s_in) - bin_) + max(0, math.ceil(rout / s_out) - bout)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    tp = json.loads(TP.read_text())
    per = {}
    for n in tp["nodes"]:
        if n["op"] in JOBS and n["critical"]:
            per.setdefault(n["op"], []).append(n["cycles"])
    rows, extra_tok = [], 0.0
    for op, (eng, win, wout, bin_, bout, unit) in JOBS.items():
        price = max(per.get(op, [0]) or [0])
        nc = len(per.get(op, []))
        rin, rout = math.ceil(win / W), math.ceil(wout / W)
        d = DIE[eng]
        tdie = t(price, rin, rout, bin_, bout, d["s_in"], d["s_out"])
        smin = None
        for s in (1, 2, 4, 8, 16, 32, 64, 128):
            if t(price, rin, rout, bin_, bout, s, s) <= 1.10 * price:
                smin = s
                break
        extra_tok += (tdie - price) * nc
        rows.append(dict(op=op, engine=eng, unit=unit, price=price, critical_instances=nc, rows_in=rin, rows_out=rout,
                         die_slots_in=d["s_in"], die_slots_out=d["s_out"], cycles_at_die_buses=tdie,
                         ratio_at_die_buses=round(tdie / price, 3) if price else None,
                         min_slots_each_way_for_1p10=smin))
    out = dict(schema="opentallas.s81_suhc.transport.v1", token_path=str(TP.relative_to(ROOT)), row_words=W,
               rule="T(S) = price + serialised transport beyond the unit's own beats; qualify T <= 1.10 x price",
               jobs=rows, critical_extra_cycles_per_token_at_die_buses=round(extra_tok, 1),
               token_cycles=tp["totals"].get("cycles") if isinstance(tp.get("totals"), dict) else None)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(f"{r['op']:18} {r['engine']} price {r['price']:7.1f} x{r['critical_instances']:3}  die {r['cycles_at_die_buses']:7.1f} "
              f"({r['ratio_at_die_buses']}x)  min slots {r['min_slots_each_way_for_1p10']}")
    print("critical extra cycles / token at die buses:", out["critical_extra_cycles_per_token_at_die_buses"], "token", out["token_cycles"])


if __name__ == "__main__":
    main()
