# Private native owner join wrappers

Source-only common-clock COMPONENT family; no public/root activation or physical/CDC qualification. All eight baseline sources match frozen 5f2ce19bc bytes. Public files are untouched. These clones retain every existing register declaration and always block count; added exports and connections add zero holding-state bits. The canonical scheduler extension is provided separately by scheduler owner 89f60efe6, not copied here.

The scheduler pin wrapper forwards the canonical join/retention ABI directly, including raw POR, warm reset, health and owner-drained inputs. Both private feature parameters default off. Existing physical pin channels and role/reset logic remain intact. Functional common-clock fixture does not assert these new crossing wires are production-safe CDC.

The control service wrapper retains its actual registered readiness and request ancestry, real qkd_host_ctl implementation and unchanged ot_qfd_pkgctl. package_start_v is hc[38], with token[35:18], position[17:0] and generation[37:36]. No client or descriptor identity is invented. HC station hc_accept_v is cmd_v && cmd_hc[38], exposing actual station command acceptance with matching HC fields.

Allocator alloc_fire is request_valid && request_ready, alloc_tag is {next_epoch,6'd0,request_token,request_position[12:0],6'd0}, and alloc_gen is request_generation. These combinational pre-NBA exports flow through the actual lifecycle/services/coordinator clones. They do not reuse previous grant registers.

Private coordinator inputs join_client, join_slot and join_pos come from the join core's existing pending owner state. POST association uses actual alloc_fire and those fields, since a queued UNBOUND scheduler issue can arrive while the previous POST owner still exists. Actual allocator/lifecycle admission still serializes allocation behind previous POST retirement; raw retirement, CQ commit, cancellation, terminal and drain checks remain unchanged. POST collector itself remains public original source. This association adds no queue or scheduling decoupling.

No compile or simulation run was launched by this source worker. Bench owner must compose the final core and scheduler ABI, hash the full family, and run actual healthy and causal negative cases on the fleet before claiming functional PASS. Conditional warm/reset tests do not establish a reachable existing reset bug. Production health horizon/calendar remain ineligible until separately derived.
