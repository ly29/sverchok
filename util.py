import bpy, bmesh, mathutils
from mathutils import Vector, Matrix
from node_s import *
from functools import reduce
from math import radians
import itertools
import collections
import time
import copy
import traceback

global bmesh_mapping, per_cache

DEBUG_MODE = True

# temporary setting while testing new update system
# to test new, set to False
USE_OLD = True

temp_handle = {}

cache_nodes = {}
# cache node group update trees
list_nodes4update = {}
# cache for partial update lists
partial_update_cache = {}
# wifi node data
sv_Vars = {}
# socket cache
socket_data_cache = {}
#
cache_viewer_baker = {}

# note used?

bmesh_mapping = {}
per_cache = {}

#####################################################
################### update magic ####################
#####################################################
# is this used?

# main update
def read_cnodes(cnode):
    global cache_nodes
    if cnode not in cache_nodes:
        return None
    return cache_nodes[cnode]

def write_cnodes(cnode, number):
    global cache_nodes
    if cnode in cache_nodes:
        del cache_nodes[cnode]
    cache_nodes[cnode] = number

def clear_cnodes(cnode='ALL'):
    global cache_nodes
    if cnode=='ALL':
        for i in cache_nodes.items:
            del cache_nodes[i]
    else:
        if read_cnodes(cnode)!=None:
            del cache_nodes[cnode]

def initialize_cnodes():
    node_name = 'GLOBAL CNODE'
    write_cnodes(node_name, 1)
    write_cnodes('LOCK UPDATE CNODES', 1)

def check_update_node(node_name, write=False):
    numb = read_cnodes(node_name)
    etalon = read_cnodes('GLOBAL CNODE')
    #print('etalon',etalon)
    if numb == etalon:
        return False
    else:
        if write:
            write_cnodes(node_name, etalon)
        return True

def ini_update_cnode(node_name):
    if read_cnodes('LOCK UPDATE CNODES')==1:
        return False

    etalon = read_cnodes('GLOBAL CNODE')
    if etalon == None:
        initialize_cnodes()
        etalon = 1
    else:
        etalon += 1

    write_cnodes('GLOBAL CNODE', etalon)
    write_cnodes(node_name, etalon)
    return True

def is_updated_cnode():
     write_cnodes('LOCK UPDATE CNODES', 0)

def lock_updated_cnode():
     write_cnodes('LOCK UPDATE CNODES', 1)



#####################################################
################### bmesh magic #####################
#####################################################

def read_bmm(bm_ref):
    global bmesh_mapping
    if bm_ref not in bmesh_mapping:
        return None
    return bmesh_mapping[bm_ref]


def write_bmm(bm_ref, bm):
    global bmesh_mapping
    if bm_ref in bmesh_mapping:
        del bmesh_mapping[bm_ref]
    bmesh_mapping[bm_ref] = bm


def clear_bmm(bm_ref='ALL'):
    global bmesh_mapping
    if bm_ref=='ALL':
        for i in bmesh_mapping.items:
            del bmesh_mapping[i]
    else:
        if read_bm(bm_ref)!=None:
            del bmesh_mapping[bm_ref]


#####################################################
################### cache magic #####################
#####################################################


def handle_delete(handle):
    if handle in temp_handle:
       del temp_handle[handle]

def handle_read(handle):
    if not (handle in temp_handle):
        return (False, False)

    prop = temp_handle[handle]['prop']
    return (True, prop)

def handle_write(handle, prop):
    if handle in temp_handle:
        if prop != temp_handle[handle]['prop']: handle_delete(handle)

    if not (handle in temp_handle) and handle !='':
        temp_handle[handle] = {"prop": prop}

def handle_check(handle, prop):
    result = True
    if handle in handle_check:
        if prop != handle_check[handle]['prop']:
                result = False
    else:
        result = False
    return result

#####################################################
################ list matching magic ################
#####################################################

# creates an infinite iterator
# use with terminating input

def repeat_last(lst):
    i = -1
    while lst:
        i += 1
        if len(lst) > i:
            yield lst[i]
        else:
            yield lst[-1]

# longest list matching [[1,2,3,4,5], [10,11]] -> [[1,2,3,4,5], [10,11,11,11,11]]
def match_long_repeat(lsts):
    max_l = 0
    tmp = []
    for l in lsts:
        max_l = max(max_l,len(l))
    for l in lsts:
        if len(l)==max_l:
            tmp.append(l)
        else:
            tmp.append(repeat_last(l))

    return list(map( list, zip(*zip(*tmp))))

