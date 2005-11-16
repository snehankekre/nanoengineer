# Copyright (c) 2004-2005 Nanorex, Inc.  All rights reserved.

"""
part.py

Provides class Part, for all chunks and jigs in a single physical space,
together with their selection state and grouping structure (shown in the model tree).

$Id$

see assembly.py docstring, some of which is really about this module. ###@@@ revise

==

This module also contains a lot of code for specific operations on sets of molecules,
which are all in the current part. Some of this code might ideally be moved to some
other file. [As of 050507, much of that has now been moved.]

==

History: split out of assembly.py (the file, and more importantly the class)
by bruce 050222. The Part/assembly distinction was introduced by bruce 050222
(though some of its functionality was anticipated by the "current selection group"
introduced earlier, just before Alpha-1). [I also rewrote this entire docstring then.]

The Part/assembly distinction is unfinished, particularly in how it relates to some modes and to movie files.

Prior history of assembly.py (and thus of much code in this file) unclear;
assembly.py was almost certainly originated by Josh.

bruce 050507 moved various methods out of this file, into more appropriate
smaller files, some existing (jigs.py) and some new (ops_*.py).

bruce 050513 replaced some == with 'is' and != with 'is not', to avoid __getattr__
on __xxx__ attrs in python objects.

bruce 050901 used env.history in some places.
"""

###e imports -- many of these are probably not needed [bruce 050507 removed some of them]
from Numeric import *
from VQT import *
from string import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from chem import *
from movie import *
from jigs import * # maybe only needs jigmakers_Mixin
from Utility import *

from HistoryWidget import greenmsg, redmsg
from inval import InvalMixin
from assembly import SELWHAT_CHUNKS, SELWHAT_ATOMS
import env #bruce 050901
from undo_mixin import GenericDiffTracker_API_Mixin #bruce 051013

from ops_atoms     import ops_atoms_Mixin
from ops_connected import ops_connected_Mixin
from ops_copy      import ops_copy_Mixin
from ops_motion    import ops_motion_Mixin
from ops_rechunk   import ops_rechunk_Mixin
from ops_select    import ops_select_Mixin

# number of atoms for detail level 0
HUGE_MODEL = 20000
# number of atoms for detail level 1
LARGE_MODEL = 5000

debug_parts = False # set this to True in a debugger, to enable some print statements, etc


