# Copyright (c) 2004-2005 Nanorex, Inc.  All rights reserved.

"""
assembly.py -- provides class assembly, for everything stored in one file,
including one main part and zero or more clipboard items; see also part.py.

TEMPORARILY OWNED BY BRUCE 050202 for the Part/assembly split ####@@@@

$Id$

==

About the assembly and Part classes, and their relationship:

[###@@@ warning, 050309: docstring not reviewed recently]

Each assembly has a set of Parts, of which one is always "current"; the current part
is what is displayed in the glpane and operated on by most operations,
and (for now, as of 050222) the assy attributes selmols, selatoms, and molecules
always refer to the same-named attrs of the current Part. (In fact, many other
assy methods and attrs are either delegated to the current Part or have directly
become Part methods or been split into assy and Part methods.)

All selected objects (even atoms) must be in the current part;
the current part is changed by using the model tree to select something
in some other part. The main model is one part, and each clipboard item is another part.
It is not yet possible to form Groups of separate parts in the Clipboard,
but this might be added somehow in the future. For now, any Group in the clipboard
is necessarily a single Part (or inside one); each toplevel member of the clipboard
is exactly one separate Part.

Once several known bugs (like 371) are fixed, then bonds between parts will not be allowed
(since they would be bonds between atoms or jigs in different physical spaces),
and bonds that become "interspace bonds" (due to move or copy operations)
will be automatically broken, or will cause things to be placed into the same space
in order not to break them.

Note that all info in the assy relates either to its named file or to something
about the current mode (in the general sense of that term, not just the current assy.o.mode object);
but the assy's info relating to its named file is not all stored directly in that file --
some of it is stored in other files (such as movie files), and in the future, some of it
might be stored in files referred to from some object within one of its Parts.

==

Both Part and assembly might well be renamed. We don't yet know the best terms
with which to refer to these concepts, or even the exact ideal boundary between them in the code.

==

History: the Part/assembly distinction was introduced by bruce 050222
(though some of its functionality was anticipated by the "current selection group"
introduced earlier, just before Alpha-1). [I also rewrote this entire docstring then.]

The Part/assembly distinction is unfinished, particularly in how it relates to some modes and to movie files.

Prior history unclear; almost certainly originated by Josh.

"""

###@@@ Note: lots of old code below has been commented out for the initial
# assy/part commit, to help clarify what changed in viewcvs,
# but will be removed shortly thereafter.
# Also, several functions will be moved between files after that first commit
# but have been kept in the same place before then for the benefit of viewcvs diff.

from Numeric import *
from VQT import *
from string import *
import re
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from struct import unpack

##bruce 050222 thinks the following are not needed here anymore:
##from drawer import drawsphere, drawcylinder, drawline, drawaxes
##from drawer import segstart, drawsegment, segend, drawwirecube
##from shape import *

from chem import *
from movie import *
from gadgets import *
from Utility import *
from HistoryWidget import greenmsg, redmsg
from platform import fix_plurals

# bruce 050308 adding named constants for selwhat values;
# not yet uniformly used (i.e. most code still uses hardcoded 0 or 2,
#  and does boolean tests on selwhat to see if chunks can be selected);
# not sure if these would be better off as assembly class constants:
# values for assy.selwhat: what to select: 0=atoms, 2 = molecules
SELWHAT_ATOMS = 0
SELWHAT_CHUNKS = 2

from part import Part # this must come after the SELWHAT constants! #e move them into constants.py??


class assembly:

    # default values of instance variables
    ## .part is now computed by __getattr__
##    part = None # the current Part, or None
    
    def __init__(self, win, name = None):

