# Export the same current real-clock boundary used for corner signoff.
read_sdc /src/physical/dsrom_fh_safe/gen/signoff_ep.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /src/physical/dsrom_fh_safe/routed_boundary.sdc
