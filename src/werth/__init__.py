import os
import datetime as dt
import numpy as np
from enum import Enum, IntEnum
from typing import overload


probes = {
    "Master" : {"name": "MProbe4_0", "diameter": 8.0},
    "Probe0.7" : {"name": "MProbe4_9", "diameter": 0.7},
    "Probe1.5" : {"name": "MProbe4_10", "diameter": 1.5}
}


class Werth:
    _elements = None
    _tempco = 0.00001150
    _w3d_deflection = 0.05
    _writer = None
    _saftey_plane = None

    def __init__(self, writer):
        self._elements = []
        self._writer = writer

    def add(self, element):
        self._elements.append(element)

    def set_safty_plane(self, saftey_plane):
        self._saftey_plane = saftey_plane

    def unroll(self, element, obj):
          for item in element:
            if type(item) == obj:
                self._writer(item.definition())
            if type(item) == Pattern:
                self.unroll(item._elements, obj)


    def generate(self):
        self._writer(header())
        self._writer(algo_definitions())
        
        self.unroll(self._elements, Call)
        
        self._writer("FILNAM / 'P:\\Programs_Werth\\test\\Gauge_Ring.dms'\n")
        self._writer(f"TECOMP / ON, {self._tempco:.8f}\n")
        self._writer(f"W3D / DEFLECTION, {self._w3d_deflection:.8f}\n")

        self.unroll(self._elements, Probe)
        

        for item in self._elements:
            self._writer(str(item))

        
        self._writer("ENDFIL")

        
class Probe:
    _name = ""
    _diameter = 0.0
    _search = 2.0
    _approach = 2.0
    _algo = ""
    _scan_speed = 1.5
    _deflection = 0.065

    def __init__(self, w: Werth, probe):
        self._name = probe['name']
        self._diameter = probe['diameter']

        w.add(self)

    def definition(self):
        return f"S({self._name}) = SNSDEF / PROBE, FIXED, CART, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000,0.00000000, 0.00000000\n"
   

    def set_deflection(self, value):
        if value < 0.0 or value > 1.0:
            return
        
        self._deflection = value
    
    def __str__(self) -> str:
        return ""

def header():

    now = dt.datetime.now()

    return f"""
$$ DMIS file generated by Python
BEGIN / CHFILE
	TYPE = MAIN
	VERSION = L-9.44.00.0064.00.08 C:\Werth\Werth\Winwerth
	DATE = {now.strftime("%d.%m.%y")}
	TIME = {now.strftime("%H:%M:%S")}
	MAJORVERSION = 9
	MINORVERSION = 440000640008
	MC-VERSION = MoSeS V8.44.00.0009.00.01
	USER = Guest
	TEACHEDIT = YES
	SENSORCHECK = Yes
END / CHFILE\n\n"""


def units(length="MM", angle="ANGDEC"):
    return f"UNITS / {length}, {angle}\n"
 

def algo_definitions():
    return """\
$$ algorithm definitions
VA(PROBE) = ALGDEF / CODE, 1600
VA(SCAN_NOMGEO_6503) = ALGDEF / CODE, 6503
VA(SCAN_SPEED) = ALGDEF / CODE, 6130
VA(SCAN_DEV_EXT) = ALGDEF / CODE, 6140
VA(SCAN_NOMGEO_6500) = ALGDEF / CODE, 6500
"""


def chr_element(name:str, element:str):
    return f"""T({name}) = TOL / DIAM, 0.20000000, -0.20000000
OUTPUT / F({element}), T({name})\n"""

class Circle_Type(Enum):
    INNER = "INNER"
    OUTER = "OUTER"


