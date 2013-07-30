'''
(*)~----------------------------------------------------------------------------------
 Pupil - eye tracking platform
 Copyright (C) 2012-2013  Moritz Kassner & William Patera

 Distributed under the terms of the CC BY-NC-SA License.
 License details are in the file license.txt, distributed as part of this software.
----------------------------------------------------------------------------------~(*)
'''
# make shared modules available across pupil_src
if __name__ == '__main__':
    from sys import path as syspath
    from os import path as ospath
    loc = ospath.abspath(__file__).rsplit('pupil_src', 1)
    syspath.append(ospath.join(loc[0], 'pupil_src', 'shared_modules'))
    del syspath, ospath

import sys, os
import OpenGL.GL as gl
from glfw import *
import numpy as np
import cv2
from methods import Temp,denormalize
from uvc_capture import autoCreateCapture
from time import sleep
from glob import glob
from gl_utils import adjust_gl_view, draw_gl_texture, clear_gl_screen, draw_gl_point_norm,draw_gl_polyline,draw_gl_point
from OpenGL.GLU import gluOrtho2D

def make_grid(dim=(11,4)):
    """
    this function generates the structure for an assymetrical circle grid
    centerd around 0 width=1, height scaled accordingly
    """
    x,y = range(dim[0]),range(dim[1])
    p = np.array([[[s,i] for s in x] for i in y], dtype=np.float32)
    p[:,1::2,1] += 0.5
    p = np.reshape(p, (-1,2), 'F')

    # scale height = 1
    x_scale =  1./(np.amax(p[:,0])-np.amin(p[:,0]))
    y_scale =  1./(np.amax(p[:,1])-np.amin(p[:,1]))

    p *=x_scale,x_scale/.5

    # center x,y around (0,0)
    x_offset = (np.amax(p[:,0])-np.amin(p[:,0]))/2.
    y_offset = (np.amax(p[:,1])-np.amin(p[:,1]))/2.
    p -= x_offset,y_offset
    return p

def player(g_pool,size):
    """player
        - Shows 9 point calibration pattern
        - Plays a source video synchronized with world process
        - Get src videos from directory (glob)
        - Iterate through videos on each record event
    """


    grid = make_grid()
    grid *=2.5###scale to fit
    # player object
    player = Temp()
    player.play_list = glob('src_video/*')
    path_parent = os.path.dirname( os.path.abspath(sys.argv[0]))
    player.playlist = [os.path.join(path_parent, path) for path in player.play_list]
    player.captures = [autoCreateCapture(src) for src in player.playlist]
    print "Player found %i videos in src_video"%len(player.captures)
    player.captures =  [c for c in player.captures if c is not None]
    print "Player sucessfully loaded %i videos in src_video"%len(player.captures)
    # for c in player.captures: c.auto_rewind = False
    player.current_video = 0

    # Callbacks
    def on_resize(w, h):
        adjust_gl_view(w,h)

    def on_key(key, pressed):
        if key == GLFW_KEY_ESC:
                on_close()
    def on_char(char, pressed):
        if pressed:
            g_pool.player_input.value = char


    def on_close():
        g_pool.quit.value = True
        print "Player Process closing from window"

    def draw_circle(pos,r,c):
        pts = cv2.ellipse2Poly(tuple(pos),(r,r),0,0,360,5)
        draw_gl_polyline(pts,c,'Polygon')

    def draw_marker(pos):
        pos = int(pos[0]),int(pos[1])
        black = (0.,0.,0.,1.)
        white = (1.,1.,1.,1.)
        for r,c in zip((50,40,30,20,10),(black,white,black,white,black)):
            draw_circle(pos,r,c)

    # Initialize glfw
    glfwInit()
    glfwOpenWindow(size[0], size[1], 0, 0, 0, 8, 0, 0, GLFW_WINDOW)
    glfwSetWindowTitle("Player")
    glfwSetWindowPos(100,0)
    glfwDisable(GLFW_AUTO_POLL_EVENTS)


    # Callbacks
    glfwSetWindowSizeCallback(on_resize)
    glfwSetWindowCloseCallback(on_close)
    glfwSetKeyCallback(on_key)
    glfwSetCharCallback(on_char)


    # gl state settings
    gl.glEnable( gl.GL_BLEND )
    gl.glEnable(gl.GL_POINT_SMOOTH)
    gl.glClearColor(1.,1.,1.,0.)


    while glfwGetWindowParam(GLFW_OPENED) and not g_pool.quit.value:

        glfwPollEvents()

        if g_pool.player_refresh.wait(0.01):
            g_pool.player_refresh.clear()

            clear_gl_screen()
            if not g_pool.marker[:] == [0,0]:

                draw_gl_point_norm(g_pool.marker[:],10,(1,0,0,1))
                # Set Projection Matrix
                gl.glMatrixMode(gl.GL_PROJECTION)
                gl.glLoadIdentity()
                gluOrtho2D(0,glfwGetWindowSize()[0],glfwGetWindowSize()[1], 0) # origin in the top left corner just like the img np-array
                # Switch back to Model View Matrix
                gl.glMatrixMode(gl.GL_MODELVIEW)
                gl.glLoadIdentity()
                # draw_gl_point_norm(g_pool.marker[:], 20.0, (0.,1.,0.,.5))
                # draw_gl_point_norm(g_pool.marker[:], 5.0, (1.,1.,0.,.5))


                screen_pos = denormalize(g_pool.marker[:],glfwGetWindowSize(),flip_y=True)
                draw_marker(screen_pos)
                if g_pool.ref[:] == [0.,0.]:
                    draw_gl_point(screen_pos, 5.0, (1.,0.,0.,1.))
                else:
                    draw_gl_point(screen_pos, 5.0, (0.,1.,0.,1.))


                # circle_id,step = g_pool.cal9_circle_id.value,g_pool.cal9_step.value
                # gl.glColor4f(0.0,0.0,0.0,1.0)
                # gl.glPointSize(40)
                # gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
                # gl.glBegin(gl.GL_POINTS)
                # for p in grid:
                #     gl.glVertex3f(p[0],p[1],0.0)
                # gl.glEnd()

                # display the animated target dot

            elif g_pool.play.value:
                if len(player.captures):
                    s, img = player.captures[player.current_video].read()
                    if s:
                        draw_gl_texture(img)
                    else:
                        player.captures[player.current_video].rewind()
                        player.current_video +=1
                        if player.current_video >= len(player.captures):
                            player.current_video = 0
                        g_pool.play.value = False
                else:
                    print 'PLAYER: Warning: No Videos available to play. Please put your vidoes into a folder called "src_video" in the Capture folder.'
                    g_pool.play.value = False
            glfwSwapBuffers()

    glfwCloseWindow()
    glfwTerminate()
    print "PLAYER Process closed"

if __name__ == '__main__':
    print make_grid()