# longest list matching, cycle [[1,2,3,4,5] ,[10,11]] -> [[1,2,3,4,5] ,[10,11,10,11,10]]
def match_long_cycle(lsts):
    max_l = 0
    tmp = []
    for l in lsts:
        max_l = max(max_l,len(l))
    for l in lsts:
        if len(l)==max_l:
            tmp.append(l)
        else:
            tmp.append(itertools.cycle(l))
    return list(map( list, zip(*zip(*tmp))))

# cross matching
# [[1,2], [5,6,7]] -> [[1,1,1,2,2,2], [5,6,7,5,6,7]]
def match_cross(lsts):
    return list(map(list,zip(*itertools.product(*lsts))))

# use this one
# cross matching 2, more useful order
# [[1,2], [5,6,7]] ->[[1, 2, 1, 2, 1, 2], [5, 5, 6, 6, 7, 7]]
# but longer and less elegant expression
# performance difference is minimal since number of lists is usually small

def match_cross2(lsts):
    return list(reversed(list(map(list,zip(*itertools.product(*reversed(lsts)))))))


# Shortest list decides output length [[1,2,3,4,5], [10,11]] -> [[1,2], [10, 11]]
def match_short(lsts):
    return list(map(list,zip(*zip(*lsts))))

# extends list so len(l) == count
def fullList(l, count):
    d = count - len(l)
    if d > 0:
        l.extend([l[-1] for a in range(d)])
    return

def sv_zip(*iterables):
    # zip('ABCD', 'xy') --> Ax By
    # like standard zip but list instead of tuple
    sentinel = object()
    iterators = [iter(it) for it in iterables]
    while iterators:
        result = []
        for it in iterators:
            elem = next(it, sentinel)
            if elem is sentinel:
                return
            result.append(elem)
        yield result

#####################################################
################# list levels magic #################
#####################################################

# working with nesting levels
# define data floor

# data from nasting to standart: TO container( objects( lists( floats, ), ), )
def dataCorrect(data, nominal_dept=2):
    dept = levelsOflist(data)
    output = []

    if dept < 2:
        return [dept, data]
    else:
        output = dataStandart(data, dept, nominal_dept)
        return output

# from standart data to initial levels: to nasting lists  container( objects( lists( nasty_lists( floats, ), ), ), ) это невозможно!
def dataSpoil(data, dept):
    if dept:
        out = []
        for d in data:
            out.append([dataSpoil(d, dept-1)])
    else:
        out = data
    return out

# data from nasting to standart: TO container( objects( lists( floats, ), ), )
def dataStandart(data, dept, nominal_dept):
    deptl = dept - 1
    output = []
    for object in data:
        if deptl >= nominal_dept:
            output.extend(dataStandart(object, deptl, nominal_dept))
        else:
            output.append(data)
            return output
    return output


# calc list nesting only in countainment level integer

def levelsOflist(lst):
    level = 1
    for n in lst:
        if n and isinstance(n,(list,tuple)): 
            level += levelsOflist(n)
        return level
    return

#####################################################
################### matrix magic ####################
#####################################################

# tools that makes easier to convert data
# from string to matrixes, vertices,
# lists, other and vise versa

def Matrix_listing(prop):
    # matrix degenerate
    mat_out = []
    for i, matrix in enumerate(prop):
        unit = []
        for k, m in enumerate(matrix):
            # [Matrix0, Matrix1, ... ]
            unit.append(m[:])
        mat_out.append((unit))
    return mat_out

def Matrix_generate(prop):
    mat_out = []
    for i, matrix in enumerate(prop):
        unit = Matrix()
        for k, m in enumerate(matrix):
            # [Matrix0, Matrix1, ... ]
            unit[k] = Vector(m)
        mat_out.append(unit)
    return mat_out

def Matrix_location(prop, list=False):
    Vectors = []
    for p in prop:
        if list:
            Vectors.append(p.translation[:])
        else:
            Vectors.append(p.translation)
    return [Vectors]

def Matrix_scale(prop, list=False):
    Vectors = []
    for p in prop:
        if list:
            Vectors.append(p.to_scale()[:])
        else:
            Vectors.append(p.to_scale())
    return [Vectors]

# returns (Vector, rotation) utility function for Matrix Destructor. if list is true
# the Vector is decomposed into tuple format.
def Matrix_rotation(prop, list=False):
    Vectors = []
    for p in prop:
        q = p.to_quaternion()
        if list:
            vec,angle=q.to_axis_angle()
            Vectors.append(( vec[:], angle))
        else:
            Vectors.append(q.to_axis_angle())
    return [Vectors]

def Vector_generate(prop):
    return [[Vector(v) for v in obj] for obj in prop]

def Vector_degenerate(prop):
    vec_out = []
    for i, object in enumerate(prop):  # lists by objects
        veclist = []
        for v in object: # verts
            veclist.append((v[:]))
        vec_out.append(veclist)
    return vec_out

