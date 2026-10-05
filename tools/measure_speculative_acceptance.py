#!/usr/bin/env python3
"""Measure speculative acceptance length (tau) of Qwen3-8B drafters per workload.

tau is the number of tokens one verification pass commits, INCLUDING the target's
own bonus token -- the convention of configs/studies/speculative_profiles.json
and of DFlash (arXiv:2602.06036) equation (1).  Everything here is greedy
(temperature 0), batch 1, one request at a time.

Four subcommands, run in order:

``prepare``  builds the prompt set from public datasets (pinned Hugging Face
             revisions / git commits, seeded selection) and writes one JSONL row
             per prompt: workload, prompt id, messages, tools, thinking mode,
             generation budget and source.  No model is loaded.

``run-hf``   the DFlash reference implementation (github.com/z-lab/dflash,
             ``dflash.model.dflash_generate``, imported unmodified from a pinned
             checkout) on Hugging Face Transformers.  For every prompt it runs the
             SAME function twice: ``block_size=1`` (plain autoregressive greedy,
             the reference's own baseline) and the drafter's block size.  It
             records every cycle's committed length, the output tokens of both,
             and a token-for-token losslessness check; at a divergence it measures
             the target's top-1/top-2 logit margin there with one teacher-forced
             forward, so a numerical near-tie is told apart from a real mismatch.

``run-vllm`` EAGLE-3 heads (chain drafting, ``num_speculative_tokens = k``) or no
             speculation, through vLLM's offline ``LLM`` engine, one request at a
             time (``max_num_seqs = 1``).  Per-request acceptance is the delta of
             vLLM's own counters (``vllm:spec_decode_num_drafts``,
             ``..._num_accepted_tokens`` and ``..._num_accepted_tokens_per_pos``)
             around each request.  The no-speculation run requests top-2
             logprobs so a divergence can be graded by its margin.

``aggregate`` joins the runs into results/speculative/acceptance_tau.json.

Why two engines: DFlash's reference implementation is the Transformers one and
it exposes every cycle; the EAGLE-3 heads used here are published for vLLM
(RedHatAI's is in the vLLM ``speculators`` format).  Losslessness is always
checked against plain greedy decoding IN THE SAME ENGINE, never across engines,
because bf16 kernels differ between engines.

Per-position acceptance and the histogram
-----------------------------------------
Greedy verification accepts a prefix: if draft position i is accepted then so are
1..i-1.  So ``per_pos[i] = #cycles with >= i+1 accepted drafts`` and the committed
-length histogram is ``P(tau = a+1) = (per_pos[a-1] - per_pos[a]) / drafts`` (with
``per_pos[-1] = drafts`` and ``per_pos[k] = 0``).  The survival ``s_i =
per_pos[i-1]/drafts`` gives ``tau(gamma) = 1 + sum_{i<=gamma} s_i``; evaluated at
a gamma SMALLER than the one run, that is a derived truncation and is labelled so.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET_MODEL = "Qwen/Qwen3-8B"
SEED = 42

# ---------------------------------------------------------------------------
# Workloads
# ---------------------------------------------------------------------------

MATH_FMT = "{problem}\nPlease reason step by step, and put your final answer within \\boxed{{}}."
HUMANEVAL_FMT = (
    "Write a solution to the following problem and make sure that it passes the tests:\n"
    "```python\n{prompt}\n```"
)  # both strings verbatim from dflash/benchmark.py (DFlash's own benchmark harness)

WORKLOADS = {
    # class, thinking, max_new_tokens
    "reasoning_math500": ("reasoning", True, 2048),
    "reasoning_aime25": ("reasoning", True, 2048),
    "reasoning_humaneval": ("reasoning", True, 2048),
    "agentic_bfcl": ("agentic", False, 1024),
    "agentic_tau_bench": ("agentic", False, 1024),
    "agentic_swe_agent": ("agentic", False, 1024),
    "agentic_mind2web": ("agentic", False, 1024),
    "agentic_json_mode": ("agentic", False, 1024),
    "chat_mt_bench": ("chat", False, 2048),
    "xcheck_math500_nothink": ("crosscheck", False, 2048),
    "xcheck_humaneval_nothink": ("crosscheck", False, 2048),
}

SOURCES = {
    "math500": {"dataset": "HuggingFaceH4/MATH-500", "file": "test.jsonl",
                "url": "https://huggingface.co/datasets/HuggingFaceH4/MATH-500"},
    "aime25": {"dataset": "MathArena/aime_2025", "file": "data/train-00000-of-00001.parquet",
               "url": "https://huggingface.co/datasets/MathArena/aime_2025"},
    "humaneval": {"dataset": "openai/openai_humaneval", "file": "openai_humaneval/test-00000-of-00001.parquet",
                  "url": "https://huggingface.co/datasets/openai/openai_humaneval"},
    "bfcl": {"dataset": "gorilla-llm/Berkeley-Function-Calling-Leaderboard",
             "files": ["BFCL_v3_simple.json", "BFCL_v3_multiple.json", "BFCL_v3_parallel.json",
                       "BFCL_v3_live_multiple.json"],
             "url": "https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard"},
    "tau_bench": {"repo": "https://github.com/sierra-research/tau-bench",
                  "files": ["historical_trajectories/gpt-4o-retail.json",
                            "historical_trajectories/gpt-4o-airline.json"],
                  "note": "tau-bench's own published historical trajectories (gpt-4o agent); tools from tau_bench/envs/*/tools"},
    "swe_agent": {"dataset": "nebius/SWE-agent-trajectories", "file": "data/train-00000-of-00012.parquet",
                  "url": "https://huggingface.co/datasets/nebius/SWE-agent-trajectories"},
    "mind2web": {"dataset": "osunlp/Mind2Web", "file": "data/train/train_10.json",
                 "url": "https://huggingface.co/datasets/osunlp/Mind2Web"},
    "json_mode": {"dataset": "NousResearch/json-mode-eval", "file": "data/train-00000-of-00001.parquet",
                  "url": "https://huggingface.co/datasets/NousResearch/json-mode-eval"},
    "mt_bench": {"dataset": "HuggingFaceH4/mt_bench_prompts", "file": "raw/question.jsonl",
                 "url": "https://huggingface.co/datasets/HuggingFaceH4/mt_bench_prompts"},
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _hf_file(repo: str, filename: str):
    from huggingface_hub import HfApi, hf_hub_download

    path = Path(hf_hub_download(repo, filename, repo_type="dataset"))
    revision = path.parent.name
    # snapshot dir name is the commit; walk up if the file sits in a subdirectory
    parts = path.parts
    if "snapshots" in parts:
        revision = parts[parts.index("snapshots") + 1]
    return path, {"dataset": repo, "file": filename, "revision": revision, "sha256": _sha256_file(path)}


def _pick(items: list, n: int, salt: str) -> list:
    order = list(range(len(items)))
    random.Random(f"{SEED}:{salt}").shuffle(order)
    return [items[i] for i in order[:n]]


def _bfcl_schema(node):
    """BFCL writes JSON-schema 'dict' for object; the Qwen3 template dumps the schema verbatim."""
    if isinstance(node, dict):
        out = {k: _bfcl_schema(v) for k, v in node.items()}
        if out.get("type") == "dict":
            out["type"] = "object"
        return out
    if isinstance(node, list):
        return [_bfcl_schema(v) for v in node]
    return node


def _tau_tools(domain: str, tau_root: Path) -> list[dict]:
    """Import tau-bench's tool classes without importing the package (which pulls litellm)."""
    import importlib.util
    import types

    if "tau_bench.envs.tool" not in sys.modules:
        for name in ("tau_bench", "tau_bench.envs"):
            mod = types.ModuleType(name)
            mod.__path__ = []
            sys.modules[name] = mod
        spec = importlib.util.spec_from_file_location("tau_bench.envs.tool", tau_root / "tau_bench/envs/tool.py")
        tool_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool_mod)
        sys.modules["tau_bench.envs.tool"] = tool_mod
    pkg = f"tau_bench.envs.{domain}.tools"
    spec = importlib.util.spec_from_file_location(
        pkg, tau_root / f"tau_bench/envs/{domain}/tools/__init__.py",
        submodule_search_locations=[str(tau_root / f"tau_bench/envs/{domain}/tools")])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[pkg] = mod
    spec.loader.exec_module(mod)
    return [t.get_info() for t in mod.ALL_TOOLS]


def _tau_messages(traj: list[dict]) -> list[dict]:
    out = []
    for m in traj:
        role = m["role"]
        if role == "assistant":
            msg = {"role": "assistant", "content": m.get("content") or ""}
            calls = m.get("tool_calls") or []
            if calls:
                msg["tool_calls"] = [
                    {"type": "function", "function": {
                        "name": c["function"]["name"],
                        "arguments": json.loads(c["function"]["arguments"])
                        if isinstance(c["function"]["arguments"], str) else c["function"]["arguments"]}}
                    for c in calls]
            out.append(msg)
        elif role == "tool":
            out.append({"role": "tool", "content": str(m.get("content"))})
        else:
            out.append({"role": role, "content": m.get("content") or ""})
    return out