##        self.parts = {} # a dict from node ids to Parts
        
        # ignore changes to this assembly during __init__;
        # this will be set back to 0 at the end of __init__:
        self._modified = 1 
        
        # the MWsemantics displaying this assembly. 
        self.w = win
        # self.mt = win.modelTreeView
        # self.o = win.glpane
        #  ... done in MWsemantics to avoid a circularity
        
        # the name if any
        self.name = name or gensym("Assembly")

        # the Clipboard... this is replaced by another one later (of a different class),
        # once or twice each time a file is opened. ####@@@@ should clean up
        self.shelf = Group("Clipboard", self, None, [])
        self.shelf.open = False

        # the model tree for this assembly
        self.tree = Group(self.name, self, None)

        # a node containing both tree and shelf (also replaced when a file is opened)
        ####@@@@ is this still needed, after assy/part split? not sure why it would be. ###k
        self.root = Group("ROOT", self, None, [self.tree, self.shelf])

        # bruce 050131 for Alpha:
        # For each assembly, maintain one Node or Group which is the
        # "current selection group" (the PartGroup or one of the
        # clipboard items), in which all selection is required to reside.
        #    It might sometimes be an out-of-date node, either a
        # former shelf item or a node from a previously loaded file --
        # not sure if these can happen, but "user beware".
        #    [As of 030510, we store it privately and check it in all uses.]
        #    Sometime after Alpha, we'll show this group in the glpane
        # and let operations (which now look at self.tree or self.molecules)
        # affect it instead of affecting the main model
        # (or having bugs whenever clipboard items are selected, as they
        # often do now).
        # bruce 050228 update: this is still used after assy/part split,
        # but some of the above comment has been done differently,
        # and this needs to be kept in sync with self.part. #doc sometime.
        self.init_current_selgroup() # must be re-called when self.tree is replaced

        # filename if this entire assembly (all parts) was read from a file
        self.filename = ""
        # what to select: 0=atoms, 2 = molecules
        # [bruce 050308 change: new code should use SELWHAT_ATOMS and SELWHAT_CHUNKS
        #  instead of hardcoded constants, and never do boolean tests of selwhat]
        self.selwhat = SELWHAT_CHUNKS

        ####@@@@ set up the Parts
        
        #bruce 050131 for Alpha:
        from Utility import kluge_patch_assy_toplevel_groups
        kluge_patch_assy_toplevel_groups( self)
        self.update_parts() #bruce 050309 for assy/part split
##        self.fix_parts() #bruce 050302 for assy/part split

##        #####@@@@@ make a part, just for testing:
##        self.part = Part(self)

        # 1 if there is a structural difference between assy and file
        self._modified = 0 # note: this was set to 1 at start of __init__
        
        # the current version of the MMP file format
        # this is set in fileIO.writemmp. Mark 050130
        self.mmpformat = ''

        ###@@@ this belongs in Part, most likely, but the menu item maker in movieMode needs it here for now...
        # the Movie object.
        # [bruce 050324 extensively revising movie code for assy/part split and to permit multiple movies]
        ## self.m = Movie(self)
        self.current_movie = Movie(self) #######@@@@@@@ should be None, with new ones to be made as needed

        return # from assembly.__init__

    def init_current_selgroup(self):
        self._last_current_selgroup = self.tree
        return

    def name_autogrouped_nodes_for_clipboard(self, nodes, howmade = ""):
        """Make up a default initial name for an automatically made Group
        whose purpose is to keep some nodes in one clipboard item.
           The nodes in question might be passed, but this is optional
        (but you have to pass None or [] if you don't want to pass them),
        and they might not yet be in the clipboard, might not be the complete set,
        and should not be disturbed by this method in any way.
           A word or phrase describing how the nodes needing this group were made
        can also optionally be passed.
           Someday we might use these args (or anything else, e.g. self.filename)
        to help make up the name.
        """
        return "<Clipboard item>"
    
    # == Parts
    
