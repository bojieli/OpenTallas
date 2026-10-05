Existing-source all40 S81 phase schedules (metadata only)

Implementation: tools/dsrom_1m_field.py bind-schedules --layers 0,1,...,39
--work NEW_OUT. This reuses the existing layer_groups/greedy phase partition,
SourceExecution.resolve, StageProgramJoin identity/CFG and actual ISA dispatch.
No checkpoint, NPZ/activation payload, rand_x, inference, ROM image, frontend,
native library, observer or whole-system execution is generated.

manifest.json pins actual canonical inputs and source; L00..L39.json.gz are
3.1MiB total. Each layer contains phases in existing observer order and
native_dispatch in literal instruction order with all four rank slices.
These are distinct orders. Per fragment: stage/die/CFG phase/key/gather/K/
template/emitted-word SHA and input/output controls. Actual six expert IDs
come from retained 1M chunk8 JSON records; no accepted runtime journal implied.

All40: 913 observer phases /1149 source operations /5244 rank fragments,
1311 actual selected matrix owners. All33 missing layers are now bound.
retained_join.json uses the EXISTING Maxwell structural signature function;
237 retained matrix records match canonical after reversing ONLY explicit
retained R93 movements. Actual missing groups have no exact retained candidate
signature match; dimensions alone do not authorize observer reuse or gain.

Canonical allocation remains NP2417/BF519/R128/S81. The retained measured
planv is S81+R93/BF520. NO R93 remap or candidate CFG substitution is applied
here; neither native nor observer execution is qualified by this metadata.
Six original native-ME commands fail the existing round admission requirement.
They keep geometry and source_instruction, native_dispatch_refused=true and
emitted_word_sha256=null; the guard has not been waived. First exporter refusal
8ec97b1c6 EXIT1 remains in remote canonical_all40.log/.rc. Corrected exporter
da8ec9c88 completed EXIT0, remote canonical_all40_r2.log/.rc.

Internal activation payload availability remains false; this artifact gives
source hooks, not golden intermediate restores or expected input vectors.
Epicurus owns observer/47FF RTL, Maxwell owns exposed composition. No gain,
physical admission or new campaign is granted. Exact remote usable directory:
ot-epyc2:/srv/opentallas-scratch/codex/arendt-all40-source-schedules-20261005/canonical_all40_r2/

Full-parent immutable phase/stream ROM image is a separate current source
binding. This artifact does not substitute regional observer ROM images for
it, and does not reconcile the existing 40-bit/48-bit stream codecs by fiat.
