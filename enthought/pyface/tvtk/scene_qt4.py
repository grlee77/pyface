#------------------------------------------------------------------------------
# Copyright (c) 2005, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!
#
# Author: Enthought, Inc.
# Description: <Enthought pyface package component>
#------------------------------------------------------------------------------
"""A VTK interactor scene widget for the PyFace wxPython backend.  See
the class docs for more details.

"""
# Author: Prabhu Ramachandran <prabhu_r@users.sf.net>
# Copyright (c) 2004-2007, Enthought, Inc.
# License: BSD Style.


import sys
import os
import tempfile

from PyQt4 import QtGui

from enthought.tvtk.api import tvtk
from enthought.traits.api import Instance, Button, Any
from enthought.traits.ui.api import View, Group, Item, InstanceEditor

from enthought.pyface.api import Widget
from enthought.pyface.tvtk import picker
from enthought.pyface.tvtk import light_manager
from enthought.pyface.tvtk.tvtk_scene import TVTKScene, VTK_VER

from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor



######################################################################
# `_VTKRenderWindowInteractor` class.
######################################################################
class _VTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    """ This is a thin wrapper around the standard VTK PyQt interactor.
    """
    def __init__(self, scene, parent, **kwargs):
        QVTKRenderWindowInteractor.__init__(self, parent, **kwargs)

        self._scene = scene

    def resizeEvent(self, e):
        """ Reimplemented to refresh the traits of the render window.
        """
        QVTKRenderWindowInteractor.resizeEvent(self, e)

        self._scene._renwin.update_traits()

    def showEvent(self, e):
        """ Reimplemented to create the light manager only when needed.  This
        is necessary because it makes sense to create the light manager only
        when the widget is realized.  Only when the widget is realized is the
        VTK render window created and only then are the default lights all
        setup correctly.
        """
        if self._scene.light_manager is None:
            self._scene.light_manager = light_manager.LightManager(self._scene)
            self._scene._renwin.update_traits()


######################################################################
# `FullScreen` class.
######################################################################
class FullScreen(object):
    """Creates a full screen interactor widget.  This will use VTK's
    event loop until the user presses 'q'/'e' on the full screen
    window.  This does not yet support interacting with any widgets on
    the renderered scene.

    This class is really meant to be used for VTK versions earlier
    than 5.1 where there was a bug with reparenting a window.

    """
    def __init__(self, scene):
        self.scene = scene
        self.old_rw = scene.render_window
        self.ren = scene.renderer

    def run(self):
        # Remove the renderer from the current render window.
        self.old_rw.remove_renderer(self.ren)

        # Creates renderwindow tha should be used ONLY for
        # visualization in full screen
        full_rw = tvtk.RenderWindow(stereo_capable_window=True,
                                    full_screen=True
                                    )
        # add the current visualization
        full_rw.add_renderer(self.ren)

        # Under OS X there is no support for creating a full screen
        # window so we set the size of the window here.
        # FIXME: Is this problem wx specific?
        if sys.platform  == 'darwin':
            full_rw.size = tuple(wx.GetDisplaySize())

        # provides a simple interactor
        style = tvtk.InteractorStyleTrackballCamera()
        self.iren = tvtk.RenderWindowInteractor(render_window=full_rw,
                                                interactor_style=style)

        # Gets parameters for stereo visualization
        if self.old_rw.stereo_render:
            full_rw.set(stereo_type=self.old_rw.stereo_type, stereo_render=True)

        # Starts the interactor
        self.iren.initialize()
        self.iren.render()
        self.iren.start()

        # Once the full screen window is quit this releases the
        # renderer before it is destroyed, and return it to the main
        # renderwindow.
        full_rw.remove_renderer(self.ren)
        self.old_rw.add_renderer(self.ren)
        self.old_rw.render()
        self.iren.disable()


######################################################################
# `PopupScene` class.
######################################################################
class PopupScene(object):
    """Pops up a Scene instance with an independent `wx.Frame` in
    order to produce either a standalone window or usually a full
    screen view with *complete* interactivity (including widget
    interaction).
    """
    def __init__(self, scene):
        self.orig_parent = None
        self.orig_geometry = None
        self.frame = None
        self.scene = scene
        self.vtk_control = self.scene._vtk_control

    def _setup_frame(self):
        vtk_control = self.vtk_control
        self.orig_parent = vtk_control.parent()
        self.orig_geometry = vtk_control.geometry()
        f = self.frame = QtGui.QWidget()
        return f

    def popup(self, size=None):
        """Create a popup window of scene and set its default size.
        """
        vc = self.vtk_control
        f = self._setup_frame()
        if size is None:
            f.resize(vc.size())
        else:
            f.resize(size)
        f.show()
        vc.setParent(f)

    def fullscreen(self):
        """Create a popup window of scene.
        """
        f = self._setup_frame()
        self.vtk_control.setParent(f)
        f.showFullScreen()

    def close(self):
        """Close the window and reparent the TVTK scene.
        """
        f = self.frame
        if f is None:
            return

        vc = self.vtk_control
        vc.setParent(self.orig_parent)
        vc.setGeometry(self.orig_geometry)
        f.hide()
        self.frame = None


