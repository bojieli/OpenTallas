# Critical direct admission: Docker usage counted once

SCHED-1's direct reservation loop read only the job scope MemoryCurrent. Docker containers run outside that scope, so their memory reduced MemAvailable but remained charged as unused direct reservation. On EPYC2 at 2026-11-07 06:20:51 PST five direct jobs reserved192GB, scopes used<0.1GB, and the fresh Docker-aware unused charge was154GB. At214GB MemAvailable this permits a20GB critical job while preserving32GB headroom.

The read-only ot-direct-pending helper credits fresh cgroup usage only after unique matching of the live docker client command, image, mounts and explicit name to a running inspected container ID. The exact container cgroup must exist, and its launcher must still belong to the scope with the same command. No sampled use.* data supplies credit; no reservation records are edited. Every remaining reservation rounds upward. Fresh/unstarted and unknown units retain their full charge. A missing/failed helper leaves the prior conservative scope-only calculation intact. All job caps, host floors, disk checks, queues and critical eligibility stay.

Atomic ot-heavy replacement affects future launcher processes. Existing parsed shell waiter loops retain their prior calculation; replacing an unstarted waiter requires the current owner's explicit permission and duplicate protection. Never rewrite a live launcher in place.

The06:15 handoff's EPYC4 "scratch571GB" is selected usable root scratch, not scratch2. Actual06:16:42PST df: scratch2 full1GB, root/scratch3~691GB. Existing wrappers explicitly authorize scratch3 and set fallback root floor150GB; per-host defaults override that with100GB on EPYC5/6. New EPYC4 own jobs can use scratch3 under existing150GB floor; scratch2 accepts no new writers. No deletion or floor change is part of this fix.

Validation:8 targeted unittests covering physical+unused accounting, ambiguous/stopped/name identity, duplicate container credit, fresh versus stale-use-file measurements, fractional rounding, full fresh/unstarted/unknown reservations and unchanged32GB floor/fallback; bash syntax check. No broad suite.