class Part( jigmakers_Mixin, InvalMixin, GenericDiffTracker_API_Mixin,
            ops_atoms_Mixin, ops_connected_Mixin, ops_copy_Mixin,
            ops_motion_Mixin, ops_rechunk_Mixin, ops_select_Mixin
           ):
    """
    One Part object is created to hold any set of chunks and jigs whose
    coordinates are intended to lie in the same physical space.
    When new clipboard items come into being, new Parts are created as needed
    to hold them; and they should be destroyed when those clipboard items
    no longer exist as such (even if the chunks inside them still exist in
    some other Part).
       Note that parts are not Nodes (or at least, they are not part of the same node-tree
    as the chunks/jigs they contain); each Part has a toplevel node self.topnode,
    and a reference to its assy, used for (e.g.) finding a reference to the shared
    (per-assy) clipboard to use, self.shelf.
    """
    def __init__(self, assy, topnode):
        self.alive = False # set to True at end of init
        self.name = None # this is [someday] set to any name autogenerated for our topnode,
            # so it can be reused if necessary (if our topnode changes a couple times in a row)
            # rather than autogenerating another name.
            # It would also be useful if there was a Part Tree Widget...
        self.init_InvalMixin()
        self.assy = assy
        self.topnode = topnode
            # some old code refers to topnode as tree or root, but that's deprecated
            # since it doesn't work for setting the value (it causes bugs we won't detect)
            # so change all uses of that... maybe I have by now? ###k
        self.nodecount = 0 # doesn't yet include topnode until we self.add it, below
        prior_part = topnode.part
        if prior_part is None:
            prior_part = topnode.prior_part #bruce 050527 new feature; also might be None
        if prior_part is not None:
            # topnode.part might be destroyed when we add topnode to ourselves,
            # so we'd better first salvage from it whatever might be useful
            # (copying its view attributes fixes bug 556 [bruce 050420])
            # [now we can also get these from topnode.prior_part if necessary;
            #  it is like .part but doesn't modify part's nodecount or stats;
            #  this is added to nodes made by copying other nodes, or Groups containing those,
            #  so that view info can generally be preserved for copies -- bruce 050527]
            self.homeCsys = prior_part.homeCsys.copy()
            self.lastCsys = prior_part.lastCsys.copy()
            # (copying its name, if we were the first ones to get to it and if it doesn't
            #  any longer need its name (since it has no topnode), might be enough
            #  to make ungroup/regroup of a clipboard item preserve an autogenerated name;
            #  I'm not 100% sure it's always a good idea, but it's worth a try, I guess;
            #  if it's bad it'll be because the part still wanted its name for some reason. [bruce 050420])
            if prior_part.name and prior_part.topnode is None:
                # steal its name
                self.name = prior_part.name
                prior_part.name = None
        else:
            # HomeView and LastView -- these are per-part, are switched into GLPane
            # when its current part changes (i.e. very soon after our assy's current part changes),
            # and are written into mmp file for main part, and in future for all parts.
            ###e bruce 050527 comment: would it ever be better to set these to fit the content? If so,
            # we'd have to just inval them here, since most of the content is probably
            # in nodes other than topnode, which are not yet added (and we don't want to
            # assume topnode's kids will all be added, though for now this might be true -- not sure).
            self.homeCsys = Csys(self.assy, "HomeView", 10.0, V(0,0,0), 1.0, 0.0, 1.0, 0.0, 0.0)
            self.lastCsys = Csys(self.assy, "LastView", 10.0, V(0,0,0), 1.0, 0.0, 1.0, 0.0, 0.0)
            
        self.add(topnode)
        # for now:
        from assembly import assembly
        assert isinstance(assy, assembly)
        assert isinstance(topnode, Node)
        
        # self._modified?? not yet needed for individual parts, but will be later.

        
        ##bruce 050417 zapping all Datum objects, since this will have no important effect,
        ## even when old code reads our mmp files.
        ## More info about this can be found in other comments/emails.
##        self.xy = Datum(self.assy, "XY", "plane", V(0,0,0), V(0,0,1))
##        self.yz = Datum(self.assy, "YZ", "plane", V(0,0,0), V(1,0,0))
##        self.zx = Datum(self.assy, "ZX", "plane", V(0,0,0), V(0,1,0))

        ##bruce 050418 replacing this with viewdata_members method and its caller in assy:
