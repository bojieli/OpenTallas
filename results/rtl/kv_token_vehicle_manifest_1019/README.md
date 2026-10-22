# Frozen KV token vehicle dependency manifest

Artifact-only dependency inventory. No tools, RTL, golden, cases, deadlines, running jobs, waiters or default entrypoints were changed. Main snapshot: `92cdd86006eb3e872554ddf4b95542482d028403`. Candidate source: `ae997fbd262e1e7765e7cd053eec746ad3bef0ce`; original staging receipt `b8b26f17f29483710a65e228781c2db5d45c05a2`; independent live-job collection `e4cf1917a68e4f7b4353fabcd7750ca3f32f73e9`. This packet does not install the vehicle in main or qualify full token results.

`source_adoption_manifest.json` records all 20 explicit tool paths, complete candidate/main SHA256s, candidate last-change commit, exact frozen snapshot hashes and matching repository commits. `frozen_files.json` records 152 exact files read or used by frozen G7 vehicles/vector provenance, master sets, generated inputs and all compiled source/model paths. All 75 paths under the selected source tree match the exact bytes at `4db097403`; each includes its git blob and SHA256. Generated/runtime files have content identity, not a fabricated source commit. File-list closure includes literal Verilog includes recursively; Python regeneration closure includes local imports and the explicitly dynamic oracle import. Python standard library, numpy and torch are external toolchain dependencies, not imported repository files.

## Concrete adoption scope for review

Seven paths are absent from main: the five runtime files `kva_vehicle.sh`, `run_kv_attn_mu.sh`, `kv_attn_grp_map.py`, `kva_mu_ports.py`, `drive_qwk_slice_attn_mu.svh`, plus the two optional regeneration files `kv_attn_vectors.py`, `kv_attn_gold.py`, all under `tools/qwen_layerbench/`. Runtime operation on already frozen vectors does not invoke the two regeneration files. Additions, if approved, must be explicit paths at the manifest hashes, not a whole ancestor/path import.

Main `slice_cut.py` is already byte-identical. Main `slice_smoke.py` lacks `--src REGEX=NAME[@HALF_NS]`, which `run_kv_attn_mu.sh` unconditionally uses for HBM clock `hck`: seven additions alone cannot run. `slice_smoke_candidate_delta.patch` contains only that candidate support delta for review; defaults remain the existing shared ck/reset unless an override is supplied. Main `die_port_bind.py` differs: retain current main parser and separately verify compatibility rather than overwrite it with the older frozen/candidate parser. No proof here licenses a parser/helper rollback.

The ae997 correction itself depends on the unimported runtime family: map boot JSON validation and exact programmable-age assignments plus launch forwarding of `--boot-ages`. The independent original `independent_fixture_proof.log` is copied unchanged from ae997 and remains a component fixture proof, not proof that main has the executable vehicle. Positive G7 P0 map differs from its original map by precisely nine assignment lines (one packed PV-age word plus eight selected V-port words); missing boot and inconsistent named/packed words reject. RT31/DQ15 are hardware bounds, not a selected age or authority to move a deadline. No arithmetic/golden change.

## Entrypoints, defaults and limits

`kva_vehicle.sh VEH DIE_RUN KSRC OUT CASES` is an explicit invocation; it has no default vehicle/paths. It cuts, maps and builds/runs; it does not invoke fleet admission itself, so callers must use ot-run. VEH=all selects four stacks; WS/WN/ES/EN select partial stack vehicles; WSQK/WNQK/ESQK/ENQK exclude PV pair clusters. Flattened MU is detected by qkd_astk_ctl_s in the binder JSON; selection then uses astk_*__, seq__*, pvw_*__ prefixes. Old hierarchical sources use master/instance selection. P0/P1 are supported by the flattened MU branch: P0 requires WS+ES+pvw_0, P1 requires WN+EN+pvw_1, plus shared control. A single stack cannot complete a PV pair. Do not feed flattened dies to old hierarchical selections.

