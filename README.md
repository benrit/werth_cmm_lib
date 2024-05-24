# Werth Lib

this is a library to generate DMIS code from python. This library is not complete yet, many features still needs to be implemented. But is is usable.

## Example:

``` Python
import werth

with open("c:/temp/inspection.dms", "w") as file:
    w = werth.Werth(file.write, "00304198-plate", show_start_gui=True)
    # w = werth.Werth(print)
    probe = werth.Probe(w, werth.probes["Probe0.7"])

    P0 = werth.Point(w, "P0", x=0.0, y=0.0, z=8.0, theoretical=True)
    werth.Goto(w, z=5, relativeTo=P0, probe=probe)
    werth.Alignment(w, "Coordi1").translate().X(P0).Y(P0).Z(P0)

    SP = werth.Plane(w, "SP", 0.0, 0.0, 5.0, theoretical=True)

    Pln1 = werth.M_Plane(w, "Pln1", 0.0, 0.0, 0.0, saftey_plane=SP, probe=probe)
    Pln1.add_point(3.0, 3.0, 0.0)
    Pln1.add_point(3.0, 47.0, 0.0)
    Pln1.add_point(142.0, 47.0, 0.0)
    Pln1.add_point(142.0, 3.0, 0.0)

    werth.Alignment(w, "Coordi2").rotate().ZDIR(Pln1)
    werth.Alignment(w, "Coordi3").translate().Z(Pln1)

    Lin1 = werth.M_Line(w, "Lin1", x=3, y=0.0, z=-4.0, i=1.0, j=0.0, k=0.0, len=139, angle=-90, probe=probe, saftey_plane=SP)
    Lin1.add_points(3, probe=probe)

    werth.Alignment(w, "Coordi4").rotate().ZAXIS().XDIR(Lin1)

    Lin2 = werth.M_Line(w, "Lin2", x=0, y=3.0, z=-4.0, i=0.0, j=1.0, k=0.0, len=44, angle=90, probe=probe, saftey_plane=SP)
    Lin2.add_points(3, probe=probe)

    pnt1 = werth.T_Intersection(w, "pnt1", Lin1, Lin2)
    
    werth.Alignment(w, "Coordi5").translate().X(pnt1).Y(pnt1)

    P1 = werth.Point(w, "P1", x=13.16, y=8.5, z=-3.1, theoretical=True)
    werth.Alignment(w, "Coordi6").translate().X(P1).Y(P1).Z(P1)

    werth.Protokol_open(w, f"P:/results/{w._name}/00304198_60092786-2.txt")
 
    p = werth.Pattern(w, "Pat1")

    p.linear(x=0.0, y=0.0, z=0.0, i=1.0, j=0.0, k=0.0, count=10, offset=12.5)
    p.linear(x=6.25, y=11.0, z=0.0, i=1.0, j=0.0, k=0.0, count=10, offset=12.5)
    p.linear(x=0.0, y=22.0, z=0.0, i=1.0, j=0.0, k=0.0, count=10, offset=12.5)
    p.linear(x=6.25, y=33.0, z=0.0, i=1.0, j=0.0, k=0.0, count=10, offset=12.5)


    # # Cir2 = werth.Circle(p, "Cir2", diameter=14.8, x=0.0, y=0.0, z=-1.5, circle_type=Circle_Type.OUTER, probe=probe, saftey_plane=SP)
    # # Cir2.add_points(count=3)
    # # werth.Output(p, "Cir2", Cir2).Diameter(0.01, -0.01)
    
    werth.Call(p, "P:/Programs_Werth/0030/00304198/M_00304198.dms")
    werth.Endpoint(p, 0.0, 0.0, 8.0, probe=probe, saftey_plane=SP)
    
    
    werth.Protokol_close(w)


    werth.Endpoint(w, 0.0, 50.0, 50.0, probe=probe, saftey_plane=SP)
    
    w.generate()

```