def Edg_pol_generate(prop):
    edg_pol_out = []
    if len(prop[0][0]) == 2:
        type = 'edg'
    elif len(prop[0]) > 2:
        type = 'pol'
    for ob in prop:
        list = []
        for p in ob:
            list.append(p)
        edg_pol_out.append(list)
    # [ [(n1,n2,n3), (n1,n7,n9), p, p, p, p...], [...],... ] n = vertexindex
    return type, edg_pol_out



def matrixdef(orig, loc, scale, rot, angle, vec_angle=[[]]):
    modif = []
    for i, de in enumerate(orig):
        ma = de.copy()

        if loc[0]:
            k = min(len(loc[0])-1,i)
            mat_tran = de.Translation(loc[0][k])
            ma *= mat_tran

        if vec_angle[0] and rot[0]:
            k = min(len(rot[0])-1,i)
            a = min(len(vec_angle[0])-1,i)

            vec_a = vec_angle[0][a].normalized()
            vec_b = rot[0][k].normalized()

            mat_rot = vec_b.rotation_difference(vec_a).to_matrix().to_4x4()
            ma = ma * mat_rot

        elif rot[0]:
            k = min(len(rot[0])-1,i)
            a = min(len(angle[0])-1,i)
            mat_rot = de.Rotation(radians(angle[0][a]), 4, rot[0][k].normalized())
            ma = ma * mat_rot

        if scale[0]:
            k = min(len(scale[0])-1,i)
            scale2=scale[0][k]
            id_m = Matrix.Identity(4)
            for j in range(3):
                id_m[j][j] = scale2[j]
            ma *= id_m

        modif.append(ma)
    return modif

#####################################################
#################### lists magic ####################
#####################################################

def create_list(x, y):
    if type(y) in [list, tuple]:
        return reduce(create_list,y,x)
    else:
        return x.append(y) or x

def preobrazovatel(list_a,levels,level2=1):
    list_tmp = []
    level = levels[0]

    if level>level2:
        if type(list_a)in [list, tuple]:
            for l in list_a:
                if type(l) in [list, tuple]:
                    tmp = preobrazovatel(l,levels,level2+1)
                    if type(tmp) in [list, tuple]:
                        list_tmp.extend(tmp)
                    else:
                        list_tmp.append(tmp)
                else:
                    list_tmp.append(l)

    elif level==level2:
        if type(list_a) in [list, tuple]:
            for l in list_a:
                if len(levels)==1:
                    tmp = preobrazovatel(l,levels,level2+1)
                else:
                    tmp = preobrazovatel(l,levels[1:],level2+1)
                list_tmp.append(tmp if tmp else l)

    else:
        if type(list_a) in [list, tuple]:
            list_tmp = reduce(create_list,list_a,[])

    return list_tmp


def myZip(list_all, level, level2=0):
    if level==level2:
        if type(list_all) in [list, tuple]:
            list_lens = []
            list_res = []
            for l in list_all:
                if type(l) in [list, tuple]:
                    list_lens.append(len(l))
                else:
                    list_lens.append(0)
            if list_lens==[]:return False
            min_len=min(list_lens)
            for value in range(min_len):
                lt=[]
                for l in list_all:
                    lt.append(l[value])
                t = list(lt)
                list_res.append(t)
            return list_res
        else:
            return False
    elif level>level2:
        if type(list_all) in [list, tuple]:
            list_res = []
            list_tr = myZip(list_all, level, level2+1)
            if list_tr==False:
                list_tr = list_all
            t = []
            for tr in list_tr:
                if type(list_tr) in [list, tuple]:
                    list_tl = myZip(tr, level, level2+1)
                    if list_tl==False:
                        list_tl=list_tr
                    t.extend(list_tl)
            list_res.append(list(t))
            return list_res
        else:
            return False


#####################################################
################### update List join magic ##########
#####################################################

def myZip_2(list_all, level, level2=1):
    def create_listDown(list_all, level):
        def subDown(list_a, level):
            list_b = []
            for l2 in list_a:
                if type(l2) in [list, tuple]:
                    list_b.extend(l2)
                else:
                    list_b.append(l2)
            if level>1:
                list_b = subDown(list_b, level-1)
            return list_b


        list_tmp = []
        if type(list_all) in [list, tuple]:
            for l in list_all:
                list_b = subDown(l, level-1)
                list_tmp.append(list_b)
        else:
            list_tmp = list_all
        return list_tmp

    list_tmp = list_all.copy()
    for x in range(level-1):
        list_tmp = create_listDown(list_tmp, level)

    list_r = []
    l_min = []

    for el in list_tmp:
        if type(el) not in [list, tuple]:
            break

        l_min.append(len(el))

    if l_min==[]: l_min=[0]
    lm = min(l_min)
    for elm in range(lm):
        for el in list_tmp:
            list_r.append(el[elm])

    list_tmp = list_r

    for lev in range(level-1):
        list_tmp=[list_tmp]

    return list_tmp