class Circle:
    _id = ""
    _diameter = 0.0
    _start_angle = 0
    _angle = 360
    _probe: Probe = None
    _saftey_plane = None
    _circle_type: Circle_Type = None

    _points = None

    _position = None
    _vector = None

    _output = None

    def __init__ (self, w:Werth, name, diameter, x=0.0, y=0.0, z=0.0, circle_type: Circle_Type=None, probe: Probe=None, saftey_plane=None):
        if circle_type == None:
            raise ValueError("no circle type secified Circle_Type.INNER or Circle_Type.OUTER")
        
        self._circle_type = circle_type
        self._id = name
        self._diameter = diameter

        self._position = np.array([x, y, z])
        self._vector = np.array([0.0, 0.0, 1.0])

        self._probe = probe
        self._saftey_plane = saftey_plane if saftey_plane else w._saftey_plane
        self._points = []

        w.add(self)


    def add_points(self, start_angle=0.0, angle_range=360.0, count=8, angles: list=None, probe=None, move_to_saftey_plane=False):
        probe = probe if probe else self._probe
        if angles:
            for a in angles:
                self._points({"type": "single", "angle": a, "probe": probe, "MTSP": move_to_saftey_plane})
        else:
            angle_step = angle_range / count
            angle = start_angle
            for _ in range(count):
                self.add_point(angle=angle, probe=probe, move_to_saftey_plane=move_to_saftey_plane)
                angle += angle_step


    def add_point(self, angle=None, dx=0.0, dy=0.0, probe=None, move_to_saftey_plane=False):
        probe = probe if probe else self._probe
        if angle != None:
            self._points.append({"type": "single", "angle": angle, "dx": dx, "dy": dy, "probe": probe, "MTSP": move_to_saftey_plane})


    def add_scan(self, start_angle=0.0, angle_range=360.0):
        circumstances = self._diameter * np.pi
        ar = angle_range / 360.0

        count = round(circumstances * ar) + 1
        angle_step = (angle_range / count) 

        self._points.append({"type": "scan", "angles": [start_angle + (angle_step * a) for a in range(count + 1)]})
    
        
    def move_to(self):
        pass


    def calc_support_points(self, angle, angle_step, num_point):
        
        a_step = angle_step / num_point
        support_point_start_angle = (angle - angle_step) + a_step
        pl = []
        for _ in range(num_point):
            pl.append({"type": "support", "angle": support_point_start_angle})
            support_point_start_angle += a_step
        return pl
    

    def add_support_points(self):
        pl = []
        if len(self._points) > 0:
            # adding support points
            
            for index, point in enumerate(self._points):
                if point['type'] == "scan":
                    pl.append(point)
                    continue

                if index == 0:
                    angle_step = point['angle']

                if point["type"] == "single":
                    angle = point['angle']
                    angle_step = angle - angle_step
                    
                    if index !=0: pl.append({"type": "support", "angle": angle - angle_step})
                    if not point["MTSP"]: 
                        num_point = round((((self._diameter * 3.1415) / 360) * angle_step) / 3 ) 
                        if num_point > 0:
                            pl.extend(self.calc_support_points(angle, angle_step, num_point + 1))

                pl.append(point)
                angle_step = angle

        return pl


    def calc_point_position(self, angle):
        rad = np.radians(angle)
        i = np.cos(rad)
        j = np.sin(rad)
        p = np.array([i, j, 0]) * (self._diameter / 2)
        v = np.array([i, j, 0]) if self._circle_type.name == "OUTER" else np.array([i, j, 0]) * -1

        return (p, v)
    

    def tolerance(self, Diameter=None, xPos=None, yPos=None):
        if Diameter:
            pass
        


    def __str__(self) -> str:

        radius = self._diameter / 2.0
        circle_x = self._position[0]
        circle_y = self._position[1]
        circle_z = self._position[2]

        temp = f"F({self._id}) = FEAT / CIRCLE, {self._circle_type.value}, CART, {circle_x:.8f}, {circle_y:.8f}, {circle_z:.8f}, 0.00000000, 0.00000000, 1.00000000, {radius:.8f}\n"
        temp +="MODE / PROG\n"
        temp +=f"POINTDIST / PARAMS, FA({self._id})\n"
        
        point_list = self.add_support_points()


        for index, point in enumerate(point_list):
                
            if point['type'] == "single":
                
                p, v = self.calc_point_position(point['angle'])

                if index == 0:
                    temp += "PIEZOWFP / OFF\n"
                    temp += f"MEAS / CIRCLE, F(Cir_1), {len(self._points)}\n"
                
                temp += "SNSET / VA(SCAN_NOMGEO_6500)\n"
                temp += f"SNSLCT / S({self._probe._name})\n"
                temp += f"SNSET / SEARCH, {self._probe._search}\n"
                temp += f"SNSET / APPRCH, {self._probe._approach}\n"
                
                if index == 0 and self._saftey_plane or point['MTSP']: 
                    temp +=f"CZSLCT / CZ({self._saftey_plane._id}), ON, FIX\n"

                vi = v * -1
                pa = p + self._position
                temp += f"PTMEAS / CART, {pa[0]:.8f}, {pa[1]:.8f}, {pa[2]:.8f}, {vi[0]:.8f}, {vi[1]:.8f}, {vi[2]:.8f}\n"

       
            elif point['type'] == "support":
                p, v = self.calc_point_position(point['angle'])
                approach = self._probe._approach + (self._probe._diameter / 2)
                pa = p + self._position
                temp += f"GOTO / {pa[0] + (approach * v[0]):.8f}, {pa[1] + (approach * v[1]):.8f}, {pa[2] + (approach * v[2]):.8f}\n"
            
            elif point['type'] == "scan":
                
                if index == 0:
                    temp +="SPLINESCAN3D / PARAMS, 0.10000000, 0.02000000, 5.00000000, 0.10000000, 50.00000000, 1, 0\n"
                    temp +="SCANFILTER / ON, 0.80000000, 0.00500000\n"
                    temp +="PIEZOWFP / OFF\n"
                    temp +=f"MEAS / CIRCLE, F({self._id}), {len(point['angles'])}\n"

                for index, d in enumerate(point['angles']):
                    # FIXME
                    i = np.cos(np.radians(d))
                    j = np.sin(np.radians(d))
                    x = (radius * i) + circle_x
                    y = (radius * j) + circle_y
                    z = circle_z

                    temp +="SNSET / VA(SCAN_NOMGEO_6503)\n"
                    temp +=f"SNSLCT / S({self._probe._name})\n"
                    temp +=f"SNSET / VA(SCAN_SPEED), {self._probe._scan_speed}\n"
                    temp +=f"SNSET / VA(SCAN_DEV_EXT), {self._probe._deflection}\n"
                    temp +=f"SNSET / SEARCH, {self._probe._search}\n"
                    temp +=f"SNSET / APPRCH, {self._probe._approach}\n"
                    if index == 0 and self._saftey_plane: temp += f"CZSLCT / CZ({self._saftey_plane._id}), ON, FIX\n"
                    temp +=f"PTMEAS / CART, {x:.8f}, {y:.8f}, {z:.8f}, {i*-1:.8f}, {j*-1:.8f}, 0.00000000\n"
        

        temp +="ENDMES\n\n"

        return temp
    

