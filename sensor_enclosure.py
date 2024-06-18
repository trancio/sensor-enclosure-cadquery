#!/usr/bin/env python3
""" Enclousere for PCB

The dimensions of the enclusure depend on the
parameters of the PCB

Optional features:
   - mount tabs
   - ventilation holes
   - holes (rectangular, circular, sensor)
"""

import tomllib
import sys
import cadquery as cq

#############
# Parameters
#############

CONFIG_FILE = 'enclosures.toml'
SELECTED_ENCLOSURE = 'wemos_d1_mini_sensor'

with open(CONFIG_FILE, 'rb') as f:
    try:
        config = tomllib.load(f)[SELECTED_ENCLOSURE]
    except tomllib.TOMLDecodeError as e:
        if __name__ == '__main__':
            # Write error message to terminal
            print(f'Invalid TOML configuration in {CONFIG_FILE}')
            print(e)
            sys.exit(1)
        else:
            # Write error message to log viewer pane of ca-editor
            log(f'Invalid TOML configuration in {CONFIG_FILE}')
            log(e)

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
rounding_cover_bottom_edges = general_config['rounding_cover_bottom_edges']
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
if top_perforation or x_side_perforation or y_side_perforation:
    vent_hole_diameter = perforation_config['vent_hole_diameter']
    grid_density = perforation_config['grid_density']

# Circular connector
circular = circular_config['circular']
if circular:
    circular_diameter = circular_config['diameter']
    circular_from_pcb_plane = circular_config['from_pcb_plane']
    circular_from_pcb_corner = circular_config['from_pcb_corner']
    circular_faces = circular_config['faces']

# Rectangular connector
rectangular = rectangular_config['rectangular']
if rectangular:
    rectangular_height = rectangular_config['height']
    rectangular_width = rectangular_config['width']
    rectangular_from_pcb = rectangular_config['from_pcb']
    rectangular_from_pcb_corner = rectangular_config['from_pcb_corner']
    rectangular_faces = rectangular_config['faces']

# Circular hole at top
sensor = sensor_config['sensor']
if sensor:
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
if mounts:
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
MAX_DENSITY = 0.50
min_density = 1 / ((inner_depth - z_forbidden_zone) / vent_hole_diameter)
grid_density = max(grid_density, min_density)
grid_density = min(grid_density, MAX_DENSITY)
if rounding_radius >= wall:
    rounding_radius = wall - 0.01

##########
# Objects
##########


def lid_base():
    """Create base plate w/wo mounting tabs"""

    mount_tab_width = 5 * mount_bolt_diameter
    lid_thickness = lid_bolt_head_length
    points = [(0, -width / 2), (length / 2, -width / 2)]
    if mounts:
        points += [(length / 2, -mount_tab_width / 2),
                   ((length + mount_tab_width) / 2, -mount_tab_width / 2),
                   ((length + mount_tab_width) / 2, mount_tab_width / 2),
                   (length / 2, mount_tab_width / 2)]
    points += [(length / 2, width / 2), (0, width / 2)]
    base = cq.Workplane('front')
    base = base.polyline(points).close()
    if mounts:
        base = base.moveTo(
            (length + mount_tab_width) / 2 - 1.2 * mount_bolt_diameter, 0)
        base = base.rect(mount_bolt_diameter,
                         mount_tab_width - 2 * mount_bolt_diameter)
    base = base.mirrorY()
    base = base.extrude(lid_thickness)
    if rounding_cover_bottom_edges:
        base = base.edges('<Z').fillet(rounding_radius)
    return base


def lid_bolts(base):
    """Add bolt-holes to base plate

    Parameters
    ----------
    base : base plate object

    Returns
    -------
    base : base plate object with holes
    """

    base = base.faces('<Z').workplane()
    hole_pos = [length - 2 * x_padding, width - 2 * y_padding]
    if bolts_nr == 2:
        if bolts_mirror:
            base = base.pushPoints([(hole_pos[0] / 2, -hole_pos[1] / 2),
                                    (-hole_pos[0] / 2, hole_pos[1] / 2)])
        else:
            base = base.pushPoints([(hole_pos[0] / 2, hole_pos[1] / 2),
                                    (-hole_pos[0] / 2, -hole_pos[1] / 2)])
    else:
        base = base.rect(hole_pos[0], hole_pos[1], forConstruction=True)
        base = base.vertices()
    base = base.cboreHole(lid_bolt_diameter, lid_bolt_head_diameter,
                          lid_bolt_head_length)
    return base