def joiner(list_all, level, level2=1):
    list_tmp = []

    if level>level2:
        if type(list_all) in [list, tuple]:
            for list_a in list_all:
                if type(list_a) in [list, tuple]:
                    list_tmp.extend(list_a)
                else:
                    list_tmp.append(list_a)
        else:
            list_tmp = list_all

        list_res = joiner(list_tmp, level, level2=level2+1)
        list_tmp = [list_res]

    if level==level2:
        if type(list_all) in [list, tuple]:
            for list_a in list_all:
                if type(list_a) in [list, tuple]:
                    list_tmp.extend(list_a)
                else:
                    list_tmp.append(list_a)
        else:
            list_tmp.append(list_all)

    if level<level2:
        if type(list_all) in [list, tuple]:
            for l in list_all:
                list_tmp.append(l)
        else:
            list_tmp.append(l)

    return list_tmp


def wrapper_2(l_etalon, list_a, level):
    def subWrap(list_a, level, count):
        list_b = []
        if level==1:
            if len(list_a)==count:
                for l in list_a:
                    list_b.append([l])
            else:
                dc=len(list_a)//count
                for l in range(count):
                    list_c = []
                    for j in range(dc):
                        list_c.append(list_a[l*dc+j])
                    list_b.append(list_c)
        else:
            for l in list_a:
                list_b = subWrap(l, level-1, count)
        return list_b

    def subWrap_2(l_etalon, len_l, level):
        len_r = len_l
        if type(l_etalon) in [list, tuple]:
            len_r = len(l_etalon) * len_l
            if level>1:
                len_r = subWrap_2(l_etalon[0], len_r, level-1)

        return len_r

    len_l = len(l_etalon)
    lens_l = subWrap_2(l_etalon, 1, level)
    list_tmp = subWrap(list_a, level, lens_l)

    for l in range(level-1):
         list_tmp = [list_tmp]
    return list_tmp

#####################################################
############### debug settings magic ################
#####################################################

def sverchok_debug(mode):
    global DEBUG_MODE
    DEBUG_MODE=mode
    return DEBUG_MODE

#####################################################
############### update system magic! ################
#####################################################


def updateNode(self, context):
    """
    When a node has changed state and need to call a partial update.
    For example a user exposed bpy.prop
    """
    global DEBUG_MODE
    a=time.time()
    speedUpdate(start_node = self)
    b=time.time()
    if DEBUG_MODE:
        print("Partial update from node",self.name,"in",round(b-a,4))

def make_update_list(ng,node_set = None):
    '''
    Temporary functions while testing for swithing implementation
    '''
    if USE_OLD: 
        return make_update_list_old(ng,node_set) 
    else: 
        return make_update_list_new(ng,node_set)   

def make_update_list_old(node_tree,node_set = None):
    """
    NOTE THIS IS THE OLD SLOW IMPLEMENTATION 
    Makes a list for updates from a node_group
    if a node set is passed only the subtree defined by the node set is used. 
    Otherwise the complete node tree is used.
    """
    deps = {}
    # get nodes, select root nodes, wifi nodes and create dependencies for each node
    # 70-80% of the time is in the first loop
    #  stack for traversing node graph
    tree_stack = collections.deque()
    wifi_out = []
    wifi_in = []
        
    ng = node_tree
    if not node_set: # if no node_set, take all
        node_set = set(ng.nodes.keys())
    for name,node in [(node_name,ng.nodes[node_name]) for node_name in node_set]:
        node_dep = []
        for socket in node.inputs:
            if socket.links and socket.links[0].from_node.name in node_set:
                if socket.links[0].is_valid:
                    node_dep.append(socket.links[0].from_node.name)
                else: #invalid node tree. Join nodes with F gives one instance of this, then ok
                    #print("Invalid Link in",node_tree,"!",socket.name,"->",socket.links[0].from_socket.name)
                    return []
        is_root = True
        for socket in node.outputs:
            if socket.links:
                is_root = False
                break
        # ignore nodes without input or outputs, like frames
        if node_dep or len(node.inputs) or len(node.outputs):
            deps[name]=node_dep
        if is_root and node_dep and not node.bl_idname == 'WifiInNode':
            tree_stack.append(name)
        if node.bl_idname == 'WifiOutNode':
            wifi_out.append(name)
        if node.bl_idname == 'WifiInNode':
            wifi_in.append(name)

    # create wifi out dependencies
    for wifi_out_node in wifi_out:
        wifi_dep = []
        for wifi_in_node in wifi_in:
            if ng.nodes[wifi_out_node].var_name == ng.nodes[wifi_in_node].var_name:
                wifi_dep.append(wifi_in_node)
        if wifi_dep:
            deps[wifi_out_node]=wifi_dep
        else:
            print("Broken Wifi dependency:",wifi_out_node,"-> var:",ng.nodes[wifi_out_node].var_name)
            return []

    if tree_stack:
        name = tree_stack.pop()
    else:
        if len(deps):
            tmp = list(deps.keys())
            name = tmp[0]
        else: # no nodes
            return []

    out = collections.OrderedDict()

    # travel in node graph create one sorted list of nodes based on dependencies
    node_count = len(deps)
    while node_count > len(out):
        node_dependencies = True
        for dep_name in deps[name]:
            if not dep_name in out:
                tree_stack.append(name)
                name = dep_name
                node_dependencies = False
                break
        if len(tree_stack) > node_count:
            print("Invalid node tree!")
            return []
        # if all dependencies are in out
        if node_dependencies:
            if not name in out:
                out[name]=1
                del deps[name]
            if tree_stack:
                name = tree_stack.pop()
            else:
                if node_count == len(out):
                    break
                for node_name in deps.keys():
                    name=node_name
                    break
    return list(out.keys())
    
