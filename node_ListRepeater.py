import bpy, bmesh, mathutils
from mathutils import Vector, Matrix
from node_s import *
from util import *

class ListRepeaterNode(Node, SverchCustomTreeNode):
    ''' List repeater '''
    bl_idname = 'ListRepeaterNode'
    bl_label = 'List repeater'
    bl_icon = 'OUTLINER_OB_EMPTY'
    
    level = bpy.props.IntProperty(name = 'level', default=1, min=0, update=updateNode)
    number = bpy.props.IntProperty(name = 'number', default=1, min=1, update=updateNode)
    unwrap = bpy.props.BoolProperty(name = 'unwrap', default=False, update=updateNode)
    
    def draw_buttons(self, context, layout):
        layout.prop(self, "level", text="level")
        layout.prop(self, "number", text="number")
        layout.prop(self, "unwrap", text="unwrap")
        
    def init(self, context):
        self.inputs.new('StringsSocket', "Data", "Data")
        self.inputs.new('StringsSocket', "Number","Number")
        self.outputs.new('StringsSocket',"Data", "Data")

    def update(self):
        # достаём два слота - вершины и полики
        if 'Data' in self.inputs and self.inputs['Data'].links:
            if not self.inputs['Data'].node.socket_value_update:
                self.inputs['Data'].node.update()
            if type(self.inputs['Data'].links[0].from_socket) == StringsSocket:
                data = eval(self.inputs['Data'].links[0].from_socket.StringsProperty)
            elif type(self.inputs['Data'].links[0].from_socket) == VerticesSocket:
                data = eval(self.inputs['Data'].links[0].from_socket.VerticesProperty)
            elif type(self.inputs['Data'].links[0].from_socket) == MatrixSocket:
                data = eval(self.inputs['Data'].links[0].from_socket.MatrixProperty)
            
            if 'Number' in self.inputs and len(self.inputs['Number'].links)>0:
                if not self.inputs['Number'].node.socket_value_update:
                    self.inputs['Number'].node.update()
                Number = eval(self.inputs['Number'].links[0].from_socket.StringsProperty)[0][0]
            else:
                Number = self.number
            
            if 'Data' in self.outputs and self.outputs['Data'].links:
                out_ = self.count(data, self.level, int(Number))
                if self.unwrap:
                    if len(out_)>0:
                        out = []
                        for o in out_:
                            out.extend(o)
                else:
                    out = out_
                    
                self.outputs['Data'].StringsProperty = str(out)  
            
    def count(self, data, level, number):
        if level:
            out = []
            for obj in data:
                out.append(self.count(obj, level-1, number))
                
        else:
            out = []
            for i in range(number):
                out.append(data)
        return out
            

    def update_socket(self, context):
        self.update()

def register():
    bpy.utils.register_class(ListRepeaterNode)   
    
def unregister():
    bpy.utils.unregister_class(ListRepeaterNode)

if __name__ == "__main__":
    register()