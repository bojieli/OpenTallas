# DHU k3 native PG reconciliation

Adoption is **PG_HOLD**: one fresh read-only native audit found 54 unbound terminals among 26,394 native POWER/GROUND MTerms (13,197 instances, 65 master types). The 27 affected CTS buffers are 18 BUFx24 and 9 BUFx16f, each missing both VDD and VSS. The other 26,340 terminals bind correctly. Wrong net, unknown domain, missing ITerm and role mismatch counts are all zero. Five retained native global-connect rules determine expected domains independently of actual net membership. Every native master PG terminal is enumerated, including macros, ties, fillers and CTS cells; no role/name exclusion.

This is the distinct `qfd_sys_face_mu_dhuser` master, not frozen GEN's `qfd_sys_face` and not its 3,188-unbound count. Preserve the actual old CLOSED result: TT setup +172.82 ps, FF hold +29.59 ps, DRC 0; SS sensitivity -129.91 ps. PG binding failure blocks adoption; it does not rewrite those timing measurements or establish conductor connectivity.

## Exact identity and integration checklist

- Original job `qfd_sys_face_mu_dhuser-k3-46980a0f6`, source `46980a0f66fa36487c49dcb45156a1fb1feab0ec`, closure record `377992fec`, automatic main integration `3bc54fd8a`.
- Main snapshot `aae57a4e3e0cccf45d98358e41fa8129b9abdaa8`: RTL, blackbox, generated kit spec, floorplan and kit.env match original source hashes; native insertion/LEF/TT/FF/SS views exactly match closure-record hashes. See `source_identity.json`.
- Generated physical kit and retained route config use 84.24 x 71.28 um. The separate tools/ref_tile source template still says 69.12 um height; do not regenerate that template and label it the k3 PSM-fixed geometry.
- Original run `src/` is now empty. Its historical executed file hashes cannot be recovered from that directory; Git identity and retained route VERILOG_FILES declarations are evidence with this explicit limit.
- Actual frozen dv2f18dh2 GEN die.v SHA256 `7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7`, equal in out/case and chain/dieclk: `qfd_sys_face_mu_dhobs mu_dhobs` drives tt_ctlm.dh_user; `qfd_sys_face` remains separate. No `qfd_sys_face_mu_dhuser` instance exists. Existing dh_user is driven, but binding this ROM/op-start leaf is not that completed integration.
- No prior complete native binding receipt was found in the original run's receipt inventory. This is the fresh full census, not admission authority for future jobs.
- Native all-terminal binding **FAIL**; adoption **HOLD**. Actual pin/reset/reach/fanout/depth/current phase/first-use requalification is outside this read-only collection and is not asserted. No old CLOSED-label bind or release-tree tick is justified.

## Execution and immutable receipt

The final ODB is mounted read-only in one OpenROAD invocation using the main native_pg_binding collector. No `global_connect`, connect, protection clearing or `write_db` is invoked. Original final ODB SHA256 is unchanged before/after. `output/native_audit.json` contains every failure and domain rule; deterministic `output/all_native_terms.jsonl.gz` contains all 26,394 rows with master role, actual net/role, expected net/role and census errors. Collector Tcl is retained verbatim.

Actual unpinned ot-run admitted 1 CPU / 4 GB / 2 GB scratch on ot-epyc7 (data locality): original ODB 7.5 MiB, SPEF 2.8 MiB, admission 1,028 GB, available memory 780 GB, free scratch 6,272 GB. Unit `oth-ubuntu-144274-1792447794`, exit 0, native snapshot verdict FAIL, 2.60 s wall. time.log RSS belongs to Docker client, not OpenROAD container; do not claim it as engine peak. See summary.json for observed timestamp.

Actual image ID and RepoDigest are `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`; actual binary hash is retained in output/binary.sha256. This is current audit provenance, not reconstructed historic image identity. Original routed SPEF/design/config hashes are in route_identity.txt. No RC re-extraction, timing rerun, reroute, source activation, bind or submission occurred. Root merger owns corrective work.
