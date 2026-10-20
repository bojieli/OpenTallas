# Source-pinned diagnostic pickup

Source parent 5fba94815; fleet source recipe remains 027b78781. Bind (landed and flat), 200+200 line-beat integration, and swap causal negative control completed successfully. Wrapper logs retain exact fleet units and tool version.

The stand-in diagnostic gate FAILS: 5345 stages exceed its historical 500 um threshold; combinational child-to-output paths reach 1331 um; CTS and per-root clock coverage fail. This does not qualify a physical parent. Binding current policy is <=405 um or registered/landed, native fanout <=32 including resets, real children, registered pins, and no tied functional ports.

At pickup the original lockstep campaign was still active: MUT0 PASS, MUT1 also PASS, MUT2 build active. No aggregate mutant qualification is claimed. MUT1 needs stimulus/observability diagnosis before accepting the parent. No new jobs or gates were launched by this pickup.
