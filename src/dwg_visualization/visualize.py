import ezdxf
import matplotlib.pyplot as plt

doc = ezdxf.readfile("data/swissbuildings3d_3_0_2019_1052-34_2056_5728.dwg/swissBUILDINGS3D_3-0_solid_1052-34.dwg")
msp = doc.modelspace()
msp = doc.modelspace()

for e in msp:
    print(e.dxftype())
xs, ys = [], []
for e in msp.query("LINE"):
    xs.extend([e.dxf.start.x, e.dxf.end.x, None])  # None breaks the polyline
    ys.extend([e.dxf.start.y, e.dxf.end.y, None])

plt.figure()
plt.plot(xs, ys)
plt.axis("equal")
plt.show()
