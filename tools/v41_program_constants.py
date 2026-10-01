#!/usr/bin/env python3
"""Checked constants manifest of the DeepSeek-V4.1 decode-core program emitter.

    python3 tools/v41_program_constants.py [--check] [--output results/rtl/v41_program_constants.json]

Every numeric immediate the shape-generic emitter (tools/hdc_replay_v41.py ShapeBuilder) places in an
instruction -- epsilons, scales, clip limits, reduction counts -- is taken from this manifest, never from a
literal in the emitter.  The manifest is DERIVED, not typed:

* model constants come from the model's inference_config.json (the key named in `source_key`), converted
  exactly as the golden's Model.__init__ converts them (tools/hdc_golden_v41.py: F(c[key]), F(hd ** -0.5), ...);
* the two constants the release writes as code literals rather than config keys -- the hyper-connection
  post-mix multiplier (`2 * sigmoid`) and the router denominator epsilon -- are parsed out of the golden's own
  source (Model.hc_mixes, Model.moe), so a change there changes the manifest;
* reduction counts (the DIVIMM operand of each RMS statistic) are products of config dimensions;
* where the released HF config.json is present its spelling of the same value (text_config.rms_norm_eps,
  swiglu_limit, routed_scaling_factor, head_dim, hidden_size) is cross-checked.

Each entry carries its value, its float32 bits, the source key and the sha256 of the file it came from.
`--check` rebuilds the manifest in memory and fails if the committed one differs.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

OUT = ROOT / "results/rtl/v41_program_constants.json"
SCHEMA = "opentallas.v41.program_constants.v1"
F = np.float32
MODELS = {
    "deepseek-v4.1-flash": ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json",
    "reduced-v2": ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v2/inference_config.json",
}
RELEASE_CONFIG = Path(os.environ.get(
    "OT_V41_FLASH_SNAPSHOT", Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/"
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277")) / "config.json"
GOLDEN = ROOT / "tools/hdc_golden_v41.py"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def f32_bits(x) -> int:
    return int(np.asarray(F(x)).view(np.uint32))


def _golden_literal(method, pattern: str, what: str) -> float:
    """The one float literal of the golden method matching `pattern` (group 1)."""
    src = inspect.getsource(method)
    hits = re.findall(pattern, src)
    if len(hits) != 1:
        raise ValueError(f"golden {method.__qualname__}: expected one {what} literal, found {hits}")
    return float(hits[0])


def derive(model: str) -> dict:
    """The manifest entry of one model: every emitter constant with its provenance."""
    cfg_path = MODELS[model]
    c = json.loads(cfg_path.read_text())
    cfg = str(cfg_path.relative_to(ROOT))
    golden = str(GOLDEN.relative_to(ROOT))
    out = {}

    def put(name, value, source_file, source_key, derivation, used_by):
        v = F(value)
        out[name] = dict(value=float(v), f32_bits=f"0x{f32_bits(v):08x}", source_file=source_file,
                         source_key=source_key, derivation=derivation, used_by=used_by)

    put("norm_eps", c["norm_eps"], cfg, "norm_eps", "F(c['norm_eps']) (Model.__init__ self.eps)",
        "every RMS statistic's +eps (rms_r imm2; the HC mix rstd and the Engram norms included)")
    put("hc_eps", c["hc_eps"], cfg, "hc_eps", "F(c['hc_eps']) (Model.__init__ self.hc_eps)",
        "HC pre-mix sigmoid(...) + hc_eps (imm2, E1_ADDIMM); XU Sinkhorn unit parameter EPS")
    put("swiglu_limit", c["swiglu_limit"], cfg, "swiglu_limit", "F(c['swiglu_limit']) (Model.__init__ self.limit)",
        "SwiGLU gate min / up clip (imm3, a_min + c_clip)")
    put("route_scale", c["route_scale"], cfg, "route_scale", "F(c['route_scale']) (Model.__init__ self.route_scale)",
        "routed expert weight scale (imm1, M2_IMM)")
    put("attn_scale", c["head_dim"] ** -0.5, cfg, "head_dim",
        "F(head_dim ** -0.5) (Model.__init__ self.attn_scale)", "softmax score scale (imm1, M1_AIMM)")
    put("index_w_scale", c["index_head_dim"] ** -0.5 * c["index_n_heads"] ** -0.5, cfg,
        "index_head_dim,index_n_heads", "F(index_head_dim ** -0.5 * index_n_heads ** -0.5) "
        "(Model.__init__ self.index_w_scale)", "indexer head weight scale (imm1, M1_AIMM)")
    put("engram_scale", c["dim"] ** -0.5, cfg, "dim", "F(dim ** -0.5) (Model.__init__ self.engram_scale)",
        "Engram gate dot scale (imm2, E1_MULIMM)")
    put("hc_post_scale", _golden_literal(V.Model.hc_mixes, r"post = mul\(sigmoid\(.*\), F\(([0-9.eE+-]+)\)\)",
                                         "post multiplier"),
        golden, "Model.hc_mixes: post = mul(sigmoid(...), F(<literal>))",
        "release code literal (2 * sigmoid), parsed from the golden source", "HC post-mix multiplier (imm2, E1_MULIMM)")
    put("router_den_eps", _golden_literal(V.Model.moe, r"den = add\(total, F\(([0-9.eE+-]+)\)\)",
                                          "router denominator"),
        golden, "Model.moe: den = add(total, F(<literal>))",
        "release code literal, parsed from the golden source", "router weight denominator (imm2, AD_IMM)")
    counts = {
        "count_hc_dim": (c["hc_mult"] * c["dim"], "hc_mult*dim", "HC mix rstd mean over the 4-copy residual"),
        "count_dim": (c["dim"], "dim", "sublayer norms (attn_norm, ffn_norm, final norm) and Engram norms"),
        "count_q_rank": (c["q_lora_rank"], "q_lora_rank", "q_norm"),
        "count_head_dim": (c["head_dim"], "head_dim", "kv_norm, compressor norm"),
        "count_index_head_dim": (c["index_head_dim"], "index_head_dim", "indexer k_norm"),
    }
    for name, (v, key, use) in counts.items():
        put(name, v, cfg, key, f"float32({key}) exactly", f"DIVIMM mean count (imm1): {use}")
    units = {"sinkhorn_iters": dict(value=int(c["hc_sinkhorn_iters"]), source_file=cfg,
                                    source_key="hc_sinkhorn_iters",
                                    rtl_parameter="rtl/hdc/v41/ot_hdc_sinkhorn_seq.sv ITERS"),
             "sinkhorn_eps": dict(value=out["hc_eps"]["value"], f32_bits=out["hc_eps"]["f32_bits"],
                                  source_file=cfg, source_key="hc_eps",
                                  rtl_parameter="rtl/hdc/v41/ot_hdc_sinkhorn_seq.sv EPS")}
    return dict(config=cfg, config_sha256=sha(cfg_path), constants=out, unit_parameters=units)


def release_crosscheck() -> dict | None:
    """The released HF config.json's spelling of the shipped constants (absent -> None)."""
    if not RELEASE_CONFIG.is_file():
        return None
    t = json.loads(RELEASE_CONFIG.read_text())["text_config"]
    c = json.loads(MODELS["deepseek-v4.1-flash"].read_text())
    pairs = {"norm_eps": ("rms_norm_eps", "norm_eps"), "swiglu_limit": ("swiglu_limit", "swiglu_limit"),
             "route_scale": ("routed_scaling_factor", "route_scale"), "head_dim": ("head_dim", "head_dim"),
             "dim": ("hidden_size", "dim"), "q_lora_rank": ("q_lora_rank", "q_lora_rank")}
    rows = {}
    for name, (rk, ck) in pairs.items():
        rows[name] = dict(release_key=f"text_config.{rk}", release=t[rk], inference_config=c[ck],
                          agree=bool(F(t[rk]) == F(c[ck])))
    bad = [k for k, v in rows.items() if not v["agree"]]
    if bad:
        raise ValueError(f"released config.json disagrees with inference_config.json on {bad}")
    return dict(file=str(RELEASE_CONFIG), sha256=sha(RELEASE_CONFIG), checks=rows)


