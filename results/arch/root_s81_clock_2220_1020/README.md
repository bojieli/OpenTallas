# S81 contract clock discovery review

Source candidate35ae46714 based ROOT source e807f878d. Clean picks f6d32776e (explicit contract ck/ck_in discovery via source reachability, port existence and direction, never payload-name heuristic) and evidence-only b590b7708 (real96-frame dense one-phase capacity refusal:112 necessary). No native Liberty changed. Physical GRT/STA validation remains die_s81-owned, no timing qualification claimed.

Six causal clock-role tests ran on unpinned fleet ep6 unit oth-ubuntu-4131258-1792560044, exit0: direct source contract, payload exclusion, missing source, unreachable source, wrong direction, constant bit cannot hide unconnected clock. Read-only review confirms new generator invocation uses actual parsed module port directions and complete instance connections. Full paired ROOT helper suite applies to unchanged parent e807f878d; this additive generator change touches no closure helpers.
