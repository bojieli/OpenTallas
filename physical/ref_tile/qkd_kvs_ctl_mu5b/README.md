# qkd_kvs_ctl_mu5b

Parallel clock fallback of qkd_kvs_ctl_mu5 (KV-GRP-CTL/MU5 10-19): identical RTL, floorplan, macros, benches and
checklist (see ../qkd_kvs_ctl_mu5/README.md); only OT_SPINE_TREE_PAD=1 (subtree-common pad cells instead of per-leaf
pads).  Bind whichever closes first under the checklist; cancel the other.