##    def fix_parts(self): #####@@@@@ still needs: answer docstring Qs; implem Part.destroy()
##        #bruce 050302... this is pretty confused, and probably fundamentally wrongheaded. Even when to call it is unclear.
##        """[private]
##        After init or after a file is read (which replaces self.tree and self.shelf with new Groups),
##        and after the caller has given those toplevel Groups the right subclasses
##        (using kluge_patch_assy_toplevel_groups, or the equivalent),
##        fix up the node -> Part mapping, and destroy any no-longer-used Parts.
##            Also, if some new clipboard items have been created, make new Parts for each one.
##        [Not clear whether, in that case, we'll also break interspace bonds.
##        Not clear whether this func (or some code from it) gets involved when
##        nodes are moved or copied between Parts.]
##        """
##        oldparts = self.parts # a dict from node-ids to Parts
##        self.parts = newparts = {}
##        for node in [self.tree] + self.shelf.members:
##            # for each node which should have its own Part, use old part or make a new one #####@@@@@ use correct Part subclass
##            #####@@@@@ ###e is it right to key them on node, not on position in this assy? what about movie filename persistence?
##            # The answer might be different for main part vs others. Guess: main Part should change only when filename does....
##            key = node_id(node)
##            try:
##                part = oldparts.pop(key)
##            except KeyError:
##                from part import MainPart, ClipboardItemPart
##                partclass = (node == self.tree) and MainPart or ClipboardItemPart
##                part = partclass(self, node)
##            assert part
##            assert isinstance(part, Part)
##            newparts[key] = part
##        for oldpart in oldparts.values():
##            oldpart.destroy() ###e is this ok? someday worry about whether some other assy might use it, or whatever...
##                #####@@@@@ also - is it supposed to destroy the nodes in that part, too? in theory this is bad... removing cycles might be good...
##                # what we need to destroy is the topnodes... if we can tell nodes have no dad, we might want to remove...
##                # one problem is that assy.data, tree, shelf are trashed (in fileIO), maybe need destroying instead.
##                # Not only that -- maybe those need to turn into official "part slots" or so! ie slots for nodes which make
##                # a Part for whatever topnode they hold, making a new one when that node is reset.
##                # To think about this, think about what kind of node clipboard is, when dropped on....
##                # alternatively: maybe every node *either* gets fed a part to be in from its dad, *or* has to make its own.
##                # we continuously update this, but when it's wrong, store the node in that move-tracker object i started writing...
##                # then at the end, fix all those objects. Maybe this helps with assy init and file read, too. and insertmmp.
##                # [050302 eve comment]
##        return

    def update_parts(self):
        """For every node in this assy, make sure it's in the correct Part,
        creating new parts if necessary. [See also checkparts method.] 
        For now [050308], also break inter-Part bonds; later this might be done separately.
        """
        ###@@@ revise the following comment, it's just notes during development:
        # this is a simple brute-force scan, which might be good enough, and if so might be the simplest method that could work.
        # so if it works and seems ok to use whenever nodes change parts, then take care of entirely new nodes somehow (mol init),
        # and then just call this whenever needed... and it should be ok to add nodes to parts in addmember, when they're new
        # (and when dad has a part); and to do this to kids when groups with no parts are added to nodes with parts.
        # So only for a node-move must we worry and do it later... or so it seems, 050308 806pm.
        from part import MainPart, ClipboardItemPart
        self.ensure_one_part(self.tree, MainPart)
        for node in self.shelf.members:
            self.ensure_one_part(node, ClipboardItemPart)
        # now all nodes have correct parts, so it's safe to break inter-part bonds.
        # in the future we're likely to do this separately for efficiency (only on nodes that might need it).
        for node in [self.tree] + self.shelf.members:
            node.part.break_interpart_bonds()
        # now make sure current_selgroup() runs without errors, and also make sure
        # its side effects (from fixing an out of date selgroup, notifying observers
        # of any changes (e.g. glpane)) happen now rather than later.
        sg = self.current_selgroup()
        # and make sure selgroup_part finds a part from it, too
        assert self.selgroup_part(sg)
        return
    
    def ensure_one_part(self, node, partclass):
        """Ensure node is the top node of its own Part, and all its kids are in that Part.
        If node's part is None or not owned by node (ie node is not its topnode),
        give node its own new Part of the given class. (Class is not used if node already owns its Part.)
        If kids are not in node's part, add them.
        [But don't try to break inter-Part bonds, since when this is run,
         some nodes might still be in the wrong Part, e.g. when several nodes
         will be moved from one part to another.]
        """
        if node.part and node != node.part.topnode:
            # this happens, e.g., when moving a Group to the clipboard, and it becomes a new clipboard item
            node.part.remove(node) # node's kids will be removed below
            assert not node.part
        if not node.part:
            part1 = partclass(self, node)
            assert node.part == part1
            assert node == node.part.topnode
        # now make sure all node's kids (recursively) are in node.part
        addmethod = node.part.add
        node.apply2all( addmethod ) # noop for nodes already in part;
            # also auto-removes nodes from their old part, if any;
            # also destroys emptied parts.
        return

    # == Part-related debugging functions

    def checkparts(self):
        "make sure each selgroup has its own Part, and all is correct about them"
        # presumably this is only called when platform.atom_debug, but that's up to the caller
        for node in [self.tree] + self.shelf.members:
            ## print "checking part-related stuff about node:" ,node
            #e print the above in an except clause, so on asfail we'd see it...
            try:
                assert node.is_top_of_selection_group() ##e rename node.is_selection_group()??
                assert node.part.topnode == node # this also verifies each node has a different part
                kids = []
                node.apply2all( kids.append ) # includes node itself
                for kid in kids:
                    assert kid.part == node.part
                assert node.part.nodecount == len(kids), "node.part.nodecount %d != len(kids) %d" % (node.part.nodecount, len(kids))
            except:
                print "exception while checking part-related stuff about node:", node
                raise
        return

    # ==

    def draw(self, win): ###@@@ win arg, unused in submethod, should be renamed or removed
        if platform.atom_debug:
            self.checkparts()
            # if that raises an exception, don't catch it, drawing might not work
        if self.part: #k condition needed??
            self.part.draw(win)
        return
    
    # == current selection group (see it and/or change it)

    def current_selgroup_iff_valid(self):
        """If the current selection group, as stored (with no fixing!),
        is valid in all ways we can think of checking
        (except any ways related to Parts, which are not examined here),
        return it, otherwise return None (not an error).
        Never has side effects.
        """
        sg = self._last_current_selgroup
        if not self.valid_selgroup( sg):
            return None
        return sg

    def valid_selgroup(self, sg):
        """If the GIVEN (not current) selection group (with no fixing!)
        is valid in all ways we can think of checking
        (except ways related to its .part, which is not examined -- see selgroup_part for that)
        as a candidate for being or becoming our current selection group,
        then return True, otherwise False (not an error).
        Never has side effects.
        """
        if not sg: return False
        if sg.assy != self: return False
        if not sg.is_top_of_selection_group():
            return False
        if not self.root.is_ascendant(sg):
            return False # can this ever happen??
        # I think we won't check the Part, even though it could, in theory,
        # be present but wrong (in the sense that sg.part.topnode != sg),
        # since that way, this method can be independent of Parts,
        # and since is_top_of_selection_group should have been enough
        # for what this method is used for. Logically, we use this to see
        # the selgroup structure, but consider it lower-level than where we
        # know that each selgroup wants its own Part (and maintain that).
        return True

    def current_selgroup(self):
        """If the current selection group is valid as stored, return it.
        If not, try to fix it, choosing a new one which includes the stored one if possible
        (this situation might be normal after a DND move of a whole clipboard item
         into the inside of some other Part),
        or the main part (self.tree) if not (this might happen if some code deletes nodes
        without changing the selection group).
           Like current_selgroup_iff_valid(), ignore its Part; see selgroup_part for that.
        Also, new Parts are never made (or old Parts revised) in this method.
           If the current selgroup is changed, the new one is both returned and stored.
        """
        sg = self.current_selgroup_iff_valid()
        if sg:
            return sg
        # now we're a bit redundant with that method (this seems necessary);
        # also, at this point we're almost certain to debug print and/or
        # to change self._last_current_selgroup (via self.set_current_selgroup ###k).
        sg = self._last_current_selgroup
        # since that guy was invalid, we'll definitely forget about it now
        # except for its use below as 'sg' (in this run of this method).
        self._last_current_selgroup = None # hopefully to be revised below
        if sg and sg.assy == self and self.root.is_ascendant(sg):
            assert not sg.is_top_of_selection_group() # the only remaining way it could have been wrong
            # this is the one case where we use the invalid _last_current_selgroup in deciding on the new one.
            newsg = sg.find_selection_group() # might be None
            if not newsg:
                newsg = self.tree
        else:
            newsg = self.tree
        # now newsg is the one we'll *try* to change to and return, if *it* is valid.
        # (if it is not None but not valid, that's probably a bug, and we won't change to it;
        #  ideally we'd change to self.tree then, but since it's probably a bug we won't bother.)
        if not newsg:
            #k probably can't happen unless self.tree is None, which I hope never happens here
            if platform.atom_debug:
                print_compact_stack("atom_debug: cur selgroup None, no tree(?), should never happen: ")
            # we already stored None, and it's not good to call current_selgroup_changed now (I think) ##k
            return None
        # Note: set_current_selgroup looks at prior self._last_current_selgroup,
        # so the fact that we set that to None (above) is important.
        # Also, what if newsg == sg (should never happen here)?
        # Then it won't be valid (else we'd have returned at top of this method)
        # and we'll see debug prints in set_current_selgroup.
        self.set_current_selgroup( newsg) # this stores it and notifies observers if any (eg updates glpane)
        return self._last_current_selgroup # (this will be same as newsg, or debug prints already occurred)

    def selgroup_part(self, sg):
        """Given a valid selgroup sg (or None), check that it's its .part's topnode,
        and if so return its .part, and if not return None after emitting debug prints
        (which always indicates a bug, I'm 90% sure as I write it -- except maybe during init ###k #doc).
        """
        if not sg or not sg.part or not sg.part.topnode == sg:
            #doc: ... assy.tree.part being None.
            # (which might happen during init, and trying to make a part for it might infrecur or otherwise be bad.)
            # so if following debug print gets printed, we might extend it to check whether that "good excuse" is the case.
            if 0 and platform.atom_debug:
                print_compact_stack("atom_debug: fyi: selgroup.part problem during: ")
            if 1:
                # for now, always raise an exception #####@@@@@
                assert sg
                assert sg.part
                assert sg.part.topnode
                assert sg.part.topnode == sg, "part %r topnode is %r should be %r" % (sg.part, sg.part.topnode, sg)
            return None
        return sg.part
    
    # == changing the current selection group

    ##e move this lower down?
    def fyi_part_topnode_changed(self, old_top, new_top):
        """[private method for a single caller in Part]
        Some Part tells us that its topnode changed from old_top to new_top.
        If our current selgroup happened to be old_top, make it now be new_top,
        but don't emit a history message about this change.
        [#e: not sure if we should do any unpicking or updating, in general;
         current caller doesn't need or want any.]
        """
        if self._last_current_selgroup == old_top:
            self._last_current_selgroup = new_top
            # no need (in fact, it would be bad) to call current_selgroup_changed, AFAIK
            # (does this suggest that "current part" concept ought to be more
            #  primitive than "current selgroup" concept??)
        # now the Part situation should be ok, no need for assy.update_parts
        return

    def set_current_selgroup(self, node): #bruce 050131 for Alpha; heavily revised 050315; might need options wrt history msg, etc
        "Set our current selection group to node, which should be a valid one. [public method; no retval]"
        assert node
        prior = self.current_selgroup_iff_valid() # don't call current_selgroup itself here --
            # it might try to "fix an out of date current selgroup"
            # and end up unpicking the node being passed to us.
        if node == prior:
            return # might be redundant with some callers, that's ok [#e simplify them?]
        if not prior and self._last_current_selgroup:
            prior = 0 # tell submethod that we don't know the true prior one
        if not self.valid_selgroup(node):
            # probably a bug in the caller. Complain, and don't change current selgroup.
            if platform.atom_debug:
                print_compact_stack("atom_debug: bug: invalid selgroup %r not being used" % (node,))
            #e if this never happens, change it to raise an exception (ie just be an assert) ###@@@
            return
        #####@@@@@ now inline the rest
        # ok to set it and report that it changed.
        self._last_current_selgroup = node
        self.current_selgroup_changed(prior = prior) # as of 050315 this is the only call of that method
        return
    
    def current_selgroup_changed(self, prior = 0): #bruce 050131 for Alpha
        "#doc; caller has already stored new valid one; prior == 0 means unknown -- caller might pass None"
        #e in future (post-Alpha) this might revise self.molecules, what to show in glpane, etc
        # for now, make sure nothing outside it is picked!
        # This is the only place where that unpicking from changing selgroup is implemented. ###@@@ verify that claim

        sg = self._last_current_selgroup

        # unpick everything in a different selgroup (but save the message about this for last)
        didany = self.root.unpick_all_except( sg )

        # notify observers of changes to our current selgroup (after the side effect of the unpick!)
        try:
            self.o.gl_update()
        except:
            print_compact_traceback("too early for self.o.gl_update? ") ######@@@@@@
        
        # print a history message about a new current Part, if possible #####@@@@@ not when initing to self.tree!
        try:
            # during init, perhaps lots of things could go wrong with this, so catch them all
            msg = "showing %r (%s)" % (sg.part.topnode.name, sg.part.location_name())
                # AttributeError: 'NoneType' object has no attribute 'topnode' ######@@@@@@
            ## this was too frequent to leave them all in, when clicking around the clipboard:
            ## self.w.history.message( greenmsg( msg)) ###e need option for this?
            self.w.history.message( msg, transient_id = "current_selgroup_changed")
        except:
            if platform.atom_debug:
                print_compact_traceback("atom_debug: bug?? or just init?: can't print changed-part msg: ")
            pass

        # emit a message about what we unpicked, if anything
        if didany:
            try: # precaution against new bugs in this alpha-bug-mitigation code
                # what did we deselect?
                if prior and not isinstance(prior, Group):
                    what = node_name(prior)
                elif prior:
                    what = "some items in " + node_name(prior)
                else:
                    what = "some items"
                ## why = "since selection should not involve more than one clipboard item or part at a time" #e wording??
                why = "to limit selection to one clipboard item or the part" #e wording??
                    #e could make this more specific depending on which selection groups were involved
                msg = "Warning: deselected %s, %s" % (what, why)
            except:
                if platform.atom_debug:
                    raise 
                msg = "Warning: deselected some previously selected items"
            try:
                self.w.history.message( redmsg( msg))
            except:
                pass # too early? (can this happen?)

        return # from current_selgroup_changed

