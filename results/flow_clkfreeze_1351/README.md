FLOW-CLKFREEZE canary collection, 2026-10-27

Exact candidate claude/flow-clkfreeze-1027@1f7ecaeb49 (clock helper/HEAD/KV paths as run at d6231262f; subsequent candidate only reverts unverified QC read_guides). This packet collects the existing COORD13:14 canaries, without rerunning proof or physical work.

HEAD intel1 flow-clkfreeze-1027/head_elemA_m2.eco_r19_clkfreeze: signoff_actual SIGNED TT+121.07ps/FF+6.51ps, DRC0/antenna0, clock geometry zero changed across712nets/29434clock-connected instances. Routed final functional-export LEC EQUIVALENT30203/30203,0different/undecided,4915.8s; complete receipt copied under head/lec.json. Source/head proof tool and existing semantics are the original reviewed canary, not a new tool/scope waiver; provenance import error remains explicit in raw receipt.

KV intel2 flow-clkfreeze-1027/kv_e1_holdeco_clkfreeze: SIGNED TT+12.02ps/FF+3.00ps, DRC0/antenna0, PIN_AUDIT544/544,88dataholdbuffers. Clock geometry zero changed across1375nets/28917instances. Native unit3366485 exit0 at13:15:48. Raw signoff and clock-diff receipts retained.

Original1f7 candidate plus separately reviewed stale-dump checker fix0f95af93cc/fac5ca0010 is the ROOT intake. Neither unqualified QC route-segment handoff commits nor the failed QC warm canary is qualified by this HEAD/KV packet. QC has separate native diagnostic/fix work in progress.
