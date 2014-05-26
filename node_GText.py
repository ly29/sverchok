import bpy
from bpy.props import IntVectorProperty, StringProperty
from mathutils import Vector

from node_s import *
from util import *

import random
from random import random
import re
import ast
import os

def openjson_asdict(fname):
    sv_path = os.path.dirname(os.path.realpath(__file__))
    path_to_json = os.path.join(sv_path, fname)
    with open(path_to_json) as d:
        return ast.literal_eval(''.join(d.readlines()))

fdict = openjson_asdict('font3.dict')


def generate_greasepencil(node, text, col, pxwide, pos, fontdict):

    line_height = 38
    char_width = pxwide

    spaces = 0
    yof = 0
    xof = 0
    bcx, bcy = pos

    nt = node.id_data
    node_name = node.name
    tree_name = nt.name
    grease_pencil_name = tree_name + "_grease"

    # get grease pencil data
    if grease_pencil_name not in bpy.data.grease_pencil:
        nt.grease_pencil = bpy.data.grease_pencil.new(grease_pencil_name)
    else:
        nt.grease_pencil = bpy.data.grease_pencil[grease_pencil_name]
    gp = nt.grease_pencil

    # get grease pencil layer
    if not (node_name in gp.layers):
        layer = gp.layers.new(node_name)
        layer.frames.new(1)
        layer.line_width = 1
    else:
        layer = gp.layers[node_name]
        layer.frames[0].clear()
        
    for ch in text:
        if ch == "\n":
            yof -= line_height
            xof = 0
            continue

        if ch == " ":
            xof += char_width
            continue

        v = fdict.get(str(ord(ch)), None)

        if not v:
            xof += char_width
            continue

        for chain in v:
            s = layer.frames[0].strokes.new()
            s.draw_mode = '2DSPACE'
            s.points.add(len(chain))
            for idx, p in enumerate(chain):
                ap = Vector(p) * 25
                x, y = ap[:2]
                xyz = ((x + bcx + xof), (y + bcy + yof), 0)
                s.points[idx].co = xyz

        xof += char_width


class SverchokGText(bpy.types.Operator):
    bl_idname = "node.sverchok_gtext_button"
    bl_label = "Sverchok gtext"
    bl_options = {'REGISTER', 'UNDO'}

    mode = bpy.props.StringProperty(default="")

    def execute(self, context):
        node = context.node
        if self.mode == 'set':
            node.draw_gtext()
        if self.mode == 'clear':
            node.erase_gtext()
        if self.mode == 'clipboard':
            node.set_gtest()

        return {'FINISHED'}


class GTextNode(Node, SverchCustomTreeNode):

    ''' G Notes '''
    bl_idname = 'GTextNode'
    bl_label = 'GText'
    bl_icon = 'OUTLINER_OB_EMPTY'

    text = StringProperty(name='text', default='your text here')
    locator = IntVectorProperty(name="locator", description="stores location", default=(0, 0), size=2)

    def draw_buttons(self, context, layout):
        row = layout.row(align=True)
        row.operator('node.sverchok_gtext_button', text='Set').mode = 'set'
        row.operator('node.sverchok_gtext_button', text='Clear').mode = 'clear'

        # if not (self.locator) == self.location:
        #     # self.locator = self.location
        #     self.draw_gtext()
        pass

    def draw_buttons_ext(self, context, layout):
        row = layout.row(align=True)
        row.operator(
            'node.sverchok_gtext_button', text='Get from Clipboard'
            ).mode = 'clipboard'
        if self.id_data.grease_pencil:
            gp_layer=self.id_data.grease_pencil.layers.get(self.name)
            if gp_layer:
                layout.prop(gp_layer,'color')
                layout.prop(gp_layer,'line_width')

    def init(self, context):
        pass

    def update(self):
        # if not (self.intx, self.inty) == self.location:
        #     self.intx, self.inty = self.location
        #     self.draw_gtext()
        pass

    def set_gtest(self):
        self.text = bpy.context.window_manager.clipboard
        self.draw_gtext()

    def erase_gtext(self):
        print("should be erasing")

        nt = self.id_data
        node_name = self.name
        tree_name = nt.name
        grease_pencil_name = tree_name + "_grease"

        # get grease pencil data
        gp = nt.grease_pencil
        if (node_name in gp.layers):
            layer = gp.layers[node_name]
            layer.frames[0].clear()

    def draw_gtext(self):
        text = self.text

        col = []
        pxwide = 21
        pos = self.location

        x_offset = 0
        y_offset = -90
        offset = lambda x, y: (x+x_offset, y+y_offset)
        pos = offset(*pos)
        generate_greasepencil(self, text, col, pxwide, pos, fdict)


def register():
    bpy.utils.register_class(GTextNode)
    bpy.utils.register_class(SverchokGText)


def unregister():
    bpy.utils.unregister_class(SverchokGText)
    bpy.utils.unregister_class(GTextNode)
