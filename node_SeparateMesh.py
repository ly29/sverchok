from node_s import *
from util import *

import collections

class SvSeparateMeshNode(Node, SverchCustomTreeNode):
    '''Separate Loose mesh parts'''
    bl_idname = 'SvSeparateMeshNode'
    bl_label = 'Separate Loose'
    bl_icon = 'OUTLINER_OB_EMPTY'
    
   
    def init(self, context):
        self.inputs.new('VerticesSocket', 'Vertices', 'Vertices')
        self.inputs.new('StringsSocket', 'Poly Egde', 'Poly Edge')
        
        self.outputs.new('VerticesSocket', 'Vertices', 'Vertices')
        self.outputs.new('StringsSocket', 'Poly Egde', 'Poly Egde')
        
    def update(self):
        if not 'Poly Egde' in self.outputs:
            return
        if not any((self.outputs[0].links,self.outputs[1].links)):
            return       
        if self.inputs['Vertices'].links and self.inputs['Poly Egde'].links:

            verts = SvGetSocketAnyType(self,self.inputs['Vertices'])
            poly = SvGetSocketAnyType(self,self.inputs['Poly Egde'])
            verts_out = []
            poly_edge_out = []
            for ve,pe in zip(verts,poly):
                
                # build links        
                node_links = {}
                for edge_face in pe:
                    for i in edge_face:
                        if not i in node_links:
                            node_links[i]=set()
                        s=node_links[i]
                        node_links[i]=s.union(edge_face)
                
                nodes=set(node_links.keys())
                
                n= nodes.pop()
                node_set_list = [set([n])]
                node_stack = collections.deque()
                # find separate sets
                while nodes:
                    for node in node_links[n]:
                        if not node in node_set_list[-1]:
                            node_stack.append(node)                                                        
                    if not node_stack: # new mesh part
                        n=nodes.pop()
                        node_set_list.append(set([n]))
                    else:
                        while node_stack and n in node_set_list[-1]:
                            n = node_stack.pop()
                        nodes.discard(n)
                        node_set_list[-1].add(n)

                # create new meshes from sets
                if len(node_set_list)>1:
                    for node_set in node_set_list:
                        mesh_index = sorted(node_set)
                        vert_dict = {j:i for i,j in enumerate(mesh_index)}
                        new_vert = [ve[i] for i in mesh_index]
                        new_pe=filter(lambda x:x[0] in node_set,pe)
                        new_pe= [list(map(lambda n:vert_dict[n],fe)) for fe in new_pe]
                        verts_out.append(new_vert)
                        poly_edge_out.append(new_pe)
                elif node_set_list: #no reprocessing needed
                    verts_out.append(ve)
                    poly_edge_out.append(pe)
                    
            if 'Vertices' in self.outputs and self.outputs['Vertices'].links:
                SvSetSocketAnyType(self, 'Vertices',verts_out)
            
            if 'Poly Egde' in self.outputs and self.outputs['Poly Egde'].links:
                if poly_edge_out:
                    SvSetSocketAnyType(self,'Poly Egde',poly_edge_out)

    def update_socket(self, context):
        self.update()

def register():
    bpy.utils.register_class(SvSeparateMeshNode)   
    
def unregister():
    bpy.utils.unregister_class(SvSeparateMeshNode)

if __name__ == "__main__":
    register()