class Point:
    _id = ""
    _x=0.0
    _y=0.0
    _z=0.0
    _i=1.0
    _j=0.0
    _k=0.0

    _theoretical = False

    def __init__(self, w:Werth, name, x=0.0, y=0.0, z=0.0, theoretical = False, relativeTo=None):

        self._id = name
        
        if relativeTo:
            self._x = relativeTo._x + x
            self._y = relativeTo._y + y
            self._z = relativeTo._z + z
        else:
            self._x = x
            self._y = y
            self._z = z

        self._theoretical = theoretical

        w.add(self)

        
    def __str__(self) -> str:

        if self._theoretical:
            return f"FA({self._id}) = FEAT / POINT, CART, {self._x:.8f}, {self._y:.8f}, {self._z:.8f}, {self._i:.8f}, {self._j:.8f}, {self._k:.8f}\n\n"


class Plane:
    _id=""
    _x=0.0
    _y=0.0
    _z=0.0
    _theoretical=False
    _points = None
    _position = None
    _vector = None

    def __init__(self, w:Werth, name, x=0.0, y=0.0, z=0.0, i=0.0, j=0.0, k=0.0, theoretical = False):
        self._id = name
        self._x = x
        self._y = y
        self._z = z
        self._theoretical = theoretical
        self._points = []
        self._position = np.array([x, y, z])
        self._vector = np.array([i, j, k])
    
        w.add(self)

    def add_point(self, x=0.0, y=0.0, z=0.0, dx=None, dy=None, dz=None):
        x = x if not dx else self._x + dx
        y = y if not dx else self._y + dy
        z = z if not dx else self._z + dz
        print(f"[PLANE] {self._id} x: {x}\ty: {y}\tz: {z}")
        self._points.append({"x": x, "y": y, "z": z})
        


    def __str__(self):
        if self._theoretical:
            return f"FA({self._id}) = FEAT / PLANE, CART, {self._x:.8f}, {self._y:.8f}, {self._z:.8f}, 0.00000000, 0.00000000, 1.00000000\n\n"
        else:
            return ""