# new 5 times quicker implementation

def make_update_list_new(node_tree,node_set = None):
    """ 
    Makes a list for updates from a node_group
    if a node set is passed only the subtree defined by the node set is used. Otherwise
    the complete node tree is used.
    """
    
    ng = node_tree
    
    if not node_set: # if no node_set, take all
        node_set = set(ng.nodes.keys())
    
    if len(node_set) == 1:
        return list(node_set)
        
    deps = {name:set() for name in node_set}
    root_set = set()
    for link in ng.links:
        if not link.is_valid:
            return [] #this happens more often than one might think
        t_node = link.to_node
        t_name = t_node.name
        f_name = link.from_node.name
        if t_name in node_set:
            is_root = not any((s.links for s in t_node.outputs))
            if f_name in node_set:
                deps[t_name].add(f_name)
            if is_root and t_node.bl_idname != 'WifiInNode':
                root_set.add(t_node.name)  
    
    #  stack for traversing node graph
    tree_stack = collections.deque(root_set)
    
    # create wifi out dependencies, process if needed
    wifi_out_nodes = [(name,node.var_name) for name,node in ng.nodes.items() 
                       if node.bl_idname == 'WifiOutNode' and name in node_set ]
    if wifi_out_nodes:
        wifi_dict = {node.var_name:name for name,node in ng.nodes.items() 
                        if node.bl_idname == 'WifiInNode'}
        for name,var_name in wifi_out_nodes:
            if not var_name in wifi_dict:
                print("Unsatisifed Wifi dependency: node, {0} var,{1}".format(name,var_name))
                return []
            deps[name].add(wifi_dict[var_name])

    if tree_stack:
        name = tree_stack.pop()
    else:
        if len(deps):
            tmp = deps.popitem()
            name = tmp[0]
        else: # no nodes
            return []

    out = collections.OrderedDict()

    # travel in node graph create one sorted list of nodes based on dependencies
    node_count = len(deps)
    while node_count > len(out):
        node_dependencies = True
        for dep_name in deps[name]:
            if not dep_name in out:
                tree_stack.append(name)
                name = dep_name
                node_dependencies = False
                break
        if len(tree_stack) > node_count:
            print("Invalid node tree!")
            return []
        # if all dependencies are in out
        if node_dependencies:
            if not name in out:
                out[name]=1
            if tree_stack:
                name = tree_stack.pop()
            else:
                if node_count == len(out):
                    break
                for node_name in deps.keys():
                    if not node_name in out:
                        name=node_name
                        break

    return list(out.keys())

def separate_nodes(ng):
    ''' 
    Separate a node group (layout) into unconnected parts
    Arguments: Node group
    Returns: A list of sets with separate node groups
    '''
    node_links = { name:set() for name in ng.nodes.keys()}
    nodes=set(ng.nodes.keys())
    if not nodes:
        return []
    for index,link in ng.links.items():
        if not link.is_valid:
            return []
        f_name=link.from_node.name
        t_name=link.to_node.name
        node_links[f_name].add(t_name)
        node_links[t_name].add(f_name)
    wifi_dict = {node.var_name:name for name,node in ng.nodes.items() if node.bl_idname == 'WifiInNode'}
    wifi_out_nodes = [(name,node.var_name) for name,node in ng.nodes.items() if node.bl_idname == 'WifiOutNode']
    for name,var_name in wifi_out_nodes:
        if not var_name in wifi_dict:
            print("Unsatisifed Wifi dependency: node, {0} var,{1}".format(name,var_name))
            return []
        node_links[name].add(wifi_dict[var_name])
        node_links[wifi_dict[var_name]].add(name)
    n= nodes.pop()
    node_set_list = [set([n])]
    node_stack = collections.deque()
    # find separate sets
    while nodes:
        for node in node_links[n]:
            if not node in node_set_list[-1]:
                node_stack.append(node)
        if not node_stack: # new part
            n=nodes.pop()
            node_set_list.append(set([n]))
        else:
            while  n in node_set_list[-1] and node_stack:
                n = node_stack.pop()
            nodes.discard(n)
            node_set_list[-1].add(n)
    return node_set_list