##        grpl1 = [self.homeCsys, self.lastCsys] ## , self.xy, self.yz, self.zx] # [note: only use of .xy, .yz, .zx as of 050417]
##        self.viewdata = Group("View Data", self.assy, None, grpl1) #bruce 050418 renamed this; not a user-visible change
##        self.viewdata.open = False

                
        # some attrs are recomputed as needed (see below for their _recompute_ or _get_ methods):
        # e.g. molecules, bbox, center, drawLevel, alist, selatoms, selmols
                
        # movie ID, for future use. [bruce 050324 commenting out movieID until it's used; strategy for this will change, anyway.]
        ## self.movieID=0
        
        # ppa = previous picked atoms. ###@@@ not sure these are per-part; should reset when change mode or part
        self.ppa2 = self.ppa3 = self.ppm = None

        self.alive = True # we're not yet destroyed

        if debug_parts:
            print "debug_parts: fyi: created Part:", self

        return # from Part.__init__

    def viewdata_members(self, i): #bruce 050418: this helps replace old assy.data for writing mmp files
        #bruce 050421: patch names for sake of saving per-Part views;
        # should be ok since names not otherwise used (I hope);
        # if not (someday), we can make copies and patch their names
        suffix = i and str(i) or ""
        self.homeCsys.name = "HomeView" + suffix
        self.lastCsys.name = "LastView" + suffix
        return [self.homeCsys, self.lastCsys]

    def __repr__(self):
        classname = self.__class__.__name__
        try:
            topnodename = "%r" % self.topnode.name
        except:
            topnodename = "<topnode??>"
        try:
            return "<%s %#x %s (%d nodes)>" % (classname, id(self), topnodename, self.nodecount)
        except:
            return "<some part, exception in its __repr__>" #bruce 050425

    # == updaters (###e refile??)

    def gl_update(self):
        "update whatever glpane is showing this part (more than one, if necessary)"
        self.assy.o.gl_update()
    
    # == membership maintenance

    # Note about selection of nodes moving between parts:
    # when nodes are removed from or added to parts, we ensure they (or their atoms) are not picked,
    # so that we needn't worry about updating selatoms, selmols, or current selection group;
    # this also seems best in terms of the UI. But note that it's not enough, if .part revision
    # follows tree revision, since picked nodes control selection group using tree structure alone.

    def add(self, node):
        if node.part is self:
            # this is normal, e.g. in ensure_one_part, so don't complain
            return
        if node.part is not None:
            if debug_parts:
                # this will be common
                print "debug_parts: fyi: node added to new part so removed from old part first:", node, self, node.part
            node.part.remove(node)
        assert node.part is None
        assert not node.picked # since remove did it, or it was not in a part and could not have been picked (I think!)
        #e should assert a mol's atoms not picked too (too slow to do it routinely; bugs in this are likely to be noticed)
        node.part = node.prior_part = self
            #bruce 050527 comment: I hope and guess this is the only place node.part is set to anything except None; need to check ###k
        self.nodecount += 1
        if isinstance(node, molecule): #####@@@@@ #e better if we let the node add itself to our stats and lists, i think...
            self.invalidate_attrs(['molecules'], skip = ['natoms']) # this also invals bbox, center
                #e or we could append node to self.molecules... but I doubt that's worthwhile ###@@@
            self.adjust_natoms( len(node.atoms)) 
        # note that node is not added to any comprehensive list of nodes; in fact, we don't have one.
        # presumably this function is only called when node was just, or is about to be,
        # added to a nodetree in a place which puts it into this part's tree.
        # Therefore, in the absence of bugs and at the start of any user event handler,
        # self.topnode should serve as a comprehensive tree of this part's nodes.
        return
    
    def remove(self, node):
        """Remove node (a member of this part) from this part's lists and stats;
        reset node.part; DON'T look for interspace bonds yet (since this node
        and some of its neighbors might be moving to the same new part).
        Node (and its atoms, if it's a chunk) will be unpicked before the removal.
        """
        assert node.part is self
        node.unpick() # this maintains selmols if necessary
        if isinstance(node, molecule):
            # need to unpick the atoms? [would be better to let the node itself have a method for this]
            # (#####@@@@@ fix atom.unpick to not remake selatoms if missing, or to let this part maintain it)
            if (not self.__dict__.has_key('selatoms')) or self.selatoms:
                for atm in node.atoms.itervalues():
                    atm.unpick() #e optimize this by inlining and keeping selatoms test outside of loop
            self.invalidate_attrs(['molecules'], skip = ['natoms']) # this also invals bbox, center
            self.adjust_natoms(- len(node.atoms))
        self.nodecount -= 1
        node.part = None
        if self.topnode is node:
            self.topnode = None #k can this happen when any nodes are left??? if so, is it bad?
            if debug_parts:
                print "debug_parts: fyi: topnode leaves part, %d nodes remain" % self.nodecount
            # it can happen when I drag a Group out of clipboard: "debug_parts: fyi: topnode leaves part, 2 nodes remain"
            # and it doesn't seem to be bad (the other 2 nodes were pulled out soon).
        if self.nodecount <= 0:
            assert self.nodecount == 0
            assert not self.topnode
            self.destroy()
        return
    
    def destroy_with_topnode(self): #bruce 050927; consider renaming this to destroy, and destroy to something else
        "destroy self.topnode and then self; assertionerror if self still has nodes after topnode is destroyed"
        if self.topnode is not None:
            self.topnode.kill() # use kill, since Node.destroy is NIM [#e this should be fixed, might cause memory leaks]
        self.destroy()
        return
    
    def destroy(self): #bruce 050428 making this much more conservative for Alpha5 release and to fix bug 573 
        "forget enough to prevent memory leaks; only valid if we have no nodes left; MUST NOT forget views!"
        #bruce 050527 added requirement (already true in current implem) that this not forget views,
        # so node.prior_part needn't prevent destroy, but can be used to retrieve default initial views for node.
        if debug_parts:
            print "debug_parts: fyi: destroying part", self
        assert self.nodecount == 0, "can't destroy a Part which still has nodes" # esp. since it doesn't have a list of them!
            # actually it could scan self.assy.root to find them... but for now, we'll enforce this anyway.
        if self.assy and self.assy.o: #e someday change this to self.glpane??
            self.assy.o.forget_part(self) # just in case we're its current part
        ## self.invalidate_all_attrs() # not needed
        self.alive = False # do this one first ####@@@@ see if this can help a Movie who knows us see if we're safe... [050420]
        if "be conservative for now, though memory leaks might result": #bruce 050428 
            return
        # bruce 050428 removed the rest for now. In fact, even what we had was probably not enough to
        # prevent memory leaks, since we've never paid attention to that, so the Nodes might have them
        # (in the topnode tree, deleted earlier, or the View nodes we still have, which might get into
        #  temporary Groups in writemmp_file code and not get properly removed from those groups).
        ## BTW, bug 573 came from self.assy = None followed by __getattr__ wanting attrs from self.assy
        ## such as 'w' or 'current_selgroup_iff_valid'.
