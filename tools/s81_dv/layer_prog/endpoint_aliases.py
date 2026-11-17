"""Resolve direct wrapper-input aliases on selected RTL; never infer a stage count."""
import hashlib
import re
from pathlib import Path


def direct_child_input(body, child, leaf_pin, top_pins):
    """Return the top pin wired directly into an immediate child's input, else None.

    Only one literal child instance and a plain identifier/constant slice qualify.
    Expressions, assignments, nested paths and ambiguous generate arms fail closed.
    """
    if not re.fullmatch(r'[A-Za-z_]\w*',child) or not re.fullmatch(r'[A-Za-z_]\w*',leaf_pin):return None
    hits=list(re.finditer(r'\b'+re.escape(child)+r'\s*\(',body))
    if len(hits)!=1:return None
    start=hits[0].end();depth=1;end=start
    while end<len(body) and depth:
        depth+=(body[end]=='(')-(body[end]==')');end+=1
    if depth:return None
    call=body[start:end-1]
    found=re.findall(r'\.'+re.escape(leaf_pin)+r'\s*\(\s*([A-Za-z_]\w*)(?:\s*\[\s*\d+(?:\s*:\s*\d+)?\s*\])?\s*\)',call)
    return found[0] if len(found)==1 and found[0] in top_pins else None


class SelectedInputAliases:
    def __init__(self, die, root, manifest):
        from . import slice_source
        self.root=Path(root);self.die=die
        _,_,self.index,self.prefer=slice_source.manifest_selection(self.root,manifest)
        self.cache={};self.used={}

    def matches(self, sink, leaf_pin, top_pins):
        # Only immediate direct aliases are admitted. More hierarchy must be
        # proven explicitly rather than treating a similarly named port as equal.
        names=sink.split('.')
        if len(names)!=2 or names[0] not in self.die.inst:return False
        master=self.die.inst[names[0]].get('master')
        if not master:return False
        import bind_elab
        if master not in self.cache:
            path,amb=bind_elab.pick(self.index,master,self.prefer)
            if not path or amb:return False
            self.cache[master]=(Path(path),bind_elab.module_body(path,master))
        path,body=self.cache[master]
        top=direct_child_input(body,names[1],leaf_pin,top_pins)
        if top is None:return False
        self.used[sink+'.'+leaf_pin]=dict(top_instance=names[0],top_port=top,
            source_path=str(path.relative_to(self.root)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            basis='literal selected wrapper child pin wired directly to this top input (or constant slice)')
        return True
