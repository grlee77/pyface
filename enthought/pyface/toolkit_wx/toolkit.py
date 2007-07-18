#------------------------------------------------------------------------------
# Copyright (c) 2007, Riverbank Computing Limited
# All rights reserved.
# 
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#------------------------------------------------------------------------------

from enthought.pyface.toolkit import Toolkit

from action.menu_bar_manager import MenuBarManager_wx
from action.menu_manager import MenuManager_wx
from action.tool_bar_manager import ToolBarManager_wx


class Toolkit_wx(Toolkit):
    """ Implementation of the wx toolkit. """

    MenuBarManager = MenuBarManager_wx
    MenuManager = MenuManager_wx
    ToolBarManager = ToolBarManager_wx

    def init_toolkit(self, *args, **kw):
        pass
