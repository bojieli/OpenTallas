# MC3c v3 mapped native census: rejected

Source bcb9f188f. Exact gate synthesis ODB: agidock128
ref_gate/hdie_pc_ctrl_mc3c_p540-20261020-002331/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face_asap7_ref_gate/base/1_synth.odb.
ODB SHA256: 3f8b184035901b64fd8d5ccec59bb080194ef05335fda141181f4440b204dc0f.
Audit v5 is the unchanged native_audit.py used for earlier MC3 candidates; executed via ot-run mem32 in openroad/orfs:asap7lock.

10 drivers exceed32, of which2 are constant tie cells and8 are dynamic.
Three ACT-head registers drive42/34/35 logical terminals; five combinational nodes drive34/33/37/49/38.
Reset is included and no reset driver exceeds32. The census follows actual transparent Liberty unary functions; CTS buffering cannot qualify these dynamic failures.

The unplaced synthesis ODB does not establish reach: its huge invalid pin-box bounds and FAR405 count are not physical violations.
The existing v3 gates were already running at pickup and remain preserved for diagnostic evidence.
No further gate or submission is authorized by this result. Source copies must be fixed and mapped census repeated first.
MC3b remains superseded for head-bank starvation and may not bind.