def lid():
    """Create lid with bolt-holes, w/wo mounting tabs"""

    base = lid_base()
    base = base.faces('>Z').rect(length - 2 * wall, width - 2 * wall)
    base = base.rect(length - 2 * (x_padding - tolerance),
                     width - 2 * (x_padding - tolerance))
    base = base.extrude(pcb_lid_dist - gap_z)
    base = lid_bolts(base)
    return base


def grid_params(s_length, s_width):
    """Calculate grid parameters

    Parameters
    ----------
    s_length : float
        Length of side or top
    s_width : float
        Width of side or top

    Returns
    -------
    distance : float
        Distance of the ventilation holes
    l_count : float
        The number of holes in longitudinal direction
    w_count : float
        The number fo holes in the other direction
    """

    distance = vent_hole_diameter / grid_density
    l_count = int(s_length / distance)
    w_count = int(s_width / distance)
    return distance, l_count, w_count


def perf(box, face):
    """Perforate the enclosure

    Parameters
    ----------
    box : enclosure object
    face : string
        The side to be perforated

    Returns
    -------
    box : perforated enclosure object
    """

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
    """Create screw posts in the enclosure

    Parameters
    ----------
    box : enclosure object

    Returs
    ------
    box : enclosure obect with screw posts
    """

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
    """Calculate auxiliary parameters for perforation

    Parameteres
    -----------
    faces : face of the enclosure object

    Returns
    -------
    aux_gap : float
        Gap between holes
    aux_length : float
        Length of the perforation area
    """

    if 'Y' in faces:
        aux_gap = gap_y
        aux_length = inner_length
    else:
        aux_gap = gap_x
        aux_length = inner_width
    return aux_gap, aux_length


def circular_hole(box):
    """Create circular hole on side

    Parameters
    ----------
    box : enclosure object

    Return
    ------
    box : enclosure object with circular hole
    """

    circular_dist = circular_from_pcb_plane + pcb_thick + gap_z + pcb_lid_dist
    aux_gap, aux_length = get_aux_parameters(circular_faces)
    x_origin = aux_length / 2 - aux_gap - circular_from_pcb_corner
    y_origin = depth / 2 - circular_dist
    box = box.faces(circular_faces).workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.circle(circular_diameter / 2 + wall).extrude(-wall)
    box = box.faces(circular_faces).workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.hole(circular_diameter, depth=wall)
    return box


def rectangular_hole(box):
    """Create rectangular hole on side

    Parameters
    ----------
    box : enclosure object

    Return
    ------
    box : enclosure object with rectangular hole
    """

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
    """Create sensor hole on top

    Parameters
    ----------
    box : enclosure object

    Return
    ------
    box : enclosure object with circular hole on top
    """

    x_origin = inner_length / 2 - sensor_distance_from_x_edge - gap_x
    y_origin = -inner_width / 2 + sensor_distance_from_y_edge + gap_y
    box = box.faces('<Z').workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.circle(sensor_hole_diameter / 2 + wall).extrude(-wall)
    box = box.faces('<Z').workplane(centerOption='CenterOfBoundBox')
    box = box.moveTo(x_origin, y_origin)
    box = box.hole(sensor_hole_diameter)
    return box


def enclosure():
    """Create enclosure

    Returns
    -------
    box : enclosure object

    """

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
    cq.exporters.export(lid(), f'{SELECTED_ENCLOSURE}-lid.stl')
    cq.exporters.export(enclosure(), f'{SELECTED_ENCLOSURE}-box.stl')
else:
    assy = cq.Assembly()
    assy.add(enclosure(),
             name='box',
             loc=cq.Location(cq.Vector(0, 0, 0)),
             color=cq.Color('yellow'))
    assy.add(lid(),
             name='lid',
             loc=cq.Location(cq.Vector(0, pcb_width + 10, 0)),
             color=cq.Color('green'))
    show_object(assy, name=f'{SELECTED_ENCLOSURE}-enclosure')
