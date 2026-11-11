DIE-QC-97 PLACEREP-1 (11-11): per-read-chunk kept copy of the ring placement value RP0 (ot_meso_place_rep), emitted as
.PLACEREP(1) on strap-form rings with more than one read chunk when clock.landing_ring_fanout_max > 0.
LEC (yosys equiv_make/equiv_simple/equiv_induct, ORFS image): gold = fanout-32 form (DSREP 2, RSTREP 4, STATUS_REG 1, WREG 1,
WFALL 1) without PLACEREP, gate = with PLACEREP(1), W=549 DEPTH 4 (the slw_fe_v2 dd_ei ring), strap_k = constant K in {5, 13, 38}:
4292 / 4292 $equiv cells proven for each K (lec/equiv_status_k*.txt).  Assumption of the proof: the strap is constant (tied) and
at least one rclk edge precedes the first align edge (opt_dff refines the un-initialised place copies to the constant); the
placement value is read only by the align load, which runs inside the held reset.