def make_tree_from_nodes(node_names,tree_name):
    """
    Create a partial update list from a sub-tree, node_names is a list of node that
    drives change for the tree
    Only nodes downtree from node_name are updated
    """
    ng = bpy.data.node_groups[tree_name]
    nodes = ng.nodes
    if not node_names:
        print("No nodes!")
        return make_update_list(ng)
    
    out_set = set(node_names)
    current_node = node_names.pop()
    out_stack = node_names[:]
    wifi_out = []
    # build the set of nodes that needs to be updated
    while current_node:
        if nodes[current_node].bl_idname == 'WifiInNode':
            if not wifi_out:  # build only if needed
                wifi_out = [name for name,node in nodes.items() if node.bl_idname == 'WifiOutNode']
            var_name = nodes[current_node].var_name
            for wifi_out_node in wifi_out:
                if nodes[wifi_out_node].var_name == var_name:
                    if not wifi_out_node in out_set:
                        out_stack.append(wifi_out_node)
                        out_set.add(wifi_out_node)
        for socket in nodes[current_node].outputs:
            if socket.links:
                for link in socket.links:
                    if not link.to_node.name in out_set:
                        out_set.add(link.to_node.name)
                        out_stack.append(link.to_node.name)
        if out_stack:
            current_node = out_stack.pop()
        else:
            current_node = ''
    return make_update_list(ng,out_set)


# to make update tree based on node types and node names bases
# no used yet
# should add a check do find animated or driven nodes.
def make_animation_tree(node_types,node_list,tree_name):
    global list_nodes4update
    ng = bpy.data.node_groups[tree_name]
    node_set = set(node_list)
    for n_t in node_types:
        node_set = node_set | {name for name in ng.nodes.keys() if ng.nodes[name].bl_idname == n_t}
    a_tree = make_tree_from_nodes(list(node_set),tree_name)
    return a_tree
    
def create_update_list(ng):
    '''
    Create update list with separate node groups in layouts
    '''
    split = separate_nodes(ng)
    out = [make_update_list(ng,s) for s in split]
    return out

def makeTreeUpdate2(tree=None):
    """ makes a complete update list for the tree_name, or all node trees"""
    global list_nodes4update
    global partial_update_cache
    global socket_data_cache
    # clear cache on every full update
    
    if tree != None:
        list_nodes4update[tree.name] = create_update_list(tree)
        partial_update_cache[tree.name] = {}
        socket_data_cache[tree.name] = {}
    else:
        for name,ng in bpy.data.node_groups.items():
            if ng.bl_idname == 'SverchCustomTreeType':
                list_nodes4update[name]=create_update_list(ng)
                partial_update_cache[name] = {}
                socket_data_cache[name] = {}    



def do_update_debug(node_list,nods):
    global DEBUG_MODE
    timings =[]
    for nod_name in node_list:
        if nod_name in nods:
            delta=None
            try:
                start = time.perf_counter()
                nods[nod_name].update()
                delta = time.perf_counter()-start
            except Exception as e:
                print("Node {0} had exception {1}".format(nod_name,e))
            if delta:  
                print("Updated  {0} in:{1}".format(nod_name,round(delta,4)))  
                timings.append((nod_name,delta))
    
                
# master update function, has several different modes