##        # set all attrs to None, including self.alive (which is otherwise True to indicate we're not yet destroyed)
##        for attr in self.__dict__.keys():
##            if not attr.startswith('_'):
##                #bruce 050420 see if this 'if' prevents Python interpreter hang
##                # when this object is later passed as argument to other code
##                # in bug 519 (though it probably won't fix the bug);
##                # before this we were perhaps deleting Python-internal attrs too,
##                # such as __dict__ and __class__!
##                if 0 and platform.atom_debug:
##                    print "atom_debug: destroying part - deleting i mean resetting attr:",attr
##                ## still causes hang in movie mode:
##                ## delattr(self,attr) # is this safe, in arb order of attrs??
##                setattr(self, attr, None)
        return

    # incremental update methods
    
    def selmols_append(self, mol):
        if self.__dict__.has_key('selmols'):
            assert mol not in self.selmols
            self.selmols.append(mol)
        return

    def selmols_remove(self, mol):
        if self.__dict__.has_key('selmols'):
            ## might not always be true in current code, though it should be:
            ## assert mol in self.selmols
            try:
                self.selmols.remove(mol)
            except ValueError: # not in the list
                if platform.atom_debug:
                    print_compact_traceback("selmols_remove finds mol not in selmols (might not be a bug): ")
        return

    def adjust_natoms(self, delta):
        "adjust the number of atoms, if known. Useful since drawLevel depends on this and is often recomputed."
        if self.__dict__.has_key('natoms'):
            self.natoms += delta
        return
    
    # == compatibility methods

    #####@@@@@ find and fix all sets of .tree or .root or .data (old name, should all be renamed now) or .viewdata (new name) or .shelf
    
    def _get_tree(self): #k this would run for part.tree; does that ever happen?
        print_compact_stack("_get_tree is deprecated: ")
        return self.topnode

    def _get_root(self): #k needed?
        print_compact_stack("_get_root is deprecated: ")
        return self.topnode
    
    # == properties that might be overridden by subclasses
    
    def immortal(self):
        """Should this Part be undeletable from the UI (by cut or delete operations)?
        When true, delete will delete its members (leaving it empty but with its topnode still present),
        and cut will cut its members and move them into a copy of its topnode, which is left still present and empty.
        [can be overridden in subclasses]
        """
        return False # simplest value used as default

    # == attributes which should be delegated to self.assy
    
    # attrnames to delegate to self.assy (ideally for writing as well as reading, until all using-code is upgraded)
    assy_attrs = ['w','o','mt','selwhat']
        # 050308: selwhat will be an official assy attribute;
        # some external code assigns to assy.selwhat directly,
        # and for now can keep doing that. Within the Part, perhaps we should
        # use a set_selwhat method if we need one, but for now we just assign
        # directly to self.assy.selwhat.
    assy_attrs_temporary = ['changed'] # tolerable, but might be better to track per-part changes, esp. re movies #####@@@@@
    assy_attrs_review = ['shelf', 'current_movie']
        #e in future, we'll split out our own methods for some of these, incl .changed
        #e and for others we'll edit our own methods' code to not call them on self but on self.assy (incl selwhat).
    assy_attrs_all = assy_attrs + assy_attrs_temporary + assy_attrs_review
    
    def __getattr__(self, attr):
        "[overrides InvalMixin.__getattr__]"
        if attr.startswith('_'): # common case, be fast (even though it's done redundantly by InvalMixin.__getattr__)
            raise AttributeError, attr
        if attr in self.assy_attrs_all:
            # delegate to self.assy
            return getattr(self.assy, attr) ###@@@ detect error of infrecur, since assy getattr delegates to here??
        return InvalMixin.__getattr__(self, attr) # uses _get_xxx and _recompute_xxx methods

    # == attributes which should be invalidated and recomputed as needed (both inval and recompute methods follow)

    _inputs_for_molecules = [] # only invalidated directly #####@@@@@ need to do it in any other places too?
    def _recompute_molecules(self):
        "recompute self.molecules as a list of this part's chunks, IN ARBITRARY AND NONDETERMINISTIC ORDER."
        self.molecules = 333 # not a sequence - detect bug of touching or using this during this method
        seen = {} # values will be new list of mols
        def func(n):
            "run this exactly once on all molecules that properly belong in this assy"
            if isinstance(n, molecule):
                # check for duplicates (mol at two places in tree) using a dict, whose values accumulate our mols list
                if seen.get(id(n)):
                    print "bug: some chunk occurs twice in this part's topnode tree; semi-tolerated but not fixed"
                    return # from func only
                seen[id(n)] = n
            return # from func only
        self.topnode.apply2all( func)
        self.molecules = seen.values()
            # warning: not in the same order as they are in the tree!
            # even if it was, it might elsewhere be incrementally updated.
        return

    def nodes_in_mmpfile_order(self, nodeclass = None): #bruce 050325 to help with movie writing; might not be needed
        """Return a list of leaf nodes in this part (only of the given class, if provided)
        in the same order as they appear in its nodetree (depth first),
        which should be the same order they'd be written into an mmp file,
        unless something reorders them first (as happens for certain jigs
        in workaround_for_bug_296, as of 050325,
        but maybe not as of 051115 since workaround_for_bug_296 was removed some time ago).
        See also _recompute_alist.
        """
        res = []
        def func(n):
            if not nodeclass or isinstance(n, nodeclass):
                res.append(n)
            return # from func only
        self.topnode.apply2all( func)
        return res

    _inputs_for_natoms = ['molecules']
    def _recompute_natoms(self):
        #e we might not bother to inval this for indiv atom changes in mols -- not sure yet
        #e should we do it incrly? should we do it on every node, and do other stats too?
        num = 0
        for mol in self.molecules:
            num += len(mol.atoms)
        return num

    _inputs_for_drawLevel = ['natoms']
    def _recompute_drawLevel(self):
        "This is used to control the detail level of sphere subdivision when drawing atoms."
        num = self.natoms
        self.drawLevel = 2
        if num > LARGE_MODEL: self.drawLevel = 1
        if num > HUGE_MODEL: self.drawLevel = 0
    
    def computeBoundingBox(self):
        """Compute the bounding box for this Part. This should be
        called whenever the geometry model has been changed, like new
        parts added, parts/atoms deleted, parts moved/rotated(not view
        move/rotation), etc."""
        self.invalidate_attrs(['bbox','center'])
        self.bbox, self.center
        return

    _inputs_for_bbox = ['molecules'] # in principle, this should also be invalidated directly by a lot more than does it now
    def _recompute_bbox(self):
        self.bbox = BBox()
        for mol in self.molecules:
              self.bbox.merge(mol.bbox)
        self.center = self.bbox.center()
    
    _inputs_for_center = ['molecules']
    _recompute_center = _recompute_bbox

    _inputs_for_alist = [] # only invalidated directly. Not sure if we'll inval this whenever we should, or before uses. #####@@@@@
    def _recompute_alist(self):
        """Recompute self.alist, a list of all atoms in this Part, in the same order in which they
        were read from, or would be written to, an mmp file --
        namely, tree order for chunks, atom.key order within chunks.
        See also nodes_in_mmpfile_order.
        """
        #bruce 050228 changed chunk.writemmp to make this possible,
        # by writing atoms in order of atom.key,
        # which is also the order they're created in when read from an mmp file.
        # Note that just after reading an mmp file, all atoms in alist are ordered by .key,
        # but this is no longer true in general after chunks are reordered, separated, merged,
        # or atoms are created or destroyed. What does remain true is that newly written mmp files
        # would have atoms (and the assy.alist computed by the old mmp-writing code)
        # in the same order as this function computes.
        #   (#e Warning: if we revise mmp file format, this might no longer be correct.
        # For example, if we wanted movies to remain valid when chunks were reordered in the MT
        # and even when atoms were divided into chunks differently,
        # we could store an array of atoms followed by chunking and grouping info, instead of
        # using tree order at all to determine the atom order in the file. Or, we could change
        # the movie file format to not depend so strongly on atom order.)
        self.alist = 333 # not a valid Python sequence
        alist = []
        def func_alist(nn):
            "run this exactly once on all molecules (or other nodes) in this part, in tree order"
            if isinstance(nn, molecule):
                alist.extend(nn.atoms_in_mmp_file_order())
            return # from func_alist only
        self.topnode.apply2all( func_alist)
        self.alist = alist
        return

    # == do the selmols and selatoms recomputers belong in ops_select??
    
    _inputs_for_selmols = [] # only inval directly, since often stays the same when molecules changes, and might be incrly updated
    def _recompute_selmols(self):
        #e not worth optimizing for selwhat... but assert it was consistent, below.
        self.selmols = 333 # not a valid Python sequence
        res = []
        def func_selmols(nn):
            "run this exactly once on all molecules (or other nodes) in this part (in any order)"
            if isinstance(nn, molecule) and nn.picked:
                res.append(nn)
            return # from func_selmols only
        self.topnode.apply2all( func_selmols)
        self.selmols = res
        if self.selmols:
            if self.selwhat != SELWHAT_CHUNKS:
                msg = "bug: part has selmols but selwhat != SELWHAT_CHUNKS"
                if platform.atom_debug:
                    print_compact_stack(msg)
                else:
                    print msg
        return

    _inputs_for_selatoms = [] # only inval directly (same reasons as selmols; this one is *usually* updated incrementally, for speed)
    def _recompute_selatoms(self):
        if self.selwhat != SELWHAT_ATOMS:
            # optimize, by trusting selwhat to be correct.
            # This is slightly dangerous until changes to assy's current selgroup/part
            # also fix up selatoms, and perhaps even verify no atoms selected in new part.
            # But it's likely that there are no such bugs, so we can try it this way for now.
            # BTW, someday we might permit selecting atoms and chunks at same time,
            # and this will need revision -- perhaps we'll have a selection-enabled boolean
            # for each type of selectable thing; perhaps we'll keep selatoms at {} when they're
            # known to be unselectable.
            # [bruce 050308]
            return {} # caller (InvalMixin.__getattr__) will store this into self.selatoms
        self.selatoms = 333 # not a valid dictlike thing
        res = {}
        def func_selatoms(nn):
            "run this exactly once on all molecules (or other nodes) in this part (in any order)"
            if isinstance(nn, molecule):
                for atm in nn.atoms.itervalues():
                    if atm.picked:
                        res[atm.key] = atm
            return # from func_selatoms only
        self.topnode.apply2all( func_selatoms)
        self.selatoms = res
        return

    def selatoms_list(self): #bruce 051031
        """Return the current list of selected atoms, in order of selection (whenever that makes sense), earliest first.
        This list is recomputed whenever requested, since order can change even when set of selected atoms
        doesn't change; therefore its API looks like a method rather than like an attribute.
           Intended usage: use .selatoms_list() instead of .selatoms.values() for anything which might care about atom order.
        """
        items = [(atm.pick_order(), atm) for atm in self.selatoms.itervalues()]
        items.sort()
        return [pair[1] for pair in items]
        
    # ==
    
    def addmol(self, mol): #bruce 050228 revised this for Part (was on assy) and for inval/update of part-summary attrs.
        """(Public method:)
        Add a chunk to this Part (usually the "current Part").
        Invalidate part attributes which summarize part content (e.g. bbox, drawLevel).
##        Merge bboxes and update our drawlevel
##        (though there is no guarantee that mol's bbox and/or number of atoms
##        won't change again during the same user-event that's running now;
##        some code might add mol when it has no atoms, then add atoms to it).
        """
        ## not needed since done in changed_members:
        ## self.changed() #bruce 041118
