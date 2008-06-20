# Copyright 2008 Nanorex, Inc.  See LICENSE file for details. 
"""
DnaDisplayStyle_PropertyManager.py

 The DnaDisplayStyle_PropertyManager class provides a Property Manager 
 for the B{Display Style} command on the flyout toolbar in the 
 Build > Dna mode. 

@author: Mark
@version: $Id: DnaDisplayStyle_PropertyManager.py 13151 2008-06-09 17:26:26Z marksims $
@copyright: 2008 Nanorex, Inc. See LICENSE file for details.

To do:
- Add "Display Base Orientation Indicators" groupbox and remove from 
the Preferences dialog.
- Add "Base Colors" pref keys/values.
"""
import os, time, fnmatch, string
import foundation.env as env

from widgets.DebugMenuMixin import DebugMenuMixin
from widgets.prefs_widgets import connect_checkbox_with_boolean_pref

from utilities.prefs_constants import getDefaultWorkingDirectory
from utilities.Log import greenmsg
from utilities.constants import white, gray, orange, red, green, blue, black, cyan

from PyQt4.Qt import SIGNAL
from PyQt4.Qt import Qt
from PyQt4 import QtGui
from PyQt4.Qt import QFileDialog, QString, QMessageBox
from PM.PM_Dialog   import PM_Dialog
from PM.PM_GroupBox import PM_GroupBox
from PM.PM_ComboBox import PM_ComboBox
from PM.PM_ColorChooser import PM_ColorChooser
from PM.PM_StackedWidget import PM_StackedWidget
from PM.PM_CheckBox import PM_CheckBox
from PM.PM_DoubleSpinBox import PM_DoubleSpinBox
from PM.PM_ToolButtonRow import PM_ToolButtonRow

from PM.PM_Constants     import PM_DONE_BUTTON
from PM.PM_Constants     import PM_WHATS_THIS_BUTTON

from utilities.constants import diDNACYLINDER

from utilities.prefs_constants import dnaRendition_prefs_key

from utilities.prefs_constants import dnaStyleAxisShape_prefs_key
from utilities.prefs_constants import dnaStyleAxisColor_prefs_key
from utilities.prefs_constants import dnaStyleAxisScale_prefs_key
from utilities.prefs_constants import dnaStyleAxisEndingStyle_prefs_key

from utilities.prefs_constants import dnaStyleStrandsShape_prefs_key
from utilities.prefs_constants import dnaStyleStrandsColor_prefs_key
from utilities.prefs_constants import dnaStyleStrandsScale_prefs_key
from utilities.prefs_constants import dnaStyleStrandsArrows_prefs_key

from utilities.prefs_constants import dnaStyleStrutsShape_prefs_key
from utilities.prefs_constants import dnaStyleStrutsColor_prefs_key
from utilities.prefs_constants import dnaStyleStrutsScale_prefs_key

from utilities.prefs_constants import dnaStyleBasesShape_prefs_key
from utilities.prefs_constants import dnaStyleBasesColor_prefs_key
from utilities.prefs_constants import dnaStyleBasesScale_prefs_key
from utilities.prefs_constants import dnaStyleBasesDisplayLetters_prefs_key

from utilities.prefs_constants import dnaStrandLabelsEnabled_prefs_key
from utilities.prefs_constants import dnaStrandLabelsColorMode_prefs_key

dnaDisplayStylePrefsList = \
                         [dnaRendition_prefs_key,
                          dnaStyleAxisShape_prefs_key, 
                          dnaStyleAxisScale_prefs_key,
                          dnaStyleAxisColor_prefs_key,
                          dnaStyleAxisEndingStyle_prefs_key,
                          
                          dnaStyleStrandsShape_prefs_key,
                          dnaStyleStrandsScale_prefs_key,
                          dnaStyleStrandsColor_prefs_key,
                          dnaStyleStrandsArrows_prefs_key,
                          
                          dnaStyleStrutsShape_prefs_key,
                          dnaStyleStrutsScale_prefs_key,
                          dnaStyleStrutsColor_prefs_key,
                          
                          dnaStyleBasesShape_prefs_key,
                          dnaStyleBasesScale_prefs_key,
                          dnaStyleBasesColor_prefs_key,
                          dnaStyleBasesDisplayLetters_prefs_key,
                          
                          dnaStrandLabelsEnabled_prefs_key,
                          dnaStrandLabelsColorMode_prefs_key]

