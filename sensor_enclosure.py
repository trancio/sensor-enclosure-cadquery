#!/usr/bin/env python3

import cadquery as cq
import tomllib

#################################################
# Enclousere for PCB created with CadQuery
#
# The dimensions of the enclusure depend on the
# parameters of the PCB
#
# Optional features:
#   - mount tabs
#   - ventilation holes
#   - holes for rectangular (rectangular, circular, sensor)
#################################################

#############
# Parameters
#############

with open('esp12f_sensor.toml', 'rb') as f:
    config = tomllib.load(f)
general_config = config['box']
perforation_config = config['perforation']
circular_config = config['circular_connector']
rectangular_config = config['rectangular_connector']
sensor_config = config['sensor_hole_at_top']
lid_config = config['lid_bolt']
mounting_config = config['mounting']

tolerance = general_config['tolerance']

# PCB
pcb_length = general_config['pcb_length']
pcb_width = general_config['pcb_width']
pcb_thick = general_config['pcb_thick']
pcb_hole_diameter = general_config['pcb_hole_diameter']
pcb_hole_corner_dist = general_config['pcb_hole_corner_dist']
pcb_lid_dist = general_config['pcb_lid_dist']

# Box
inner_depth = general_config['inner_depth']
wall = general_config['wall']
rounding_vertical_edges = general_config['rounding_vertical_edges']
rounding_top_edges = general_config['rounding_top_edges']
rounding_radius = general_config['rounding_radius']
# Gaps between PCB and box
gap_x = general_config['gap_x']
gap_y = general_config['gap_y']
# Gap between PCB and lid
gap_z = general_config['gap_z']

# Perforation
top_perforation = perforation_config['top_perforation']
x_side_perforation = perforation_config['x_side_perforation']
y_side_perforation = perforation_config['y_side_perforation']
vent_hole_diameter = perforation_config['vent_hole_diameter']
grid_density = perforation_config['grid_density']

# Circular connector
circular = circular_config['circular']
circular_diameter = circular_config['diameter']
circular_from_pcb_plane = circular_config['from_pcb_plane']
circular_from_pcb_corner = circular_config['from_pcb_corner']
circular_faces = circular_config['faces']

# Rectangular connector
rectangular = rectangular_config['rectangular']
rectangular_height = rectangular_config['height']
rectangular_width = rectangular_config['width']
rectangular_from_pcb = rectangular_config['from_pcb']
rectangular_from_pcb_corner = rectangular_config['from_pcb_corner']
rectangular_faces = rectangular_config['faces']

# Circular hole at top
sensor = sensor_config['sensor']
sensor_hole_diameter = sensor_config['hole_diameter']
sensor_distance_from_y_edge = sensor_config['distance_from_x_edge']
sensor_distance_from_x_edge = sensor_config['distance_from_y_edge']

# Lid
lid_bolt_head = lid_config['head']
lid_bolt_diameter = lid_config['bolt_diameter']
lid_bolt_head_diameter = lid_config['head_diameter']
lid_bolt_head_length = lid_config['head_length']
# bolts for Box and Lid assembly
bolts_nr = lid_config['nr']
bolts_mirror = lid_config['mirror']

# Mounting
mounts = mounting_config['mounts']
mount_bolt_diameter = mounting_config['bolt_diameter']

#######################
# Calculated parameters
#######################

aux_x_padding = gap_x + wall
aux_y_padding = gap_y + wall
x_padding = pcb_hole_corner_dist + aux_x_padding
y_padding = pcb_hole_corner_dist + aux_y_padding
length = pcb_length + 2 * aux_x_padding  # outer length
width = pcb_width + 2 * aux_y_padding  # outer width
depth = inner_depth + wall  # outher depth
inner_length = length - 2 * wall
inner_width = width - 2 * wall
# for perforation
x_forbidden_zone = gap_x + pcb_hole_corner_dist + pcb_hole_diameter
y_forbidden_zone = gap_y + pcb_hole_corner_dist + pcb_hole_diameter
z_forbidden_zone = pcb_lid_dist + gap_z + pcb_thick
max_density = 0.55
min_density = 1 / ((inner_depth - z_forbidden_zone) / vent_hole_diameter)
print(min_density)
grid_density = max(grid_density, min_density)
grid_density = min(grid_density, max_density)
if rounding_radius >= wall:
    rounding_radius = wall - 0.01