##    def is_nonstd_selection_group(self, node):
##        return node and node != self.tree

    # == general attribute code
    
    # attrnames to delegate to the current part
    # (ideally for writing as well as reading, until all using-code is upgraded) ###@@@ use __setattr__ ?? etc??
    part_attrs = ['molecules','selmols','selatoms']
    ##part_methods = ['selectAll','selectNone','selectInvert']###etc... the callable attrs of part class??
    part_methods = filter( lambda attr:
                             not attr.startswith('_')
                             and callable(getattr(Part,attr)), # note: this tries to get self.part before it's ready...
                          dir(Part) ) #approximation!
##    if platform.atom_debug:
##        print "part_methods = %r" % (part_methods,)
##        print "dir(Part) = ",dir(Part)
    #####@@@@@ for both of the following:
    part_attrs_temporary = ['bbox','center','drawLevel'] # temp because caller should say assy.part or be inside self.part
    part_attrs_review = ['alist','ppa2','ppa3','temperature','waals','data','homeCsys','lastCsys','xy','yz','zx']
        #e in future, we'll split out our own methods for some of these, incl .changed
        #e and for others we'll edit our own methods' code to not call them on self but on self.assy (incl selwhat)
    part_attrs_all = part_attrs + part_attrs_temporary + part_attrs_review
    
    def __getattr__(self, attr):
        if attr.startswith('_'): # common case, be fast
            raise AttributeError, attr
        elif attr == 'part':