######################################################################
# `Scene` class.
######################################################################
class Scene(TVTKScene, Widget):
    """A VTK interactor scene widget for pyface and wxPython.

    This widget uses a RenderWindowInteractor and therefore supports
    interaction with VTK widgets.  The widget uses TVTK.  In addition
    to the features that the base TVTKScene provides this widget
    supports:

    - saving the rendered scene to the clipboard.

    - picking data on screen.  Press 'p' or 'P' when the mouse is over
      a point that you need to pick.

    - The widget also uses a light manager to manage the lighting of
      the scene.  Press 'l' or 'L' to activate a GUI configuration
      dialog for the lights.

    - Pressing the left, right, up and down arrow let you rotate the
      camera in those directions.  When shift-arrow is pressed then
      the camera is panned.  Pressing the '+' (or '=')  and '-' keys
      let you zoom in and out.

    - full screen rendering via the full_screen button on the UI.

    """

    # The version of this class.  Used for persistence.
    __version__ = 0

    ###########################################################################
    # Traits.
    ###########################################################################

    # Turn on full-screen rendering.
    full_screen = Button('Full Screen')

    # The picker handles pick events.
    picker = Instance(picker.Picker)

    ########################################

    # Render_window's view.
    _stereo_view = Group(Item(name='stereo_render'),
                         Item(name='stereo_type'),
                         show_border=True,
                         label='Stereo rendering',
                         )

    # The default view of this object.
    default_view = View(Group(
                            Group(Item(name='background'),
                                  Item(name='foreground'),
                                  Item(name='parallel_projection'),
                                  Item(name='disable_render'),
                                  Item(name='off_screen_rendering'),
                                  Item(name='jpeg_quality'),
                                  Item(name='jpeg_progressive'),
                                  Item(name='magnification'),
                                  Item(name='anti_aliasing_frames'),
                                  Item(name='full_screen',
                                       show_label=False),
                                  ),
                            Group(Item(name='render_window',
                                       style='custom',
                                       visible_when='object.stereo',
                                       editor=InstanceEditor(view=View(_stereo_view)),
                                       show_label=False),
                                  ),
                            label='Scene'),
                        Group( Item(name='light_manager',
                                style='custom', show_label=False),
                                label='Lights')
                        )

    ########################################
    # Private traits.

    _vtk_control = Instance(_VTKRenderWindowInteractor)
    _fullscreen = Any

    ###########################################################################
    # 'object' interface.
    ###########################################################################
    def __init__(self, parent=None, **traits):
        """ Initializes the object. """

        # Base class constructor.
        super(Scene, self).__init__(parent, **traits)

        # Setup the default picker.
        self.picker = picker.Picker(self)

        # The light manager needs creating.
        self.light_manager = None


    def __get_pure_state__(self):
        """Allows us to pickle the scene."""
        # The control attribute is not picklable since it is a VTK
        # object so we remove it.
        d = super(Scene, self).__get_pure_state__()
        for x in ['_vtk_control', '_fullscreen']:
            d.pop(x, None)
        return d

    ###########################################################################
    # 'Scene' interface.
    ###########################################################################
    def render(self):
        """ Force the scene to be rendered. Nothing is done if the
        `disable_render` trait is set to True."""
        if not self.disable_render:
            self._vtk_control.Render()

    def get_size(self):
        """Return size of the render window."""
        return self._vtk_control.GetSize()

    def set_size(self, size):
        """Set the size of the window."""
        self._vtk_control.SetSize(size)

    ###########################################################################
    # 'TVTKScene' interface.
    ###########################################################################
    def save_to_clipboard(self):
        """Saves a bitmap of the scene to the clipboard."""
        handler, name = tempfile.mkstemp()
        self.save_bmp(name)
        bmp = wx.Bitmap(name, wx.BITMAP_TYPE_BMP)
        bmpdo = wx.BitmapDataObject(bmp)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(bmpdo)
        wx.TheClipboard.Close()
        os.close(handler)
        os.unlink(name)

    ###########################################################################
    # `QVTKRenderWindowInteractor` interface.
    ###########################################################################
    def OnKeyDown(self, event):
        """This method is overridden to prevent the 's'/'w'/'e'/'q'
        keys from doing the default thing which is generally useless.
        It also handles the 'p' and 'l' keys so the picker and light
        manager are called.
        """
        keycode = event.GetKeyCode()
        modifiers = event.HasModifiers()
        camera = self.camera
        if keycode < 256:
            key = chr(keycode)
            if key == '-':
                camera.zoom(0.8)
                self.render()
                return
            if key in ['=', '+']:
                camera.zoom(1.25)
                self.render()
                return
            if key.lower() in ['q', 'e']:
                self._disable_fullscreen()
            if key.lower() in ['s', 'w']:
                event.Skip()
                return
            # Handle picking.
            if key.lower() in ['p']:
                # In wxPython-2.6, there appears to be a bug in
                # EVT_CHAR so that event.GetX() and event.GetY() are
                # not correct.  Therefore the picker is called on
                # KeyUp.
                event.Skip()
                return
            # Light configuration.
            if key.lower() in ['l'] and not modifiers:
                self.light_manager.configure()
                return
            
        shift = event.ShiftDown()
        if keycode == wx.WXK_LEFT:
            if shift:
                camera.yaw(-5)
            else:
                camera.azimuth(5)
            self.render()
            return
        elif keycode == wx.WXK_RIGHT:
            if shift:
                camera.yaw(5)
            else:
                camera.azimuth(-5)
            self.render()
            return
        elif keycode == wx.WXK_UP:
            if shift:
                camera.pitch(-5)
            else:
                camera.elevation(-5)
            camera.orthogonalize_view_up()
            self.render()
            return
        elif keycode == wx.WXK_DOWN:
            if shift:
                camera.pitch(5)
            else:
                camera.elevation(5)
            camera.orthogonalize_view_up()
            self.render()
            return

        self._vtk_control.OnKeyDown(event)

        # Skipping the event is not ideal but necessary because we
        # have no way of knowing of the event was really handled or
        # not and not skipping will break any keyboard accelerators.
        # In practice this does not seem to pose serious problems.
        event.Skip()

    def OnKeyUp(self, event):
        """This method is overridden to prevent the 's'/'w'/'e'/'q'
        keys from doing the default thing which is generally useless.
        It also handles the 'p' and 'l' keys so the picker and light
        manager are called.
        """
        keycode = event.GetKeyCode()
        modifiers = event.HasModifiers()
        if keycode < 256:
            key = chr(keycode)
            if key.lower() in ['s', 'w', 'e', 'q']:
                event.Skip()
                return
            # Handle picking.
            if key.lower() in ['p']:
                if not modifiers:
                    x = event.GetX()
                    y = self._vtk_control.GetSize()[1] - event.GetY()
                    self.picker.pick(x, y)
                    return
                else:
                    # This is here to disable VTK's own pick handler
                    # which can get called when you press Alt/Ctrl +
                    # 'p'.
                    event.Skip()
                    return
            # Light configuration.
            if key.lower() in ['l']:
                event.Skip()
                return

        self._vtk_control.OnKeyUp(event)
        event.Skip()

    ###########################################################################
    # Non-public interface.
    ###########################################################################
    def _create_control(self, parent):
        """ Create the toolkit-specific control that represents the widget. """

        # Create the VTK widget.
        self._vtk_control = window = _VTKRenderWindowInteractor(self, parent,
                                                                 stereo=self.stereo)

        # Override these handlers.
        #wx.EVT_CHAR(window, None) # Remove the default handler.
        #wx.EVT_CHAR(window, self.OnKeyDown)
        #wx.EVT_KEY_UP(window, None) # Remove the default handler.
        #wx.EVT_KEY_UP(window, self.OnKeyUp)

        # Switch the default interaction style to the trackball one.
        window.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

        # Grab the renderwindow.
        renwin = self._renwin = tvtk.to_tvtk(window.GetRenderWindow())
        renwin.set(point_smoothing=self.point_smoothing,
                   line_smoothing=self.line_smoothing,
                   polygon_smoothing=self.polygon_smoothing)
        # Create a renderer and add it to the renderwindow
        self._renderer = tvtk.Renderer()
        renwin.add_renderer(self._renderer)

        # Sync various traits.
        self.sync_trait('background', self._renderer)
        self.renderer.on_trait_change(self.render, 'background')
        self.sync_trait('parallel_projection', self.camera)
        self.sync_trait('off_screen_rendering', self._renwin)
        self.render_window.on_trait_change(self.render, 'off_screen_rendering')
        self.render_window.on_trait_change(self.render, 'stereo_render')
        self.render_window.on_trait_change(self.render, 'stereo_type')
        self.camera.on_trait_change(self.render, 'parallel_projection')

        self._interactor = tvtk.to_tvtk(window._Iren)
        return window

    def _lift(self):
        """Lift the window to the top. Useful when saving screen to an
        image."""
        if self.render_window.off_screen_rendering:
            # Do nothing if off screen rendering is being used.
            return

        w = self._vtk_control
        while w and not w.IsTopLevel():
            w = w.GetParent()
        if w:
            w.Raise()
            wx.Yield()
            self.render()

    def _full_screen_fired(self):
        fs = self._fullscreen
        if isinstance(fs, PopupScene):
            fs.close()
            self._fullscreen = None
        elif fs is None:
            ver = tvtk.Version()
            if (ver.vtk_major_version >= 5) and \
               (ver.vtk_minor_version >= 1):
                # There is a bug with earlier versions of VTK that
                # breaks reparenting a window which is why we test for
                # the version above.
                f = PopupScene(self)
                self._fullscreen = f
                f.fullscreen()
            else:
                f = FullScreen(self)
                f.run() # This will block.
                self._fullscreen = None

    def _disable_fullscreen(self):
        fs = self._fullscreen
        if isinstance(fs, PopupScene):
            fs.close()
            self._fullscreen = None