##        self.bbox.merge(mol.bbox) # [see also computeBoundingBox -- bruce 050202 comment]
##        self.center = self.bbox.center()
##        self.molecules += [mol]
        self.ensure_toplevel_group() # need if, e.g., we use Build mode to add to a clipboard item
        self.topnode.addchild(mol)
            #bruce 050202 comment: if you don't want this location for the added mol,
            # just call mol.moveto when you're done, like [some code in files_mmp.py] does.   
        ## done in addchild->changed_dad->inherit_part->Part.add:
        ## self.invalidate_attrs(['natoms','molecules']) # this also invals bbox and center, via molecules
        
        #bruce 050321 disabling the following debug code, since not yet ok for all uses of _readmmp;
        # btw does readmmp even need to call addmol anymore??
        #bruce 050322 now readmmp doesn't call addmol so I'll try reenabling this:
        if 1 and platform.atom_debug:
            self.assy.checkparts()

    def ensure_toplevel_group(self): #bruce 050228, 050309
        "make sure this Part's toplevel node is a Group, by Grouping it if not."
        assert self.topnode
        if not self.topnode.is_group():
            self.create_new_toplevel_group()
        return

    def create_new_toplevel_group(self):
        "#doc; return newly made toplevel group"
        ###e should assert we're a clipboard item part
        # to do this correctly, I think we have to know that we're a "clipboard item part";
        # this implem might work even if we permit Groups of clipboard items someday
        old_top = self.topnode
        #bruce 050420 keep autogen names in self as well as in topnode
        name = self.name or self.assy.name_autogrouped_nodes_for_clipboard( [old_top])
        self.name = name
        # beginning of section during which assy's Part structure is invalid
        self.topnode = Group(name, self.assy, None)
        self.add(self.topnode)
        # now put the new Group into the node tree in place of old_top
        old_top.addsibling(self.topnode)
        self.topnode.addchild(old_top) # do this last, since it makes old_top forget its old location
        # now fix our assy's current selection group if it used to be old_top,
        # but without any of the usual effects from "selgroup changed"
        # (since in a sense it didn't -- at least the selgroup's part didn't change).
        self.assy.fyi_part_topnode_changed(old_top, self.topnode)
        # end of section during which assy's Part structure is invalid
        if platform.atom_debug:
            self.assy.checkparts()
        return self.topnode
    
    # ==
    
    def draw(self, glpane): #bruce 050617 renamed win arg to glpane, and made this method use it for the first time
        ###e bruce 050617: might revise this to draw "computed topnode for drawing" if that exists and is enabled and updated...
        #e and it might be that the glpane we're passed is modified or a proxy, and can tell us what to do about this.
        self.topnode.draw(glpane, glpane.display)

    def draw_text_label(self, glpane):
        "#doc; called from GLPane.paintGL just after it calls mode.Draw()"
        # caller catches exceptions, so we don't have to bother
        text = self.glpane_text()
        if text:
            # code from GLPane.drawarrow
            glDisable(GL_LIGHTING)
            glDisable(GL_DEPTH_TEST)
            glPushMatrix()
            font = QFont(QString("Helvetica"), 24, QFont.Bold)
            glpane.qglColor(Qt.red) # this needs to be impossible to miss -- not nice-looking!
                #e tho it might be better to pick one of several bright colors
                # by hashing the partname, so as to change the color when the part changes.
            # this version of renderText uses window coords (0,0 at upper left)
            # rather than model coords (but I'm not sure what point on the string-image
            # we're setting the location of here -- guessing it's bottom-left corner):
            glpane.renderText(25,40, QString(text), font)
            glPopMatrix()
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            return

    def glpane_text(self):
        return "" # default implem, subclasses might override this
        
    # ==
    
    # for debugging
    def prin(self):
        for a in self.selatoms.itervalues():
            a.prin()

    # ==

    def break_interpart_bonds(self): ###@@@ move elsewhere in method order? review, implem for jigs
        """Break all bonds between nodes in this part and nodes in other parts;
        jig-atom connections count as bonds [but might not be handled correctly as of 050308].
        #e In future we might optimize this and only do it for specific node-trees.
        """
        # Note: this implem assumes that the nodes in self are exactly the node-tree under self.topnode.
        # As of 050309 this is always true (after update_parts runs), but might not be required except here.
        self.topnode.apply2all( lambda node: node.break_interpart_bonds() )
        return

    # == these are event handlers which do their own full UI updates at the end
    
    # bruce 050201 for Alpha:
    #    Like I did to fix bug 370 for Delete (and cut and copy),
    # make Hide and Unhide work on jigs even when in selatoms mode.
    
    def Hide(self):
        "Hide all selected chunks and jigs"
        self.topnode.apply2picked(lambda x: x.hide())
        self.w.win_update()

    def Unhide(self):
        "Unhide all selected chunks and jigs"
        self.topnode.apply2picked(lambda x: x.unhide())
        self.w.win_update()

    # ==

    def place_new_jig(self, jig): #bruce 050415, split from all jig makers, extended, bugfixed
        """Place a new jig
        (created by user, from atoms which must all be in this Part)
        into a good place in this Part's model tree.
        """
        atoms = jig.atoms # public attribute of the jig
        assert atoms, "bug: new jig has no atoms: %r" % jig
        for atm in atoms:
            assert atm.molecule.part is self, "bug: new jig's atoms are not all in the current Part"
        # First just put it after any atom's chunk (as old code did); then fix that place below.
        self.ensure_toplevel_group() #bruce 050415 fix bug 452 item 17
        mol = atoms[0].molecule # arbitrary chunk involved with this jig
        mol.dad.addchild(jig)
        assert jig.part is self, "bug in place_new_jig's way of setting correct .part for jig %r" % jig
        # Now put it in the right place in the tree, if it didn't happen to end up there in addchild.
        # BTW, this is probably still good to do, even though it's no longer necessary to do
        # whenever we save the file (by workaround_for_bug_296, now removed),
        # i.e. even though the mmp format now permits forward refs to jigs. [bruce 051115 revised comment]
        from node_indices import fix_one_or_complain
        def errfunc(msg):
            "local function for error message output"
            # I think this should never happen
            env.history.message( redmsg( "Internal error making new jig: " + msg))
        fix_one_or_complain( jig, self.topnode, errfunc)
        return
    
    # ==
    
    def resetAtomsDisplay(self):
        """Resets the display mode for each atom in the selected chunks 
        to default display mode.
        Returns the total number of atoms that had their display setting reset.
        """
        n = 0
        for chunk in self.selmols:
            n += chunk.set_atoms_display(diDEFAULT)
        if n: self.changed()
        return n

    def showInvisibleAtoms(self):
        """Resets the display mode for each invisible (diINVISIBLE) atom in the 
        selected chunks to default display mode.
        Returns the total number of invisible atoms that had their display setting reset.
        """
        n = 0
        for chunk in self.selmols:
            n += chunk.show_invisible_atoms()
        if n: self.changed()
        return n

    ###e refile these new methods:

    def writemmpfile(self, filename):
        # as of 050412 this didn't yet turn singlets into H;
        # but as of long before 051115 it does (for all calls -- so it would not be good to use for Save Selection!)
        from files_mmp import writemmpfile_part
        writemmpfile_part( self, filename)
        
    pass # end of class Part