def speedUpdate(start_node = None, tree = None, animation_mode = False):
    global list_nodes4update
    global socket_data_cache
    global DEBUG_MODE

    def do_update_normal(node_list,nods):
        for nod_name in node_list:
            if nod_name in nods:
                nods[nod_name].update()
    
    if not DEBUG_MODE:
        do_update=do_update_normal
    else:
        do_update=do_update_debug
        
    
    # try to update optimized animation trees, not ready, needs to be redone
    if animation_mode:
        pass
    # start from the mentioned node the, called from updateNode
    if start_node != None:
        tree = start_node.id_data
        if tree.name in list_nodes4update and list_nodes4update[tree.name]:
            update_list = None
            if tree.name in partial_update_cache:
                if start_node in partial_update_cache[tree.name]:
                    update_list= partial_update_cache[tree.name][start_node.name]
            if not update_list:
                update_list = make_tree_from_nodes([start_node.name],tree.name)
                partial_update_cache[tree.name][start_node.name]=update_list
            nods = tree.nodes
            do_update(update_list,nods)
            return
        else:
            makeTreeUpdate2(tree)
            do_update(list_nodes4update[tree.name],tree.nodes)
            return
    # draw the complete named tree, called from SverchokCustomTreeNode
    # we flatten this update lists for now, refactoring in progress
    if tree != None:
        if not tree.name in list_nodes4update:
            makeTreeUpdate2(tree)
        do_update(itertools.chain.from_iterable(list_nodes4update[tree.name]),tree.nodes)
        return

    # update all node trees
    for name,ng in bpy.data.node_groups.items():
        if ng.bl_idname == 'SverchCustomTreeType':
            do_update(itertools.chain.from_iterable(list_nodes4update[name]),ng.nodes)

def get_update_lists(ng):
    global list_nodes4update
    global partial_update_cache
    
    return (list_nodes4update[ng.name],partial_update_cache[ng.name])

##############################################################
##############################################################
############## changable type of socket magic ################
########### if you have separate socket solution #############
#################### wellcome to provide #####################
##############################################################
##############################################################

# node has to have self veriables:
# self.typ = bpy.props.StringProperty(name='typ', default='')
# self.newsock = bpy.props.BoolProperty(name='newsock', default=False)
# and in update:
# inputsocketname = 'data' # 'data' - name of your input socket, that defines type
# outputsocketname = ['dataTrue','dataFalse'] # 'data...' - are names of your sockets to be changed
# changable_sockets(self, inputsocketname, outputsocketname)

def check_sockets(self, inputsocketname):
    if type(self.inputs[inputsocketname].links[0].from_socket) == bpy.types.VerticesSocket:
        if self.typ == 'v':
            self.newsock = False
        else:
            self.typ = 'v'
            self.newsock = True
    if type(self.inputs[inputsocketname].links[0].from_socket) == bpy.types.StringsSocket:
        if self.typ == 's':
            self.newsock = False
        else:
            self.typ = 's'
            self.newsock = True
    if type(self.inputs[inputsocketname].links[0].from_socket) == bpy.types.MatrixSocket:
        if self.typ == 'm':
            self.newsock = False
        else:
            self.typ = 'm'
            self.newsock = True
    return

# cleaning of old not fited
def clean_sockets(self, outputsocketname):
    for n in outputsocketname:
        if n in self.outputs:
            self.outputs.remove(self.outputs[n])
    return

# main def for changable sockets type
def changable_sockets(self, inputsocketname, outputsocketname):
    if len(self.inputs[inputsocketname].links) > 0:
        check_sockets(self, inputsocketname)
        if self.newsock:
            clean_sockets(self, outputsocketname)
            self.newsock = False
            if self.typ == 'v':
                for n in outputsocketname:
                    self.outputs.new('VerticesSocket', n, n)
            if self.typ == 's':
                for n in outputsocketname:
                    self.outputs.new('StringsSocket', n, n)
            if self.typ == 'm':
                for n in outputsocketname:
                    self.outputs.new('MatrixSocket', n, n)
        else:
            self.newsock = False
    return

def get_socket_type(node, inputsocketname):
    if type(node.inputs[inputsocketname].links[0].from_socket) == bpy.types.VerticesSocket:
        return 'v'
    if type(node.inputs[inputsocketname].links[0].from_socket) == bpy.types.StringsSocket:
        return 's'
    if type(node.inputs[inputsocketname].links[0].from_socket) == bpy.types.MatrixSocket:
        return 'm'
    
def get_socket_type_full(node, inputsocketname):
   # this is solution, universal and future proof.
    return node.inputs[inputsocketname].links[0].from_socket.bl_idname
     # it is real solution, universal
    #if type(node.inputs[inputsocketname].links[0].from_socket) == bpy.types.VerticesSocket:
    #    return 'VerticesSocket'
    #if type(node.inputs[inputsocketname].links[0].from_socket) == bpy.types.StringsSocket:
    #    return 'StringsSocket'
    #if type(node.inputs[inputsocketname].links[0].from_socket) == bpy.types.MatrixSocket:
    #    return 'MatrixSocket'


       
###########################################
# Multysocket magic / множественный сокет #
###########################################

#     utility function for handling n-inputs, for usage see Test1.py
#     for examples see ListJoin2, LineConnect, ListZip
#     min parameter sets minimum number of sockets
#     setup two variables in Node class
#     create Fixed inputs socket, the multi socket will not change anything
#     below min
#     base_name = 'Data '
#     multi_socket_type = 'StringsSocket'