##            try:
                sg = self.current_selgroup() # this fixes it if possible; should always be a node but maybe with no Part during init
                ## return self.parts[node_id(sg)]
                if 1:
                    # open all containing nodes below assy.root (i.e. the clipboard, if we're a clipboard item)
                    containing_node = sg.dad
                    while containing_node and containing_node != self.root:
                        containing_node.open = True
                        containing_node = containing_node.dad
                part = self.selgroup_part(sg)
                if not part:
                    #e [this IS REDUNDANT with debug prints inside selgroup_part] [which for debugging are now asserts #####@@@@@]
                    # no point in trying to fix it -- if that was possible, current_selgroup() did it.
                    # if it has no bugs, the only problem it couldn't fix would be assy.tree.part being None.
                    # (which might happen during init, and trying to make a part for it might infrecur or otherwise be bad.)
                    # so if following debug print gets printed, we might extend it to check whether that "good excuse" is the case.
                    if platform.atom_debug:
                        print_compact_stack("atom_debug: fyi: assy.part getattr finds selgroup problem: ")
                    return None
                return part
##            except:
##                # as of 050315 this seems unlikely, and its fallback is also redundant with current_selgroup()'s fallback; remove?? #e
##                print_compact_traceback("bug: exception getting assy.part; switching to main part (might worsen the bug): ")
##                self.set_current_selgroup(self.tree)
##                return self.tree.part
        elif attr in self.part_attrs_all:
            # delegate to self.part
            try:
                part = self.part
            except:
                print "fyi: following exception getting self.part happened just before we looked for its attr %r" % (attr,)
                raise
            try:
                return getattr(part, attr) ###@@@ detect error of infrecur, since part getattr delegates to here??
            except:
                print "fyi: following exception in assy.part.attr was for attr = %r" % (attr,)
                raise
        elif attr in self.part_methods:
            # attr is a method-name for a method we should delegate to our current part.
            # it's not enough to return the current self.part's bound method...
            # we need to create and return a fake bound method of our own
            # which, when called in the future, will delegate to our .part *at that time* --
            # in case it is not called immediately, but stored away (e.g. as a menu item's callable)
            # and used later when our current part might have changed.
            def deleg(*args,**kws):
                meth = getattr(self.part, attr)
                return meth(*args,**kws)
            return deleg
        ###@@@ obs after this??
        try:
            #e learn how to extend part_methods, or the set of methods to split
            meth = getattr(self.part, attr)
            if callable(meth):
                # guess it's a method we should delegate
                print "assy delegating to part method -- bug, need to extend part_methods:",attr
                return meth
            # else fall thru
        except AttributeError:
            raise AttributeError, attr
        raise AttributeError, attr

    # == change-tracking
    
    def has_changed(self): # bruce 050107
        """Report whether this assembly (or something it contains)
        has been changed since it was last saved or loaded from a file.
        See self.changed() docstring and comments for more info.
        Don't use or set self._modified directly!
           #e We might also make this method query the current mode
        to see if it has changes which ought to be put into this assembly
        before it's saved.
        """
        return self._modified
    
    def changed(self): # bruce 050107
        """Record the fact that this assembly (or something it contains)
        has been changed, in the sense that saving it into a file would
        produce meaningfully different file contents than if that had been
        done before the change.
           Note that some state changes (such as selecting chunks or atoms)
        affect some observers (like the glpane or model tree), but not what
        would be saved into a file; such changes should *not* cause calls to
        this method (though in the future there might be other methods for
        them to call, e.g. perhaps self.changed_selection() #e).
           [Note: as of 050107, it's unlikely that this is called everywhere
        it needs to be. It's called in exactly the same places where the
        prior code set self.modified = 1. In the future, this will be called
        from lower-level methods than it is now, making complete coverage
        easier. #e]
        """
        # bruce 050107 added this method; as of now, all method names (in all
        # classes) of the form 'changed' or 'changed_xxx' (for any xxx) are
        # hereby reserved for this purpose! [For beta, I plan to put in a
        # uniform system for efficiently recording and propogating change-
        # notices of that kind, as part of implementing Undo (among other uses).]
        if not self._modified:
            self._modified = 1
            # Feel free to add more side effects here, inside this 'if'
            # statement, even if they are slow! They will only run the first
            # time you modify this assembly, since its _modified flag was most
            # recently reset [i.e. since it was saved].
            # [For Beta, they might run more often (once per undoable user-
            #  event), so we'll review them for speed at that time. For now,
            #  only saving this assembly to file (or loading or clearing it)
            #  is permitted to reset this flag to 0.]
            
            self.w.history.message("(fyi: part now has unsaved changes)") #e revise terminology?

            ## [bruce 050324 commenting out movieID until it's used; strategy for this will change, anyway.]