class Goto:
    _x = 0.0
    _y = 0.0
    _z = 0.0
    _probe = None
    def __init__(self, w: Werth, x=0.0, y=0.0, z=0.0, relativeTo: Point=None, probe: Probe=None):

        self._probe = probe

        if relativeTo:
            self._x = relativeTo._x + x
            self._y = relativeTo._y + y
            self._z = relativeTo._z + z
        else:
            self._x = x
            self._y = y
            self._z = z


        w.add(self)


    def __str__(self):
        temp = f"SNSLCT / S({self._probe._name})\n"
        temp += f"GOTO / {self._x:.8f}, {self._y:.8f}, {self._z:.8f}\n\n"
        return temp


class Translate:
    _parent = None
    _x = None
    _y = None
    _z = None

    def __init__(self, parent):
        self._parent = parent

    def __str__(self) -> str:
        t=[]
        temp = "WKPLAN / NONE \n"
        temp += f"D({self._parent._id}) = TRANS / "
        if self._x: t.append(f"XORIG, FA({self._x._id})")
        if self._y: t.append(f"YORIG, FA({self._y._id})")
        if self._z: t.append(f"ZORIG, FA({self._z._id})")
        temp += ", ".join(t)
        temp += "\n\n"

        return temp

    def X(self, element):
        self._x = element
        return self

    def Y(self, element):
        self._y = element
        return self

    def Z(self, element):
        self._z = element
        return self


class Rotate:
    _parent = None
    _dir = None
    _axis = "XAXIS"
    _element = None

    def __init__(self, parent):
        self._parent = parent

    def __str__(self) -> str:
        t=[]
        temp = "WKPLAN / NONE \n"
        temp += f"D({self._parent._id}) = ROTATE / "
        temp += f"{self._axis}, FA({self._element._id}), {self._dir}"
        temp += "\n\n"

        return temp

    def XDIR(self, element):
        self._dir = "XDIR"
        self._element = element
        return self

    def YDIR(self, element):
        self._dir = "YDIR"
        self._element = element
        return self

    def ZDIR(self, element):
        self._dir = "ZDIR"
        self._element = element
        return self

    def ZAXIS(self):
        self._axis = "ZAXIS"
        return self
    

class Alignment:
    _id = None
    _w: Werth = None
    _item = None

    def __init__(self, w: Werth, name: str):
        self._id = name
        w.add(self)
        
    def Translate(self) -> Translate:
        self._item = Translate(self)
        return self._item
    
    def Rotate(self) -> Rotate:
        self._item = Rotate(self)
        return self._item
    
    def __str__(self) -> str:

        return str(self._item)
    

