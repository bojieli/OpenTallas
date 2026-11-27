"""kit_flags.py -- the one registry of the opt-in kit flags the die_plan generators read (P-FLAG-SCHEMA-UNREGISTERED, STATION-BITORDER 11-27).

A flag is REGISTERED when it is listed here, with where it can be set and who consumes it.  test_kit_flag_registry.py scans gen_phys.py for
every `os.environ.get("OT_*")` and every `budgets.get("<key>")` and fails when one is neither registered here (or in LEGACY_GEN_ENV, the frozen
list of keys that predate the registry) nor, for a budgets key, declared in schema.py (PRE SCHEMA-UNKNOWN-KEY would refuse the plan).  So a new
flag cannot ship as a hand edit of a flow script: it needs a generator export, a schema key and a line here.

KIT_FLAGS[name] = {"set": where it is set, "budgets": plan keys (all must be in the schema), "config": the config.mk export the generator
writes, "consumer": the flow script that reads it, "default": behaviour when unset}.  Settings are recorded per kit by env_provenance:
the gen env as "env", the exported value as "config_ot".
"""

KIT_FLAGS = {
    "OT_FT_LANE_MONO": {
        "set": "plan budgets.ft_lane_mono / budgets.ft_lane_mono_types, or kit-wave item_env OT_FT_LANE_MONO=1 (=0 forces off)",
        "budgets": ("ft_lane_mono", "ft_lane_mono_types"), "config": "OT_FT_LANE_MONO",
        "consumer": "face_flops.tcl", "default": "off (byte-identical placement)"},
    "OT_FT_LANE_MONO_RING_UM": {
        "set": "kit-wave item_env, only with OT_FT_LANE_MONO on", "budgets": (), "config": "OT_FT_LANE_MONO_RING_UM",
        "consumer": "face_flops.tcl", "default": "20 um"},
    "OT_FT_LANE_MONO_FILL": {
        "set": "kit-wave item_env, only with OT_FT_LANE_MONO on", "budgets": (), "config": "OT_FT_LANE_MONO_FILL",
        "consumer": "face_flops.tcl", "default": "0.5 (channel-capacity warning threshold)"},
}

# generator keys that predate the registry (frozen 11-27): a NEW key is not added here, it gets a KIT_FLAGS entry.
LEGACY_GEN_ENV = (
    "OT_ABC_RECIPE", "OT_ABC_TARGET_PS", "OT_CLAND_STRIP_DENS",
    "OT_CLASS_KEEP", "OT_COLLS_RX_STABLE", "OT_CONS_STRIP_ROWS",
    "OT_CORE_OUT_LAND", "OT_CORE_PIN_RELAY", "OT_CTS_TAP_CENTROID",
    "OT_FLOW_TAG", "OT_FSM_NONE_WIRES", "OT_FT_POLARITY_LOCAL",
    "OT_GEN_SECONDARY_CLOCK", "OT_GEN_TAP_GRT_PRE", "OT_GPL_HPWL_RATIO",
    "OT_GPL_OVERFLOW", "OT_GPL_SPARSE_OVERFLOW", "OT_GRT_ALLOW_CONGESTION",
    "OT_GRT_CLOCK_FIRST", "OT_GRT_CONG_ITERS", "OT_GRT_NONPORT_HOLD",
    "OT_GRT_PORT_HOLD_MARGIN_PS", "OT_GRT_PORT_HOLD_PORTS", "OT_GUTTER_BLOCK_KEEP",
    "OT_GUTTER_BLOCK_MIN_SPAN_UM", "OT_GUTTER_BLOCK_UM", "OT_HEAD_POST_GPL_RESEAT",
    "OT_HEAD_WEST_CK5", "OT_HOLD_AFTER_TT", "OT_HOLD_FF_MARGIN_PS",
    "OT_HOLD_STOP_PS", "OT_HOOK_COVERAGE", "OT_HOOK_MANIFEST",
    "OT_HOP_CENSUS", "OT_HOP_LATCH_CAPTURE_TAP", "OT_IO_HOLD",
    "OT_KEEP_THROUGH", "OT_KEEP_WIRES", "OT_LAND_RESERVE",
    "OT_LEAF_AFF_ASYNC", "OT_LOGIC_CLUSTER_POST_GPL", "OT_MAXWIRE_POST_SKIP",
    "OT_MERGE_CENSUS", "OT_MIDFLOP_RE", "OT_NATIVE_SRAM_PATHS",
    "OT_PGCAP", "OT_PG_CELL_KEEPOUT", "OT_PG_DIE_PHASE",
    "OT_PG_FACE_CUT", "OT_PG_PAIR_ROW_KEEPOUT", "OT_PG_PIN_CHECK",
    "OT_PG_RAIL_CHECK", "OT_PG_ROW_GUIDES", "OT_PG_TRACK_TRUTH_MODE",
    "OT_PLACE_MAX_FANOUT", "OT_PLACE_MAX_TRANSITION", "OT_RC_SIGNAL",
    "OT_RC_SIGNAL_SCALE", "OT_RELAY_MID_FIT", "OT_RELAY_MID_FIT_CHAIN",
    "OT_RELAY_MID_RE", "OT_RELAY_MID_SOFT_FRAC", "OT_RELAY_MID_STAGGER",
    "OT_RELAY_MID_TAIL", "OT_RELAY_POLY", "OT_RELAY_POLY_FAIL",
    "OT_REPLICA_KEEP", "OT_RESERVED_SNAP", "OT_REVIEWED_STATION_PREPARE",
    "OT_REVIEWED_STATION_PREPARE_SHA256", "OT_RFLOW", "OT_RTL_LINT_DEAD_OUTPUT_MODULES",
    "OT_S81_P2_CROP_REVIEW_GUIDES", "OT_S81_SSTN_M5_BLOCK", "OT_S81_SVC_LIVE_SITES",
    "OT_S81_VPW_BANK", "OT_SIGNOFF_PROFILE", "OT_SKIP_PRECTS_METRICS",
    "OT_STAGE_SEAT_RE_EXTRA", "OT_SYNTH_ARGS", "OT_TAP_CORE_DIRECT",
    "OT_TAP_ESCAPE_CLEAR_UM", "OT_TAP_MAX_SINKS", "OT_TAP_SPAN_UM",
    "OT_TT_SETUP_REPAIR",
)

