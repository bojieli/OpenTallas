#!/usr/bin/env python3
"""Greedy speculative-acceptance statistics from a teacher-forced main pass + DSpark drafts.

Definitions (row = (sequence j, position p)):
  g_q      main-model greedy token at position q (prediction for token q+1), over the TRACE prefix
  drafts   d_1..d_5 from the block [g_p, noise x4]; d_k targets g_{p+k}
  a        accepted drafts = leading k with d_k == g_{p+k}   (depth D = min(5, T-1-p))
  tau      tokens per verification pass = a + 1 (bonus token), over rows with full depth 5
  EXACT    the row's acceptance equals true greedy acceptance iff the trace IS the model's greedy
           text over the tokens the targets condition on: x_{p+i} == g_{p+i-1}, i = 1..min(a+1, D)
  assistant row: token p+1 lies inside an assistant span (assistant_mask of the trace)
  greedy-match rate: fraction of assistant tokens x_t with x_t == g_{t-1}

INPUT   --traces traces.json : list of {"ids", "assistant_mask", "source", "id"?}
        --main main_pass.pt (v41_stream.py)   --drafts drafts.pt (v41_dspark_tf.py)
OUTPUT  --out stats.json : per source and overall: counts, greedy-match rate, proxy tau over
        assistant spans, tau on EXACT assistant rows, accepted-length histogram, per-position
        conditional acceptance P(d_k ok | d_1..d_{k-1} ok) and marginal match P(d_k == target).
Command: python3 v41_acceptance_stats.py --traces traces.json --main main_pass.pt --drafts drafts.pt --out stats.json
"""
import argparse, json
import torch

BS = 5


def summarize(sel):
    full = [r for r in sel if r["D"] == BS]
    out = {"rows": len(sel), "rows_full_depth": len(full)}
    if not full:
        return out
    acc = torch.tensor([r["a"] for r in full], dtype=torch.float64)
    out["tau_tokens_per_verification_incl_bonus"] = (acc + 1).mean().item()
    out["tau_stderr"] = ((acc + 1).std() / len(full) ** 0.5).item() if len(full) > 1 else None
    out["mean_accepted_drafts"] = acc.mean().item()
    out["accepted_length_histogram_0..5"] = torch.bincount(acc.long(), minlength=BS + 1).tolist()
    cond, marg = [], []
    for k in range(1, BS + 1):
        reach = (acc >= k - 1).sum().item()
        cond.append((acc >= k).sum().item() / reach if reach else None)
        marg.append(sum(r["m"][k - 1] for r in full) / len(full))
    out["per_position_conditional_acceptance"] = cond
    out["per_position_marginal_match"] = marg
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--traces", required=True)
    ap.add_argument("--main", required=True)
    ap.add_argument("--drafts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tr = json.load(open(a.traces))
    mp = torch.load(a.main)
    dd = torch.load(a.drafts)
    recs = []
    for r in range(dd["rows"].size(0)):
        j, p = dd["rows"][r].tolist()
        x = tr[j]["ids"]; L = len(x); g = mp["argmax"][j]
        D = min(BS, L - 1 - p)
        if D <= 0:
            continue
        d = dd["drafts"][r].tolist()
        m = [int(d[k - 1] == int(g[p + k])) for k in range(1, D + 1)] + [0] * (BS - D)
        acc = 0
        while acc < D and m[acc]:
            acc += 1
        exact = all(x[p + i] == int(g[p + i - 1]) for i in range(1, min(acc + 1, D) + 1))
        recs.append({"j": j, "p": p, "a": acc, "D": D, "m": m, "exact": exact,
                     "asst": bool(tr[j]["assistant_mask"][p + 1]), "src": tr[j].get("source", "all")})

    def block(src):
        rows = [r for r in recs if src is None or r["src"] == src]
        seqs = [j for j, t in enumerate(tr) if src is None or t.get("source", "all") == src]
        n_asst = match = 0
        for j in seqs:
            x, g, m = tr[j]["ids"], mp["argmax"][j], tr[j]["assistant_mask"]
            for t in range(1, len(x)):
                if m[t]:
                    n_asst += 1
                    match += int(x[t] == int(g[t - 1]))
        asst = [r for r in rows if r["asst"]]
        return {"sequences": len(seqs), "ids": [tr[j].get("id") for j in seqs],
                "tokens": sum(len(tr[j]["ids"]) for j in seqs), "assistant_tokens": n_asst,
                "greedy_match_rate_assistant_tokens": match / n_asst if n_asst else None,
                "assistant_rows_proxy": summarize(asst),
                "assistant_rows_EXACT_greedy_only": summarize([r for r in asst if r["exact"]]),
                "non_assistant_rows_proxy": summarize([r for r in rows if not r["asst"]])}

    srcs = sorted({t.get("source", "all") for t in tr})
    res = {"definitions": __doc__.split("INPUT")[0].strip(),
           "per_source": {s: block(s) for s in srcs}, "overall": block(None)}
    json.dump(res, open(a.out, "w"), indent=1)
    for s, b in list(res["per_source"].items()) + [("overall", res["overall"])]:
        pa, pe = b["assistant_rows_proxy"], b["assistant_rows_EXACT_greedy_only"]
        print(f"{s:14s} seqs={b['sequences']} tok={b['tokens']} asst={b['assistant_tokens']} "
              f"match={b['greedy_match_rate_assistant_tokens']:.3f} "
              f"tau_proxy={pa.get('tau_tokens_per_verification_incl_bonus', float('nan')):.3f} (n={pa['rows_full_depth']}) "
              f"tau_exact={pe.get('tau_tokens_per_verification_incl_bonus', float('nan')):.3f} (n={pe['rows_full_depth']}) "
              f"cond={[round(c, 3) if c is not None else None for c in pa.get('per_position_conditional_acceptance', [])]}")


if __name__ == "__main__":
    main()