class M_Line:
    _id = None
    _len = None
    _angle = None
    _probe = None
    _saftey_plane = None
    _points = None   
    _position = None
    _vector = None


    def __init__(self, w: Werth, name: str, x: float, y: float, z: float, i: float, j: float, k: float, len: float, angle: float, probe: Probe = None, saftey_plane=None) -> None:
        self._id = name
        self._angle = angle
        self._points = []
        self._probe = probe
        self._saftey_plane = saftey_plane

        self._position = np.array([x, y, z])
        self._vector = np.array([i, j, k])
        self._len = len

        w.add(self)

    def add_point(self, x: float, y: float, z: float, probe=None, move_to_saftey_plane=None):
        probe = probe if probe else self._probe
        move_to_saftey_plane = move_to_saftey_plane if move_to_saftey_plane else self._saftey_plane

        v = np.array([0.0, 0.0, 1.0])
        k = self._vector #np.array([self._i, self._j, self._k])
        p = np.radians(self._angle)
        vrot = v*np.cos(p) + (np.cross(k, v)*np.sin(p)) + k*(np.dot(k, v))*(1-p)
        point = (k * x) + self._position

        self._points.append({"type": "single", "x": point[0], "y": point[1], "z": point[2], "i": vrot[0], "j": vrot[1], "k": vrot[2], "probe": probe, "MTSP": move_to_saftey_plane})

    def add_points(self, count = 4, probe=None, move_to_saftey_plane=None):
        
        pos_step = self._len / (count - 1)
        pos = 0
        for i in range(count):
            self.add_point(pos, 0.0, 0.0, probe=probe, move_to_saftey_plane=move_to_saftey_plane)
            pos += pos_step
            

    def __str__(self) -> str:
        p = self._position
        v = self._vector
        temp = f"F({self._id}) = FEAT / LINE, UNBND,CART, {p[0]:.8f}, {p[1]:.8f}, {p[2]:.8f}, {v[0]:.8f}, {v[1]:.8f}, {v[2]:.8f}\n"
        temp += "MODE / PROG\n"
        temp += f"POINTDIST / PARAMS, FA({self._id})\n"
        temp += "PIEZOWFP / OFF\n"
        temp += f"MEAS / LINE, F({self._id}), {len(self._points)}\n"
        
        pre_point = None
        for index, point in enumerate(self._points):
            position = np.array([point['x'], point['y'], point['z']])
            vector = np.array([point['i'], point['j'], point['k']]) * -1
            approach = position + (vector * self._probe._approach ) + (vector * (self._probe._diameter / 2))

            temp += "SNSET / VA(SCAN_NOMGEO_6500)\n"
            temp += f"SNSLCT / S({self._probe._name})\n"
            temp += f"SNSET / SEARCH, {self._probe._search:.8f}\n"
            temp += f"SNSET / APPRCH, {self._probe._approach:.8f}\n"
            if index == 0: 
                temp += f"CZSLCT / CZ({self._saftey_plane._id}), ON, FIX\n"
            else:
                temp += f"GOTO / {pre_point[0]:.8f}, {pre_point[1]:.8f}, {pre_point[2]:.8f}\n"
                temp += f"GOTO / {approach[0]:.8f}, {approach[1]:.8f}, {approach[2]:.8f}\n"
            temp += f"PTMEAS / CART, {point['x']:.8f}, {point['y']:.8f}, {point['z']:.8f}, {point['i']:.8f}, {point['j']:.8f}, {point['k']:.8f}\n"

            pre_point = approach

        temp +="ENDMES\n\n"
        
        return temp
    

