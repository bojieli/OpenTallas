#!/usr/bin/env python3
"""Build a reproducible sample of PUBLIC agentic traces rendered in DeepSeek-V4.1's own chat format.

Sources (all turns are OTHER models' outputs, not V4.1's):
  tau_retail / tau_airline : tau-bench historical trajectories gpt-4o-{retail,airline}.json
                             (github.com/sierra-research/tau-bench, local git HEAD recorded);
                             tool schemas from tau_bench/envs/<domain>/tools get_info()
  swe_agent                : nebius/SWE-agent-trajectories, data/train-00000-of-00012.parquet at
                             HF revision 68195a1450865274106246d0d0296a1d6807b88e (SWE-agent turns
                             by the row's model_name, e.g. swe-agent-llama-*)
Selection: random.Random(f"{seed}:{salt}").shuffle over item indices, first n (ids recorded).
Rendering: vendor encoding/encoding.py encode_messages(..., thinking_mode="chat"). tau assistant
tool calls become DSML <｜DSML｜ calls> blocks; tool results become <tool_result> user blocks;
SWE-agent turns map system->system, user->user, ai->assistant.

Truncation to --cap-tau (1500) / --cap-swe (600) tokens per trace (budget: ~16k tokens in total), with these DOCUMENTED deviations from the source:
  tau: the domain policy wiki (the system message, ~1.2k tokens) is OMITTED and the tool schemas
       are restricted to the tools the trajectory actually calls (full schema set is ~2.9k tokens);
       the DSML tool-format instructions are kept (rendered by the vendor encoder).
  swe: the SWE-agent system prompt (~1.1k tokens, command docs) is OMITTED and the issue text
       (first user turn) is cut to --swe-issue-tokens tokens.
  both: the rendered text is cut at the cap (possibly mid-turn). The tau cap is larger because
       the rendered DSML format block + schemas of 5-7 tools already take ~0.9-1.0k tokens.
Both omissions remove context the original agent had, which should make the (other model's)
turns less predictable for V4.1 -- a downward bias on the proxy numbers.

OUTPUT --out traces.json : list of {"id", "source", "ids", "assistant_mask" (1 = token inside an
       assistant span, from after <｜Assistant｜> through <｜end▁of▁sentence｜>), "n_tokens",
       "n_assistant_tokens", "text"}; --prov provenance.json (files, revisions, sha256, seed, ids)
Command: python3 v41_build_public_traces.py --out traces.json --prov provenance.json
"""
import argparse, hashlib, importlib.util, json, random, subprocess, sys, types
from pathlib import Path

SNAP = Path("/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
            "dba1be0a40aa45a94ad051997016db3960a90277")
TAU = Path("/home/ubuntu/tau-bench")
SWE_REPO, SWE_REV, SWE_FILE = "nebius/SWE-agent-trajectories", "68195a1450865274106246d0d0296a1d6807b88e", \
    "data/train-00000-of-00012.parquet"
A_TOK, E_TOK = "<｜Assistant｜>", "<｜end▁of▁sentence｜>"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def pick(n_items, n, seed, salt):
    order = list(range(n_items))
    random.Random(f"{seed}:{salt}").shuffle(order)
    return order[:n]


