# Clean-baseline RTL implementation replay

**Status:** **PASS**

Run fingerprint: `87e057764094b9ed`  
Clean snapshot commit: `34a0d2ec791a1344a5db96f0123e5d02d57d02ab`  
Clean snapshot tree: `a8bf5906a98014739058615c61c32e9d4cd05f36`

The exact fingerprinted source inventory was copied into an isolated repository and committed with deterministic identity. The complete seven-case campaign then ran without any dirty-tree or skip option.

- Clean source tree: pass.
- Equal source/tool fingerprint: pass.
- Equal source inventory: pass.
- Equal pinned toolchain identity: pass.
- Equal technical closure signature: pass.
- Required cases: 7/7.
- Generic equivalence: 2/2.
- Mapped equivalence: 1/1.
- Physical proxies: 2/2.
- Post-route equivalence: 2/2.
- Hash-verified case artifacts after archival: 386.

The shared worktree was not reset, cleaned, stashed, checked out, or committed. Its unrelated and user-owned changes remain in place.
