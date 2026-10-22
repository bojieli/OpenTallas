# CB16 collection

The v2 MAIN and fallback gate failures are retained unchanged. They are replaced by the same RTL/topology kits at source 715cc6f51, which correct only the generated kit hook paths to absolute /src paths. Both v3 jobs are admitted and progressing on gold1; no physical result is claimed. The old MAIN was admitted and completed synthesis before reaching the known missing relative hook. Its completed objects remain intact.

The collector uses an own sparse worktree. The original builder worktree and running controllers remain untouched. This parent still uses explicit A0 diagnostic stand-ins; a successful diagnostic gate cannot qualify the actual A0 child views.