# =
# DNA Display Style Favorite File I/O functions. Talk to Bruce about splitting
# these into a separate file and putting them elsewhere. Mark 2008-05-15.

def writeDnaDisplayStyleSettingsToFavoritesFile( basename ):
    """
    Writes a "favorite file" (with a .txt extension) to store all the 
    DNA display style settings (pref keys and their current values).
            
    @param basename: The filename (without the .fav extension) to write.
    @type  basename: string
            
    @note: The favorite file is written to the directory
            $HOME/Nanorex/Favorites/DnaDisplayStyle.
    """
            
    if not basename:
        return 0, "No name given."
            
    # Get filename and write the favorite file.
    favfilepath = getFavoritePathFromBasename(basename)
    writeDnaFavoriteFile(favfilepath)            
            
    # msg = "Problem writing file [%s]" % favfilepath

    return 1, basename


def getFavoritePathFromBasename( basename ):
    """
    Returns the full path to the favorite file given a basename.
    
    @param basename: The favorite filename (without the .txt extension).
    @type  basename: string
    
    @note: The (default) directory for all favorite files is
           $HOME/Nanorex/Favorites/DnaDisplayStyle.
    """
    _ext = "txt"
    
    # Make favorite filename (i.e. ~/Nanorex/Favorites/DnaDisplayStyleFavorites/basename.txt)
    from platform.PlatformDependent import find_or_make_Nanorex_subdir
    _dir = find_or_make_Nanorex_subdir('Favorites/DnaDisplayStyle')
    return os.path.join(_dir, "%s.%s" % (basename, _ext))

def writeDnaFavoriteFile( filename ):
    """
    Writes a favorite file to I{filename}.
    """
    
    f = open(filename, 'w')
        
    # Write header
    f.write ('!\n! DNA display style favorite file')
    f.write ('\n!Created by NanoEngineer-1 on ')
    timestr = "%s\n!\n" % time.strftime("%Y-%m-%d at %H:%M:%S")
    f.write(timestr)
    
    #write preference list in file without the NE version 
    for pref_key in dnaDisplayStylePrefsList:
        val = env.prefs[pref_key]
        
        pref_keyArray = pref_key.split("/")
        pref_key = pref_keyArray[1]
        
        if isinstance(val, int):
            f.write("%s = %d\n" % (pref_key, val))
        elif isinstance(val, float):
            f.write("%s = %-6.2f\n" % (pref_key, val))
        elif isinstance(val, bool):
            f.write("%s = %d\n" % (pref_key, val))
        else:
            print "Not sure what pref_key '%s' is." % pref_key
        
    f.close()

    
def loadFavoriteFile( filename ):
    """
    Loads a favorite file from anywhere in the disk.
    
    @param filename: The full path for the favorite file.
    @type  filename: string
    
    """
    
    if os.path.exists(filename):
        favoriteFile = open(filename, 'r')
    else:
        env.history.message("Favorite file to be loaded does not exist.")
        return 0
     
    # do syntax checking on the file to figure out whether this is a valid
    # favorite file
    
    
    line = favoriteFile.readline()
    line = favoriteFile.readline()
    
    if line != "! DNA display style favorite file\n":
        env.history.message(" Not a proper favorite file")
        favoriteFile.close()
        return 0
    
    while 1:
        line = favoriteFile.readline()
        
        # marks the end of file
        if line == "":
            break
        
        
        # process each line to obtain pref_keys and their corresponding values
        if line[0] != '!':
        
            keyValuePair = line.split('=')
            pref_keyString = keyValuePair[0].strip()
            pref_value=keyValuePair[1].strip()
        
            # check if pref_value is an integer or float. Booleans currently 
            # stored as integer as well.
        
            try: 
                int(pref_value)
                pref_valueToStore = int(pref_value)
                
            except ValueError:
                pref_valueToStore = float(pref_value)
            
        
            # match pref_keyString with its corresponding variable name in the 
            # preference key list
        
            pref_key = findPrefKey( pref_keyString )
        
            #add preference key and its corresponding value to the dictionary
        
            if pref_key:
                env.prefs[pref_key] = pref_valueToStore
             
     
               
    favoriteFile.close()
    
    #check if a copy of this file exists in the favorites directory. If not make
    # a copy of it in there
    
    
    favName = os.path.basename(str(filename))
    name = favName[0:len(favName)-4]
    favfilepath = getFavoritePathFromBasename(name)
    
    if not os.path.exists(favfilepath):
        saveFavoriteFile(favfilepath, filename)
    
    return 1
      
    
