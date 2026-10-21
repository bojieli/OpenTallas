# New linked infrastructure ECO continuation candidate

Base: published `07edb49ad`. Candidate only: no live state writes, restored-runtime installation or EDA launch.

`closure_loop.py link-infra-eco PARENT --new-name CHILD --manifest FILE` prints a dry prepared record. `--apply` verifies an already restored, distinct runtime and creates a new record at verdict. The parent JSON is never saved or reclassified. A second linked child for the same parent is refused.

Eligibility is specifically a recorded scheduled-retirement CANCELLED parent whose started hold ECO has no durable ECO checkpoint or completed result, whose measured source/route disposition is TT setup >=0, FF hold <0 and DRC0, and whose original source-bound benchmarks passed. E86's known negative internal setup path is refused. No claim that infrastructure retirement repairs a DUT failure.

The new record contains only verdict/collect/export/commit execution stages; the existing ECO admission, output guard, installation and post-ECO verdict paths remain in use. Route, benchmark, calibrate and signoff reconstruction launches are refused. Fresh GRT, automatic VT/combo alternatives and automatic successor campaigns are disabled for this narrowly requested continuation. Earlier routed files, source evidence, parent benchmark provenance and cancelled history remain separate.

The manifest binds canonical parent-state/source identity, all restored input SHA256 values, all frozen helper SHA256 values, actual `5_2_route.odb` plus original final ODB/SPEF/SDC/config/reference inputs, and an immutable new runtime image/library set. Verification reads the prepared files and image libraries before exclusively reserving a new guard/output directory. Large manifests travel on SSH stdin. Path-bearing corner JSON must explicitly point at the new restored ORFS tree; an old absolute prefix is refused. The operator must preserve the original archived JSON and record its path-only relocation rather than pretending the restored tree is the original historical tree.

New ECO/install/export launch environments pin ORFS_IMAGE. Frozen helpers using the two historical image aliases are guarded against a different image ID. The measured routed-reference re-STA gains an optional `--image` argument; its default is unchanged and linked callers pass the immutable ID. Normal jobs otherwise keep their existing behavior.

VE concrete input evidence is on `codex/s81-ve-postretire-1021` at `7cb0026a2` (and preceding `3ab9acff7`, `e7d9e97d9`): all13971 original gate source hashes recovered/durable, originalf51 source comparison, all50 frozen helper bytes joined to durable gate source or the289-file archived route root, exact original5_2ODB/SPEF/SDC hashes, and explicit historical image/loaded-library provenance limitations. No known required source bytes remain missing. Runtime host/path and the final relocated source/config SHA manifest must be sealed after normal automatic staging, before invoking `--apply`.

Validation:8 focused causal tests PASS;7 existing ECO recovery tests PASS; Python compile/CLI help/diff checks PASS. Tests use isolated state and mocked remote execution; no simulations or physical work. ROOT owns relevant paired suites, review, publication and runtime activation.
