.PHONY: pc_drt_preflight
pc_drt_preflight:
	$(OPENROAD_CMD) -no_splash /work/preflight.tcl
