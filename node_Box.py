import bpy
from node_s import *
from util import *

import bmesh
import mathutils
from mathutils import Vector

class SvBoxNode(Node, SverchCustomTreeNode):
    ''' Box '''
    bl_idname = 'SvBoxNode'
    bl_label = 'Box'
    bl_icon = 'OUTLINER_OB_EMPTY'
    
    Divx = bpy.props.IntProperty(name = 'Divx', description='divisions x',
            default=2, min=1, options={'ANIMATABLE'}, update=updateNode)
    Divy = bpy.props.IntProperty(name = 'Divy', description='divisions y',
            default=2, min=1, options={'ANIMATABLE'}, update=updateNode)
    Divz = bpy.props.IntProperty(name = 'Divz', description='divisions z',
            default=2, min=1, options={'ANIMATABLE'}, update=updateNode)
    Size = bpy.props.FloatProperty(name = 'Size', description='Size',
            default=1.0, options={'ANIMATABLE'}, update=updateNode)
    
    def init(self, context):
        self.inputs.new('StringsSocket', "Size", "Size")
        self.inputs.new('StringsSocket', "Divx", "Divx")
        self.inputs.new('StringsSocket', "Divy", "Divy")
        self.inputs.new('StringsSocket', "Divz", "Divz")
        self.outputs.new('VerticesSocket', "Vers", "Vers")
        self.outputs.new('StringsSocket', "Edgs", "Edgs")
        self.outputs.new('StringsSocket', "Pols", "Pols")
    
    def draw_buttons(self, context, layout):
        layout.prop(self, "Size", text="Size")
        layout.prop(self, "Divx", text="Divx")
        layout.prop(self, "Divy", text="Divy")
        layout.prop(self, "Divz", text="Divz")

    def makecube(self, size, divx, divy, divz):
        if 0 in (divx, divy, divz):
            return [], []

        b = size / 2.0

        verts = [
            [b, b, -b], [b, -b, -b], [-b, -b, -b],
            [-b, b, -b], [b, b, b], [b, -b, b],
            [-b, -b, b], [-b, b, b]
        ]

        faces = [[0, 1, 2, 3], [4, 7, 6, 5],
                 [0, 4, 5, 1], [1, 5, 6, 2],
                 [2, 6, 7, 3], [4, 0, 3, 7]]

        if (divx, divy, divz) == (1, 1, 1):
            return verts, faces

        bm = bmesh.new()
        [bm.verts.new(co) for co in verts]
        bm.verts.index_update()
        for face in faces:
            bm.faces.new(tuple(bm.verts[i] for i in face))
        bm.faces.index_update()

        dist = 0.0001
        section_dict = {0: divx, 1: divy, 2: divz}

        for axis in range(3):

            num_sections = section_dict[axis]
            if num_sections == 1:
                continue

            step = 1 / num_sections
            v1 = Vector(tuple((b if (i == axis) else 0) for i in [0, 1, 2]))
            v2 = Vector(tuple((-b if (i == axis) else 0) for i in [0, 1, 2]))

            for section in range(num_sections):
                mid_vec = v1.lerp(v2, section * step)
                plane_no = v2 - mid_vec
                plane_co = mid_vec
                visible_geom = bm.faces[:] + bm.verts[:] + bm.edges[:]

                bmesh.ops.bisect_plane(
                    bm, geom=visible_geom, dist=dist,
                    plane_co=plane_co, plane_no=plane_no,
                    use_snap_center=False,
                    clear_outer=False, clear_inner=False)

        indices = lambda i: [j.index for j in i.verts]
        
        verts = [v.co.to_tuple() for v in bm.verts]
        faces = [indices(face) for face in bm.faces]
        edges = [indices(edge) for edge in bm.edges]
        return [verts], edges, [faces]


    def update(self):

        if 'Size' in self.inputs and self.inputs['Size'].links:
            size = int(SvGetSocketAnyType(self,self.inputs['Size'])[0][0])
        else:
            size = self.Size
        if 'Divx' in self.inputs and self.inputs['Divx'].links:
            divx = int(SvGetSocketAnyType(self,self.inputs['Divx'])[0][0])
        else:
            divx = self.Divx
        if 'Divy' in self.inputs and self.inputs['Divy'].links:
            divy = int(SvGetSocketAnyType(self,self.inputs['Divy'])[0][0])
        else:
            divy = self.Divy
        if 'Divz' in self.inputs and self.inputs['Divz'].links:
            divz = int(SvGetSocketAnyType(self,self.inputs['Divz'])[0][0])
        else:
            divz = self.Divz
            
        out = self.makecube(size,divx,divy,divz)
        
        # outputs
        if 'Vers' in self.outputs and self.outputs['Vers'].links:       
            SvSetSocketAnyType(self, 'Vers', out[0])
        if 'Edgs' in self.outputs and self.outputs['Edgs'].links:       
            SvSetSocketAnyType(self, 'Edgs', out[1])
        if 'Pols' in self.outputs and self.outputs['Pols'].links:       
            SvSetSocketAnyType(self, 'Pols', out[2])

    def update_socket(self, context):
        self.update()


def register():
    bpy.utils.register_class(SvBoxNode)
    
def unregister():
    bpy.utils.unregister_class(SvBoxNode)

if __name__ == "__main__":
    register()