##            # Regenerate the movie ID.
##            # This will probably not make Alpha.  It is intended to be used in the future
##            # as a way to validate movie files.  assy.movieID is handed off to the simulator
##            # as an argument (-b) where it writes the number in the movie (.dpb) file header.
##            # (see writemovie() in fileIO.py.) [writemovie is now in runSim.py, and might be renamed -- bruce 050325]
##            # The number is then compared to assy.movieID when the movie file is opened
##            # at a later time. This check will be done in movie._checkMovieFile().
##            # Mark - 050116
##            import random
##            self.movieID = random.randint(0,4000000000) # 4B is good enough
            
            pass
        # If you think you need to add a side-effect *here* (which runs every
        # time this method is called, not just the first time after each save),
        # that would probably be too slow -- we'll need to figure out a different
        # way to get the same effect (like recording a "modtime" or "event counter").
        return

    def reset_changed(self): # bruce 050107
        """[private method] #doc this... see self.changed() docstring.
        """
        self._modified = 0

# bruce 050201: this is not currently used. If confirmed, zap it in a few days.
##    def selectingWhat(self):
##        """return 'Atoms' or 'Molecules' to indicate what is currently
##        being selected [by bruce 040927; might change]
##        """
##        # bruce 040927: this seems to be wrong sometimes,
##        # e.g. when no atoms or molecules exist in the assembly... not sure.
##        return {0: "Atoms", 2: "Molecules"}[self.selwhat]

    # ==
    
    ## bruce 050308 disabling checkpicked for assy/part split; they should be per-part
    ## and they fix errors in the wrong direction (.picked is more fundamental)
    def checkpicked(self, always_print = 0):
        if always_print: print "fyi: checkpicked() is disabled until assy/part split is completed"
        return
    
