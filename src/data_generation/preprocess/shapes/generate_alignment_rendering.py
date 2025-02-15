"""
blener renderer
"""
import argparse
import bpy
import copy
import math
import mathutils
import numpy as np
import os 
import sys
#os.environ['CUDA_VISIBLE_DEVICES'] = '0'


def point_at(obj, target, roll=0):
    if not isinstance(target, mathutils.Vector):
        target = mathutils.Vector(target)
    loc = obj.location
    direction = target - loc
    quat = direction.to_track_quat('-Z', 'Y')
    quat = quat.to_matrix().to_4x4()
    rollMatrix = mathutils.Matrix.Rotation(roll, 4, 'Z')
    loc = loc.to_tuple()
    obj.matrix_world = quat @ rollMatrix
    obj.location = loc


def get_material_names():
    mats = bpy.data.materials
    mat_list = []
    for m in mats:
        if m.name.startswith('material_'):
            mat_list.append(m.name)
    return mat_list


def new_color_material(mat_name, color, shadow_mode='NONE'):
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    # principled_node = nodes.get('Principled BSDF')
    principled_node = nodes.new(type="ShaderNodeBsdfPrincipled")
    output_node = nodes.get("Material Output")
    principled_node.inputs.get("Base Color").default_value = color
    principled_node.inputs.get("Alpha").default_value = color[3]
    principled_node.inputs.get("Roughness").default_value = 1.0
    # principled_node.inputs.get("Emission Strength").default_value = 0
    link = links.new( principled_node.outputs['BSDF'], output_node.inputs['Surface'] )
    if color[-1] < 1:
        mat.blend_method = 'BLEND'
    mat.shadow_method = shadow_mode
    return mat


def spherical_to_cartesian(radius, azimuth, elevation):
    x = radius * math.cos(azimuth) * math.sin(elevation)
    y = radius * math.cos(elevation)
    z = radius * math.sin(azimuth) * math.sin(elevation)
    x_blender = x * 1.15
    y_blender = -z * 1.15
    z_blender = y * 1.15
    return (x_blender, y_blender, z_blender)


parser = argparse.ArgumentParser(description='Renders given obj file by rotation a camera around it.')
parser.add_argument('obj', type=str, help='Path to the obj file to be rendered.')
parser.add_argument('cam', type=str, help='Path to the cam pose file.')
argv = sys.argv[sys.argv.index("--") + 1:]
args = parser.parse_args(argv)
print('args.obj:' + args.obj)
print('args.cam:' + args.cam)

# set GPU render.
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'CUDA'
bpy.context.preferences.addons["cycles"].preferences.get_devices()
for d in bpy.context.preferences.addons["cycles"].preferences.devices:
    # only use GPU.
    # if 'GPU' not in d["name"]:
    #     d["use"] = 0 
    # else:
    #     d["use"] = 1
    d["use"] = 1
    print(d["name"], d["use"])

# set out size.
num_samples = 256
bpy.context.scene.render.resolution_x = 100
bpy.context.scene.render.resolution_y = 100
bpy.context.scene.render.film_transparent = True
bpy.context.scene.view_settings.view_transform = 'Standard'

# load obj files.
cube = bpy.data.objects['Cube']
cube.select_set(True)
bpy.ops.object.delete()
lig = bpy.data.objects['Light']
lig.select_set(True)
bpy.ops.object.delete()
bpy.ops.import_scene.obj(filepath=args.obj)

# set nodes.
bpy.context.scene.use_nodes = True
tree = bpy.context.scene.node_tree
links = tree.links
for n in tree.nodes:
    tree.nodes.remove(n)
# set bg white.
render_layers = tree.nodes.new('CompositorNodeRLayers')
alpha_node = tree.nodes.new(type="CompositorNodeAlphaOver")
alpha_node.premul = 1
output_node_img = tree.nodes.new(type='CompositorNodeOutputFile')
output_node_img.format.color_mode = 'RGBA'
output_node_img.format.file_format = 'PNG'
links.new(render_layers.outputs['Image'], alpha_node.inputs[2])
links.new(alpha_node.outputs['Image'], output_node_img.inputs[0])

# set output path.
output_node_img.base_path = args.obj.replace('models/uvmapped_v2.obj', 'images/')
if not os.path.exists(output_node_img.base_path):
    os.makedirs(output_node_img.base_path)

# set lights
focus_point = [0,0,0]
light_distance = 5
light_names = ['Light_front', 'Light_back', 'Light_left', 'Light_right', 'Light_top', 'Light_bottom']
light_locations = []
for i in range(3):
    light_location = focus_point[:]
    light_location[i] -= light_distance
    light_locations.append(light_location)
    light_location = focus_point[:]
    light_location[i] += light_distance
    light_locations.append(light_location)
for i in range(len(light_names)):
    light_data = bpy.data.lights.new(name=light_names[i], type='POINT')
    light_data.energy = 500
    light_object = bpy.data.objects.new(name=light_names[i], object_data=light_data)
    bpy.context.collection.objects.link(light_object)
    bpy.context.view_layer.objects.active = light_object
    light_object.location = light_locations[i]

# set obj materials.
mat_list = get_material_names()
for mat in mat_list:
    tar_color = (0,0,0)
    new_color_material(mat, [tar_color[0] / 255., tar_color[1] / 255., tar_color[2] / 255., 1.])

# set camera.
cam = bpy.data.objects['Camera']
cam_poses = np.load(args.cam)
print(cam_poses.shape)
for i in range(cam_poses.shape[0]):
    cam.location = spherical_to_cartesian(2, cam_poses[i][1], cam_poses[i][2])
    point_at(cam, (0., 0., 0.))
    output_node_img.file_slots[0].path = f'fov=50,theta={cam_poses[i][1]},phi={cam_poses[i][2]}_'
    print(output_node_img.file_slots[0].path)
    bpy.ops.render.render(write_still=True)