def findPrefKey( pref_keyString ):
    """
    Matches prefence key in the dnaDisplayStylePrefsList with pref_keyString
    from the favorte file that we intend to load. 

    
    @param pref_keyString: preference from the favorite file to be loaded.
    @type  pref_keyString: string
    
    @note: very inefficient since worst case time taken is proportional to the 
    size of the list. If original preference strings are in a dictionary, access
    can be done in constant time
    
    """
    
    for keys in dnaDisplayStylePrefsList:
        #split keys in dnaDisplayStylePrefList into version number and pref_key
        
        pref_array= keys.split("/")
        if pref_array[1] == pref_keyString:
            return keys
        
    return None
    
def saveFavoriteFile( savePath, fromPath ):
    
    """
    Save favorite file to anywhere in the disk

    
    @param savePath: full path for the location where the favorite file is to be saved.
    @type  savePath: string
    
    @param savePath: ~/Nanorex/Favorites/DnaDisplayStyle/$FAV_NAME.txt
    @type  fromPath: string
    
    """
    if savePath:
        saveFile = open(savePath, 'w')
    if fromPath:
        fromFile = open(fromPath, 'r')
        
    lines=fromFile.readlines()   
    saveFile.writelines(lines)
        
    saveFile.close()
    fromFile.close()
    
    return    

# =