##    def checkpicked(self, always_print = 0):
##        """check whether every atom and molecule has its .picked attribute
##        set correctly. Fix errors, too. [bruce 040929]
##        Note that this only checks molecules in assy.tree, not assy.shelf,
##        since self.molecules only includes those. [bruce 050201 comment]
##        """
##        if always_print: print "fyi: checkpicked()..."
##        self.checkpicked_atoms(always_print = 0)
##        self.checkpicked_mols(always_print = 0)
##        # maybe do in order depending on selwhat, right one first?? probably doesn't matter.
##        #e we ought to call this really often and see when it prints something,
##        # so we know what causes the selection bugs i keep hitting.
##        # for now see menu1 in select mode (if i committed my debug hacks in there)
##        
##    def checkpicked_mols(self, always_print = 1):
##        "checkpicked, just for molecules [bruce 040929]"
##        if always_print: print "fyi: checkpicked_mols()..."
##        for mol in self.molecules:
##            wantpicked = (mol in self.selmols)
##            if mol.picked != wantpicked:
##                print "mol %r.picked was %r, should be %r (fixing)" % (mol, mol.picked, wantpicked)
##                mol.picked = wantpicked
##        return
##
##    def checkpicked_atoms(self, always_print = 1):
##        "checkpicked, just for atoms [bruce 040929]"
##        if always_print: print "fyi: checkpicked_atoms()..."
##        lastmol = None
##        for mol in self.molecules:
##            for atom in mol.atoms.values(): ##k
##                wantpicked = (atom.key in self.selatoms) ##k
##                if atom.picked != wantpicked:
##                    if mol != lastmol:
##                        lastmol = mol
##                        print "in mol %r:" % mol
##                    print "atom %r.picked was %r, should be %r (fixing)" % (atom, atom.picked, wantpicked)
##                    atom.picked = wantpicked
##        return

    #####@@@@@ newly made up 050225
    
##    def update_mols(self):
##        "call update_mols on all our parts"
##        #####@@@@@stub
##        for part in self.parts.values():
##            part.update_mols()
##        return

    # ==

##    def unselect_clipboard_items(self): #bruce 050131 for Alpha
##        "to be called before operations which are likely to fail when any clipboard items are selected"
##        self.set_current_selgroup( self.tree)

    def __str__(self):
        return "<Assembly of " + self.filename + ">"

    pass # end of class assembly

# end