##########
# Objects
##########


def lid_base():
    mount_tab_width = 5 * mount_bolt_diameter
    lid_thickness = lid_bolt_head_length
    points = [(0, -width / 2), (length / 2, -width / 2)]
    if mounts:
        points += [(length / 2, -mount_tab_width / 2),
                   ((length + mount_tab_width) / 2, -mount_tab_width / 2),
                   ((length + mount_tab_width) / 2, mount_tab_width / 2),
                   (length / 2, mount_tab_width / 2)]
    points += [(length / 2, width / 2), (0, width / 2)]
    r = cq.Workplane('front')
    r = r.polyline(points).close()
    if mounts:
        r = r.moveTo(
            (length + mount_tab_width) / 2 - 1.2 * mount_bolt_diameter, 0)
        r = r.rect(mount_bolt_diameter,
                   mount_tab_width - 2 * mount_bolt_diameter)
    r = r.mirrorY()
    r = r.extrude(lid_thickness)
    return r


def lid_bolts(r):
    r = r.faces('<Z').workplane()
    hole_pos = [length - 2 * x_padding, width - 2 * y_padding]
    if bolts_nr == 2:
        if bolts_mirror:
            r = r.pushPoints([(hole_pos[0] / 2, -hole_pos[1] / 2),
                              (-hole_pos[0] / 2, hole_pos[1] / 2)])
        else:
            r = r.pushPoints([(hole_pos[0] / 2, hole_pos[1] / 2),
                              (-hole_pos[0] / 2, -hole_pos[1] / 2)])
    else:
        r = r.rect(hole_pos[0], hole_pos[1], forConstruction=True)
        r = r.vertices()
    r = r.cboreHole(lid_bolt_diameter, lid_bolt_head_diameter,
                    lid_bolt_head_length)
    return r


def lid():
    r = lid_base()
    r = r.faces('>Z').rect(length - 2 * wall, width - 2 * wall)
    r = r.rect(length - 2 * (x_padding - tolerance),
               width - 2 * (x_padding - tolerance))
    r = r.extrude(pcb_lid_dist - gap_z)
    if rounding_vertical_edges:
        r = r.edges('|Z').fillet(rounding_radius)
    r = lid_bolts(r)
    return r


def grid_params(length, width):
    distance = vent_hole_diameter / grid_density
    l_count = int(length / distance)
    w_count = int(width / distance)
    return distance, l_count, w_count


def perf(box, face):
    if face == '>X':
        distance, l_count, w_count = grid_params(
            inner_width - y_forbidden_zone, inner_depth - z_forbidden_zone)
    elif face == '>Y':
        distance, l_count, w_count = grid_params(
            inner_length - 2 * x_forbidden_zone,
            inner_depth - z_forbidden_zone)
    elif face == '>Z':
        distance, l_count, w_count = grid_params(
            inner_length - 2 * x_forbidden_zone,
            inner_width - y_forbidden_zone)
    else:
        return box
    box = box.faces(face).workplane(centerOption='CenterOfBoundBox')
    box = box.rarray(distance, distance, l_count, w_count)
    box = box.hole(vent_hole_diameter)
    if l_count > 1 and w_count > 1:
        box = box.rarray(distance, distance, l_count - 1, w_count - 1)
        box = box.hole(vent_hole_diameter)
    return box