# subclasses of Part

class MainPart(Part):
    def immortal(self): return True
    def location_name(self):
        return "main part"
    def movie_suffix(self):
        "what suffix should we use in movie filenames? None means don't permit making them."
        return ""
    pass

class ClipboardItemPart(Part):
    def glpane_text(self):
        #e abbreviate long names...
        return "%s (%s)" % (self.topnode.name, self.location_name())
    def location_name(self):
        "[used in history messages and on glpane]"
        # bruce 050418 change:
        ## return "clipboard item %d" % ( self.clipboard_item_number(), )
        return "on Clipboard" #e might be better to rename that to Shelf, so only the current
            # pastable (someday also in OS clipboard) can be said to be "on the Clipboard"!
    def clipboard_item_number(self):
        "this can be different every time..."
        return self.assy.shelf.members.index(self.topnode) + 1
    def movie_suffix(self):
        "what suffix should we use in movie filenames? None means don't permit making them."
        ###e stub -- not a good choice, since it changes and thus is reused...
        # it might be better to assign serial numbers to each newly made Part that needs one for this purpose...
        # actually I should store part numbers in the file, and assign new ones as 1 + max of existing ones in shelf.
        # then use them in dflt topnode name and in glpane text (unless redundant) and in this movie suffix.
        # but this stub will work for now. Would it be better to just return ""? Not sure. Probably not.
        return "-%d" % ( self.clipboard_item_number(), )
    pass

# end