class DnaDisplayStyle_PropertyManager( PM_Dialog, DebugMenuMixin ):
    """
    The DnaDisplayStyle_PropertyManager class provides a Property Manager 
    for the B{Display Style} command on the flyout toolbar in the 
    Build > Dna mode. 

    @ivar title: The title that appears in the property manager header.
    @type title: str

    @ivar pmName: The name of this property manager. This is used to set
                  the name of the PM_Dialog object via setObjectName().
    @type name: str

    @ivar iconPath: The relative path to the PNG file that contains a
                    22 x 22 icon image that appears in the PM header.
    @type iconPath: str
    """

    title         =  "Edit Protein Display Style"
    pmName        =  title
    iconPath      =  "ui/actions/Command Toolbar/Dna_Display_Style.png"
    
    
    def __init__( self, parentCommand ):
        """
        Constructor for the property manager.
        """

        self.parentMode = parentCommand
        self.w = self.parentMode.w
        self.win = self.parentMode.w
        self.pw = self.parentMode.pw        
        self.o = self.win.glpane                 
                    
        PM_Dialog.__init__(self, self.pmName, self.iconPath, self.title)
        
        DebugMenuMixin._init1( self )

        self.showTopRowButtons( PM_DONE_BUTTON | \
                                PM_WHATS_THIS_BUTTON)
        
        msg = "Modify the protein display settings below."
        self.updateMessage(msg)
    
    def connect_or_disconnect_signals(self, isConnect):
        """
        Connect or disconnect widget signals sent to their slot methods.
        This can be overridden in subclasses. By default it does nothing.
        @param isConnect: If True the widget will send the signals to the slot 
                          method. 
        @type  isConnect: boolean
        """
        
        
    def ok_btn_clicked(self):
        """
        Slot for the OK button
        """      
        self.win.toolsDone()
    
    def cancel_btn_clicked(self):
        """
        Slot for the Cancel button.
        """  
        #TODO: Cancel button needs to be removed. See comment at the top
        self.win.toolsDone()
        
    def show(self):
        """
        Shows the Property Manager. Overrides PM_Dialog.show.
        """
        PM_Dialog.show(self)
        
        # Force the Global Display Style to "DNA Cylinder" so the user
        # can see the display style setting effects on any DNA in the current
        # model. The current global display style will be restored when leaving
        # this command (via self.close()).
        self.originalDisplayStyle = self.o.getGlobalDisplayStyle()
        self.o.setGlobalDisplayStyle(diDNACYLINDER)
        
        # Update all PM widgets, then establish their signal-slot connections.
        # note: It is important to update the widgets *first* since doing
        # it in the reverse order will generate signals when updating
        # the PM widgets (via updateDnaDisplayStyleWidgets()), causing
        # unneccessary repaints of the model view.
        self.updateDnaDisplayStyleWidgets()
        self.connect_or_disconnect_signals(isConnect = True)

    def close(self):
        """
        Closes the Property Manager. Overrides PM_Dialog.close.
        """
        self.connect_or_disconnect_signals(False)
        PM_Dialog.close(self)
        
        # Restore the original global display style.
        self.o.setGlobalDisplayStyle(self.originalDisplayStyle)
    
    def _addGroupBoxes( self ):
        """
        Add the Property Manager group boxes.
        """
        self._pmGroupBox1 = PM_GroupBox( self, 
                                         title = "Favorites")
        self._loadGroupBox1( self._pmGroupBox1 )
        
        self._pmGroupBox2 = PM_GroupBox( self, 
                                         title = "Display")
        self._loadGroupBox2( self._pmGroupBox2 )
        
        self._pmGroupBox3 = PM_GroupBox( self, 
                                         title = "Color")
        self._loadGroupBox3( self._pmGroupBox3 )
        
    def _loadGroupBox1(self, pmGroupBox):
        """
        Load widgets in group box.
        """
        # Other info
        # Not only loads the factory default settings but also all the favorite
        # files stored in the ~/Nanorex/Favorites/DnaDisplayStyle directory
        
        favoriteChoices = ['Factory default settings']

        #look for all the favorite files in the favorite folder and add them to 
        # the list
        from platform.PlatformDependent import find_or_make_Nanorex_subdir
        _dir = find_or_make_Nanorex_subdir('Favorites/DnaDisplayStyle')
        
        
        for file in os.listdir(_dir):
            fullname = os.path.join( _dir, file)
            if os.path.isfile(fullname):
                if fnmatch.fnmatch( file, "*.txt"):
                    
                    # leave the extension out
                    favoriteChoices.append(file[0:len(file)-4])
        
        self.favoritesComboBox  = \
            PM_ComboBox( pmGroupBox,
                         choices       =  favoriteChoices,
                         spanWidth  =  True)
        
        self.favoritesComboBox.setWhatsThis(
            """<b> List of Favorites </b>
        
            <p>
            Creates a list of favorite DNA display styles. Once favorite
            styles have been added to the list using the Add Favorite button,
            the list will display the chosen favorites.
            To change the current favorite, select a current favorite from
            the list, and push the Apply Favorite button.""")
        
        # PM_ToolButtonRow ===============
        
        # Button list to create a toolbutton row.
        # Format: 
        # - QToolButton, buttonId, buttonText, 
        # - iconPath,
        # - tooltip, shortcut, column
        
        BUTTON_LIST = [ 
            ( "QToolButton", 1,  "APPLY_FAVORITE", 
              "ui/actions/Properties Manager/ApplyFavorite.png",
              "Apply Favorite", "", 0),
            ( "QToolButton", 2,  "ADD_FAVORITE", 
              "ui/actions/Properties Manager/AddFavorite.png",
              "Add Favorite", "", 1),
            ( "QToolButton", 3,  "DELETE_FAVORITE",  
              "ui/actions/Properties Manager/DeleteFavorite.png",
              "Delete Favorite", "", 2),
            ( "QToolButton", 4,  "SAVE_FAVORITE",  
              "ui/actions/Properties Manager/SaveFavorite.png",
              "Save Favorite", "", 3),
            ( "QToolButton", 5,  "LOAD_FAVORITE",  
              "ui/actions/Properties Manager/LoadFavorite.png",
              "Load Favorite", \
              "", 4)  
            ]
            
        self.favsButtonGroup = \
            PM_ToolButtonRow( pmGroupBox, 
                              title        = "",
                              buttonList   = BUTTON_LIST,
                              spanWidth    = True,
                              isAutoRaise  = False,
                              isCheckable  = False,
                              setAsDefault = True,
                              )
        
        self.favsButtonGroup.buttonGroup.setExclusive(False)
        
        self.applyFavoriteButton  = self.favsButtonGroup.getButtonById(1)
        self.addFavoriteButton    = self.favsButtonGroup.getButtonById(2)
        self.deleteFavoriteButton = self.favsButtonGroup.getButtonById(3)
        self.saveFavoriteButton   = self.favsButtonGroup.getButtonById(4)
        self.loadFavoriteButton   = self.favsButtonGroup.getButtonById(5)
        
    def _loadGroupBox2(self, pmGroupBox):
        """
        Load widgets in group box.
        """
        dnaComponentChoices = ['Main chain - wire']

        self.dnaComponentComboBox  = \
            PM_ComboBox( pmGroupBox,
                         label         =  "Style:", 
                         choices       =  dnaComponentChoices,
                         setAsDefault  =  True)
                
        qualityChoices = ['Good']

        self.dnaComponentComboBox  = \
            PM_ComboBox( pmGroupBox,
                         label         =  "Quality:", 
                         choices       =  qualityChoices,
                         setAsDefault  =  True)
                
        
        self.myCheckBox = \
            PM_CheckBox( pmGroupBox,
                         text         = "Smoothing",
                         setAsDefault = True)
        

        scaleChoices = ['Constant']

        self.scaleComboBox  = \
            PM_ComboBox( pmGroupBox,
                         label         =  "Scaling:", 
                         choices       =  scaleChoices,
                         setAsDefault  =  True)
                
        self.scaleFactorSpinBox  =  \
            PM_DoubleSpinBox( pmGroupBox,
                              label         =  "Scaling factor:",
                              value         =  1.000,
                              setAsDefault  =  True,
                              minimum       =  1.00,
                              maximum       =  200.0,
                              decimals      =  3,
                              singleStep    =  1.0)
        
    
    def _loadGroupBox3(self, pmGroupBox):
        """
        Load widgets in group box.
        """
        colorChoices = ['Chunk']

        self.dnaComponentComboBox  = \
            PM_ComboBox( pmGroupBox,
                         label         =  "Color:", 
                         choices       =  colorChoices,
                         setAsDefault  =  True)

        self.colorChooser = \
            PM_ColorChooser(pmGroupBox,
                            label      = "Custom color:",
                            color      = orange,
                            setAsDefault  =  True)
                
        auxcolorChoices = ['Custom']

        self.dnaComponentComboBox  = \
            PM_ComboBox( pmGroupBox,
                         label         =  "Auxiliary color:", 
                         choices       =  auxcolorChoices,
                         setAsDefault  =  True)

        self.colorChooser = \
            PM_ColorChooser(pmGroupBox,
                            label      = "Custom auxiliary color:",
                            color      = gray,
                            setAsDefault  =  True)
                
        standLabelColorChoices = ['Hide',
                                  'Show (in strand color)', 
                                  'Black',
                                  'White',
                                  'Custom color...']

        self.myCheckBox = \
            PM_CheckBox( pmGroupBox,
                         text         = "Discrete colors:",
                         setAsDefault = True)
        
        self.colorChooser = \
            PM_ColorChooser(pmGroupBox,
                            label      = "Helix color:",
                            color      = red,
                            setAsDefault  =  True)
                
        self.colorChooser = \
            PM_ColorChooser(pmGroupBox,
                            label      = "Strand color:",
                            color      = cyan,
                            setAsDefault  =  True)
                
        self.colorChooser = \
            PM_ColorChooser(pmGroupBox,
                            label      = "Coil color:",
                            color      = gray,
                            setAsDefault  =  True)
                

    
    
    def updateDnaDisplayStyleWidgets( self ):
        """
        Updates all the DNA Display style widgets based on the current pref keys
        values.
        
        @note: This should be called each time the PM is displayed (see show()).
        """
        pass
    
    def change_dnaStrandLabelsDisplay(self, mode):
        """
        Changes DNA Strand labels display (and color) mode.

        @param mode: The display mode:
                    - 0 = hide all labels
                    - 1 = show (same color as chunk)
                    - 2 = show (black)
                    - 3 = show (white)
		    - 4 = show (custom color...)

        @type mode: int
        """
        pass
    
    def applyFavorite(self):
        """
        Apply the DNA display style settings stored in the current favorite 
        (selected in the combobox) to the current DNA display style settings.
        """
        # Rules and other info:
        # The user has to press the button related to this method when he loads
        # a previously saved favorite file
        
        current_favorite = self.favoritesComboBox.currentText()
        if current_favorite == 'Factory default settings':
            env.prefs.restore_defaults(dnaDisplayStylePrefsList)
        else:
            favfilepath = getFavoritePathFromBasename(current_favorite)
            loadFavoriteFile(favfilepath)
            
        self.updateDnaDisplayStyleWidgets()
        return
    
    def addFavorite(self):
        """
        Adds a new favorite to the user's list of favorites.
        """
        # Rules and other info:
        # - The new favorite is defined by the current DNA display style 
        #    settings.
    
        # - The user is prompted to type in a name for the new 
        #    favorite.
        # - The DNA display style settings are written to a file in a special 
        #    directory on the disk 
        # (i.e. $HOME/Nanorex/Favorites/DnaDisplayStyle/$FAV_NAME.fav).
        # - The name of the new favorite is added to the list of favorites in
        #    the combobox, which becomes the current option. 
        
        # Existence of a favorite with the same name is checked in the above 
        # mentioned location and if a duplicate exists, then the user can either
        # overwrite and provide a new name.
        
        
        
        # Prompt user for a favorite name to add. 
        from widgets.simple_dialogs import grab_text_line_using_dialog
        
        ok1, name = \
          grab_text_line_using_dialog(
              title = "Add new favorite",
              label = "favorite name:",
              iconPath = "ui/actions/Properties Manager/AddFavorite.png",
              default = "" )
        if ok1:
            # check for duplicate files in the 
            # $HOME/Nanorex/Favorites/DnaDisplayStyle/ directory
            
            fname = getFavoritePathFromBasename( name )
            if os.path.exists(fname):
                
                #favorite file already exists!
                
                _ext= ".txt"
                ret = QMessageBox.warning( self, "Warning!",
                "The favorite file \"" + name + _ext + "\"already exists.\n"
                "Do you want to overwrite the existing file?",
                "&Overwrite", "&Cancel", "",
                0,    # Enter == button 0
                1)   # Escape == button 1  
                
                if ret == 0:
                    #overwrite favorite file
                    ok2, text = writeDnaDisplayStyleSettingsToFavoritesFile(name)
                    indexOfDuplicateItem = self.favoritesComboBox.findText(name)
                    self.favoritesComboBox.removeItem(indexOfDuplicateItem)
                    print "Add Favorite: removed duplicate favorite item."
                else:
                    env.history.message("Add Favorite: cancelled overwriting favorite item.")              
                    return 
                
            else:
                ok2, text = writeDnaDisplayStyleSettingsToFavoritesFile(name)
        else:
            # User cancelled.
            return
        if ok2:
            
            self.favoritesComboBox.addItem(name)
            _lastItem = self.favoritesComboBox.count()
            self.favoritesComboBox.setCurrentIndex(_lastItem - 1)
            msg = "New favorite [%s] added." % (text)
        else:
            msg = "Can't add favorite [%s]: %s" % (name, text) # text is reason why not
        
        env.history.message(msg) 
        
        return
        
    def deleteFavorite(self):
        """
        Deletes the current favorite from the user's personal list of favorites
        (and from disk, only in the favorites folder though).
        
        @note: Cannot delete "Factory default settings".
        """
        currentIndex = self.favoritesComboBox.currentIndex()
        currentText = self.favoritesComboBox.currentText()
        if currentIndex == 0:
            msg = "Cannot delete '%s'." % currentText
        else:
            self.favoritesComboBox.removeItem(currentIndex)
            
            
            # delete file from the disk
            
            deleteFile= getFavoritePathFromBasename( currentText )
            os.remove(deleteFile)
            
            msg = "Deleted favorite named [%s].\n" \
                "and the favorite file [%s.txt]." \
                % (currentText, currentText)
            
        env.history.message(msg) 
        return
        
    def saveFavorite(self):
        """
        Writes the current favorite (selected in the combobox) to a file, any 
        where in the disk that 
        can be given to another NE1 user (i.e. as an email attachment).
        """
        
        cmd = greenmsg("Save Favorite File: ")
        env.history.message(greenmsg("Save Favorite File:"))
        current_favorite = self.favoritesComboBox.currentText()
        favfilepath = getFavoritePathFromBasename(current_favorite)
        
        formats = \
                    "Favorite (*.txt);;"\
                    "All Files (*.*)"
         
        
        fn = QFileDialog.getSaveFileName(
            self, 
            "Save Favorite As", # caption
            favfilepath, #where to save
            formats, # file format options
            QString("Favorite (*.txt)") # selectedFilter
            )
        if not fn:
            env.history.message(cmd + "Cancelled")
        
        else:
            saveFavoriteFile(str(fn), favfilepath)
        return
        
    def loadFavorite(self):
        """
        Prompts the user to choose a "favorite file" (i.e. *.txt) from disk to
        be added to the personal favorites list.
        """
        # If the file already exists in the favorites folder then the user is 
        # given the option of overwriting it or renaming it
        
        env.history.message(greenmsg("Load Favorite File:"))
        formats = \
                    "Favorite (*.txt);;"\
                    "All Files (*.*)"
         
        directory= getDefaultWorkingDirectory()
        
        fname = QFileDialog.getOpenFileName(self,
                                         "Choose a file to load",
                                         directory,
                                         formats)
                    
        if not fname:
            env.history.message("User cancelled loading file.")
            return

        else:
            canLoadFile=loadFavoriteFile(fname)
            
            if canLoadFile == 1:
                
            
                #get just the name of the file for loading into the combobox
            
                favName = os.path.basename(str(fname))
                name = favName[0:len(favName)-4]
                indexOfDuplicateItem = self.favoritesComboBox.findText(name)
            
                #duplicate exists in combobox 
            
                if indexOfDuplicateItem != -1:
                    ret = QMessageBox.warning( self, "Warning!",
                                               "The favorite file \"" + name + 
                                               "\"already exists.\n"
                                               "Do you want to overwrite the existing file?",
                                               "&Overwrite", "&Rename", "&Cancel",
                                               0,    # Enter == button 0
                                               1   # button 1
                                               )  
                
                    if ret == 0:
                        self.favoritesComboBox.removeItem(indexOfDuplicateItem)
                        self.favoritesComboBox.addItem(name)
                        _lastItem = self.favoritesComboBox.count()
                        self.favoritesComboBox.setCurrentIndex(_lastItem - 1)
                        ok2, text = writeDnaDisplayStyleSettingsToFavoritesFile(name)
                        msg = "Overwrote favorite [%s]." % (text)
                        env.history.message(msg) 
         
                    elif ret == 1:
                        # add new item to favorites folder as well as combobox
                        self.addFavorite()
                        
                    else:
                        #reset the display setting values to factory default
                    
                        factoryIndex = self.favoritesComboBox.findText(
                                             'Factory default settings')
                        self.favoritesComboBox.setCurrentIndex(factoryIndex)
                        env.prefs.restore_defaults(dnaDisplayStylePrefsList)
                    
                        env.history.message("Cancelled overwriting favorite file.")              
                        return 
                else:
                    self.favoritesComboBox.addItem(name)
                    _lastItem = self.favoritesComboBox.count()
                    self.favoritesComboBox.setCurrentIndex(_lastItem - 1)
                    msg = "Loaded favorite [%s]." % (name)
                    env.history.message(msg) 
         
                
                self.updateDnaDisplayStyleWidgets()  
            
            
        return
    
    def change_dnaRendition(self, rendition):
        """
        Sets the DNA rendition to 3D or one of the optional 2D styles.
        
        @param rendition: The rendition mode, where:
                          - 0 = 3D (default)
                          - 1 = 2D with base letters
                          - 2 = 2D ball and stick
                          - 3 = 2D ladder
        @type  rendition: int
        """
        if rendition == 0:
            _enabled_flag = True
        else:
            _enabled_flag = False
            
        self.dnaComponentComboBox.setEnabled(_enabled_flag)
        self.standLabelColorComboBox.setEnabled(_enabled_flag)
        
        env.prefs[dnaRendition_prefs_key] = rendition
        
        self.o.gl_update() # Force redraw
        
        return
    
    def _addWhatsThisText( self ):
        """
        What's This text for widgets in the DNA Property Manager.  
        """
        from ne1_ui.WhatsThisText_for_PropertyManagers import WhatsThis_EditDnaDisplayStyle_PropertyManager
        WhatsThis_EditDnaDisplayStyle_PropertyManager(self)
                
    def _addToolTipText(self):
        """
        Tool Tip text for widgets in the DNA Property Manager.  
        """
        from ne1_ui.ToolTipText_for_PropertyManagers import ToolTip_EditDnaDisplayStyle_PropertyManager 
        ToolTip_EditDnaDisplayStyle_PropertyManager(self)
    
    