def multi_socket(node , min=1, start=0, breck=False, output=False):
    '''
     min - integer, minimal number of sockets, at list 1 needed
     start - integer, starting socket.
     breck - boolean, adding brecket to nmae of socket x[0] x[1] x[2] etc
     output - integer, deal with output, if>0 counts number of outputs multy sockets
     base name added in separated node in self.base_name = 'some_name', i.e. 'x', 'data'
     node.multi_socket_type - type of socket, added in self.multi_socket_type 
     as one of three sverchok types 'StringsProperty', 'MatricesProperty', 'VerticesProperty'
     
    '''
    #probably incorrect state due or init or change of inputs
    # do nothing
    if not len(node.inputs):
        return
    if min < 1:
        min = 1
    if not output:
        if node.inputs[-1].links:
            length = start + len(node.inputs)
            if breck:
                name = node.base_name + '[' + str(length) + ']'
            else:
                name = node.base_name + str(length)
            node.inputs.new(node.multi_socket_type, name, name)
        else:
            while len(node.inputs)>min and not node.inputs[-2].links:
                node.inputs.remove(node.inputs[-1])
    else:
        lenod=len(node.outputs)
        if lenod<output:
            length = output-lenod
            for n in range(length):
                if breck:
                    name = node.base_name + '[' + str(n+lenod-1) + ']'
                else:
                    name = node.base_name + str(n+lenod-1)
                node.outputs.new(node.multi_socket_type, name, name)
        else:
            while len(node.outputs)>output:
                node.outputs.remove(node.outputs[-1])
        

#####################################
# node and socket id functions      #
#####################################



# socket.name is not unique... identifier is
def socket_id(socket):
    #return hash(socket)
    return hash(socket.id_data.name+socket.node.name+socket.identifier)

# For when need a key for use with dict in node
#  create a string property like this.
#  n_id =  StringProperty(default='')
# And a copy function 
#  def copy(self,node)
#      self.n_id=''
# the always use like this 
# n_id = node_id(self)
# node_dict[n_id]['key']

def node_id(node):
    if not node.n_id:
        node.n_id=str(hash(node)^hash(time.monotonic()))
    return node.n_id


#####################################
# socket data cache                 #
#####################################


def SvGetSocketAnyType(self, socket):

    out = SvGetSocket(socket)
    if out :
        return out
    else:
        return []

def SvSetSocketAnyType(self, socket_name, out):
    SvSetSocket(self.outputs[socket_name],out)
    return

# faster than builtin deep copy for us.
# useful for our limited case
# we should be able to specify vectors here to get them create
# or stop destroying them when in vector socket.

def sv_deep_copy(lst):
    if isinstance(lst,(list,tuple)):
        if lst and not isinstance(lst[0],(list,tuple)):
            return lst[:]
        return [sv_deep_copy(l) for l in lst]
    return lst

# Build string for showing in socket label

def SvGetSocketInfo(socket):    
    def build_info(data):
        if not data:
            return str(data)
        #if isinstance(data,list):
            #return '['+build_info(data[0])
        #elif isinstance(data,tuple):
            #return '('+build_info(data[0])
        else:
            return str(data)
    global socket_data_cache
    ng = socket.id_data.name
    if socket.is_output:
        s_id = socket_id(socket)
    elif socket.links:
        s_id = socket_id(socket.links[0].from_socket)
    else:
        return ''
    if ng in socket_data_cache:
        if s_id in socket_data_cache[ng]:
            data=socket_data_cache[ng][s_id]
            if data:        
                return str(len(data))
    return ''
        
def SvSetSocket(socket, out):
    global socket_data_cache
    s_id = socket_id(socket)
    s_ng = socket.id_data.name
    if not s_ng in socket_data_cache:
        socket_data_cache[s_ng]={}
    socket_data_cache[s_ng][s_id]=out

def SvGetSocket(socket, copy = False):
    global socket_data_cache
    global DEBUG_MODE
    if socket.links:
        other = socket.links[0].from_socket
        s_id = socket_id(other)
        s_ng = other.id_data.name
        if not s_ng in socket_data_cache:
            return None
        if s_id in socket_data_cache[s_ng]:
            out = socket_data_cache[s_ng][s_id]
            if copy:
                return out.copy()
            else:
                return sv_deep_copy(out)
        else: # failure, should raise error in future
            if DEBUG_MODE:
#                traceback.print_stack()
                print("cache miss:",socket.node.name,"->",socket.name,"from:",other.node.name,"->",other.name)
    return None


####################################
# быстрый сортировщик / quick sorter
####################################

def svQsort(L):
    if L: return svQsort([x for x in L[1:] if x<L[0]]) + L[0:1] + svQsort([x for x in L[1:] if x>=L[0]])
    return []


