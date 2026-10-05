#!/usr/bin/env python3
"""ONE canonical registry of third-party (external) figures used by OpenTallas records.

OWNER CORRECTION (2026-10-04): every agent cites results/external/registry.json instead of re-researching.
This tool (a) HARVESTS every third-party reference already committed in the repo (sync_cost_table references,
decode_roofline citations, acceptance_tau published sources, qwen_gpu_calibration, v41_rack physical constants,
the H100 NVLS README's published references and the 2026-10-04 switch-latency research note), (b) adds the
entries researched on 2026-10-04 to fill genuine gaps (each marked "new": true), (c) computes which committed
records/tools cite each URL ("used_by"), and (d) writes the three topical records that are views of the registry:

  results/external/registry.json + README.md
  results/speculative/third_party_acceptance_20261004/acceptance.json + README.md   (read by tools/third_party_tau.py)
  results/measured/gpu_third_party_20261004/gpu_baselines.json + README.md
  results/arch/vendor_assumption_check_20261004/vendor_check.json + README.md

No network access, no simulation: everything is read from committed files or written inline below with the
exact quote seen on the fetched page.  Usage: python3 tools/external_registry.py [--check]
(--check rebuilds in memory and fails if any committed output differs).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-04"
OWNER_RULE = ("OWNER RULE 2026-10-04: speculative-decoding acceptance and the DeepSeek-V4.1 GPU decode baseline must come "
              "from PUBLISHED THIRD-PARTY sources (MLCommons, LMSys/SGLang, vLLM, model vendors, NVIDIA/AMD, ...), never "
              "from our own measurement. OWNER CORRECTION: cite this registry instead of re-researching.")

DECISION_DS_TAU = dict(
    date="2026-10-05", id="owner:ds_tau_owner6_blend",
    decision="DeepSeek-V4.1 composition default tau = 4.159, the owner 6-class workload blend (harmonic, greedy, gamma 5) "
             "in results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json; the published V4.1 value 3.8879 "
             "and the published V4.1 gamma-5 range 3.43-4.32 are kept as a SENSITIVITY (OT_TAU_SOURCE=third_party). "
             "Qwen3-8B keeps the third-party derived 3.1445.",
    reason="OWNER: a single GSM8K dataset (the 3.8879 primary) makes no sense as the headline workload, and several "
           "published sources are V4-Flash, not V4.1.",
    supersedes="the 2026-10-04 owner rule's DS default (published 3.8879); the third-party figures below are unchanged")
OUT_REG = ROOT / "results/external"
OUT_ACC = ROOT / "results/speculative/third_party_acceptance_20261004"
OUT_GPU = ROOT / "results/measured/gpu_third_party_20261004"
OUT_VEN = ROOT / "results/arch/vendor_assumption_check_20261004"

# --------------------------------------------------------------------------------------------------------------
# (a) harvest: existing committed references
# --------------------------------------------------------------------------------------------------------------


def _j(rel):
    return json.loads((ROOT / rel).read_text())


def harvest() -> list[dict]:
    out = []
    rel = "results/arch/sync_cost_table.json"
    for k, r in _j(rel)["references"].items():
        if not r.get("url"):
            continue  # this work's own measurements (r-gpu-meas, r-rtl-tp, r-signoff) are not external
        out.append(dict(id=f"sct:{k}", topic="interconnect/power/energy", title=r["text"], url=r["url"],
                        cls=r.get("cls"), quote=r.get("quote"), harvested_from=f"{rel} references.{k}"))
    rel = "results/arch/decode_roofline.json"
    for k, r in _j(rel)["cited"].items():
        src = r.get("source", "")
        if not re.search(r"http|arXiv|datasheet|NVIDIA|Megatron", src):
            continue
        m = re.search(r"https?://\S+", src)
        out.append(dict(id=f"roofline:{k}", topic="gpu/speculative", title=src[:160], url=m.group(0).rstrip(")'.,:") if m else None,
                        cls=r.get("evidence"), value=r.get("value"), unit=r.get("unit"), quote=src,
                        harvested_from=f"{rel} cited.{k}"))
    rel = "results/speculative/acceptance_tau.json"
    for s in _j(rel)["deepseek_v4_family"]["sources"]:
        if not str(s.get("url", "")).startswith("http"):
            continue  # local tech-report PDF and our own on-policy measurement are not third-party web sources
        out.append(dict(id=f"acc:{s['id']}", topic="speculative acceptance", title=s["model"],
                        url=s["url"].split(" ")[0], date_fetched=s.get("fetched"), quote=s.get("quote"),
                        value=s.get("numbers"), conditions=dict(hardware=s.get("hardware"), workload=s.get("workload"),
                                                                gamma=s.get("gamma"), sampling=s.get("sampling")),
                        harvested_from=f"{rel} deepseek_v4_family.sources[id={s['id']}]"))
    rel = "results/arch/qwen_gpu_calibration.json"
    n = _j(rel)["nim_h200"]
    out.append(dict(id="calib:nim_h200", topic="gpu baseline", title="NVIDIA NIM LLM benchmarking (H200, 8B-class decode)",
                    url=n["source"], value=dict(bf16_tok_s=n["bf16_tok_s"], fp8_tok_s=n["fp8_tok_s"]),
                    cls="vendor measurement", harvested_from=f"{rel} nim_h200"))
    rel = "results/arch/v41_rack.json"
    seen = set()

    def walk(o, p):
        if isinstance(o, dict):
            if isinstance(o.get("url"), str) and o["url"].startswith("http") and (p, o["url"]) not in seen:
                seen.add((p, o["url"]))
                out.append(dict(id=f"rack:{p.lstrip('.')}", topic="interconnect/packaging", title=str(o.get("source", ""))[:160],
                                url=o["url"], value=o.get("value"), cls=o.get("grade"), quote=o.get("source"),
                                harvested_from=f"{rel} {p.lstrip('.')}"))
            for k, v in o.items():
                walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
    walk(_j(rel), "")
    return out


# The H100 NVLS README's "published references" and the switch-latency research note (kept outside the repo at
# /tmp/claude-review-20261003/switch_latency_research.md) are imported here verbatim-in-substance; the 2026-10-04
# verification of the README's DeepSeek line is recorded in its "verification" field.
IMPORTED = [
    dict(id="nvls:lmsys_dsv4_day0", topic="gpu baseline", title="LMSYS Org, DeepSeek-V4 on Day 0 (SGLang + Miles), 25 Apr 2026",
         url="https://www.lmsys.org/blog/2026-04-25-deepseek-v4/", date="2026-04-25", cls="third-party engine measurement",
         value=dict(h200_v4flash_tp4_tok_s={"4K": 266, "900K": 240}, b200_v4pro_tp8_tok_s={"4K": 199, "900K": 180}),
         quote="The drop is under 10% on both B200 (199 -> 180 token/s) and H200 (266 -> 240 token/s). | B200 Pro (1.6T) at TP=8; "
               "H200 Flash (285B) at TP=4. Single-batch decode, OSL=4096 | Figure 2: Hybrid sparse attention combined with ShadowRadix "
               "and in-graph spec metadata keeps SGLang decode throughput essentially flat from 4K to 900K | Figure 1 (30K-token prompt): "
               "Speculative decoding (best-effort per each engine's official recipe): SGLang: EAGLE 3/1/4 (num-steps=3, eagle-topk=1, num-draft-tokens=4)",
         harvested_from="results/measured/h100_nvls_20261004/README.md (Addendum, published references)",
         verification="RE-FETCHED 2026-10-04. CORRECTS the README line: the model is DeepSeek-V4-Flash (H200) and V4-Pro (B200), not "
                      "V4.1; 266 tok/s is the 4K end of Figure 2 (240 at 900K), not a 30K-prefix figure (30K is Figure 1); the "
                      "README's 'no speculation' is NOT supported: Figure 1 used EAGLE 3/1/4 and Figure 2's caption cites in-graph "
                      "spec metadata, so speculation is most likely ON (not stated explicitly for Figure 2)."),
    dict(id="nvls:dynamo_v41_recipe", topic="gpu baseline", title="NVIDIA Dynamo recipe: DeepSeek-V4.1-Flash",
         url="https://docs.nvidia.com/dynamo/dev/recipes/deepseek-v4-1-flash", cls="vendor recipe",
         quote="Day-0 recipe. Both targets pass a functional probe. Neither is benchmarked, and neither carries a performance claim.",
         harvested_from="results/measured/h100_nvls_20261004/README.md (Addendum, published references)",
         verification="RE-FETCHED 2026-10-04: the page carries NO performance figure; it cannot support the 266 tok/s."),
    dict(id="nvls:sglang_disc_39791", topic="gpu baseline", title="SGLang discussion #39791: DeepSeek-V4.1-Flash on H100",
         url="https://github.com/sgl-project/sglang/discussions/39791", date="2026-09-16..25", cls="community report",
         value=dict(v41_flash_h100_single_request_tok_s=[40, 50], v4_flash_0731_h100_tp8_marlin_tok_s=">150"),
         quote="DeepSeek V4.1 Flash on H100: single request 40-50 tokens/s range; H100 is not a supported target for V4.1 "
               "(supported: H200, B200, B300, GB300, MI350X). DeepSeek V4 Flash 0731 on H100 TP8 marlin: 150+ tokens/sec.",
         harvested_from="results/measured/h100_nvls_20261004/README.md (Addendum, published references)",
         verification="RE-FETCHED 2026-10-04: 40-50 tok/s confirmed (unsupported target, user report)."),
    dict(id="nvls:gfactor_qwen38_27b", topic="gpu baseline", title="g factor, Benchmarking Qwen3.8-27B across inference providers (dev.to)",
         url="https://dev.to/g_factor/benchmarking-qwen-38-27b-across-inference-providers-together-fireworks-doubleword-and-g-factor-4c1i",
         cls="third-party provider benchmark", value=dict(together_tp2_tok_s=189.6, gfactor_mtp4_tok_s=133.0, fireworks_tok_s=114.5,
                                                         vanilla_vllm_tok_s=69.3),
         quote="single-stream (concurrency 1) on 2x H100: Together 189.6 tok/s (TP2), g factor MTP4 133.0, Fireworks 114.5, vanilla vLLM 69.3",
         harvested_from="results/measured/h100_nvls_20261004/README.md (Addendum)",
         verification="from search summaries per the README; not re-fetched 2026-10-04 (Qwen3.8-27B is not a target model)."),
]
for _r in [
    ("arXiv:2607.16100 Every Microsecond Matters (GB200 one-way remote store 0.792 us, SoL AllReduce 1.404 us)", "https://arxiv.org/abs/2607.16100", "V"),
    ("MSCCL++ arXiv:2504.09014 Table 1: H100 NVLink latency 822/829 ns", "https://arxiv.org/abs/2504.09014", "V"),
    ("Demystifying NVSHMEM arXiv:2606.05951: intra-node put/get 1.8-2.5 us; NCCL NVLS 5.6-5.9 us", "https://arxiv.org/abs/2606.05951", "V"),
    ("SiFAR arXiv:2607.08973: H200 one-shot AllReduce 8 KB 2.33-2.44 us barrier-free", "https://arxiv.org/abs/2607.08973", "V(fetch summary)"),
    ("NVIDIA forum: nccl-tests 8 B all_reduce ~2.3 us H800/H200, ~3 us B200", "https://forums.developer.nvidia.com/t/inter-gpu-latency-on-b200-higher-than-on-hopper/352473", "S"),
    ("HC2024 NVIDIA NVL72 deck: SHARP in-network compute 3.6 TFLOPS", "https://www.hc2024.hotchips.org/assets/program/conference/day1/64_HC2024.NVIDIA.TirumalaWong.pdf", "V"),
    ("ConvergeDigest mirror of Broadcom Tomahawk Ultra PR (250 ns, sub-400 ns XPU-XPU, INC)", "https://convergedigest.com/broadcom-ships-tomahawk-ultra-to-power-ai-scale-up/", "V"),
    ("IEEE P802.3dj Patra 2023-03: RS(544)+Hamming interleaver ~140 ns (800G 2-way) / ~56 ns (4-way)", "https://www.ieee802.org/3/dj/public/23_03/patra_3dj_01b_2303.pdf", "V"),
    ("UALink nand-research note: port-to-port 100-150 ns", "https://nand-research.com/research-note-ualink-consortium-releases-ualink-1-0/", "S"),
    ("SHARP (Switch-IB 2) COMHPC'16: 8 B MPI_Allreduce 128 hosts 6.01 -> 2.83 us", "https://network.nvidia.com/pdf/solutions/hpc/paperieee_copyright.pdf", "S"),
    ("introl blog: GB200 'any GPU to any memory within 300 ns'", "https://introl.com/blog/gb200-nvl72-deployment-72-gpu-liquid-cooled", "U"),
]:
    IMPORTED.append(dict(id="slr:" + re.sub(r"[^a-z0-9]+", "_", _r[0].lower())[:40].strip("_"), topic="collective/switch latency",
                         title=_r[0], url=_r[1], cls={"V": "verified in primary", "S": "secondary", "U": "unverified - do not use"}.get(_r[2], _r[2]),
                         harvested_from="/tmp/claude-review-20261003/switch_latency_research.md (2026-10-04 note; imported)"))

# --------------------------------------------------------------------------------------------------------------
# (b) NEW entries researched 2026-10-04 (only genuine gaps)
# --------------------------------------------------------------------------------------------------------------
NEW = [
    dict(id="new:dspark_paper_table1_qwen", topic="speculative acceptance",
         title="DSpark (DeepSeek-AI & PKU), arXiv:2607.05147, Table 1, Qwen3-8B rows for Eagle3 / DFlash / DSpark at gamma 7",
         url="https://arxiv.org/html/2607.05147v1", date="2026-07-06", cls="model vendor paper",
         value={"columns": ["GSM8K", "MATH", "AIME25", "MBPP", "HumanEval", "LCB", "MT-Bench", "Alpaca", "Arena-Hard"],
                "Qwen3-8B": {"Eagle3": [5.30, 4.77, 3.91, 3.96, 4.33, 4.17, 2.66, 2.54, 2.54],
                             "DFlash": [5.33, 4.91, 4.07, 4.36, 4.64, 4.39, 3.11, 2.98, 2.81],
                             "DSpark": [6.17, 5.78, 5.01, 5.16, 5.52, 5.17, 3.72, 3.58, 3.21]}},
         conditions=dict(draft_length=7, temperature=1.0, mode="non-thinking", convention="accepted length incl. bonus token"),
         quote="We report the accepted length (tau) per decoding round ... include the target-generated bonus token. | Figure 2: "
               "DFlash decays (0.87->0.78 on Code) while DSpark maintains stability across positions 1-7. | Figure 4 ablation over "
               "gamma in {4, 8, 12, 16} is a plot; no numerical tau at gamma 4/5 is given.",
         note="DSpark row was already harvested (acc:DSPARK); the Eagle3/DFlash rows and the per-position stability statement are new."),
    dict(id="new:infx_dsv4pro_dspark_curve", topic="speculative acceptance",
         title="SemiAnalysis InferenceX golden AL: DeepSeek-V4-Pro-0813 + DSpark, per num_speculative_tokens",
         url="https://github.com/SemiAnalysisAI/InferenceX/blob/main/inferencex-e2e/infx/golden_al_distribution/dsv4-pro-0813-dspark.yaml",
         date="2026 (InferenceX main, fetched 2026-10-04)", cls="third-party benchmark (committed golden)",
         value={"thinking_on": {"1": 1.84, "2": 2.51, "3": 3.01, "4": 3.36, "5": 3.61, "6": 3.77, "7": 3.73, "8": 3.47}},
         conditions=dict(dataset="SPEED-Bench coding", temperature=1.0, output_len=4096, hardware="B300, vLLM DSpark"),
         quote="# key = num_speculative_tokens (DSpark level); value = golden AL ... 3: 3.01 4: 3.36 5: 3.61 6: 3.77 7: 3.73"),
    dict(id="new:infx_dsv4_mtp_curve", topic="speculative acceptance",
         title="SemiAnalysis InferenceX golden AL: DeepSeek-V4-Pro native MTP, per num_speculative_tokens",
         url="https://github.com/SemiAnalysisAI/InferenceX/blob/main/inferencex-e2e/infx/golden_al_distribution/dsv4_mtp.yaml",
         date="2026 (fetched 2026-10-04)", cls="third-party benchmark (committed golden)",
         value={"thinking_on": {"1": 1.79, "2": 2.27, "3": 2.49, "4": 2.54, "5": 2.55},
                "thinking_off": {"1": 1.92, "2": 2.61, "3": 2.97, "4": 3.00, "5": 3.10}},
         conditions=dict(dataset="SPEED-Bench coding", temperature=1.0, output_len=4096, hardware="B300, vLLM MTP"),
         quote="Measured on deepseek-v4-pro (B300, vLLM MTP) ... thinking_off: 1: 1.92 2: 2.61 3: 2.97 4: 3.00 5: 3.10"),
    dict(id="new:redhat_qwen3_8b_eagle3_card", topic="speculative acceptance",
         title="RedHatAI/Qwen3-8B-speculator.eagle3 model card (vLLM 0.11.0, 1x A100)",
         url="https://huggingface.co/RedHatAI/Qwen3-8B-speculator.eagle3", date="2025 (vLLM 0.11.0)", cls="third-party drafter vendor",
         value={"HumanEval": {"1": 1.72, "3": 2.39, "5": 2.60, "7": 2.69}, "gsm8k": {"1": 1.73, "3": 2.48, "5": 2.72, "7": 2.81},
                "CNN/DailyMail": {"1": 1.62, "3": 2.13, "5": 2.25, "7": 2.30}},
         conditions=dict(temperature=0.6, top_p=0.95, top_k=20, thinking="disabled", drafter="EAGLE-3 chain"),
         quote="Coding (HumanEval): k=1: 1.72 | k=3: 2.39 | k=5: 2.60 | k=7: 2.69; Math Reasoning (gsm8k): k=1: 1.73 | k=3: 2.48 | "
               "k=5: 2.72 | k=7: 2.81; Text Summarization: k=1: 1.62 | k=3: 2.13 | k=5: 2.25 | k=7: 2.30",
         note="Our acceptance_tau.json eagle3_redhat_k7 is OUR run of this drafter (not third-party); the card's own numbers are new."),
    dict(id="new:angelslim_qwen3_eagle3_card", topic="speculative acceptance / gpu baseline",
         title="AngelSlim (Tencent) Qwen3 EAGLE-3 model card benchmark table (vLLM 0.11.2, 1x H20, bs 1)",
         url="https://huggingface.co/AngelSlim/Qwen3-4B_eagle3", cls="third-party drafter vendor",
         value=dict(qwen3_8b_eagle3_accept_length=1.99, qwen3_8b_eagle3_tok_s=257.52, qwen3_8b_vanilla_tok_s=151.81,
                    num_speculative_tokens=2),
         conditions=dict(hardware="1x H20", engine="vLLM 0.11.2", batch=1, output_len=1024,
                         datasets="mean of MT-bench, GSM8K, HumanEval, Alpaca"),
         quote="Qwen3-8B: Eagle3 mean throughput 257.52 tokens/s with an accept length of 1.99 ... vanilla 151.81 tokens/s"),
    dict(id="new:dogacel_qwen3_8b_dspark", topic="speculative acceptance",
         title="Dogacel/Qwen3-8B-DSpark model card (community DSpark re-training; reference run of DeepSeek's dspark_qwen3_8b_block7)",
         url="https://huggingface.co/Dogacel/Qwen3-8B-DSpark", cls="community measurement",
         value=dict(deepseek_dspark_qwen3_8b_block7_tau=3.41, community_tau=2.33, num_speculative_tokens=7),
         conditions=dict(dataset="SPEED-Bench coding", temperature=1.0, engine="vLLM (custom fork)"),
         quote="Reference - DeepSeek's fully-trained dspark_qwen3_8b_block7, same harness: acceptance length 3.41."),
    dict(id="new:deepspec_collection", topic="speculative acceptance",
         title="DeepSeek DeepSpec HF collection (dspark/dflash/eagle3 drafters for Qwen3-4B/8B/14B, Gemma4-12B)",
         url="https://huggingface.co/collections/deepseek-ai/deepspec", cls="model vendor",
         value=dict(qwen3_8b_drafters=["deepseek-ai/dspark_qwen3_8b_block7", "deepseek-ai/dflash_qwen3_8b_block7",
                                       "deepseek-ai/eagle3_qwen3_8b_ttt7"]),
         quote="dspark_qwen3_8b_block7 (2B) ... model card: 'No model card'",
         note="NEGATIVE finding: only block-7 drafters, no published gamma-4/5 Qwen3-8B acceptance."),
    dict(id="new:dflash_table3_table4", topic="gpu baseline / speculative acceptance",
         title="DFlash (Chen, Liang, Liu), arXiv:2602.06036v2, Table 3 (SGLang FA4, B200, c=1) and Table 4 (long context)",
         url="https://arxiv.org/html/2602.06036v2", date="2026-02-05 (rev. 2026-05-28)", cls="third-party paper",
         value=dict(qwen3_8b_b200_c1_math500=dict(ar_tok_s=230, dflash_tok_s=1175, dflash_tau=8.01, block=16),
                    long_context_32k_gov_report_tau=dict(base=2.09, finetuned=3.56)),
         quote="Table 3 (SGLang FA4, B200), concurrency 1, Math500: Baseline 230 tok/s; DFlash 1175 tok/s, tau = 8.01 | Table 4: "
               "at 32K tokens on gov_report the base model tau = 2.09, fine-tuned variant tau = 3.56",
         note="Table 3 was already cited (roofline:dflash_b200); Table 4's long-context tau is new."),
    dict(id="new:infx_dsv4pro_b200_vs_b300", topic="gpu baseline",
         title="SemiAnalysis InferenceX: DeepSeek-V4-Pro-0813 1.6T, B200 vs B300 (AgentX agentic scenario)",
         url="https://inferencex.semianalysis.com/compare/deepseek-v4-b200-vs-b300", cls="third-party benchmark",
         value=dict(interactivity_tok_s_user=[96, 159, 222],
                    b200_tok_s_chip={"96": 42233, "159": 7947, "222": 3996}, b300_tok_s_chip={"96": 19653, "159": 6453, "222": 3702}),
         quote="At 222 tok/s/user (higher concurrency): B200 3,996 tok/s/chip ... B300 3,702 tok/s/chip; agentic inference metrics "
               "from the AgentX scenario where context grows iteratively, most requests served from cache",
         note="V4-Pro (49B active), not V4.1-Flash; agentic cached contexts, not a 1M single-sequence decode."),
    dict(id="new:broadcom_tomahawk_ultra_pr", topic="switch",
         title="Broadcom press release, Broadcom Ships Tomahawk Ultra (GlobeNewswire), 15 Jul 2025",
         url="https://www.globenewswire.com/news-release/2025/07/15/3115637/19933/en/Broadcom-Ships-Tomahawk-Ultra-Reimagining-the-Ethernet-Switch-for-HPC-and-AI-Scale-up.html",
         date="2025-07-15", cls="vendor claim (primary)",
         value=dict(switch_latency_ns=250, xpu_to_xpu_ns="<400", tbps=51.2, min_packet_B=64, mpps=77000, header_B="46 -> 10"),
         quote="Achieves 250ns switch latency at full 51.2 Tbps throughput. | sub-400ns XPU-to-XPU communication latency, including the "
               "switch transit time | Tomahawk Ultra executes these [AllReduce, Broadcast, AllGather] directly within the switch chip | "
               "LLR, the switch detects link errors using Forward Error Correction and automatically retransmits packets | CBFC prevents "
               "buffer overflows | Reduces header overhead from 46 bytes down to as low as 10 bytes",
         note="URL already cited in results/arch/v41_rack.json; exact quotes re-verified 2026-10-04. No in-network collective latency is published."),
    dict(id="new:coolit_4000w_coldplate", topic="cooling",
         title="CoolIT Systems, 4000W breakthrough in single-phase DLC (news), 2 Dec 2025",
         url="https://www.coolitsystems.com/resources/news/coolit-systems-4000w-breakthrough-redefining-single-phase-dlc-for-ultra-high-wattage-ai-processors/",
         date="2025-12-02", cls="vendor claim (test vehicle)", value=dict(tdp_w=4000, heat_flux_w_cm2=">300", flow_lpm=6),
         quote="over 4000W thermal design power (TDP) and thermal fluxes over 300 W/cm2 | captured over 97% of heat from a 4000W "
               "thermal test vehicle (TTV) with a flow rate of 6 LPM"),
    dict(id="new:alliancechem_gpu_flux", topic="cooling",
         title="Alliance Chemical blog, GPU thermal density & coolant flow (B200/GB200/MI300), 27 Apr 2026",
         url="https://alliancechemical.com/blogs/articles/gpu-thermal-density-b200-gb200-coolant-flow-specs", date="2026-04-27",
         cls="UNRELIABLE - do not use", value=dict(b200_w_cm2="500-600 (claimed)"),
         quote="B200 500-600 W/cm2 ... 1,000 W TDP with an active die area of approximately 1.5-2 cm2",
         note="Rejected: assumes 1.5-2 cm2 for B200, whose two reticle-limited dies are ~16 cm2 (r-dgxb200); recorded so nobody re-adopts it."),
    dict(id="new:tomahawk5_power", topic="switch",
         title="Gazettabyte, Broadcom Tomahawk 5 (51.2 Tb/s, 5 nm) switch chip power",
         url="https://www.gazettabyte.com/?p=145716", cls="trade press (vendor statement)", value=dict(power_w="<500"),
         quote="consumes less than 500 W",
         note="Harvested from the committed tools/ds_energy_silicon_authoritative.py ASSUMED.switch_chip_w (no re-research). "
              "Tomahawk 5 class (51.2T, N5); Tomahawk Ultra / NVSwitch power is unpublished, so a 51.2T scale-up switch "
              "chip is charged 500 W as an upper bound by analogy. Consumer: tools/energy_silicon_measured.py."),
]


# --------------------------------------------------------------------------------------------------------------
# (c) used_by: which committed records/tools cite each URL
# --------------------------------------------------------------------------------------------------------------
SCAN = ["results/arch", "results/speculative", "results/measured", "results/roofline", "tools", "docs",
        "results/uarch/hbm_switch_latency_authoritative_20261004", "results/uarch/ds_energy_silicon_authoritative_20261004",
        "results/uarch/hbm_switch_latency_range_20261004"]
SKIP = ("results/external/", "results/speculative/third_party_acceptance_20261004/", "results/measured/gpu_third_party_20261004/",
        "results/arch/vendor_assumption_check_20261004/", "tools/external_registry.py")


def corpus() -> dict[str, str]:
    files = {}
    for d in SCAN:
        for p in (ROOT / d).rglob("*"):
            rel = str(p.relative_to(ROOT))
            if not p.is_file() or p.suffix not in (".json", ".md", ".py") or rel.startswith(SKIP) or p.stat().st_size > 8_000_000:
                continue
            try:
                files[rel] = p.read_text(errors="ignore")
            except OSError:
                pass
    return files


def _key(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def attach_used_by(entries, files):
    for e in entries:
        u = e.get("url")
        if not u:
            e["used_by"] = []
            continue
        k = _key(u)
        e["used_by"] = sorted(f for f, t in files.items() if k in t)


# --------------------------------------------------------------------------------------------------------------
# (d) topical records
# --------------------------------------------------------------------------------------------------------------
GAMMA7 = NEW[0]["value"]["Qwen3-8B"]


def _geo_r(tau7, g=7):
    lo, hi = 0.0, 0.999999
    for _ in range(200):
        r = (lo + hi) / 2
        v = 1 + sum(r ** k for k in range(1, g + 1))
        lo, hi = (r, hi) if v < tau7 else (lo, r)
    return (lo + hi) / 2


def _trunc(r, k):
    return 1 + sum(r ** i for i in range(1, k + 1))


def _owner6_tau() -> float:
    b = json.loads((ROOT / "results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json").read_text())
    return b["blends"]["owner 6-class equal"]["greedy"]["tau_blend_harmonic"]


def acceptance() -> dict:
    cols = NEW[0]["value"]["columns"]
    ds7 = GAMMA7["DSpark"]
    rs = [_geo_r(t) for t in ds7]
    by_k = {}
    for k in (3, 4, 5):
        per = {c: round(_trunc(r, k), 4) for c, r in zip(cols, rs)}
        by_k[str(k)] = dict(tau=round(sum(per.values()) / len(per), 4), per_benchmark=per,
                            basis=f"DERIVED from published DSpark Table 1 (Qwen3-8B, gamma 7, T=1.0): per benchmark solve constant "
                                  f"conditional acceptance r from tau7 = 1 + sum_{{i<=7}} r^i, then tau{k} = 1 + sum_{{i<={k}}} r^i; "
                                  f"equal weight over the 9 benchmarks (3 math, 3 code, 3 chat)")
    # cross-check of the truncation method on a PUBLISHED DSpark k-curve (InferenceX V4-Pro, thinking on)
    pub = NEW[1]["value"]["thinking_on"]
    r = _geo_r(pub["7"])
    xcheck = {k: dict(published=pub[k], geometric_from_k7=round(_trunc(r, int(k)), 3),
                      ratio=round(pub[k] / _trunc(r, int(k)), 4)) for k in ("3", "4", "5")}
    q_primary = by_k["3"]
    q = dict(
        target="Qwen3-8B (dense) + small DSpark draft head",
        composition_block=("The Qwen ROM DSpark composition (results/rtl/qwen_dspark_system_20261004/ctx8k/step_composed_ctx8k.json) "
                           "verifies a block of 4 positions = 3 draft tokens + bonus (S=3 drafter slots, n_emit 4 at a=3), so it "
                           "takes tau at 3 draft tokens; values at 4 and 5 draft tokens are listed for a gamma-4/5 configuration."),
        primary=dict(draft_tokens=3, tau=q_primary["tau"], source_ids=["new:dspark_paper_table1_qwen", "acc:DSPARK"],
                     grade="derived-from-published",
                     mismatch=["draft length: published only at gamma 7; truncated to 3 by a constant-conditional model "
                               "(DSpark's per-position conditional acceptance is published as stable across positions 1-7)",
                               "temperature 1.0, non-thinking (paper's offline protocol)",
                               "dataset: 9 public benchmarks, not the owner 6-class mix"]),
        by_draft_tokens=by_k,
        range=dict(low=min(q_primary["per_benchmark"].values()), high=max(q_primary["per_benchmark"].values()),
                   basis="derived k=3 per-benchmark spread (Arena-Hard low, GSM8K high)"),
        published_gamma7_mean=round(sum(ds7) / len(ds7), 4),
        truncation_cross_check=dict(source_id="new:infx_dsv4pro_dspark_curve", rows=xcheck,
                                    reading="on a published DSpark curve the constant-conditional truncation UNDER-estimates "
                                            "tau at k=3 by ~7-8%, so the derived Qwen primary is conservative"),
        corroborating=[
            dict(source_id="new:redhat_qwen3_8b_eagle3_card", tau_k3=[2.39, 2.48, 2.13], tau_k5=[2.60, 2.72, 2.25],
                 mismatch=["EAGLE-3 drafter (DSpark is +27-31% over Eagle3 per the DSpark paper)", "T=0.6"]),
            dict(source_id="new:dspark_paper_table1_qwen", eagle3_gamma7_mean=round(sum(GAMMA7["Eagle3"]) / 9, 4),
                 dflash_gamma7_mean=round(sum(GAMMA7["DFlash"]) / 9, 4)),
            dict(source_id="new:dogacel_qwen3_8b_dspark", tau=3.41, mismatch=["k=7", "SPEED-Bench coding", "community harness"]),
            dict(source_id="new:angelslim_qwen3_eagle3_card", tau=1.99, mismatch=["EAGLE-3", "k=2"]),
        ],
        superseded_self_measured=dict(tau=3.0375, draft_tokens=3,
                                      source="results/rtl/qwen_rom_dspark_20261003/drafter/tau_summary.json tau_w8_S3_B4",
                                      note="our measurement; SUPERSEDED 2026-10-04 by the owner rule"),
    )
    ds_set = [("acc:VLLM_57432", 3.8879, "GSM8K 1,319, greedy, thinking off, 4x GB200 vLLM TP4 (post-fix, same revision)"),
              ("acc:VLLM_57432", 3.8248, "same, DEP4"),
              ("acc:INFX_V41", 4.07, "SPEED-Bench coding, T=1.0, thinking off, B300 vLLM TP4 (pre-fix image)"),
              ("acc:INFX_V41", 3.51, "SPEED-Bench coding, T=1.0, thinking on (pre-fix image)"),
              ("acc:SGL_38929", 4.31748, "GSM8K, greedy, thinking off, SGLang PD B300 (closed PR)"),
              ("acc:VLLM_56797_AGENTIC", 3.43, "production agentic traffic, thinking max, 4x H200 (community counters)")]
    vals = sorted(v for _, v, _ in ds_set)
    infx = {"1": 1.88, "2": 2.62, "3": 3.27, "4": 3.73, "5": 4.07}
    d = dict(
        target="DeepSeek-V4.1-Flash + DSpark (block 5, the model's own drafter)",
        primary=dict(draft_tokens=5, tau=3.8879, source_ids=["acc:VLLM_57432"], grade="published",
                     why="the published V4.1-Flash gamma-5 value on the same model revision after the vLLM acceptance fix; it is "
                         "within 1% of the median (3.856) of the published V4.1-Flash gamma-5 set",
                     mismatch=["dataset GSM8K (reasoning) only, greedy, short outputs (<=1,024)"]),
        by_draft_tokens={"5": dict(tau=3.8879, basis="published: vLLM PR #57432 TP4 (acc:VLLM_57432)"),
                         "3": dict(tau=infx["3"], basis="published: InferenceX V4.1-Flash SPEED-Bench coding thinking off k=3 (acc:INFX_V41)"),
                         "4": dict(tau=infx["4"], basis="published: InferenceX V4.1-Flash SPEED-Bench coding thinking off k=4 (acc:INFX_V41)")},
        range=dict(low=vals[0], high=vals[-1], basis="published V4.1-Flash gamma-5 values"),
        published_set=[dict(source_id=s, tau=v, conditions=c) for s, v, c in ds_set],
        median_published=round(statistics.median(vals), 4),
        other_family=[dict(source_id="acc:TRTLLM_18853", tau=4.0738, mismatch=["DeepSeek-V4-Flash (not V4.1)", "GSM8K"]),
                      dict(source_id="new:infx_dsv4pro_dspark_curve", tau_k5=3.61, mismatch=["V4-Pro", "thinking on"]),
                      dict(source_id="new:infx_dsv4_mtp_curve", tau_k5_thinking_off=3.10, mismatch=["V4-Pro native MTP, not DSpark"]),
                      dict(source_id="acc:V3", tau_k1=[1.85, 1.90], mismatch=["DeepSeek-V3 MTP-1 (derived 1 + a1)"])],
        adopted=dict(draft_tokens=5, tau=_owner6_tau(), grade="owner decision 2026-10-05",
                     label="owner 6-class workload blend (adopted 2026-10-05)",
                     source="results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json "
                            "blends['owner 6-class equal'].greedy.tau_blend_harmonic",
                     note="composition default (tools/third_party_tau.py); the published primary above and its range are "
                          "the sensitivity (OT_TAU_SOURCE=third_party)"),
    )
    return dict(schema="opentallas.third_party_acceptance.v1", date=DATE, owner_rule=OWNER_RULE, decisions=[DECISION_DS_TAU],
                convention="tau = mean tokens committed per verify step INCLUDING the bonus token (EAGLE/DSpark 'accepted length')",
                registry="results/external/registry.json", consumer="tools/third_party_tau.py",
                models=dict(qwen3_8b=q, deepseek_v41=d))


def gpu_baselines() -> dict:
    return dict(
        schema="opentallas.gpu_third_party_baselines.v1", date=DATE, owner_rule=OWNER_RULE,
        note="THIRD-PARTY PUBLISHED figures (not our measurements) - the directory sits under results/measured only because that is "
             "the repo's GPU-baseline area. Our own H100 runs stay in results/measured/h100_nvls_20261004/.",
        recommended=dict(
            deepseek_v41=dict(
                h200=dict(tok_s_per_user=240, context="900K", source_id="nvls:lmsys_dsv4_day0",
                          mismatch=["DeepSeek-V4-Flash (V4.1 not published)", "speculation most likely ON (EAGLE-style MTP; "
                                    "Figure 2 does not state it)", "SGLang Day-0, TP4, single batch, OSL 4096"],
                          range=[240, 266], range_basis="900K .. 4K"),
                b200=dict(tok_s_per_user=180, context="900K", source_id="nvls:lmsys_dsv4_day0",
                          mismatch=["DeepSeek-V4-Pro 1.6T / 49B active (Flash is 13B active)", "speculation most likely ON",
                                    "TP8, single batch"], range=[180, 199], range_basis="900K .. 4K"),
                b300=dict(tok_s_per_user=383.7, context="not stated (repro: 256 in / 256 out)", source_id="acc:LMSYS",
                          mismatch=["DeepSeek-V4-Pro + DSpark accept ~5", "short context"]),
                h100=dict(tok_s_per_user=[40, 50], source_id="nvls:sglang_disc_39791",
                          mismatch=["unsupported target (user report)", "context not stated"]),
                gap="No published DeepSeek-V4.1-Flash per-user decode figure at 1M on any GPU was found (NVIDIA's Dynamo V4.1 "
                    "recipe explicitly carries no performance claim). The closest published long-context figures are V4-Flash "
                    "on H200 (240 tok/s at 900K) and V4-Pro on B200 (180 tok/s at 900K)."),
            qwen3_8b_8k=dict(
                no_spec=dict(published=[dict(gpu="B200", tok_s_per_user=230, context="MATH-500 (short)", source_id="new:dflash_table3_table4"),
                                        dict(gpu="H20", tok_s_per_user=151.81, context="<=1,024 out", source_id="new:angelslim_qwen3_eagle3_card"),
                                        dict(gpu="H200", tok_s_per_user=[140.14, 234.95], context="NIM 8B-class, BF16/FP8",
                                             source_id="calib:nim_h200")],
                             gap="No published Qwen3-8B per-user decode figure at ~8K context was found; the 8K points remain our "
                                 "measured H100 runs (TP1 FP8 180, TP8 FP8 299 tok/s; results/measured/h100_nvls_20261004)."),
                spec=dict(published=[dict(gpu="B200", tok_s_per_user=1175, drafter="DFlash block 16, tau 8.01", context="MATH-500 (short)",
                                          source_id="new:dflash_table3_table4"),
                                     dict(gpu="H20", tok_s_per_user=257.52, drafter="EAGLE-3 k=2, tau 1.99",
                                          source_id="new:angelslim_qwen3_eagle3_card")],
                          gap="No published Qwen3-8B speculative per-user figure at 8K context was found."))),
        sources=["nvls:lmsys_dsv4_day0", "nvls:dynamo_v41_recipe", "nvls:sglang_disc_39791", "acc:LMSYS", "new:infx_dsv4pro_b200_vs_b300",
                 "new:dflash_table3_table4", "new:angelslim_qwen3_eagle3_card", "calib:nim_h200", "roofline:dflash_b200",
                 "nvls:gfactor_qwen38_27b"],
        corrections=["results/measured/h100_nvls_20261004/README.md says 'DeepSeek-V4.1-Flash H200 TP4 266 tok/s (no speculation), "
                     "30K prefix': the source is DeepSeek-V4-Flash (not V4.1), 266 is the 4K end of a 4K-900K sweep (240 at 900K), and "
                     "speculation was most likely on. The Dynamo V4.1 recipe it also cites carries no performance figure."])


def vendor_check() -> dict:
    die_mm2 = 815.0
    flux = round(474.6 / (die_mm2 / 100), 1)
    return dict(
        schema="opentallas.vendor_assumption_check.v1", date=DATE,
        assumptions=[
            dict(id="cooling_474p6", assumption="liquid cooling at 474.6 W per die in 2-die packages",
                 used_in=["results/arch/power_assumptions.json (Cooling, liquid, 2-die package)", "results/arch/qwen3_budget.json die_limit_w"],
                 derivation_in_repo="GB200 package 1,200 W less its HBM stacks at peak bandwidth x 3.92 pJ/b (r-gb200-guide)",
                 our_average_flux_w_cm2=flux, die_area_mm2_assumed=die_mm2,
                 published=[dict(source_id="sct:r-gb200-guide", value="GB200 TDP configurable up to 1,200 W (2 dies + HBM)"),
                            dict(source_id="sct:r-amd-instinct", value="MI355X 1,400 W TBP liquid"),
                            dict(source_id="sct:r-dgxb200", value="HGX B200 1,000 W, two reticle-limited dies"),
                            dict(source_id="new:coolit_4000w_coldplate", value="single-phase cold plate >300 W/cm2, >4,000 W TTV")],
                 verdict="PASS",
                 reason=f"949 W of die power per package plus stacks stays inside the shipping 1,200 W GB200 rating it was derived "
                        f"from; the die-average flux is ~{flux} W/cm2 (474.6 W over ~{die_mm2:.0f} mm2), about 1/5 of the >300 W/cm2 a "
                        f"production single-phase cold plate demonstrates.",
                 residual="Hot-spot flux (local W/mm2 of the MAC fabric) is not covered by a published cold-plate figure; keep the "
                          "repo's hot-spot check (power_assumptions 'sustainable hot-spot W/mm2')."),
            dict(id="light_fec_130ns", assumption="light-FEC 130 ns package-to-package (on-module) link",
                 used_in=["results/arch/sync_cost_table.json values_checked", "results/arch/arch_budget_v41.json",
                          "results/arch/v41_latency_ladder.json", "tools/uarch_model.py", "docs/ARCH_V41_RACK.md T1"],
                 published=[dict(source_id="sct:r-sue", value="Broadcom SUE: Ethernet link+PHY Tx+Rx <100 ns"),
                            dict(source_id="sct:r-sun3cd", value="RS(272,257) ~99 ns vs RS(544,514) ~198 ns"),
                            dict(source_id="sct:r-gustlin3ck", value="Clause 91 RS544 101-151 ns total"),
                            dict(source_id="sct:r-dassharma-ofa", value="networking PHY 20+ ns (+ >100 FEC); PCIe/CXL <10 ns; UCIe <2 ns"),
                            dict(source_id="sct:r-llfec", value="RS(272) needs raw BER far below CR-copper limits"),
                            dict(source_id="sct:r-ualink", value="UALink in-rack: RS(544,514) codeword, reduced interleave")],
                 verdict="PASS (on-module MR channel only) / CONCERN on cables",
                 reason="130 ns sits inside the published 100-185 ns band for a light (RS(272)-class) code plus PHY on an OIF "
                        "MR-class channel, and the H100 NVLS measurement gives ~85 ns per board leg. On rack cables the light code "
                        "is NOT qualified (802.3ck mandates RS(544,514) for CR); the repo already prices cable hops at 209 ns "
                        "(results/arch/v41_rack.json, ARCH_V41_RACK C2). Any record still applying 130 ns to a cable hop is wrong.",
                 suggested="keep 130 ns (100-185) on-module; 209 ns (160-300) for any copper-cable hop"),
            dict(id="tomahawk_ultra", assumption="Tomahawk Ultra switch tier: 250 ns switch, SUE crossing budget, in-network collectives",
                 used_in=["tools/uarch_model.py HBM_SWITCH_LATENCY (tomahawk_ultra_protocol / tomahawk_ultra_inc)",
                          "results/uarch/hbm_switch_latency_authoritative_20261004/", "results/arch/v41_rack.json"],
                 published=[dict(source_id="new:broadcom_tomahawk_ultra_pr", value="250 ns at 51.2 Tb/s; sub-400 ns XPU-to-XPU; INC in switch"),
                            dict(source_id="sct:r-sue", value="one-way budget 477.6 ns (3 m twinax): 100 + 100 + 2 x 13.8 + 250")],
                 verdict="PASS (baseline) / CONCERN (in-network collective as baseline)",
                 reason="The repo prices a crossing with Broadcom's own SUE budget (477.6 ns one-way), which is more conservative "
                        "than the PR's sub-400 ns claim, and uses the 250 ns switch figure verbatim. Broadcom publishes NO "
                        "in-network collective latency or reduction order, so INC must stay a sensitivity (as tomahawk_ultra_inc "
                        "already is), never the baseline; bit-exactness of an in-switch reduction is also unpublished.",
                 suggested="keep; do not promote tomahawk_ultra_inc without a published latency and a fixed reduction order"),
        ])


# --------------------------------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------------------------------

def md_registry(reg):
    L = ["# External references registry", "",
         f"Canonical list of every third-party figure the repository uses ({len(reg['entries'])} entries, {reg['counts']['new']} "
         f"added on {DATE}). Built by `tools/external_registry.py` (`--check` verifies the committed outputs). **Cite an entry id "
         "from `registry.json` instead of re-researching a source.** `used_by` lists the committed records and tools that "
         "cite each URL.", "", f"> {OWNER_RULE}", "",
         "Topical views: [acceptance](../speculative/third_party_acceptance_20261004/README.md), "
         "[GPU baselines](../measured/gpu_third_party_20261004/README.md), "
         "[vendor assumption check](../arch/vendor_assumption_check_20261004/README.md).", ""] + [
         f"**Owner decision {x['date']}:** {x['decision']} Reason: {x['reason']}" for x in reg["decisions"]] + ["",
         "| id | new | class | title | used by |", "|---|---|---|---|---|"]
    for e in reg["entries"]:
        t = (e.get("title") or "").replace("|", "/")[:110]
        u = f"[{t}]({e['url']})" if e.get("url") else t
        L.append(f"| `{e['id']}` | {'yes' if e.get('new') else ''} | {e.get('cls') or ''} | {u} | {len(e['used_by'])} |")
    return "\n".join(L) + "\n"


def md_acc(a):
    q, d = a["models"]["qwen3_8b"], a["models"]["deepseek_v41"]
    L = ["# Third-party speculative-decoding acceptance (2026-10-04)", "", f"> {a['owner_rule']}", "",
         f"Convention: {a['convention']}. Sources are ids in [`results/external/registry.json`](../../external/registry.json). "
         "Read by `tools/third_party_tau.py`, which every composition uses (`OT_TAU_SOURCE=adopted` is the default; "
         "`third_party` gives the published DS sensitivity; `self_measured` reproduces the superseded records).", ""] + [
         s for x in a["decisions"] for s in (f"## Owner decision {x['date']}", "", x["decision"], "", "Reason: " + x["reason"], "",
                                               "Supersedes: " + x["supersedes"] + ".", "")] + [
         "| Model | Draft tokens | Composition default tau | Basis | Published primary (third-party) | Published range | Superseded (ours) |",
         "|---|---|---|---|---|---|---|",
         f"| Qwen3-8B + DSpark | {q['primary']['draft_tokens']} | **{q['primary']['tau']}** | {q['primary']['grade']} | "
         f"{q['primary']['tau']} | {q['range']['low']}-{q['range']['high']} | 3.0375 |",
         f"| DeepSeek-V4.1-Flash + DSpark | {d['adopted']['draft_tokens']} | **{d['adopted']['tau']}** | {d['adopted']['label']} | "
         f"{d['primary']['tau']} (sensitivity) | {d['range']['low']}-{d['range']['high']} (sensitivity) | - |", "",
         "## Qwen3-8B", "", q["composition_block"], "",
         "No source publishes a Qwen3-8B DSpark acceptance length at 3-5 draft tokens. DeepSeek's DSpark paper (Table 1) "
         "publishes it at gamma 7, and its drafters are released only as block-7 checkpoints. The primary is therefore "
         "DERIVED from Table 1. For each benchmark, the constant conditional acceptance r is solved from tau7 = 1 + sum r^i; "
         "the paper reports that DSpark's per-position acceptance is stable across positions 1-7. The tau at k draft tokens "
         "then follows, and the 9 benchmarks (3 math, 3 code, 3 chat) are weighted equally.", "",
         "| k | derived tau |", "|---|---|"] + [f"| {k} | {v['tau']} |" for k, v in q["by_draft_tokens"].items()] + [
         "", f"Published gamma-7 mean: {q['published_gamma7_mean']}. A cross-check on the published InferenceX DSpark k-curve "
         "(V4-Pro) shows that the truncation under-estimates by about 7-8% at k=3, so the derived primary is conservative:", "",
         "| k | published | geometric from k=7 | ratio |", "|---|---|---|---|"] + [
         f"| {k} | {r['published']} | {r['geometric_from_k7']} | {r['ratio']} |" for k, r in q["truncation_cross_check"]["rows"].items()] + [
         "", "Mismatch labels: " + "; ".join(q["primary"]["mismatch"]) + ".", "",
         "Corroborating values (other drafters): the RedHat EAGLE-3 card gives k=3 2.13-2.48 and k=5 2.25-2.72 at T=0.6. The "
         "Eagle3 gamma-7 mean in DSpark Table 1 is " + str(q["corroborating"][1]["eagle3_gamma7_mean"]) + ". DeepSeek's "
         "dspark_qwen3_8b_block7 measured 3.41 on SPEED-Bench coding with a community harness (k=7). AngelSlim EAGLE-3 gives "
         "1.99 at k=2.", "",
         "## DeepSeek-V4.1-Flash (DSpark, block 5)", "",
         f"Composition default: **{d['adopted']['tau']}**, the {d['adopted']['label']} "
         f"(`{d['adopted']['source']}`). The published values below are kept as a sensitivity.", "",
         f"Published primary {d['primary']['tau']} (vLLM PR #57432, TP4, same model revision, after the acceptance fix). It is "
         f"{d['primary']['why'].split('; it is ')[1]}. Mismatch: {d['primary']['mismatch'][0]}.", "",
         "| Source | tau | Conditions |", "|---|---|---|"] + [
         f"| `{p['source_id']}` | {p['tau']} | {p['conditions']} |" for p in d["published_set"]] + [
         "", "Other members of the family (labelled, not used): V4-Flash TRT-LLM 4.07, V4-Pro DSpark k=5 3.61 (thinking on), "
         "V4-Pro native MTP k=5 3.10 (thinking off), V3 MTP-1 1.85-1.90.", ""]
    return "\n".join(L)


def md_gpu(g):
    r = g["recommended"]["deepseek_v41"]
    q = g["recommended"]["qwen3_8b_8k"]
    L = ["# GPU decode baselines from third-party publications (2026-10-04)", "", f"> {OWNER_RULE}", "", g["note"], "",
         "## DeepSeek-V4.1 per-user decode (published)", "", "| GPU | tok/s per user | Context | Source | Mismatch |", "|---|---|---|---|---|"]
    for gpu in ("h200", "b200", "b300", "h100"):
        x = r[gpu]
        L.append(f"| {gpu.upper()} | {x['tok_s_per_user']} | {x.get('context', '')} | `{x['source_id']}` | {'; '.join(x['mismatch'])} |")
    L += ["", "Gap: " + r["gap"], "", "## Qwen3-8B (target 8K context)", "", "| Mode | GPU | tok/s per user | Context / drafter | Source |",
          "|---|---|---|---|---|"]
    for mode in ("no_spec", "spec"):
        for x in q[mode]["published"]:
            L.append(f"| {mode} | {x['gpu']} | {x['tok_s_per_user']} | {x.get('context', '')} {x.get('drafter', '')} | `{x['source_id']}` |")
    L += ["", "Gaps: " + q["no_spec"]["gap"] + " " + q["spec"]["gap"], "", "## Corrections", ""] + [f"- {c}" for c in g["corrections"]] + [""]
    return "\n".join(L)


def md_ven(v):
    L = ["# Vendor data check of cross-cutting assumptions (2026-10-04)", "",
         "Each published value is a registry id in [`results/external/registry.json`](../../external/registry.json).", "",
         "| Assumption | Verdict | Reason |", "|---|---|---|"]
    for a in v["assumptions"]:
        L.append(f"| {a['assumption']} | **{a['verdict']}** | {a['reason']} |")
    for a in v["assumptions"]:
        L += ["", f"## {a['assumption']}", "", "Used in: " + ", ".join(f"`{u}`" for u in a["used_in"]) + ".", ""]
        L += [f"- `{p['source_id']}`: {p['value']}" for p in a["published"]]
        for k in ("residual", "suggested"):
            if a.get(k):
                L += ["", f"{k.capitalize()}: {a[k]}"]
    return "\n".join(L) + "\n"


def build():
    entries = harvest() + IMPORTED + [dict(e, new=True) for e in NEW]
    ids = [e["id"] for e in entries]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit(f"duplicate registry ids: {sorted(dup)}")
    for e in entries:
        e.setdefault("new", False)
    attach_used_by(entries, corpus())
    reg = dict(schema="opentallas.external_registry.v1", date=DATE, owner_rule=OWNER_RULE, tool="tools/external_registry.py",
               decisions=[DECISION_DS_TAU],
               counts=dict(total=len(entries), new=sum(e["new"] for e in entries)), entries=entries)
    acc, gpu, ven = acceptance(), gpu_baselines(), vendor_check()
    known = set(ids)
    for rec in (acc, gpu, ven):
        for sid in re.findall(r'"source_ids?": (?:\[([^\]]*)\]|"([^"]+)")', json.dumps(rec)):
            for s in re.findall(r'"([^"]+)"', sid[0]) if sid[0] else [sid[1]]:
                if s not in known:
                    raise SystemExit(f"unknown registry id cited: {s}")
    return {OUT_REG / "registry.json": json.dumps(reg, indent=1) + "\n", OUT_REG / "README.md": md_registry(reg),
            OUT_ACC / "acceptance.json": json.dumps(acc, indent=1) + "\n", OUT_ACC / "README.md": md_acc(acc),
            OUT_GPU / "gpu_baselines.json": json.dumps(gpu, indent=1) + "\n", OUT_GPU / "README.md": md_gpu(gpu),
            OUT_VEN / "vendor_check.json": json.dumps(ven, indent=1) + "\n", OUT_VEN / "README.md": md_ven(ven)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    outs = build()
    bad = []
    for p, t in outs.items():
        if a.check:
            if not p.exists() or p.read_text() != t:
                bad.append(str(p.relative_to(ROOT)))
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(t)
    if bad:
        print("STALE:", *bad, sep="\n  ")
        return 1
    print(("checked " if a.check else "wrote ") + f"{len(outs)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