def prepare(args) -> None:
    import pandas as pd
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TARGET_MODEL)
    n = args.n
    rows: list[dict] = []
    provenance: dict = {}

    def add(workload, pid, messages, tools=None, source=None):
        cls, think, max_new = WORKLOADS[workload]
        rows.append({"workload": workload, "class": cls, "prompt_id": pid, "messages": messages,
                     "tools": tools, "enable_thinking": think, "max_new_tokens": max_new, "source": source})

    # --- math / aime / humaneval (reasoning, and the no-thinking cross-check) ---
    p, prov = _hf_file(SOURCES["math500"]["dataset"], SOURCES["math500"]["file"])
    provenance["math500"] = prov
    math_rows = [json.loads(l) for l in open(p)]
    for r in _pick(math_rows, n, "math500"):
        msg = [{"role": "user", "content": MATH_FMT.format(problem=r["problem"])}]
        add("reasoning_math500", r["unique_id"], msg, source="math500")
        add("xcheck_math500_nothink", r["unique_id"], msg, source="math500")
    p, prov = _hf_file(SOURCES["aime25"]["dataset"], SOURCES["aime25"]["file"])
    provenance["aime25"] = prov
    aime = pd.read_parquet(p).to_dict("records")
    for r in _pick(aime, n, "aime25"):
        add("reasoning_aime25", f"aime2025-{int(r['problem_idx'])}",
            [{"role": "user", "content": MATH_FMT.format(problem=r["problem"])}], source="aime25")
    p, prov = _hf_file(SOURCES["humaneval"]["dataset"], SOURCES["humaneval"]["file"])
    provenance["humaneval"] = prov
    he = pd.read_parquet(p).to_dict("records")
    for r in _pick(he, n, "humaneval"):
        msg = [{"role": "user", "content": HUMANEVAL_FMT.format(prompt=r["prompt"])}]
        add("reasoning_humaneval", r["task_id"], msg, source="humaneval")
        add("xcheck_humaneval_nothink", r["task_id"], msg, source="humaneval")

    # --- BFCL: n/4 each of simple, multiple, parallel, live_multiple ---
    per = max(1, n // len(SOURCES["bfcl"]["files"]))
    provenance["bfcl"] = []
    for f in SOURCES["bfcl"]["files"]:
        p, prov = _hf_file(SOURCES["bfcl"]["dataset"], f)
        provenance["bfcl"].append(prov)
        items = [json.loads(l) for l in open(p)]
        for r in _pick(items, per, f):
            tools = [{"type": "function", "function": _bfcl_schema(fn)} for fn in r["function"]]
            add("agentic_bfcl", r["id"], list(r["question"][0]), tools=tools, source="bfcl")

    # --- tau-bench: prefix of a published trajectory up to an assistant turn ---
    tau_root = Path(args.tau_bench_root)
    commit = subprocess.run(["git", "-C", str(tau_root), "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    provenance["tau_bench"] = {"repo": SOURCES["tau_bench"]["repo"], "commit": commit, "files": []}
    per = n // 2
    for f in SOURCES["tau_bench"]["files"]:
        domain = "retail" if "retail" in f else "airline"
        provenance["tau_bench"]["files"].append({"file": f, "sha256": _sha256_file(tau_root / f)})
        tools = _tau_tools(domain, tau_root)
        trajs = json.load(open(tau_root / f))
        rng = random.Random(f"{SEED}:tau:{domain}")
        for t in _pick(trajs, per, f):
            msgs = _tau_messages(t["traj"])
            cut = [i for i, m in enumerate(msgs) if m["role"] == "assistant" and i >= 2]
            if not cut:
                continue
            i = rng.choice(cut)
            add("agentic_tau_bench", f"{domain}-task{t['task_id']}-trial{t['trial']}-turn{i}",
                msgs[:i], tools=tools, source="tau_bench")

    # --- SWE-agent trajectories: prefix up to an assistant step, prompt <= 8k tokens ---
    p, prov = _hf_file(SOURCES["swe_agent"]["dataset"], SOURCES["swe_agent"]["file"])
    provenance["swe_agent"] = prov
    df = pd.read_parquet(p)
    rng = random.Random(f"{SEED}:swe")
    picked = 0
    for idx in _pick(list(range(len(df))), len(df), "swe"):
        if picked >= n:
            break
        r = df.iloc[idx]
        msgs = []
        for m in r["trajectory"]:
            role = {"system": "system", "user": "user", "ai": "assistant"}[m["role"]]
            content = m["system_prompt"] if role == "system" else m["text"]
            msgs.append({"role": role, "content": content or ""})
        cuts = [i for i, m in enumerate(msgs) if m["role"] == "assistant"]
        rng.shuffle(cuts)
        for i in cuts:
            ids = tok.apply_chat_template(msgs[:i], tokenize=True, add_generation_prompt=True,
                                          enable_thinking=False)
            if hasattr(ids, "input_ids"):
                ids = ids["input_ids"]
            if len(ids) <= 8192:
                add("agentic_swe_agent", f"{r['instance_id']}-{r['model_name']}-step{i}", msgs[:i],
                    source="swe_agent")
                picked += 1
                break

    # --- Mind2Web: MindAct-style next-action prompt, HTML window around the target ---
    p, prov = _hf_file(SOURCES["mind2web"]["dataset"], SOURCES["mind2web"]["file"])
    provenance["mind2web"] = prov
    tasks = json.load(open(p))
    steps = []
    for t in tasks:
        reprs = t["action_reprs"]
        reprs = reprs if isinstance(reprs, list) else ast.literal_eval(reprs)
        for k, a in enumerate(t["actions"]):
            steps.append((t, k, reprs, a))
    for t, k, reprs, a in _pick(steps, n, "mind2web"):
        html = a["cleaned_html"]
        pos = a["pos_candidates"]
        pos = pos if isinstance(pos, list) else ast.literal_eval(pos)
        centre = 0
        if pos:
            key = f'backend_node_id="{pos[0]["backend_node_id"]}"'
            centre = max(0, html.find(key))
        lo = max(0, centre - 6000)
        window = html[lo:lo + 12000]
        prev = "\n".join(reprs[:k]) or "None"
        system = ("You are a web-browsing agent. You see a (truncated) cleaned HTML observation of the "
                  "current page, the task, and the actions taken so far. Decide the next action. Answer "
                  "with a one-sentence rationale and then exactly three lines:\n"
                  "ELEMENT: <backend_node_id>\nACTION: CLICK | TYPE | SELECT\nVALUE: <text to type or option to "
                  "select, empty for CLICK>")
        user = (f"Website: {t['website']}\nTask: {t['confirmed_task']}\nPrevious actions:\n{prev}\n\n"
                f"Observation (HTML):\n{window}")
        add("agentic_mind2web", f"{t['annotation_id']}-step{k}",
            [{"role": "system", "content": system}, {"role": "user", "content": user}], source="mind2web")

    # --- JSON mode ---
    p, prov = _hf_file(SOURCES["json_mode"]["dataset"], SOURCES["json_mode"]["file"])
    provenance["json_mode"] = prov
    jm = pd.read_parquet(p).to_dict("records")
    idxs = _pick(list(range(len(jm))), n, "json_mode")
    for i in idxs:
        add("agentic_json_mode", f"json-mode-eval-{i}",
            [{"role": m["role"], "content": m["content"]} for m in jm[i]["prompt"]], source="json_mode")

    # --- MT-Bench: n/2 questions, both turns (turn 2 carries the model's own turn-1 answer) ---
    p, prov = _hf_file(SOURCES["mt_bench"]["dataset"], SOURCES["mt_bench"]["file"])
    provenance["mt_bench"] = prov
    qs = [json.loads(l) for l in open(p)]
    for q in _pick(qs, n // 2, "mt_bench"):
        add("chat_mt_bench", f"mtbench-{q['question_id']}", [{"role": "user", "content": q["prompt"][0]}],
            source="mt_bench")
        rows[-1]["turns"] = list(q["prompt"])

    for r in rows:
        r["prompt_sha256"] = hashlib.sha256(json.dumps([r["messages"], r["tools"], r["enable_thinking"]],
                                                       sort_keys=True).encode()).hexdigest()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    Path(str(out) + ".provenance.json").write_text(json.dumps(
        {"seed": SEED, "n_per_workload": n, "sources": SOURCES, "resolved": provenance}, indent=1))
    counts = {}
    for r in rows:
        counts[r["workload"]] = counts.get(r["workload"], 0) + 1
    print(json.dumps(counts, indent=1))


# ---------------------------------------------------------------------------
# Shared helpers for the runners
# ---------------------------------------------------------------------------

def _render(tok, messages, tools, think) -> list[int]:
    text = tok.apply_chat_template(messages, tools=tools, tokenize=False, add_generation_prompt=True,
                                   enable_thinking=think)
    return tok.encode(text, add_special_tokens=False)


def _load_rows(path, workloads):
    rows = [json.loads(l) for l in open(path)]
    if workloads:
        keep = set(workloads.split(","))
        rows = [r for r in rows if r["workload"] in keep]
    return rows


def _done_keys(out: Path) -> dict:
    """Records already written, keyed by (workload, prompt id, turn), so a run resumes."""
    if not out.exists():
        return {}
    return {(j["workload"], j["prompt_id"], j.get("turn", 0)): j for j in map(json.loads, open(out))}


def _environment() -> dict:
    env = {"python": platform.python_version(), "host": platform.node()}
    try:
        import torch
        env["torch"] = torch.__version__
        env["cuda"] = torch.version.cuda
        if torch.cuda.is_available():
            env["gpu"] = torch.cuda.get_device_name(0)
            env["gpu_total_bytes"] = torch.cuda.get_device_properties(0).total_memory
    except Exception:  # pragma: no cover
        pass
    try:
        import transformers
        env["transformers"] = transformers.__version__
    except Exception:  # pragma: no cover
        pass
    try:
        env["nvidia_driver"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True, text=True).stdout.strip()
    except Exception:  # pragma: no cover
        pass
    return env


def _turns(row):
    """MT-Bench rows carry two turns; everything else is one."""
    return row.get("turns") or [None]


# ---------------------------------------------------------------------------
# run-hf: DFlash reference implementation
# ---------------------------------------------------------------------------

def _greedy_consistency(target, ids: list[int], out_ids: list[int], tol: float, chunk: int = 1024) -> dict:
    """Teacher-forced check of EVERY emitted token: one forward over prompt+output, then
    deficit_t = max_v logit_t(v) - logit_t(emitted_t).  Deficit 0 means the token is the target's
    argmax under full-sequence evaluation; a deficit within ``tol`` is a bf16 near-tie (bf16 logits
    of magnitude 16-32 are quantised in steps of 0.125-0.25, and incremental decoding and a
    full-sequence forward round differently); a deficit above ``tol`` would be a real violation."""
    import torch

    if not out_ids:
        return {"tokens": 0}
    with torch.inference_mode():
        seq = torch.tensor([ids + out_ids], device=target.device)
        hidden = target.model(input_ids=seq).last_hidden_state[0, len(ids) - 1: len(ids) + len(out_ids) - 1]
        emitted = torch.tensor(out_ids, device=target.device)
        deficits = []
        for i in range(0, hidden.shape[0], chunk):
            logits = target.lm_head(hidden[i:i + chunk]).float()
            deficits.append(logits.max(-1).values - logits.gather(-1, emitted[i:i + chunk, None])[:, 0])
        d = torch.cat(deficits)
    return {"tokens": len(out_ids), "not_argmax": int((d > 0).sum()), "above_tol": int((d > tol).sum()),
            "max_deficit": float(d.max()), "tol": tol}


def _plain_greedy(target, ids: list[int], max_new: int, stops: list[int], reference: list[int] | None):
    """Plain greedy decoding, step for step the reference's own ``block_size=1`` path of
    ``dflash_generate`` (prefill with ``logits_to_keep=1``, then one-token forwards on a
    DynamicCache with explicit position ids, argmax, stop on a stop token).  When a
    ``reference`` (the speculative output) is given it stops at the first token that differs
    from it and returns the target's top-1/top-2 logit margin at that step: past a divergence
    the two runs are on different trajectories and comparing further means nothing."""
    import torch
    from transformers import DynamicCache

    dev = target.device
    cache = DynamicCache(config=target.config)
    out: list[int] = []
    div = None
    with torch.inference_mode():
        logits = target(torch.tensor([ids], device=dev), position_ids=torch.arange(len(ids), device=dev)[None],
                        past_key_values=cache, use_cache=True, logits_to_keep=1).logits[0, -1]
        pos = len(ids)
        while True:
            top = torch.topk(logits.float(), 2)
            nxt = int(top.indices[0])
            if reference is not None and (len(out) >= len(reference) or reference[len(out)] != nxt):
                div = {"index": len(out), "baseline_token": nxt,
                       "spec_token": reference[len(out)] if len(out) < len(reference) else None,
                       "top2_logit_margin": float(top.values[0] - top.values[1]),
                       "baseline_second_token": int(top.indices[1])}
                div["spec_token_is_baseline_second"] = div["spec_token"] == div["baseline_second_token"]
                out.append(nxt)
                break
            out.append(nxt)
            if nxt in stops or len(out) >= max_new:
                break
            logits = target(torch.tensor([[nxt]], device=dev), position_ids=torch.tensor([[pos]], device=dev),
                            past_key_values=cache, use_cache=True).logits[0, -1]
            pos += 1
    if reference is not None and div is None and len(out) != len(reference):
        div = {"index": len(out), "baseline_token": None,
               "spec_token": reference[len(out)] if len(out) < len(reference) else None,
               "top2_logit_margin": None, "note": "baseline stopped at a different length"}
    return out, div


def run_hf(args) -> None:
    """Two phases so the acceptance figures land first: ``--mode spec`` runs the drafter and
    checks every emitted token for greedy consistency; ``--mode baseline`` runs the reference's
    own plain greedy path (``block_size=1``) and compares token-for-token with the spec record."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    sys.path.insert(0, args.dflash_repo)
    from dflash.model import DFlashDraftModel, dflash_generate  # noqa: E402

    dflash_commit = subprocess.run(["git", "-C", args.dflash_repo, "rev-parse", "HEAD"], capture_output=True,
                                   text=True).stdout.strip()
    torch.manual_seed(0)
    dev = torch.device("cuda:0")
    target = AutoModelForCausalLM.from_pretrained(TARGET_MODEL, attn_implementation="sdpa",
                                                  dtype=torch.bfloat16).to(dev).eval()
    draft = DFlashDraftModel.from_pretrained(args.draft, attn_implementation="sdpa",
                                             dtype=torch.bfloat16).to(dev).eval()
    tok = AutoTokenizer.from_pretrained(TARGET_MODEL)
    block = args.block_size or draft.block_size
    bs = 1 if args.mode == "baseline" else block
    gen_eos = target.generation_config.eos_token_id
    stops = [gen_eos] if isinstance(gen_eos, int) else list(gen_eos)
    out = Path(args.out)
    done = _done_keys(out)
    spec_recs = _done_keys(Path(args.spec_records)) if args.mode == "baseline" else {}
    rows = _load_rows(args.prompts, args.workloads)
    meta = {"engine": "transformers", "mode": args.mode,
            "implementation": f"z-lab/dflash@{dflash_commit} dflash.model.dflash_generate (unmodified)",
            "drafter": args.draft, "block_size": block, "draft_tokens_per_cycle": block - 1,
            "run_block_size": bs, "environment": _environment(), "stop_token_ids": stops,
            "target_snapshot": str(target.config._name_or_path), "consistency_tol": args.tol}
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1))

    w = torch.tensor([_render(tok, rows[0]["messages"], rows[0]["tools"], rows[0]["enable_thinking"])], device=dev)
    dflash_generate(draft, target, w, 32, None, 0.0, block_size=block)  # warm-up, as the reference does

    for row in rows:
        history = list(row["messages"])
        for turn_idx, turn_text in enumerate(_turns(row)):
            if turn_text is not None and turn_idx > 0:
                history.append({"role": "user", "content": turn_text})
            key = (row["workload"], row["prompt_id"], turn_idx)
            if key in done:
                if turn_text is not None:
                    prev = spec_recs[key]["output_ids"] if args.mode == "baseline" and key in spec_recs \
                        else done[key]["output_ids"]
                    history.append({"role": "assistant", "content": tok.decode(prev, skip_special_tokens=True)})
                continue
            ids = _render(tok, history, row["tools"], row["enable_thinking"])
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            if args.mode == "spec":
                r = dflash_generate(draft, target=target, input_ids=torch.tensor([ids], device=dev),
                                    max_new_tokens=row["max_new_tokens"], stop_token_ids=stops,
                                    temperature=0.0, block_size=bs, return_stats=True)
                gen = r.output_ids[0, len(ids):].tolist()
            else:
                s = spec_recs.get(key)
                gen, div = _plain_greedy(target, ids, row["max_new_tokens"], stops,
                                         s["output_ids"] if s is not None else None)
            torch.cuda.synchronize()
            dt = time.perf_counter() - t0
            psha = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
            rec = {"workload": row["workload"], "class": row["class"], "prompt_id": row["prompt_id"],
                   "turn": turn_idx, "prompt_sha256": psha, "prompt_tokens": len(ids),
                   "enable_thinking": row["enable_thinking"], "max_new_tokens": row["max_new_tokens"],
                   "tokens": len(gen), "seconds": dt, "t_end_unix": time.time(), "hit_max_new_tokens": len(gen) >= row["max_new_tokens"],
                   "output_sha256": hashlib.sha256(json.dumps(gen).encode()).hexdigest(), "output_ids": gen}
            msg = ""
            if args.mode == "spec":
                rec["acceptance_lengths"] = r.acceptance_lengths
                rec["greedy_consistency"] = _greedy_consistency(target, ids, gen, args.tol)
                gc = rec["greedy_consistency"]
                msg = (f"tau={sum(r.acceptance_lengths) / max(1, len(r.acceptance_lengths)):.2f} "
                       f"not_argmax={gc.get('not_argmax')} above_tol={gc.get('above_tol')}")
            else:
                cmp = {"spec_record": s is not None}
                if s is not None:
                    cmp["same_prompt_tokens"] = s["prompt_sha256"] == psha
                    cmp["identical"] = div is None
                    cmp["compared_tokens"] = len(gen) if div is None else div["index"]
                    cmp["spec_tokens"] = len(s["output_ids"])
                    if div is not None:
                        cmp.update(div)
                rec["versus_spec"] = cmp
                msg = (f"identical={cmp.get('identical')} at={cmp.get('index')} "
                       f"margin={cmp.get('top2_logit_margin')}")
            with open(out, "a") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"{row['workload']:<26} {row['prompt_id'][:40]:<40} t{turn_idx} n={len(gen):5d} {dt:6.1f}s {msg}",
                  flush=True)
            if turn_text is not None:
                # a later turn is conditioned on the SPECULATIVE run's answer in both modes, so the
                # baseline is compared on the identical prompt (the baseline stops at a divergence)
                prev = spec_recs[key]["output_ids"] if args.mode == "baseline" and key in spec_recs else gen
                history.append({"role": "assistant", "content": tok.decode(prev, skip_special_tokens=True)})


# ---------------------------------------------------------------------------
# run-vllm: EAGLE-3 (or no speculation) through vLLM's offline engine
# ---------------------------------------------------------------------------

def _vllm_counters(llm) -> dict:
    out = {"drafts": 0, "draft_tokens": 0, "accepted": 0, "per_pos": []}
    for m in llm.get_metrics():
        name = getattr(m, "name", "")
        if name == "vllm:spec_decode_num_drafts":
            out["drafts"] = int(m.value)
        elif name == "vllm:spec_decode_num_draft_tokens":
            out["draft_tokens"] = int(m.value)
        elif name == "vllm:spec_decode_num_accepted_tokens":
            out["accepted"] = int(m.value)
        elif name == "vllm:spec_decode_num_accepted_tokens_per_pos":
            out["per_pos"] = [int(v) for v in m.values]
    return out


def run_vllm(args) -> None:
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams, __version__ as vllm_version
    from vllm.inputs import TokensPrompt

    kwargs = dict(model=TARGET_MODEL, dtype="bfloat16", max_num_seqs=1, seed=SEED,
                  gpu_memory_utilization=args.gpu_memory_utilization, max_model_len=args.max_model_len,
                  disable_log_stats=False, enable_prefix_caching=False)
    if args.method != "none":
        kwargs["speculative_config"] = {"method": args.method, "model": args.draft,
                                        "num_speculative_tokens": args.k}
    if args.quantization:
        kwargs["quantization"] = args.quantization
    llm = LLM(**kwargs)
    tok = AutoTokenizer.from_pretrained(TARGET_MODEL)
    out = Path(args.out)
    done = _done_keys(out)
    rows = _load_rows(args.prompts, args.workloads)
    if args.per_workload:
        seen: dict = {}
        rows = [r for r in rows if seen.setdefault(r["workload"], []).append(1) or len(seen[r["workload"]]) <= args.per_workload]
    env = _environment()
    env["vllm"] = vllm_version
    env["env_vars"] = {k: os.environ.get(k) for k in ("VLLM_USE_FLASHINFER_SAMPLER", "CUDA_HOME", "VLLM_BATCH_INVARIANT",
                                                      "VLLM_ATTENTION_BACKEND")}
    meta = {"engine": "vllm", "method": args.method, "quantization": args.quantization or "bf16",
            "timing_mode": args.timing, "drafter": args.draft, "k": args.k, "environment": env,
            "engine_kwargs": {k: v for k, v in kwargs.items()}}
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1, default=str))
    gen_eos = [151645, 151643]
    for row in rows:
        history = list(row["messages"])
        for turn_idx, turn_text in enumerate(_turns(row)):
            if turn_text is not None and turn_idx > 0:
                history.append({"role": "user", "content": turn_text})
            key = (row["workload"], row["prompt_id"], turn_idx)
            if key in done:
                if turn_text is not None:
                    history.append({"role": "assistant", "content": tok.decode(
                        done[key]["output_ids"], skip_special_tokens=True)})
                continue
            ids = _render(tok, history, row["tools"], row["enable_thinking"])
            want_lp = args.method == "none" and not args.timing
            sp = SamplingParams(temperature=0.0, max_tokens=row["max_new_tokens"], stop_token_ids=gen_eos,
                                logprobs=2 if want_lp else None, seed=SEED)
            ttft = None
            if args.timing:
                # prefill + first token alone (prefix caching is off, so the full call re-prefills)
                t0 = time.perf_counter()
                llm.generate([TokensPrompt(prompt_token_ids=ids)],
                             SamplingParams(temperature=0.0, max_tokens=1, seed=SEED), use_tqdm=False)
                ttft = time.perf_counter() - t0
            c0 = _vllm_counters(llm)
            t0 = time.perf_counter()
            o = llm.generate([TokensPrompt(prompt_token_ids=ids)], sp, use_tqdm=False)[0]
            dt = time.perf_counter() - t0
            c1 = _vllm_counters(llm)
            gen = list(o.outputs[0].token_ids)
            rec = {"workload": row["workload"], "class": row["class"], "prompt_id": row["prompt_id"],
                   "turn": turn_idx, "prompt_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
                   "prompt_tokens": len(ids), "enable_thinking": row["enable_thinking"],
                   "max_new_tokens": row["max_new_tokens"], "tokens": len(gen), "seconds": dt, "t_end_unix": time.time(),
                   "ttft_seconds": ttft,
                   "decode_tokens_per_s": ((len(gen) - 1) / (dt - ttft)) if ttft and len(gen) > 1 and dt > ttft else None,
                   "output_ids": gen, "output_sha256": hashlib.sha256(json.dumps(gen).encode()).hexdigest()}
            if args.method != "none":
                npos = max(len(c0["per_pos"]), len(c1["per_pos"]))
                p0 = c0["per_pos"] + [0] * (npos - len(c0["per_pos"]))
                rec.update({"drafts": c1["drafts"] - c0["drafts"],
                            "draft_tokens": c1["draft_tokens"] - c0["draft_tokens"],
                            "accepted": c1["accepted"] - c0["accepted"],
                            "per_pos": [a - b for a, b in zip(c1["per_pos"], p0)]})
            elif want_lp:
                margins = []
                for lp in o.outputs[0].logprobs or []:
                    vals = sorted((v.logprob for v in lp.values()), reverse=True)
                    margins.append(vals[0] - vals[1] if len(vals) > 1 else None)
                rec["top2_logprob_margin"] = margins
            with open(out, "a") as f:
                f.write(json.dumps(rec) + "\n")
            tau = (1 + rec["accepted"] / rec["drafts"]) if rec.get("drafts") else float("nan")
            print(f"{row['workload']:<26} {row['prompt_id'][:40]:<40} t{turn_idx} n={len(gen):5d} tau={tau:.2f} "
                  f"{dt:.1f}s", flush=True)
            if turn_text is not None:
                history.append({"role": "assistant", "content": tok.decode(gen, skip_special_tokens=True)})


def run_sweep(args) -> None:
    """Concurrency point for the throughput/energy sweep: ONE engine at ``max_num_seqs = c``, all
    prompts submitted at once, so continuous batching keeps up to ``c`` requests in flight.  An
    idle window with the engine loaded is recorded first, so the board power of other tenants and of
    our idle engine can be subtracted.  Board power itself is logged by an external
    ``nvidia-smi -lms 100`` process; this writes only the time windows."""
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams, __version__ as vllm_version
    from vllm.inputs import TokensPrompt

    c = args.concurrency
    kwargs = dict(model=TARGET_MODEL, dtype="bfloat16", max_num_seqs=c, seed=SEED,
                  gpu_memory_utilization=args.gpu_memory_utilization, max_model_len=args.max_model_len,
                  disable_log_stats=False, enable_prefix_caching=False)
    if args.method != "none":
        kwargs["speculative_config"] = {"method": args.method, "model": args.draft,
                                        "num_speculative_tokens": args.k}
    if args.quantization:
        kwargs["quantization"] = args.quantization
    llm = LLM(**kwargs)
    tok = AutoTokenizer.from_pretrained(TARGET_MODEL)
    rows = _load_rows(args.prompts, args.workloads)
    seen: dict = {}
    rows = [r for r in rows if seen.setdefault(r["workload"], []).append(1) or len(seen[r["workload"]]) <= args.per_workload]
    prompts = [TokensPrompt(prompt_token_ids=_render(tok, r["messages"], r["tools"], r["enable_thinking"]))
               for r in rows]
    sp = SamplingParams(temperature=0.0, max_tokens=args.max_new, stop_token_ids=[151645, 151643], seed=SEED)
    llm.generate(prompts[:1], SamplingParams(temperature=0.0, max_tokens=16, seed=SEED), use_tqdm=False)  # warm-up
    idle0 = time.time()
    time.sleep(args.idle_s)
    idle1 = time.time()
    c0 = _vllm_counters(llm)
    t0 = time.time()
    outs = llm.generate(prompts, sp, use_tqdm=False)
    t1 = time.time()
    c1 = _vllm_counters(llm)
    gen = [len(o.outputs[0].token_ids) for o in outs]
    env = _environment()
    env["vllm"] = vllm_version
    rec = {"method": args.method, "drafter": args.draft or None, "k": args.k if args.method != "none" else None,
           "weights": args.quantization or "bf16", "concurrency": c, "requests": len(prompts),
           "workloads": sorted(seen), "prompt_ids": [r["prompt_id"] for r in rows],
           "prompt_tokens_mean": round(sum(len(p["prompt_token_ids"]) for p in prompts) / len(prompts), 1),
           "max_new_tokens": args.max_new, "generated_tokens": sum(gen), "wall_s": t1 - t0,
           "total_tokens_per_s": sum(gen) / (t1 - t0), "window_unix": [t0, t1], "idle_window_unix": [idle0, idle1],
           "environment": env}
    if args.method != "none" and c1["drafts"] > c0["drafts"]:
        rec["tau_mean"] = 1 + (c1["accepted"] - c0["accepted"]) / (c1["drafts"] - c0["drafts"])
    with open(args.out, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"sweep {args.method} c={c} tok={sum(gen)} {rec['total_tokens_per_s']:.1f} tok/s "
          f"tau={rec.get('tau_mean')}", flush=True)


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

def _hist_from_lengths(lengths: list[int], cap: int) -> list[int]:
    h = [0] * (cap + 1)
    for a in lengths:
        h[min(a, cap)] += 1
    return h


def _stats_from_hist(hist: list[int], gamma: int) -> dict:
    """hist[L] = cycles that committed L tokens (L = accepted drafts + 1)."""
    cycles = sum(hist)
    if cycles == 0:
        return {}
    tau = sum(L * c for L, c in enumerate(hist)) / cycles
    surv = []
    for i in range(1, gamma + 1):  # P(at least i drafts accepted) = P(L >= i+1)
        surv.append(sum(hist[i + 1:]) / cycles)
    cond = [surv[0]] + [(surv[i] / surv[i - 1]) if surv[i - 1] > 0 else None for i in range(1, gamma)]
    return {"cycles": cycles, "tau_mean": round(tau, 4), "histogram_committed_length": hist,
            "survival_by_position": [round(s, 5) for s in surv],
            "conditional_acceptance_by_position": [None if c is None else round(c, 5) for c in cond]}


def _truncated_tau(surv: list[float], gammas) -> dict:
    return {str(g): round(1 + sum(surv[:g]), 4) for g in gammas if g <= len(surv)}


def _bootstrap_ci(values: list[float], weights: list[float], reps=2000):
    """Prompt-level bootstrap of a ratio mean (sum w*v / sum w)."""
    if len(values) < 2:
        return None
    rng = random.Random(SEED)
    n = len(values)
    est = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        sw = sum(weights[i] for i in idx)
        est.append(sum(values[i] * weights[i] for i in idx) / sw if sw else float("nan"))
    est.sort()
    return [round(est[int(0.025 * reps)], 4), round(est[int(0.975 * reps) - 1], 4)]


LOSSLESS_TIE_LOGITS = 0.5
"""A divergence counts as a bf16 near-tie when the target's own top-1/top-2 logit gap at that
step is at most this.  Qwen3-8B's bf16 logits of magnitude 16-32 are quantised in steps of
0.125-0.25, so 0.5 is two to four quanta: a 16-position verification forward and a
1-position decode forward legitimately round such a pair differently."""


def _lossless_summary(rs, base: dict | None) -> dict:
    """Two checks.  (1) EVERY emitted speculative token is teacher-forced against the target
    (``greedy_consistency``).  (2) plain greedy (same engine, same prompt) is replayed and compared
    token for token up to the first divergence, whose margin is recorded."""
    gc = [r["greedy_consistency"] for r in rs if r.get("greedy_consistency", {}).get("tokens")]
    out = {"teacher_forced_every_token": {
        "tokens": sum(g["tokens"] for g in gc),
        "not_target_argmax": sum(g["not_argmax"] for g in gc),
        "deficit_above_tol": sum(g["above_tol"] for g in gc),
        "max_deficit_logits": max((g["max_deficit"] for g in gc), default=None),
        "tol_logits": gc[0]["tol"] if gc else None}}
    if base is None:
        out["versus_plain_greedy"] = "baseline phase not run"
        return out
    ident, compared, divs, missing = 0, 0, [], 0
    for r in rs:
        b = base.get((r["workload"], r["prompt_id"], r["turn"]))
        if b is None or not b["versus_spec"].get("spec_record"):
            missing += 1
            continue
        v = b["versus_spec"]
        compared += v["compared_tokens"]
        if v["identical"]:
            ident += 1
        else:
            divs.append({k: v.get(k) for k in ("index", "baseline_token", "spec_token", "top2_logit_margin",
                                                "spec_token_is_baseline_second", "same_prompt_tokens")}
                        | {"prompt_id": r["prompt_id"], "turn": r["turn"], "spec_tokens": v["spec_tokens"]})
    ties = [d for d in divs if d["top2_logit_margin"] is not None and d["top2_logit_margin"] <= LOSSLESS_TIE_LOGITS]
    out["versus_plain_greedy"] = {
        "reference": "plain greedy, the reference's block_size=1 path, same engine/weights/prompt",
        "samples": len(rs) - missing, "identical_samples": ident, "tokens_compared_before_divergence": compared,
        "divergent_samples": len(divs), "divergences_at_bf16_near_tie": len(ties),
        "near_tie_definition": (f"the baseline's top-1/top-2 logit gap at the divergent step <= "
                                f"{LOSSLESS_TIE_LOGITS} (spec_token_is_baseline_second says whether the speculative "
                                "token was the runner-up or a third token inside the same tie)"),
        "divergences_not_explained_by_a_near_tie": [d for d in divs if d not in ties],
        "divergences": divs}
    return out


def _summarise_hf(path: Path, block: int, base_path: Path | None) -> dict:
    recs = [json.loads(l) for l in open(path)]
    base = _done_keys(base_path) if base_path and base_path.exists() else None
    by = {}
    for r in recs:
        by.setdefault(r["workload"], []).append(r)
    out = {}
    gamma = block - 1
    for w, rs in by.items():
        lengths = [a for r in rs for a in r["acceptance_lengths"]]
        hist = _hist_from_lengths(lengths, block)
        st = _stats_from_hist(hist, gamma)
        per_prompt = [sum(r["acceptance_lengths"]) / len(r["acceptance_lengths"]) for r in rs if r["acceptance_lengths"]]
        cyc = [len(r["acceptance_lengths"]) for r in rs if r["acceptance_lengths"]]
        st["tau_mean_ci95_prompt_bootstrap"] = _bootstrap_ci(per_prompt, cyc)
        st["tau_macro_mean_of_prompt_means"] = round(sum(per_prompt) / len(per_prompt), 4)
        st["tau_per_prompt"] = {f"{r['prompt_id']}#t{r['turn']}": round(sum(r["acceptance_lengths"]) /
                                                                     len(r["acceptance_lengths"]), 3)
                                for r in rs if r["acceptance_lengths"]}
        st["derived_tau_by_truncation"] = _truncated_tau(st["survival_by_position"], [1, 2, 3, 4, 5, 7, 8])
        st.update(_common(rs, "tokens"))
        st["lossless"] = _lossless_summary(rs, base)
        st["wall_s_spec"] = round(sum(r["seconds"] for r in rs), 1)
        out[w] = st
    return out


def _common(rs, tok_key) -> dict:
    return {"samples": len(rs), "prompts": len({r["prompt_id"] for r in rs}),
            "prompt_ids": sorted({r["prompt_id"] for r in rs}),
            "generated_tokens": sum(r[tok_key] for r in rs),
            "mean_prompt_tokens": round(sum(r["prompt_tokens"] for r in rs) / len(rs), 1),
            "samples_hitting_max_new_tokens": sum(r[tok_key] >= r["max_new_tokens"] for r in rs),
            "enable_thinking": rs[0]["enable_thinking"], "max_new_tokens": rs[0]["max_new_tokens"]}


def _summarise_vllm(path: Path, base_path: Path, k: int) -> dict:
    recs = [json.loads(l) for l in open(path)]
    base = {(r["workload"], r["prompt_id"], r["turn"]): r for r in map(json.loads, open(base_path))}
    by = {}
    for r in recs:
        by.setdefault(r["workload"], []).append(r)
    out = {}
    for w, rs in by.items():
        drafts = sum(r["drafts"] for r in rs)
        per_pos = [sum(r["per_pos"][i] for r in rs if i < len(r["per_pos"])) for i in range(k)]
        hist = [0] * (k + 2)
        prev = drafts
        for a in range(k):  # committed length a+1 means exactly a drafts accepted
            hist[a + 1] = prev - per_pos[a]
            prev = per_pos[a]
        hist[k + 1] = prev
        st = _stats_from_hist(hist, k)
        st["tau_mean_from_counters"] = round(1 + sum(r["accepted"] for r in rs) / drafts, 4) if drafts else None
        per_prompt = [1 + r["accepted"] / r["drafts"] for r in rs if r["drafts"]]
        st["tau_mean_ci95_prompt_bootstrap"] = _bootstrap_ci(per_prompt, [r["drafts"] for r in rs if r["drafts"]])
        st["tau_macro_mean_of_prompt_means"] = round(sum(per_prompt) / len(per_prompt), 4)
        st["derived_tau_by_truncation"] = _truncated_tau(st["survival_by_position"], [g for g in (1, 2, 3, 4, 5) if g < k])
        st.update(_common(rs, "tokens"))
        ident, divs = 0, []
        for r in rs:
            b = base.get((r["workload"], r["prompt_id"], r["turn"]))
            if b is None:
                continue
            if b["output_ids"] == r["output_ids"]:
                ident += 1
            else:
                j = next((i for i, (x, y) in enumerate(zip(b["output_ids"], r["output_ids"])) if x != y),
                         min(len(b["output_ids"]), len(r["output_ids"])))
                m = b["top2_logprob_margin"][j] if j < len(b["top2_logprob_margin"]) else None
                same_prompt = b["prompt_sha256"] == r["prompt_sha256"]
                divs.append({"prompt_id": r["prompt_id"], "turn": r["turn"], "index": j,
                             "baseline_top2_logprob_margin": m, "same_prompt_tokens": same_prompt})
        comparable = [d for d in divs if d["same_prompt_tokens"]]
        ties = [d for d in comparable if d["baseline_top2_logprob_margin"] is not None
                and d["baseline_top2_logprob_margin"] <= LOSSLESS_TIE_LOGITS]
        st["lossless"] = {"identical_samples": ident, "samples": len(rs),
                          "divergent_samples_same_prompt": len(comparable),
                          "divergences_at_bf16_near_tie": len(ties),
                          "near_tie_definition": (f"the plain run's top-1/top-2 log-probability gap (= logit gap) "
                                                  f"at the first divergent step <= {LOSSLESS_TIE_LOGITS}"),
                          "divergences_not_explained_by_a_near_tie": [d for d in comparable if d not in ties],
                          "divergences": divs,
                          "reference": "vLLM greedy without speculation, same engine and version"}
        out[w] = st
    return out


def _load_gpu_samples(path: Path) -> list[dict]:
    out = []
    for line in open(path):
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if "procs" in j:
            out.append(j)
    return out


def _contention(samples: list[dict], windows: list[tuple[float, float]]) -> dict:
    inside = [s for s in samples if any(a - 5 <= s["t"] <= b + 5 for a, b in windows)]
    if not inside:
        return {"samples": 0}
    other_sm = [sum(p["sm"] or 0 for p in s["procs"].values() if not p["ours"]) for s in inside]
    other_mem = [sum(p["fb_mb"] or 0 for p in s["procs"].values() if not p["ours"]) for s in inside]
    names = sorted({f"{pid}:{p['name']}" for s in inside for pid, p in s["procs"].items() if not p["ours"]})
    return {"samples": len(inside), "device_util_pct_mean": round(sum(s["util"] for s in inside) / len(inside), 1),
            "other_sm_pct_mean": round(sum(other_sm) / len(other_sm), 1), "other_sm_pct_max": max(other_sm),
            "fraction_of_samples_with_other_sm_active": round(sum(1 for x in other_sm if x > 0) / len(other_sm), 3),
            "other_fb_mb_max": max(other_mem), "other_processes": names}


def _load_power(path: Path) -> list[tuple[float, float]]:
    """``nvidia-smi --query-gpu=timestamp,power.draw.average,power.draw.instant,... -lms 100`` (UTC)."""
    import datetime as _dt

    out = []
    for line in open(path):
        f = [x.strip() for x in line.split(",")]
        try:
            t = _dt.datetime.strptime(f[0], "%Y/%m/%d %H:%M:%S.%f").replace(tzinfo=_dt.timezone.utc).timestamp()
            out.append((t, float(f[2])))
        except (ValueError, IndexError):
            continue
    return out


def _energy_j(power: list[tuple[float, float]], a: float, b: float):
    """Trapezoid integral of board power over [a, b]; None when the log does not cover the window."""
    import bisect

    if not power or power[0][0] > a or power[-1][0] < b:
        return None
    i = bisect.bisect_left(power, (a, -1.0))
    pts = [(a, power[max(0, i - 1)][1])] + [x for x in power[i:] if x[0] < b] + [(b, power[min(len(power) - 1, i)][1])]
    return sum((t1 - t0) * (p0 + p1) / 2 for (t0, p0), (t1, p1) in zip(pts, pts[1:]))


def _summarise_timing(path: Path, samples: list[dict], power: list | None = None,
                      idle_w: float | None = None) -> dict:
    recs = [json.loads(l) for l in open(path)]
    by: dict = {}
    for r in recs:
        by.setdefault(r["workload"], []).append(r)
    out = {}
    for w, rs in by.items():
        ok = [r for r in rs if r.get("ttft_seconds") and r["tokens"] > 1 and r["seconds"] > r["ttft_seconds"]]
        dec_tok = sum(r["tokens"] - 1 for r in ok)
        dec_s = sum(r["seconds"] - r["ttft_seconds"] for r in ok)
        st = {"samples": len(rs), "prompt_ids": [f"{r['prompt_id']}#t{r['turn']}" for r in rs],
              "enable_thinking": rs[0]["enable_thinking"], "max_new_tokens": rs[0]["max_new_tokens"],
              "prompt_tokens_mean": round(sum(r["prompt_tokens"] for r in rs) / len(rs), 1),
              "prompt_tokens_max": max(r["prompt_tokens"] for r in rs),
              "generated_tokens_mean": round(sum(r["tokens"] for r in rs) / len(rs), 1),
              "generated_tokens_total": sum(r["tokens"] for r in rs),
              "decode_tokens_per_s": round(dec_tok / dec_s, 1) if dec_s else None,
              "request_tokens_per_s_incl_prefill": round(sum(r["tokens"] for r in rs) / sum(r["seconds"] for r in rs), 1),
              "ttft_s_mean": round(sum(r["ttft_seconds"] for r in ok) / len(ok), 4) if ok else None}
        if "drafts" in rs[0]:
            d = sum(r["drafts"] for r in rs)
            st["tau_mean"] = round(1 + sum(r["accepted"] for r in rs) / d, 4) if d else None
        if power and all("t_end_unix" in r for r in rs):
            wins = [(r["t_end_unix"] - r["seconds"], r["t_end_unix"]) for r in rs]
            e = [_energy_j(power, a, b) for a, b in wins]
            if all(x is not None for x in e):
                tot_s = sum(b - a for a, b in wins)
                st["energy"] = {"board_energy_j": round(sum(e), 1), "mean_board_power_w": round(sum(e) / tot_s, 1),
                                "j_per_token_gross": round(sum(e) / sum(r["tokens"] for r in rs), 4)}
                if idle_w is not None:
                    net = sum(e) - idle_w * tot_s
                    st["energy"].update({"idle_baseline_w": round(idle_w, 1),
                                         "j_per_token_net_of_idle": round(net / sum(r["tokens"] for r in rs), 4)})
        if samples and all("t_end_unix" in r for r in rs):
            st["contention"] = _contention(samples, [(r["t_end_unix"] - r["seconds"], r["t_end_unix"]) for r in rs])
        out[w] = st
    return out


def aggregate(args) -> None:
    runs = json.loads(Path(args.manifest).read_text())
    result = {
        "schema_version": 1,
        "purpose": ("Acceptance length tau per model, drafter, workload and gamma, replacing assumed values. "
                    "tau counts the target's bonus token, so tau is in [1, gamma+1]. Qwen3-8B points are "
                    "MEASURED here; DeepSeek-V4-family points are CITED/DERIVED from published sources."),
        "tool": "tools/measure_speculative_acceptance.py",
        "convention": {
            "tau": "committed tokens per verification pass including the bonus token (DFlash eq. 1)",
            "gamma": "draft tokens proposed per cycle",
            "survival_by_position": "s_i = P(first i drafts all accepted); tau(gamma) = 1 + sum_{i<=gamma} s_i",
            "derived_tau_by_truncation": ("1 + sum of the first g survival terms of a run at larger gamma. "
                                          "Grade 'derived': it is exact for a chain drafter only up to cycle "
                                          "re-alignment, and for a block drafter the shorter block is a "
                                          "different input, so it is not a run at that gamma."),
            "tau_mean": "cycle-weighted: total committed tokens / total cycles over the workload",
            "tau_macro_mean_of_prompt_means": "DFlash benchmark.py's own averaging: mean over prompts of per-prompt tau",
        },
        "prompts": runs.get("prompts_provenance"),
        "hardware": "one NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB), SHARED with other tenants; see each run environment and contention",
        "sampling": "greedy (temperature 0), batch 1 unless stated, seed 42",
        "qwen3_8b": {},
    }
    samples = _load_gpu_samples(Path(runs["gpu_samples"])) if runs.get("gpu_samples") else []
    power = _load_power(Path(runs["gpu_power"])) if runs.get("gpu_power") else []
    sweep = [json.loads(l) for l in open(runs["sweep"])] if runs.get("sweep") and Path(runs["sweep"]).exists() else []
    idle_w = None
    idles = [_energy_j(power, *r["idle_window_unix"]) / (r["idle_window_unix"][1] - r["idle_window_unix"][0])
             for r in sweep if power and _energy_j(power, *r["idle_window_unix"]) is not None]
    if idles:
        idles.sort()
        idle_w = idles[len(idles) // 2]
    if runs.get("prompts_provenance_file"):
        result["prompts"] = json.loads(Path(runs["prompts_provenance_file"]).read_text())
    for run in runs["runs"]:
        path = Path(run["path"])
        if run.get("optional") and not path.exists():
            continue
        meta = json.loads(Path(str(path) + ".meta.json").read_text())
        if run["kind"] == "timing":
            result.setdefault("throughput_c1", {
                "what": ("Absolute concurrency-1 decode rate of Qwen3-8B on the local GPU, greedy, batch 1, "
                         "vLLM offline engine, prefix caching off. decode_tokens_per_s = sum(n-1) / sum(t_request "
                         "- t_prefill), where t_prefill is a separate max_tokens=1 call on the same prompt; the "
                         "whole-request rate (prefill included) is given too."),
                "caveat": ("The GPU is SHARED with other users' jobs; `contention` records, over each run's "
                           "request windows, the device utilisation and the SM% and memory of every process "
                           "that is not this measurement (nvidia-smi pmon, 10 s samples). Figures are a "
                           "lower bound on an idle-GPU rate whenever other_sm_pct_max > 0."),
                "runs": {}})
            result["throughput_c1"]["runs"][run["id"]] = {
                "method": meta["method"], "drafter": meta.get("drafter") or None,
                "num_speculative_tokens": meta.get("k") if meta["method"] != "none" else None,
                "weights": meta.get("quantization", "bf16"), "grade": "executed",
                "engine": f"vLLM {meta['environment'].get('vllm')}", "environment": meta["environment"],
                "raw_records": run.get("raw_records"), "raw_records_sha256": _sha256_file(path),
                "workloads": _summarise_timing(path, samples, power, idle_w)}
            continue
        if run["kind"] == "hf":
            summary = _summarise_hf(path, meta["block_size"],
                                    Path(run["baseline"]) if run.get("baseline") else None)
            gamma = meta["block_size"] - 1
        else:
            summary = _summarise_vllm(path, Path(run["baseline"]), run["k"])
            gamma = run["k"]
        entry = {"drafter": run["drafter"], "drafter_revision": run.get("drafter_revision"),
                 "drafter_family": run["family"], "gamma": gamma, "grade": "executed",
                 "engine": meta.get("implementation") or f"vLLM {meta['environment'].get('vllm')}",
                 "environment": meta["environment"], "raw_records": run.get("raw_records"),
                 "raw_records_sha256": _sha256_file(path), "workloads": summary}
        if "block_size" in meta:
            entry["block_size"] = meta["block_size"]
        if run.get("setup_suspect"):
            entry["setup_suspect"] = run["setup_suspect"]
        if run.get("note"):
            entry["note"] = run["note"]
        result["qwen3_8b"][run["id"]] = entry
    if sweep:
        pts = []
        for r in sweep:
            a, b = r["window_unix"]
            ia, ib = r["idle_window_unix"]
            e, ei = _energy_j(power, a, b), _energy_j(power, ia, ib)
            pt = {k: r[k] for k in ("method", "drafter", "k", "weights", "concurrency", "requests", "workloads",
                                    "prompt_tokens_mean", "max_new_tokens", "generated_tokens")}
            pt["total_tokens_per_s"] = round(r["total_tokens_per_s"], 1)
            pt["wall_s"] = round(r["wall_s"], 1)
            if "tau_mean" in r:
                pt["tau_mean"] = round(r["tau_mean"], 4)
            if e is not None:
                pt["board_energy_j"] = round(e, 1)
                pt["mean_board_power_w"] = round(e / (b - a), 1)
                pt["j_per_token_gross"] = round(e / r["generated_tokens"], 4)
                if ei is not None:
                    pw = ei / (ib - ia)
                    pt["idle_power_w_same_engine_loaded"] = round(pw, 1)
                    pt["j_per_token_net_of_idle"] = round((e - pw * (b - a)) / r["generated_tokens"], 4)
            if samples:
                pt["contention"] = _contention(samples, [(a, b)])
            pts.append(pt)
        result.setdefault("throughput_c1", {})["concurrency_sweep"] = {
            "what": ("One vLLM engine per point at max_num_seqs = c, all requests submitted at once; total "
                     "tokens/s and board energy per generated token. Board power (nvidia-smi power.draw.instant, "
                     "100 ms) includes other tenants; the idle window (engine loaded, 20 s, immediately before) "
                     "gives the net figure."),
            "grade": "executed", "points": sorted(pts, key=lambda x: (x["method"], x["concurrency"]))}
    if args.extra:
        for extra in args.extra:
            key, p = extra.split("=", 1)
            result[key] = json.loads(Path(p).read_text())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(f"wrote {args.out}")


# ---------------------------------------------------------------------------
# block-sweep: DFlash run directly at each block size vs truncation of block 16
# ---------------------------------------------------------------------------

PRIMARY_CLASSES = ("reasoning", "agentic", "chat")   # the crosscheck workloads repeat math/code thinking-off


def _pool(recs: list[dict], key=lambda r: r["acceptance_lengths"]) -> tuple[int, int]:
    """(committed tokens, cycles) over records."""
    return sum(sum(key(r)) for r in recs), sum(len(key(r)) for r in recs)


def block_sweep(args) -> None:
    """Join run-hf records made at several ``--block-size`` values into one table.  For each block B
    and workload: the DIRECT tau of the run at B (the drafter given B-1 mask slots, the reference's own
    ``block_size`` argument), and the TRUNCATED tau the architecture model used so far -- every cycle
    of the block-16 run with its committed length L cut to min(L, B), i.e. 1 + the first B-1 survival
    terms of the block-16 run, evaluated on the very same records."""
    ref_path = Path(args.reference)
    ref = [json.loads(l) for l in open(ref_path)]
    ref_meta = json.loads(Path(str(ref_path) + ".meta.json").read_text())
    ref_block = ref_meta["block_size"]
    ref_by = {}
    for r in ref:
        ref_by.setdefault(r["workload"], []).append(r)
    ref_rec = {(r["workload"], r["prompt_id"], r["turn"]): r for r in ref}

    def key(r):
        return r["workload"], r["prompt_id"], r["turn"]

    def prefix(r):
        """Tokens this run shares with the block-16 run's output before the first difference."""
        a, b = r["output_ids"], ref_rec[key(r)]["output_ids"]
        n = 0
        for x, y in zip(a, b):
            if x != y:
                break
            n += 1
        return n
    runs = {}
    for spec in args.run:
        b, p = spec.split("=", 1)
        runs[int(b)] = Path(p)
    if ref_block not in runs:
        runs[ref_block] = ref_path
    classes = {r["workload"]: r["class"] for r in ref}
    workloads = sorted(ref_by, key=lambda w: (classes[w] == "crosscheck", w))
    blocks = {}
    for B in sorted(runs):
        path = runs[B]
        meta = json.loads(Path(str(path) + ".meta.json").read_text())
        assert meta["block_size"] == B, (path, meta["block_size"], B)
        recs = [json.loads(l) for l in open(path)]
        by = {}
        for r in recs:
            by.setdefault(r["workload"], []).append(r)
        per_w = {}
        for w in workloads:
            rs = by.get(w, [])
            if not rs:
                continue
            tok, cyc = _pool(rs)
            ref_same = [ref_rec[key(r)] for r in rs]   # the same prompt turns, so a partial run compares fairly
            rtok, rcyc = _pool(ref_same, key=lambda r: [min(a, B) for a in r["acceptance_lengths"]])
            per_prompt = [sum(r["acceptance_lengths"]) / len(r["acceptance_lengths"]) for r in rs
                          if r["acceptance_lengths"]]
            weights = [len(r["acceptance_lengths"]) for r in rs if r["acceptance_lengths"]]
            hist = _hist_from_lengths([a for r in rs for a in r["acceptance_lengths"]], B)
            st = _stats_from_hist(hist, B - 1)
            gc = [r["greedy_consistency"] for r in rs if r.get("greedy_consistency", {}).get("tokens")]
            same = sum(ref_rec[key(r)]["output_sha256"] == r["output_sha256"] for r in rs)
            per_w[w] = {
                "class": classes[w], "samples": len(rs), "complete": len(rs) == len(ref_by[w]),
                "cycles": cyc, "generated_tokens": sum(r["tokens"] for r in rs),
                "tau_direct": round(tok / cyc, 4),
                "tau_direct_ci95_prompt_bootstrap": _bootstrap_ci(per_prompt, weights),
                "tau_direct_macro_mean_of_prompt_means": round(sum(per_prompt) / len(per_prompt), 4),
                "tau_truncated_from_block16": round(rtok / rcyc, 4),
                "direct_over_truncated": round((tok / cyc) / (rtok / rcyc), 4),
                "histogram_committed_length": hist,
                "survival_by_position": st.get("survival_by_position"),
                "teacher_forced_every_token": {
                    "tokens": sum(g["tokens"] for g in gc), "not_target_argmax": sum(g["not_argmax"] for g in gc),
                    "deficit_above_tol": sum(g["above_tol"] for g in gc),
                    "max_deficit_logits": max((g["max_deficit"] for g in gc), default=None)},
                "outputs_identical_to_block16_run": same,
                "tokens_before_first_difference_from_block16_run": sum(prefix(r) for r in rs),
                "wall_s": round(sum(r["seconds"] for r in rs), 1)}
        pooled = {}
        for label, keep in (("primary", lambda w: classes[w] in PRIMARY_CLASSES), ("all", lambda w: True)):
            ws = [w for w in per_w if keep(w)]
            rs = [r for w in ws for r in by[w]]
            if not rs:
                continue
            tok, cyc = _pool(rs)
            rtok, rcyc = _pool([ref_rec[key(r)] for r in rs],
                               key=lambda r: [min(a, B) for a in r["acceptance_lengths"]])
            pooled[label] = {
                "workloads": ws, "cycles": cyc,
                "tau_direct_cycle_weighted": round(tok / cyc, 4),
                "tau_truncated_cycle_weighted": round(rtok / rcyc, 4),
                "tau_direct_mean_of_workloads": round(sum(per_w[w]["tau_direct"] for w in ws) / len(ws), 4),
                "tau_truncated_mean_of_workloads": round(
                    sum(per_w[w]["tau_truncated_from_block16"] for w in ws) / len(ws), 4),
                "tau_direct_workload_range": [min(per_w[w]["tau_direct"] for w in ws),
                                              max(per_w[w]["tau_direct"] for w in ws)]}
        blocks[str(B)] = {"block_size": B, "draft_tokens_per_cycle": B - 1,
                          "raw_records": f"results/speculative/raw/dflash_b{B}_hf_spec.jsonl.gz",
                          "raw_records_sha256": _sha256_file(path),
                          "implementation": meta.get("implementation"), "environment": meta.get("environment"),
                          "in_training_distribution": B == ref_block, "pooled": pooled, "workloads": per_w}
    result = {
        "schema_version": 1,
        "what": ("DFlash acceptance of z-lab/Qwen3-8B-DFlash-b16 on Qwen3-8B MEASURED at each block size by running "
                 "the reference dflash_generate with that block_size (anchor + B-1 mask slots, the drafter's "
                 "within-block attention over B positions), greedy, batch 1, BF16 weights and activations, on the "
                 "same 264 prompt turns as results/speculative/acceptance_tau.json; beside it, the truncation of "
                 "the block-16 run that the architecture model used until now."),
        "tool": "tools/measure_speculative_acceptance.py block-sweep",
        "drafter": ref_meta["drafter"], "trained_block_size": ref_block,
        "out_of_distribution": (f"The drafter was trained at block {ref_block}. A shorter block is a supported "
                                "argument of the reference (dflash_generate(block_size=...)) but out of its training "
                                "distribution: the drafter sees fewer mask slots in its bidirectional block. These "
                                "rows measure that drafter at that block. A drafter trained at the short block is "
                                "not measured; no inference about retraining is made."),
        "convention": {
            "tau_direct": "committed tokens / verification cycles of the run at block B (bonus token included)",
            "tau_truncated_from_block16": "sum_c min(L_c, B) / cycles over the block-16 run's cycles c",
            "direct_over_truncated": "tau_direct / tau_truncated_from_block16",
            "primary": "reasoning + agentic + chat workloads (9); 'all' adds the two thinking-off crosschecks",
            "outputs_identical_to_block16_run": ("samples whose output token sequence equals the block-16 run's: greedy "
                                                 "speculation is lossless, so every block follows the target's greedy "
                                                 "path up to bf16 near-ties between differently shaped verify forwards "
                                                 "(teacher_forced_every_token grades those); after the first such tie "
                                                 "the two runs continue on different texts"),
            "tokens_before_first_difference_from_block16_run": "summed over samples: the shared-trajectory prefix",
        },
        "arithmetic": ("BF16 weights, BF16 activations, BF16 KV, sdpa attention on the GPU. NOT the deployment arithmetic "
                       "(3.5-bit ROM weights, FP8 KV): no quantised emulation existed when this ran (branch "
                       "claude/quality-eval had no commits past main); the vLLM FP8 W8A8 run in acceptance_tau.json "
                       "(block 16) moved MATH-500 tau from 3.65 to 3.72."),
        "prompts_sha256": _sha256_file(Path(args.prompts)) if args.prompts else None,
        "reference_run": {"path_sha256": _sha256_file(ref_path), "block_size": ref_block,
                          "raw_records": "results/speculative/raw/dflash_b16_hf_spec.jsonl.gz"},
        "blocks": blocks,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(f"wrote {args.out}")
    print(f"{'B':>3} {'direct':>8} {'trunc':>8} {'ratio':>6}  (primary, cycle-weighted; mean of workloads)")
    for B, e in blocks.items():
        p = e["pooled"].get("primary", {})
        if p:
            print(f"{B:>3} {p['tau_direct_cycle_weighted']:8.4f} {p['tau_truncated_cycle_weighted']:8.4f} "
                  f"{p['tau_direct_cycle_weighted'] / p['tau_truncated_cycle_weighted']:6.3f}  "
                  f"{p['tau_direct_mean_of_workloads']:.4f} / {p['tau_truncated_mean_of_workloads']:.4f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=24)
    p.add_argument("--tau-bench-root", default="/home/ubuntu/tau-bench")
    p = sub.add_parser("run-hf")
    p.add_argument("--prompts", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dflash-repo", required=True)
    p.add_argument("--draft", default="z-lab/Qwen3-8B-DFlash-b16")
    p.add_argument("--block-size", type=int, default=0)
    p.add_argument("--workloads", default="")
    p.add_argument("--mode", choices=["spec", "baseline"], default="spec")
    p.add_argument("--spec-records", default="")
    p.add_argument("--tol", type=float, default=0.5)
    p = sub.add_parser("run-vllm")
    p.add_argument("--prompts", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--method", default="eagle3")
    p.add_argument("--draft", default="")
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--gpu-memory-utilization", type=float, default=0.25)
    p.add_argument("--max-model-len", type=int, default=12288)
    p.add_argument("--quantization", default="", help="e.g. fp8 (online W8A8 in vLLM); default BF16")
    p.add_argument("--timing", action="store_true",
                   help="throughput mode: no logprobs, a separate max_tokens=1 call measures prefill+first token")
    p.add_argument("--per-workload", type=int, default=0)
    p.add_argument("--workloads", default="")
    p = sub.add_parser("sweep")
    p.add_argument("--prompts", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--method", default="none")
    p.add_argument("--draft", default="")
    p.add_argument("--k", type=int, default=0)
    p.add_argument("--concurrency", type=int, required=True)
    p.add_argument("--quantization", default="")
    p.add_argument("--workloads", default="xcheck_math500_nothink,chat_mt_bench")
    p.add_argument("--per-workload", type=int, default=16)
    p.add_argument("--max-new", type=int, default=512)
    p.add_argument("--idle-s", type=float, default=20.0)
    p.add_argument("--gpu-memory-utilization", type=float, default=0.24)
    p.add_argument("--max-model-len", type=int, default=4096)
    p = sub.add_parser("aggregate")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", default=str(REPO / "results/speculative/acceptance_tau.json"))
    p.add_argument("--extra", action="append", default=[])
    p = sub.add_parser("block-sweep")
    p.add_argument("--reference", required=True, help="run-hf spec records at the drafter's own block (16)")
    p.add_argument("--run", action="append", default=[], help="B=path of run-hf spec records at --block-size B")
    p.add_argument("--prompts", default="")
    p.add_argument("--out", default=str(REPO / "results/speculative/dflash_block_acceptance.json"))
    a = ap.parse_args()
    {"prepare": prepare, "run-hf": run_hf, "run-vllm": run_vllm, "sweep": run_sweep,
     "aggregate": aggregate, "block-sweep": block_sweep}[a.cmd](a)


if __name__ == "__main__":
    main()
