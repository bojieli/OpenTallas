# Current XS4 source capture-contract correspondence

The approved default-empty XS4 INSTANCE image prefix (980f1ce54) is already
current source, SHA0e49aefdedcc41a1cb571c21cad73f247c2d97a7904799027af1373b16a920e1.
The compiler's selected-source resolver still admitted only its old
974ec6/50485a source identities, so resolving this actual current XS4 failed
`changed XS4 source has no matching capture-stage receipt`.

The candidate adds only that exact new identity to the existing capture-stage
receipt set. The existing one-edge XS4 capture model is retained: the change
adds a default-empty simulation filename prefix, and its SYNTHESIS ROM
expansion is unchanged. The actual native seven-ROM namespace/default
lockstep40cycle/two-distinct-slice/wrong-prefix gate is retained in
results/rtl/s81_xs_image_prefix_2038. It tested image selection/default cycle
correspondence, not full streamer arithmetic or a production mission.

Five selected-source resolver tests pass. The new actual-source fixture
resolves current XS4 with the existing one capture edge; an altered source
still fails the unchanged exact-hash guard. Source preference, wrong defines,
override and absent-file controls remain covered by existing tests. A first
local test invocation used a mistaken result-dictionary key; correcting that
test lookup required no production source change.

No RTL, timing stage, manifest, BF measured-profile hash, source calendar,
physical binding, production default or geometry is changed by this patch.
It does not transfer the retained BF source profile to a changed manifest.