def build() -> dict:
    return dict(schema=SCHEMA,
                claim_boundary="Emitter constants and their provenance; no execution verdict.",
                golden=str(GOLDEN.relative_to(ROOT)), golden_sha256=sha(GOLDEN),
                tool_sha256=sha(Path(__file__)),
                models={name: derive(name) for name in MODELS},
                release_config_crosscheck=release_crosscheck())


def load(model: str = "deepseek-v4.1-flash", path: Path = OUT) -> dict:
    """The committed manifest's constants for `model`, fail closed if the config moved under it."""
    man = json.loads(Path(path).read_text())
    ent = man["models"][model]
    if sha(ROOT / ent["config"]) != ent["config_sha256"]:
        raise ValueError(f"{ent['config']} changed since {path} was derived; regenerate the manifest")
    for name, e in ent["constants"].items():
        if f"0x{f32_bits(e['value']):08x}" != e["f32_bits"]:
            raise ValueError(f"manifest {model}.{name}: value and bits disagree")
    return ent["constants"]


def bits(consts: dict, name: str) -> int:
    return int(consts[name]["f32_bits"], 16)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rec = build()
    if a.check:
        old = json.loads(a.output.read_text())
        skip = {"tool_sha256"} | ({"release_config_crosscheck"} if rec["release_config_crosscheck"] is None else set())
        drop = lambda r: {k: v for k, v in r.items() if k not in skip}  # noqa: E731
        if drop(old) != drop(rec):
            raise SystemExit(f"{a.output} is stale: rerun tools/v41_program_constants.py")
        print("PASS: constants manifest matches its sources")
        return
    a.output.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
