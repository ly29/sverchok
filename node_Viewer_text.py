import bpy, bmesh, mathutils
from mathutils import Matrix
from util import *
from node_s import *

#global cache_viewer_slot1, cache_viewer_slot2, cache_viewer_slot3
cache_viewer_slot1 = {} #{'veriable':'None \n'}
cache_viewer_slot2 = {} #{'veriable':'None \n'}
cache_viewer_slot3 = {} #{'veriable':'None \n'}

class SverchokViewer(bpy.types.Operator):
    """Sverchok viewer"""
    bl_idname = "node.sverchok_viewer_button"
    bl_label = "Sverchok viewer"
    bl_options = {'REGISTER', 'UNDO'}
    
    nodename = bpy.props.StringProperty(name='nodename',default='None')
    
    def execute(self, context):
        global cache_viewer_slot1
        global cache_viewer_slot2
        global cache_viewer_slot3
        
        texts = bpy.data.texts.items()
        exists = False
        for t in texts:
            if bpy.data.texts[t[0]].name == 'Sverchok_viewer':
                exists = True
                break
        bpy.context.area.type = 'TEXT_EDITOR'
        if not exists:
            bpy.ops.text.new()
            texts_new = bpy.data.texts.items()
            for t in texts_new:
                if t not in texts:
                    bpy.data.texts[t[0]].name = 'Sverchok_viewer'
        bpy.ops.text.select_all()
        podpis = '\n' + '\n' \
                + '**************************************************' + '\n' \
                + '             Sverchok parametric tools            ' + '\n' \
                + '                   nikitron.cc.ua                 ' + '\n' \
                + '\n' \
                + '             You can support Sverchok             ' + '\n' \
                + '   Feel free to donate, to code, fill wiki page   ' + '\n' \
                + '          or participate in another way           ' + '\n' \
                + '\n' \
                + 'Huge thanks for Paul Kotelevets, our prime donator' + '\n' \
                + '\n' \
                + '                                     Sverchok team' \
        
        if cache_viewer_slot1['veriable'+self.nodename] or cache_viewer_slot2['veriable'+self.nodename] or cache_viewer_slot3['veriable'+self.nodename]:
            for_file = 'node name: '+ self.nodename \
                        + '\n\nvertices: \n' \
                        + cache_viewer_slot1['veriable'+self.nodename] \
                        + cache_viewer_slot2['type'+self.nodename] \
                        + cache_viewer_slot2['veriable'+self.nodename] \
                        + '\n\nmatrixes: \n' \
                        + cache_viewer_slot3['veriable'+self.nodename] \
                        + podpis
        else:
            for_file = 'vertices: \nNone' \
                        + '\ndata: \nNone' \
                        + '\nmatrixes: \nNone' + podpis
        bpy.data.texts['Sverchok_viewer'].from_string(for_file)
        bpy.context.area.type = 'NODE_EDITOR'
        #print (cache_viewer_slot1['veriable'], cache_viewer_slot2['veriable'], cache_viewer_slot3['veriable'])
        #cache_viewer_slot1['veriable'] = 'None \n'
        #cache_viewer_slot2['veriable'] = 'None \n'
        #cache_viewer_slot3['veriable'] = 'None \n'
        return {'FINISHED'}

