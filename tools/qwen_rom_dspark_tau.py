#!/usr/bin/env python3
"""Measured DSpark acceptance (tau) for Qwen3-8B, greedy, on a small per-class prompt sample.

Target Qwen/Qwen3-8B @ b968826d (BF16, HF transformers), drafter
deepseek-ai/dspark_qwen3_8b_block7 @ 03326e50 run through the publisher's own
modeling code (github.com/deepseek-ai/DeepSpec @ 005e03b8,
deepspec/modeling/dspark/qwen3/modeling.py, MIT).

Greedy speculative decoding is lossless, so the committed sequence is the
target's greedy continuation whatever the drafts are.  This tool therefore
generates the target's greedy continuation once, takes every position's
target hidden states from one forward pass over prompt + continuation, and
replays the DSpark loop of DeepSpec's generate_decoding_sample offline: at a
step whose anchor is at `start` the drafter sees the target features of
positions [0, start) (extract_context_feature, layer ids [1, 9, 17, 25, 33]),
drafts S slots [anchor, mask x (S-1)] at positions start .. start+S-1 with
full (non-causal) attention over context + block, adds the vanilla Markov bias
sequentially and takes the argmax; the step accepts the longest prefix of the
first B-1 drafts that equals the greedy continuation and commits a+1 tokens
(the bonus).  tau(B) = mean committed tokens per step.  The confidence head is
not used (threshold 0: every slot is proposed), as in the published tau.

Configurations: S = 7 (as trained) truncated to B-1 for B = 2..8, and S = B-1
(the block itself shortened) for B = 2, 4; drafter in BF16 and with W8 per-row
fake quantisation (the ROM INT8 contract, tools/qwen3_deployment_quality.quantize_w8, dequantised into BF16 weights)
of every drafter-unique matrix.

  qwen_rom_dspark_tau.py --deepspec DIR --draft SNAP --target SNAP --classes chat,coding --out OUT.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import torch

PROMPTS = {
    "chat": [
        "What are some good ways to stay focused while working from home? Give practical advice.",
        "My friend forgot my birthday and I feel hurt. How should I bring it up with them?",
        "Explain the difference between weather and climate to a ten-year-old.",
    ],
    "reasoning": [
        "A train leaves at 9:40 and travels 210 km at 84 km/h. At what time does it arrive? Show your steps.",
        "Find all real x such that x^2 - 5x + 6 = 0, and verify each root.",
        "If 3 workers paint a house in 8 days, how long do 4 workers take at the same rate? Explain.",
    ],
    "coding": [
        "Write a Python function that returns the longest palindromic substring of a string, with comments.",
        "Implement a thread-safe LRU cache class in Python with get and put methods.",
        "Write a C function that reverses a singly linked list in place and explain its complexity.",
    ],
    "long_doc_rag": [
        "Context: The Great Barrier Reef is the world's largest coral reef system, composed of over 2,900 individual reefs "
        "and 900 islands stretching over 2,300 kilometres off the coast of Queensland, Australia. It can be seen from outer "
        "space and is the world's biggest single structure made by living organisms. Coral bleaching events in 1998, 2002, "
        "2016, 2017 and 2020 have damaged large areas.\nQuestion: Summarise the passage and list the bleaching years.",
        "Context: The Treaty of Westphalia (1648) ended the Thirty Years' War and the Eighty Years' War. It established the "
        "principle of state sovereignty and recognised the independence of the Dutch Republic and the Swiss Confederation.\n"
        "Question: What did the treaty establish? Answer from the context only.",
        "Context: Photosynthesis converts light energy into chemical energy. In the light-dependent reactions, water is split "
        "and oxygen released; the Calvin cycle then fixes carbon dioxide into sugars using ATP and NADPH.\nQuestion: Explain "
        "the two stages described in the context.",
    ],
    "multilingual": [
        "请用中文介绍一下长城的历史和意义。",
        "Explique en français pourquoi le ciel est bleu.",
        "Escribe en español una breve receta de tortilla de patatas.",
    ],
    "long_agentic": [
        "You are an agent with tools search(query) and open(url). Plan step by step how to find the population of the "
        "capital of the country that won the 2018 FIFA World Cup, writing each tool call you would make.",
        "You are a software agent. The test suite fails with 'ImportError: cannot import name x from y'. Describe the "
        "sequence of shell commands and edits you would make to diagnose and fix it.",
        "Act as a travel-planning agent. Produce a day-by-day plan for 3 days in Kyoto, with the tool calls you would use.",
    ],
    "assistant_structured": [
        "Return a JSON object with fields name, age, email for three fictional users. Output only JSON.",
        "Convert this to a JSON list of objects with keys city and country: Paris France, Tokyo Japan, Lima Peru, Cairo Egypt.",
        "Produce a YAML configuration for a web server with host, port, tls settings, and two routes.",
    ],
    "creative": [
        "Write a short poem about the sea at night.",
        "Write the opening paragraph of a mystery story set in a lighthouse.",
        "Describe an imaginary city floating in the clouds in vivid detail.",
    ],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fake_w8(w: torch.Tensor) -> torch.Tensor:
    """The W8 contract (tools/qwen3_deployment_quality.quantize_w8: per-row BF16 scale, MSE clip), dequantised."""
    from qwen3_deployment_quality import quantize_w8
    codes, scales, _ = quantize_w8(w.float())
    return (codes.float() * scales.float()).to(w.dtype)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deepspec", type=Path, required=True)
    ap.add_argument("--draft", type=Path, required=True)
    ap.add_argument("--target", type=Path, required=True)
    ap.add_argument("--classes", default=",".join(PROMPTS))
    ap.add_argument("--max-new", type=int, default=160)
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="prompts per class (0: all)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    sys.path.insert(0, str(a.deepspec))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from deepspec.modeling.dspark.qwen3 import Qwen3DSparkModel
    from deepspec.modeling.dspark.common import extract_context_feature

    tok = AutoTokenizer.from_pretrained(a.target)
    target = AutoModelForCausalLM.from_pretrained(a.target, dtype=torch.bfloat16, attn_implementation="sdpa").eval()
    drafts = {"bf16": Qwen3DSparkModel.from_pretrained(a.draft, dtype=torch.bfloat16, attn_implementation="sdpa").eval()}
    q = Qwen3DSparkModel.from_pretrained(a.draft, dtype=torch.bfloat16, attn_implementation="sdpa").eval()
    with torch.no_grad():
        for name, mod in q.named_modules():
            if isinstance(mod, torch.nn.Linear) and not name.startswith("lm_head"):
                mod.weight.copy_(fake_w8(mod.weight))
        q.markov_head.markov_w1.weight.copy_(fake_w8(q.markov_head.markov_w1.weight))
    drafts["w8"] = q
    layer_ids = drafts["bf16"].target_layer_ids
    mask_id = int(drafts["bf16"].mask_token_id)
    rec = {"schema": "opentallas.qwen-rom-dspark-tau.v1", "target": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218",
           "draft": "deepseek-ai/dspark_qwen3_8b_block7@03326e5043815da1f81b109078b2889737c26017",
           "deepspec": "deepseek-ai/DeepSpec@005e03b81cec38b7da6399833d609ee89a2587f2",
           "tool_sha256": sha(__file__), "max_new_tokens": a.max_new, "mode": "non-thinking chat template, greedy",
           "samples": []}

    @torch.no_grad()
    def draft_tokens(model, feats, seq, start, S):
        ids = torch.full((1, S), mask_id, dtype=torch.long)
        ids[0, 0] = seq[start]
        pos = torch.arange(start + S).unsqueeze(0)
        hid = model._forward_backbone(target_hidden_states=feats[:, :start], noise_embedding=model.embed_tokens(ids),
                                      position_ids=pos, attention_mask=None, past_key_values=None,
                                      use_cache=False, is_causal=False)
        base = model.compute_logits(hid[:, :S])
        toks, _ = model.sample_draft_tokens(base, first_prev_token_ids=ids[:, 0], temperature=0.0, hidden_states=hid[:, :S])
        return toks[0].tolist()

    for cls in a.classes.split(","):
        for i, prompt in enumerate(PROMPTS[cls][:a.limit or None]):
            t0 = time.time()
            text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
            inp = tok(text, return_tensors="pt").input_ids
            with torch.no_grad():
                gen = target.generate(inp, max_new_tokens=a.max_new, do_sample=False, temperature=None, top_p=None, top_k=None)
                out = target(gen, output_hidden_states=True)
            feats = extract_context_feature(out.hidden_states, layer_ids)
            seq = gen[0].tolist()
            n0, n = inp.shape[1], len(seq)
            res = {"class": cls, "prompt_index": i, "prompt_tokens": n0, "generated": n - n0}
            cache = {}
            for dname, model in drafts.items():
                for S, blocks in ((7, range(2, 9)), (3, (4,)), (1, (2,))):
                    for B in blocks:
                        start, lens = n0, []
                        while start < n - 1:
                            key = (dname, S, start)
                            if key not in cache:
                                cache[key] = draft_tokens(model, feats, seq, start, S)
                            d = cache[key][:B - 1]
                            acc = 0
                            while acc < len(d) and start + 1 + acc < n and d[acc] == seq[start + 1 + acc]:
                                acc += 1
                            lens.append(acc + 1)
                            start += acc + 1
                        res[f"tau_{dname}_S{S}_B{B}"] = sum(lens) / len(lens)
            res["seconds"] = round(time.time() - t0, 1)
            rec["samples"].append(res)
            print(json.dumps(res), flush=True)
            a.out.write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