def tau_tools(domain):
    """tau-bench tool classes without importing the package (which pulls litellm)."""
    if "tau_bench.envs.tool" not in sys.modules:
        for name in ("tau_bench", "tau_bench.envs"):
            m = types.ModuleType(name); m.__path__ = []; sys.modules[name] = m
        spec = importlib.util.spec_from_file_location("tau_bench.envs.tool", TAU / "tau_bench/envs/tool.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        sys.modules["tau_bench.envs.tool"] = mod
    pkg = f"tau_bench.envs.{domain}.tools"
    spec = importlib.util.spec_from_file_location(pkg, TAU / f"tau_bench/envs/{domain}/tools/__init__.py",
                                                  submodule_search_locations=[str(TAU / f"tau_bench/envs/{domain}/tools")])
    mod = importlib.util.module_from_spec(spec); sys.modules[pkg] = mod; spec.loader.exec_module(mod)
    return [t.get_info() for t in mod.ALL_TOOLS]


def tau_messages(traj, tools):
    used = {c["function"]["name"] for m in traj if m["role"] == "assistant" for c in (m.get("tool_calls") or [])}
    msgs = [{"role": "system", "content": "", "tools": [t for t in tools if t["function"]["name"] in used]}]
    for m in traj:
        if m["role"] == "system":
            continue  # policy wiki omitted (budget) -- see module docstring
        if m["role"] == "assistant":
            msg = {"role": "assistant", "content": m.get("content") or ""}
            calls = m.get("tool_calls") or []
            if calls:
                msg["tool_calls"] = [{"type": "function", "id": c.get("id", ""),
                                      "function": {"name": c["function"]["name"],
                                                   "arguments": c["function"]["arguments"]
                                                   if isinstance(c["function"]["arguments"], str)
                                                   else json.dumps(c["function"]["arguments"])}} for c in calls]
            msgs.append(msg)
        elif m["role"] == "tool":
            msgs.append({"role": "tool", "tool_call_id": m.get("tool_call_id", ""), "content": str(m.get("content"))})
        else:
            msgs.append({"role": "user", "content": m.get("content") or ""})
    return msgs, sorted(used)


def render(tok, msgs, cap, enc):
    text = enc(msgs, thinking_mode="chat")
    e = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = e["input_ids"], e["offset_mapping"]
    spans, pos = [], 0
    while True:
        a = text.find(A_TOK, pos)
        if a < 0:
            break
        s = a + len(A_TOK)
        t = text.find(E_TOK, s)
        t = len(text) if t < 0 else t + len(E_TOK)
        spans.append((s, t)); pos = t
    mask = [int(any(s <= a and b <= t and b > a for s, t in spans)) for a, b in offs]
    full = len(ids)
    cut_char = offs[min(cap, full) - 1][1]
    return ids[:cap], mask[:cap], text[:cut_char], full


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--prov", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-tau", type=int, default=4, help="per tau domain")
    ap.add_argument("--n-swe", type=int, default=8)
    ap.add_argument("--cap-tau", type=int, default=1500)
    ap.add_argument("--cap-swe", type=int, default=600)
    ap.add_argument("--swe-issue-tokens", type=int, default=200)
    a = ap.parse_args()
    sys.path.insert(0, str(SNAP / "encoding"))
    from encoding import encode_messages
    from transformers import AutoTokenizer
    import pandas as pd
    tok = AutoTokenizer.from_pretrained(str(SNAP))
    out, prov = [], {"seed": a.seed, "cap_tokens": {"tau": a.cap_tau, "swe_agent": a.cap_swe}, "encoding": str(SNAP / "encoding/encoding.py"),
                     "encoding_sha256": sha256(SNAP / "encoding/encoding.py"), "thinking_mode": "chat", "sources": {}}

    def add(src, iid, msgs, meta):
        ids, mask, text, full = render(tok, msgs, a.cap_swe if src == "swe_agent" else a.cap_tau, encode_messages)
        out.append({"id": iid, "source": src, "ids": ids, "assistant_mask": mask, "n_tokens": len(ids),
                     "n_tokens_before_cut": full, "n_assistant_tokens": sum(mask), "text": text, **meta})

    tau_head = subprocess.run(["git", "-C", str(TAU), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    for dom in ("retail", "airline"):
        f = TAU / f"historical_trajectories/gpt-4o-{dom}.json"
        data = json.load(open(f))
        tools = tau_tools(dom)
        idx = pick(len(data), a.n_tau, a.seed, f"v41-tau-{dom}")
        prov["sources"][f"tau_{dom}"] = {"repo": "https://github.com/sierra-research/tau-bench", "git_head": tau_head,
                                         "file": str(f.relative_to(TAU)), "sha256": sha256(f), "salt": f"v41-tau-{dom}",
                                         "picked_list_indices": idx, "n_items": len(data)}
        for i in idx:
            d = data[i]
            msgs, used = tau_messages(d["traj"], tools)
            add(f"tau_{dom}", f"gpt-4o-{dom}[{i}] task_id={d['task_id']} trial={d.get('trial')}", msgs,
                {"task_id": d["task_id"], "reward": d.get("reward"), "tools_rendered": used})
    from huggingface_hub import hf_hub_download
    p = hf_hub_download(SWE_REPO, SWE_FILE, repo_type="dataset", revision=SWE_REV)
    df = pd.read_parquet(p)
    idx = pick(len(df), a.n_swe, a.seed, "v41-swe")
    prov["sources"]["swe_agent"] = {"dataset": SWE_REPO, "revision": SWE_REV, "file": SWE_FILE, "sha256": sha256(p),
                                    "salt": "v41-swe", "picked_row_indices": idx, "n_rows": len(df)}
    for i in idx:
        r = df.iloc[i]
        msgs, first_user = [], True
        for m in r["trajectory"]:
            role = {"system": "system", "user": "user", "ai": "assistant"}[m["role"]]
            if role == "system":
                continue  # SWE-agent system prompt omitted (budget) -- see module docstring
            c = m["text"] or ""
            if role == "user" and first_user:
                first_user = False
                t = tok(c, add_special_tokens=False)["input_ids"]
                if len(t) > a.swe_issue_tokens:
                    c = tok.decode(t[:a.swe_issue_tokens]) + "\n[... issue text truncated ...]"
            msgs.append({"role": role, "content": c})
        add("swe_agent", f"row{i} {r['instance_id']} {r['model_name']}", msgs,
            {"instance_id": r["instance_id"], "model_name": r["model_name"], "target": bool(r["target"])})
    prov["items"] = [{"id": t["id"], "source": t["source"], "n_tokens": t["n_tokens"],
                      "n_tokens_before_cut": t["n_tokens_before_cut"], "n_assistant_tokens": t["n_assistant_tokens"]}
                     for t in out]
    json.dump(out, open(a.out, "w"))
    json.dump(prov, open(a.prov, "w"), indent=1)
    for t in out:
        print(f"{t['source']:12s} {t['n_tokens']:5d}/{t['n_tokens_before_cut']:6d} asst={t['n_assistant_tokens']:4d}  {t['id']}")
    print("total tokens", sum(t["n_tokens"] for t in out), "assistant", sum(t["n_assistant_tokens"] for t in out))


if __name__ == "__main__":
    main()