`KVA_CUT_ONLY` nonempty exits after generation. `KVA_HIER` defaults to the explicit leaf regex in the wrapper; empty disables hierarchy; `KVA_VFLAGS` defaults to -fno-dfg; original staged successor callers additionally selected -fno-inline. `KVA_J` defaults to 16 for hierarchical builds, 32 for flat builds. `KVA_REBUILD` nonempty forces rebuild; otherwise an existing executable is reused without an identity check. These are opt-in test tools; no production default entrypoint is connected by this artifact.

Run wrapper uses Verilator 5.050 from $HOME/.local/opentallas-tools, randomized initial/reset seed1, compile MUT=0, IDLE_EDGES=200/TAIL_EDGES=50. It starts all noncomment case lines concurrently. It prints SMOKE/KVA summaries but does not aggregate child simulation exit codes into an enforcing final verdict: collectors must inspect every log. KVA_MUT defaults0; mutants are not automatically run by the wrapper. KVA_HCKC is an explicit diagnostic clock override, absent from these case programmes. Partial cuts define KVA_PARTIAL and omit full RESULT exactness judgement, so WSQK/P0/P1 are component timing/partial checks, never a whole-die numerical token proof.

The same MU-shape executable receives u1 (one user) and u4cal/u4pack (multiple users). This does not itself prove a separately selected SU hardware configuration. Runtime defaults include NSTEP1 (max8), CTX8192, KVA_LG8, KGO200, AGE0=1, KVN34, SEQ0=9; user/layer/relative-edge/vector overrides are frozen in `cases_stk.txt`. Per-user epochs are {seq14,user2}; store row is64+layer+256*user. Fixed calendar release edges are not retimed in this packet.

## Runtime generated-input and storage contracts

DIE_RUN supplies port_bind_v2/{die_bound.v,port_bind_v2.json}, case_kv/relay_stages.json and, when exposed programmable age inputs exist, valid case_kv/boot_ages.json. Binder rtl_roots/rtl_files/defines resolve against KSRC, with exact generated slice .f +incdir/+define retained. `slice_cut.py` writes slice.json/<top>.sv/<top>.f; map writes kva_grp_map.svh/kva_grp_facts.json; ports tool writes kva_ports.svh; run wrapper writes kva_hier_refs.svh, tb_<top>.sv and optional hier.vlt. SRAM behavioral models explicitly added by the wrapper are 256x128 and64x128 r2c2 under physical/qkd_astk_strip/macros and32x128 under physical/asap7_memory_macros; all actual files are hashed in the frozen manifest. No macro view equivalence or physical timing follows from behavioral models.

G7 exact die SHA18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6; WSQK has12678 instances/1111ports, P0 18264/825, P1 18032/835. G7 relay_check.json is ABSENT: kva_mu_ports.py explicitly ignores a nonexistent optional relay-check path and uses relay_stages.problems. Successor waiter policy requires relay_check.json; absence on historical G7 is recorded, not repaired. Original G7 map/wrapper/parser hashes differ from candidate in exactly the cases identified in source_adoption_manifest; no corrected fixture was silently applied to live jobs.

Each +VECk directory supplies q.hex (512 FP32 words), gold.hex (512 FP32 words), kv.hex (K then V,2*CTX rows,128 FP8 bytes/row); these are the three files read by the bench. isa.hex and ctx are vector provenance sidecars, also hashed. Eight frozen directories selected by cases_stk are inventoried; neither golden nor a vector was regenerated. The source tree, generated slices, vectors and cases are external frozen inputs, not source files to bulk-import into main.

Optional regeneration uses kv_attn_gold.py --src SRC --out OUT -- [oracle arguments], dynamically loading tools/qwen_hbmacc_position_oracle_gpu.py; that invokes its recorded ISA/image/golden helper family. `kv_attn_vectors.py --gold GOLD --fx FIX --ksrc KSRC --layers ... --vec OUT --out RECORD` reads L<n>_{vm,kv}.npy, L<n>_me_kv.json and P<pos>/L<nn>_die<d>_x.hex / kv_at_P/L<n>_die<d>.json, checking matching real-prefill fixture bytes. It uses hdc_golden plus qwen_nearhbm_attn_ref (and hdc_isa), preserving golden TP4 split checks and explicitly recording TP8 split differences. Mutant shift/pos alter operands/context while retaining true reference gold.