class M_Plane:
    _id = None
    _x = None
    _y = None
    _z = None
    _i = None
    _j = None
    _k = None
    _probe = None
    _saftey_plane = None
    _points = None
    _position = None
    _vector = None

    def __init__(self, w: Werth, name: str, 
                 x: float, 
                 y: float, 
                 z: float, 
                 i: float=0.0, 
                 j: float=0.0, 
                 k: float= 1.0, 
                 probe: Probe = None, 
                 saftey_plane = None) -> None:
        
        self._id = name
        self._x = x
        self._y = y
        self._z = z
        self._i = 0.0
        self._j = 0.0
        self._k = 1.0

        self._points = []
        self._probe = probe
        self._saftey_plane = saftey_plane
        self._position = np.array([x, y, z])
        self._vector = np.array([i, j, k])

        w.add(self)


    def add_point(self, x: float, y: float, z: float, probe=None, move_to_saftey_plane=False):
        probe = probe if probe else self._probe

        self._points.append({"type": "single", "x": x, "y": y, "z": z, "i": self._i*-1, "j": self._j*-1, "k": self._k*-1, "probe": probe, "MTSP": move_to_saftey_plane})

    def __str__(self) -> str:
        
        temp = f"F({self._id}) = FEAT / PLANE, CART, {self._x:.8f}, {self._y:.8f}, {self._z:.8f}, {self._i:.8f}, {self._j:.8f}, {self._k:.8f}\n"
        temp += "MODE / PROG\n"
        temp += f"POINTDIST / PARAMS, FA({self._id})\n"
        temp += "PIEZOWFP / OFF\n"
        temp += f"MEAS / PLANE, F({self._id}), {len(self._points)}\n"
        
        pre_point = None
        for index, point in enumerate(self._points):
            position = np.array([point['x'], point['y'], point['z']])
            vector = np.array([point['i'], point['j'], point['k']]) * -1
            approach = position + (vector * self._probe._approach ) + (vector * self._probe._diameter)

            temp += "SNSET / VA(SCAN_NOMGEO_6500)\n"
            temp += f"SNSLCT / S({self._probe._name})\n"
            temp += f"SNSET / SEARCH, {self._probe._search:.8f}\n"
            temp += f"SNSET / APPRCH, {self._probe._approach:.8f}\n"
            if index == 0: 
                temp += f"CZSLCT / CZ({self._saftey_plane._id}), ON, FIX\n"
            else:
                temp += f"GOTO / {pre_point[0]:.8f}, {pre_point[1]:.8f}, {pre_point[2]:.8f}\n"
                temp += f"GOTO / {approach[0]:.8f}, {approach[1]:.8f}, {approach[2]:.8f}\n"
            temp += f"PTMEAS / CART, {point['x']:.8f}, {point['y']:.8f}, {point['z']:.8f}, {point['i']:.8f}, {point['j']:.8f}, {point['k']:.8f}\n"

            pre_point = approach

        temp +="ENDMES\n\n"
        
        return temp
    

class Output:
    _id = None
    _element = None
    _output = None
    
    def __init__(self, w: Werth, name, element) -> None:
        self._id = name
        self._element = element
        self._output = ""
        w.add(self)


    def Diameter(self, utol=0.0, ltol=0.0):
        # dia = dia if dia else self._element._diameter 
        temp = f"T({self._id}_D) = TOL / DIAM, {utol:.8f}, {ltol:.8f}\n"
        temp += f"OUTPUT / F({self._element._id}), T({self._id}_D)\n\n"
        self._output += temp
        return self
    
    def Roundess(self, utol=0.003):
        temp = f"T({self._id}_RN) = TOL / CIRLTY, {utol:.8f}, {0.0:.8f}\n"
        temp += f"OUTPUT / F({self._element._id}), T({self._id}_RN)\n\n"
        self._output += temp
        return self

    def xValue(self, nom=0.0, utol=0.015, ltol=-0.015):
        temp = f"T({self._id}_X) = TOL / DISTB, NOMINL, {nom:.8f}, {utol:.8f}, {ltol:.8f}, XAXIS\n"
        temp += f"OUTPUT / F({self._element._id}), T({self._id}_X)\n\n"
        self._output += temp
        return self

    def yValue(self, nom=0.0, utol=0.015, ltol=-0.015):
        temp = f"T({self._id}_Y) = TOL / DISTB, NOMINL, {nom:.8f}, {utol:.8f}, {ltol:.8f}, YAXIS\n"
        temp += f"OUTPUT / F({self._element._id}), T({self._id}_Y)\n\n"
        self._output += temp
        return self

    def zValue(self, nom=0.0, utol=0.015, ltol=-0.015):
        temp = f"T({self._id}_Z) = TOL / DISTB, NOMINL, {nom:.8f}, {utol:.8f}, {ltol:.8f}, ZAXIS\n"
        temp += f"OUTPUT / F({self._element._id}), T({self._id}_Z)\n\n"
        self._output += temp
        return self


    def __str__(self) -> str:
        return self._output
    

