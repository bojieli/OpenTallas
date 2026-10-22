# Explicit disabled binding profile

Both MU72 parents now default HBC_ENABLE to 0 and pass it to the existing stage enable. This selects its existing original-ring bypass branch. The actual status inputs, forward and return wires, and exported fault/context ports remain in the parent interface. No production clock book is asserted.

The enabled profile requires HBC_ENABLE=1 plus actual compiled stage/rank, clock identity, phase and return-arrival dates. The existing enabled-profile guards remain unchanged; missing dates still refuse when enabled. Earlier full-top receipts and capability hashes describe the source before this parameter addition. They remain immutable and must not establish source equality for this revision. Native receiver and loader implementations are unchanged.