The upstream oracle --run contract additionally needs --prep-dir/prep.json, L<nn>_d<d>.npz (and head_d<d>.npz if selected), --tokens, --embedding-npz, optional --check-token0-preload and --kv-history/L<n>_die<d>.bin. Oracle --prep additionally reads --pins, --stages, per-die layer/head layout manifests, image program.hex/segments.hex and weight/scale data referenced by those manifests. Exact original regeneration CLI/source-image/input paths were not retained in the frozen vehicle directory; their provenance is OPEN. The helper SHA inventory is a regeneration dependency contract, not a claim those images were reconstructed or every upstream weight object was observed. Existing frozen vectors have complete runtime content hashes. Any future regeneration must freeze those explicit source/image/fixture inputs rather than infer them from this packet.

## Explicit source paths

| Path | Main status | Candidate last change |
|---|---|---|
| `tools/die_port_bind.py` | different | `78fdc645de41da671eeb928a83c4faed715e39e8` |
| `tools/hdc_golden.py` | identical | `8458580674f8f75094024685585312820c1b4b34` |
| `tools/hdc_isa.py` | identical | `14ee21cb769f324cd84635ac5a3a28b746be377d` |
| `tools/hdc_program.py` | identical | `4476244cf5e2e238ace398d18b8cf106fe52a353` |
| `tools/hdc_qwen_fullshape_isa_w12.py` | identical | `0a8e89cf4584b41ec945d06bfcb976288bce767d` |
| `tools/hdc_qwen_fullshape_placement_w12.py` | identical | `5da3910e4292fb6c00fab41c6448f8e93a8dc8a3` |
| `tools/hdc_qwen_fullshape_program_w12.py` | identical | `5da3910e4292fb6c00fab41c6448f8e93a8dc8a3` |
| `tools/qwen_hbmacc_position_oracle_gpu.py` | identical | `07408994ccd6ae3de4b9e2582f7fe72cfd0b2df6` |
| `tools/qwen_layerbench/drive_qwk_slice_attn_mu.svh` | absent | `296bef634ef0d304946634d1745380c506d778d9` |
| `tools/qwen_layerbench/kv_attn_gold.py` | absent | `501cc3977d2f0b87335bb1b4b37bcfcc13fe8448` |
| `tools/qwen_layerbench/kv_attn_grp_map.py` | absent | `ae997fbd262e1e7765e7cd053eec746ad3bef0ce` |
| `tools/qwen_layerbench/kv_attn_vectors.py` | absent | `501cc3977d2f0b87335bb1b4b37bcfcc13fe8448` |
| `tools/qwen_layerbench/kva_mu_ports.py` | absent | `501cc3977d2f0b87335bb1b4b37bcfcc13fe8448` |
| `tools/qwen_layerbench/kva_vehicle.sh` | absent | `ae997fbd262e1e7765e7cd053eec746ad3bef0ce` |
| `tools/qwen_layerbench/run_kv_attn_mu.sh` | absent | `296bef634ef0d304946634d1745380c506d778d9` |
| `tools/qwen_layerbench/slice_cut.py` | identical | `9905367fada7c6bd1dc49f4a58535fe4b51f3258` |
| `tools/qwen_layerbench/slice_smoke.py` | different | `501cc3977d2f0b87335bb1b4b37bcfcc13fe8448` |
| `tools/qwen_nearhbm_attn_ref.py` | identical | `b75e0c694e66a4566d1ba8f9ab4286a3122713cc` |
| `tools/qwen_o4_layer0_oracle_w12.py` | identical | `e47ae50b6b8638104c196c835d997a8a3ebc6e5d` |
| `tools/qwen_o4_token_oracle_w12.py` | identical | `5da3910e4292fb6c00fab41c6448f8e93a8dc8a3` |

Validation: read-only remote census completed; all75 selected-source files match4db097403; all20 tool paths compared against pinned main; candidate map/wrapper SHA match original b8 staging receipt; independent fixture proof preserved. No simulation/EDA or new waiter was launched. Actual numerical results, per-layer timing/rates and production clock/reset/health qualification remain with their existing result owners.