class Call:
    _programPath = None
    _filename = None

    def __init__(self, w: Werth, programPath: str) -> None:
        self._programPath = os.path.abspath(programPath)
        self._filename = os.path.basename(self._programPath).removesuffix(".dms")

        w.add(self)

    def definition(self):
        return f"INCLUDE / '{self._programPath}'\n\n"

    def __str__(self) -> str:
        return f"CALL / {self._filename}|1\n"
        

class Pattern:
    _name = None
    _pattern = None
    _werth = None
    _elements = None
    def __init__(self, w: Werth, name: str) -> None:
        self._name = name
        self._pattern = []
        self._werth = w        
        self._elements = []
        w.add(self)


    def linear(self, x: float, y: float, z: float, i: float, j: float, k: float, count: int, offset: float):

        p = np.array([x, y, z])
        v = np.array([i, j, k])
        
        self._pattern.extend([p + (v * (offset * i)) for i in range(count)])

    
    def add(self, element):
        self._elements.append(element)

    def rectengular(self):
        pass

    def __str__(self) -> str:
        loop_count = len(self._pattern)
        temp = "DMIS / REPEATSTART\n"
        temp += f"BEGIN / LOOPDEF, VARIABLE, (LOOP_{self._name}), {loop_count}, 0\n"
        temp += f"DECL / LOCAL, REAL, loop01Offset[{loop_count};3]\n"
        temp += f"DECL / LOCAL, INT, L1, iLoopEnd01\n\n"
        offsets = ",".join([f"{{{i[0]}, {i[1]}, {i[2]}}}" for i in self._pattern])
        temp += f"LET / $loop01Offset = {{{offsets}}}\n"
        temp += "END / LOOPDEF\n"

        temp += f"SAVE / D(LOOPCOOR_{self._name}), 3\n"
        temp += f"FOR / $L1 = 1, TO, {loop_count}\n"
        temp += f"SAVE / D(LOOPDAT_{self._name}), 3\n"
        temp += f"FC(LOOPELM_{self._name}) = FEAT / POINT, CART, $loop01Offset[$L1; 1], $loop01Offset[$L1; 2], $loop01Offset[$L1; 3], 0.0, 0.0, 0.0\n"
        temp += "WKPLAN / NONE\n"
        temp += f"D(LOOPDPT_{self._name}) = TRANS / XORIG, FA(LOOPELM_{self._name}), YORIG, FA(LOOPELM_{self._name}), ZORIG, FA(LOOPELM_{self._name})\n"
        temp += "TEXT / OUTPUT , 'OFFSET x:$loop01Offset[$L1;1], y:$loop01Offset[$L1;2], z:$loop01Offset[$L1;3]'\n"     

        for item in self._elements:

            temp += str(item)

        temp += "DMIS / REPEATEND\n"
        temp += f"RECALL / D(LOOPDAT_{self._name})\n"

        temp += "NEXT / $L1\n"
        temp += f"RECALL / D(LOOPCOOR_{self._name})"

        return temp


class Endpoint:
    _position = None
    _saftey_plane = None
    _probe = None

    def __init__(self,w: Werth, x: float, y: float, z: float, probe: Probe = None, saftey_plane=None) -> None:
        self._saftey_plane = saftey_plane if saftey_plane else w._saftey_plane
        self._probe = probe

        self._position = np.array([x, y, z])
        w.add(self)

    def __str__(self) -> str:
        temp = f"CZSLCT / CZ({self._saftey_plane._id}), ON, FIX\n"
        temp += f"SNSLCT / S({self._probe._name})\n"
        p = self._position
        temp += f"GOTO / {p[0]}, {p[1]}, {p[2]}\n\n"
        return temp
        