HBM event pEv10 (DIE-HBM-101, 2026-11-12), DO_NOT_COUNT. Approved by COORD under the event scope cut.
plan_pEv10_b334c92f7a84.json.gz: the event plan. record.json: plan chain, bind provenance (main 12994e9e, clean), RTL source audit, gates.
bind/: bind.sh recipe, asbuilt manifests, bind report + LANE_ASBUILT + latency consumers + r8 landing. Large bind outputs (bind_sinks, bind_latency) stay on epyc9 hbm101/bindEv10/bind.
builders/: plan builders (run from epyc9 .../die-proto-3/hbm/hp1lane) and the gate helpers latcheck.py / pairsym.py.
asbuilt_sources/: as-built core sources the bind read that are not in main.