def screw_posts(box):
    screw_post_length = inner_depth - pcb_lid_dist - pcb_thick - gap_z
    box = box.faces('<Z').workplane(wall, True)
    if bolts_nr == 4:
        box = box.rect(length - 2 * x_padding,
                       width - 2 * y_padding,
                       forConstruction=True)
        box = box.vertices()
    else:
        hole_pos = [length - 2 * x_padding, width - 2 * y_padding]
        if bolts_mirror:
            box = box.pushPoints([(hole_pos[0] / 2, -hole_pos[1] / 2),
                                  (-hole_pos[0] / 2, hole_pos[1] / 2)])
        else:
            box = box.pushPoints([(hole_pos[0] / 2, hole_pos[1] / 2),
                                  (-hole_pos[0] / 2, -hole_pos[1] / 2)])
    box = box.circle(pcb_hole_diameter).extrude(screw_post_length)
    box = box.faces('<Z').workplane(wall + screw_post_length, True)
    box = box.rect(length - 2 * x_padding,
                   width - 2 * y_padding,
                   forConstruction=True)
    box = box.vertices()
    box = box.hole(lid_bolt_diameter, depth=screw_post_length * 2 / 3)
    return box


def get_aux_parameters(faces):
    if 'Y' in faces:
        aux_gap = gap_y
        aux_length = inner_length
    else:
        aux_gap = gap_x
        aux_length = inner_width
    return aux_gap, aux_length


def circular_hole(box):
    circular_dist = circular_from_pcb_plane + pcb_thick + gap_z + pcb_lid_dist
    aux_gap, aux_length = get_aux_parameters(circular_faces)
    x_origin = aux_length / 2 - aux_gap - circular_from_pcb_corner
    y_origin = depth / 2 - circular_dist
    box = box.faces(circular_faces).workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.circle(circular_diameter / 2 + wall).extrude(-wall)
    box = box.faces(circular_faces).workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.hole(sensor_hole_diameter, depth=wall)
    return box


def rectangular_hole(box):
    rectangular_dist = rectangular_from_pcb + pcb_thick + gap_z + pcb_lid_dist
    aux_gap, aux_length = get_aux_parameters(rectangular_faces)
    x_origin = -aux_length / 2 + aux_gap + rectangular_from_pcb_corner
    y_origin = depth / 2 - rectangular_dist
    box = box.faces(rectangular_faces).workplane(
        centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.rect(rectangular_height + 2 * wall, rectangular_width + 2 * wall)
    box = box.extrude(-wall)
    aux = box.faces(rectangular_faces).workplane(
        centerOption='CenterOfBoundBox')
    aux = aux.moveTo(x_origin, y_origin)
    aux = aux.rect(rectangular_height, rectangular_width).extrude(-wall, False)
    box = box.cut(aux)
    return box


def sensor_hole(box):
    x_origin = inner_length / 2 - sensor_distance_from_x_edge - gap_x
    y_origin = -inner_width / 2 + sensor_distance_from_y_edge + gap_y
    box = box.faces('<Z').workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.circle(sensor_hole_diameter / 2 + wall).extrude(-wall)
    box = box.faces('<Z').workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.hole(sensor_hole_diameter)
    return box


def box():
    o_shell = cq.Workplane('front')
    o_shell = o_shell.rect(length, width).extrude(depth)
    if rounding_vertical_edges:
        o_shell = o_shell.edges('|Z').fillet(rounding_radius)
    if rounding_top_edges:
        o_shell = o_shell.edges('<Z').fillet(rounding_radius)
    i_shell = o_shell.faces('<Z').workplane(wall, True)
    i_shell = i_shell.rect(inner_length,
                           inner_width).extrude(inner_depth, False)
    box = o_shell.cut(i_shell)
    if x_side_perforation:
        box = perf(box, '>X')
    if y_side_perforation:
        box = perf(box, '>Y')
    if top_perforation:
        box = perf(box, '>Z')
    box = screw_posts(box)
    if circular:  # add circular hole
        box = circular_hole(box)
    if rectangular:  # add rectangular hole
        box = rectangular_hole(box)
    if sensor:  # add sensor hole
        box = sensor_hole(box)
    return box


if __name__ == '__main__':
    cq.exporters.export(lid(), 'lid.stl')
    cq.exporters.export(box(), 'box.stl')
else:
    assy = cq.Assembly()
    assy.add(box(),
             name='box',
             loc=cq.Location(cq.Vector(0, 0, 0)),
             color=cq.Color('yellow'))
    assy.add(lid(),
             name='lid',
             loc=cq.Location(cq.Vector(0, pcb_width + 10, 0)),
             color=cq.Color('green'))
    show_object(assy, name='enclosure')
