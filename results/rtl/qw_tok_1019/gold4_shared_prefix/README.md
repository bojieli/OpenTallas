# Four independent requests with a real shared prefix

This is a fixture-generation plan and fail-closed driver, not a numerical or
RTL PASS. The coordinator approved this diagnostic workload on 2026-10-19.
User 0 retains the published P8191 prompt and full 36-layer TP4/head oracle.
Users 1–3 share those 8,191 preceding prompt tokens and independently decode
different final tokens. The three tokens are the latest distinct tokens in
the locked prompt that already have rows in the locked embedding artifact.
The workload does not claim coverage of arbitrary independent prompts.

The driver verifies the original complete golden against the published
digests before generating any new user. It converts all 144 canonical
**pre-token** layer/die K/V stores into history inputs. Each new oracle process
owns separate full layer K/V state; no post-divergence result from user 0 or
another user is reused. It checks checkpoint/prep, prompt, embedding and ISA
source identities, actual shape, primitive arithmetic tests, all 144 output
records per class, canonical pre-divergence histories and final token identity.

The original golden is still running on ot-epyc5, PID 1583528, in
`/srv/opentallas-scratch/claude/tokpass-qwen-1018`. At 12:43 PT it had reached
position 6800/8191 after about 27 hours. Preserve that progressing job.
Do not launch duplicate full prefills. Once it finishes, run the new driver
on the fleet with 64 GB and 32 threads, using the pinned source export and
the existing oracle Python environment:

```sh
python3 tools/qwen_layerbench/gold4_shared_prefix.py \
  --fx /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx \
  --canonical-gold /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/gold/tp4 \
  --oracle-root /srv/opentallas-scratch/claude/tokpass-qwen-1018/src \
  --out /srv/opentallas-scratch/claude/qw-gold4-shared-prefix-1019/out \
  --python /srv/opentallas-scratch/claude/tokpass-qwen-1018/py \
  --threads 32 --run
```

Run through unpinned `ot-run`; source/data locality must be staged before
admission. The output directory must be new, and failures remain preserved.
This driver does not wait for the canonical job and refuses incomplete gold.

Admission offsets 0/16/32/168 come from the isolated F16 witness-controller
receipt at commit `26b514ed1`; this establishes fixture ordering only.
Production FIRST/phase, per-user token identity, actual ME/XPF final-read
retirement, late/missing/zero-identity mutants, independent physical context
storage, and numerical RTL replay remain separate release requirements.

## 10-19 QW-TOK3 provenance fix (before first run)

The canonical 10-18 CPU gold runs source 8a01e4a5a, whose oracle files
`qwen_hbmacc_position_oracle_gpu.py`, `hdc_qwen_fullshape_isa_w12.py` and
`qwen_o4_layer0_oracle_w12.py` differ from the 10-04 GPU reference's recorded
`oracle_source_sha256`, and whose re-prepped `prep.json` (timestamped) differs
from the reference `prep_sha256`. The original driver would therefore have
refused the canonical gold even when every numeric digest matched. The driver
now: (1) accepts a `fixtures.py verify` FAIL only when every mismatch is the
`oracle.json oracle_source_sha256` provenance key (all layer-x, K/V, head,
logit, token, embedding and shape checks must match); (2) requires the oracle
root and every new user's oracle to use the canonical gold's own recorded
source hashes; (3) checks `prep.json` against the canonical gold's record, and
still checks all 148 checkpoint payload NPZ hashes. The verify record and the
accepted provenance difference are written into MANIFEST.json.