class ViewerNode_text(Node, SverchCustomTreeNode):
    ''' Viewer Node text '''
    bl_idname = 'ViewerNode_text'
    bl_label = 'Viewer text'
    bl_icon = 'OUTLINER_OB_EMPTY'
    
    def init(self, context):
        self.inputs.new('VerticesSocket', 'vertices', 'vertices')
        self.inputs.new('StringsSocket', 'edg_pol', 'edg_pol')
        self.inputs.new('MatrixSocket', 'matrix', 'matrix')
        
    def draw_buttons(self, context, layout):
        row = layout.row()
        row.scale_y = 4.0
        row.operator('node.sverchok_viewer_button', text='V I E W').nodename=self.name
    
    def update(self):
        # vertices socket
        
        global cache_viewer_slot1
        global cache_viewer_slot2
        global cache_viewer_slot3
        
        
        if 'vertices' in self.inputs and self.inputs['vertices'].links:

            if type(self.inputs['vertices'].links[0].from_socket) == bpy.types.VerticesSocket:
                evaverti = SvGetSocketAnyType(self,self.inputs['vertices'])
                #evaverti = eval(verti)
                deptl = levelsOflist(evaverti)
                #print(str(evaverti))
                #print (deptl, ' text viewer')
                if deptl and deptl > 2:
                    a = self.readFORviewer_sockets_data(evaverti, deptl, len(evaverti))
                elif deptl:
                    a = self.readFORviewer_sockets_data_small(evaverti, deptl, len(evaverti))
                else:
                    a = 'None \n'
                cache_viewer_slot1['veriable'+self.name] = a
                #print ('viewer text input1')
        else:
            cache_viewer_slot1['veriable'+self.name] = 'None \n'
        # edges/faces socket
        if 'edg_pol' in self.inputs and len(self.inputs['edg_pol'].links)>0:
 
            if type(self.inputs['edg_pol'].links[0].from_socket) == bpy.types.StringsSocket:
                evaline_str = SvGetSocketAnyType(self,self.inputs['edg_pol'])
                #print (line_str)
                
                if evaline_str:
                    cache_viewer_slot2['type'+self.name] = str(self.edgDef(evaline_str))
                deptl = levelsOflist(evaline_str)
                #print(str(evaline_str))
                #print (deptl, ' text viewer')
                if deptl and deptl > 2:
                    b = self.readFORviewer_sockets_data(evaline_str, deptl, len(evaline_str))
                elif deptl:
                    b = self.readFORviewer_sockets_data_small(evaline_str, deptl, len(evaline_str))
                else:
                    b = 'None \n'
                cache_viewer_slot2['veriable'+self.name] = str(b)
                #print ('viewer text input2')
        else:
            cache_viewer_slot2['veriable'+self.name] = 'None \n'
            cache_viewer_slot2['type'+self.name] = '\n\ndata \n'
        # matrix socket
        if 'matrix' in self.inputs and len(self.inputs['matrix'].links)>0:
            
            if type(self.inputs['matrix'].links[0].from_socket) == bpy.types.MatrixSocket:
                eva = SvGetSocketAnyType(self,self.inputs['matrix'])
                deptl = levelsOflist(eva)
                #print (deptl, ' text viewer')
                if deptl and deptl > 2:
                    c = self.readFORviewer_sockets_data(eva, deptl, len(eva))
                elif deptl:
                    c = self.readFORviewer_sockets_data_small(eva, deptl, len(eva))
                else:
                    c = 'None \n'
                cache_viewer_slot3['veriable'+self.name] = str(c)
                #print ('viewer text input3')
        else:
            cache_viewer_slot3['veriable'+self.name] = 'None \n'
        
        if len(self.inputs['matrix'].links)>0 or len(self.inputs['vertices'].links)>0 or \
                len(self.inputs['edg_pol'].links)>0:
            self.use_custom_color=True
            self.color = (0.5,0.5,1)
        else:
            self.use_custom_color=True
            self.color = (0.05,0.05,0.1)
                
    def update_socket(self, context):
        self.update()
    
    def edgDef(self, l):
        t = '\n\ndata: \n'
        if l[0] and type(l[0]) in [int, float]:
            if len(l) > 2:
                t = '\n\npolygons: \n'
            else:
                t = '\n\nedges: \n'
        elif l[0]:
            t = self.edgDef(l[0])
        else:
            pass
        return t


    def readFORviewer_sockets_data(self, data, dept, le):
        cache = ''
        output = ''
        deptl = dept - 1
        if le:
            cache += ('(' + str(le) + ') object(s)')
            del(le)
        if deptl > 1:
            for i, object in enumerate(data):
                cache += ('\n' + '=' + str(i) + '=   (' + str(len(object)) + ')')
                cache += str(self.readFORviewer_sockets_data(object, deptl, False))
        else:
            for k, val in enumerate(data):
                output += ('\n' + str(val))
        return cache + output
    
    def readFORviewer_sockets_data_small(self, data, dept, le):
        cache = ''
        output = ''
        deptl = dept - 1
        if le:
            cache += ('(' + str(le) + ') object(s)')
            del(le)
        if deptl > 0:
            for i, object in enumerate(data):
                cache += ('\n' + '=' + str(i) + '=   (' + str(len(object)) + ')')
                cache += str(self.readFORviewer_sockets_data_small(object, deptl, False))
        else:
            for k, val in enumerate(data):
                output += ('\n' + str(val))
        return cache + output
    

def register():
    bpy.utils.register_class(SverchokViewer)
    bpy.utils.register_class(ViewerNode_text)
    
def unregister():
    bpy.utils.unregister_class(ViewerNode_text)
    bpy.utils.unregister_class(SverchokViewer)

if __name__ == "__main__":
    register()
