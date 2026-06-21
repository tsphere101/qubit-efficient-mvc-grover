import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        return np.min(zs)

fig = plt.figure(figsize=(9, 9))
ax = fig.add_subplot(111, projection='3d')
ax.set_axis_off()

# --- Sphere Geometry ---
u = np.linspace(0, 2 * np.pi, 100)
v = np.linspace(0, np.pi, 100)
x_sphere = np.outer(np.cos(u), np.sin(v))
y_sphere = np.outer(np.sin(u), np.sin(v))
z_sphere = np.outer(np.ones(np.size(u)), np.cos(v))

ax.plot_surface(x_sphere, y_sphere, z_sphere, color='skyblue', alpha=0.08, linewidth=0)
ax.plot_wireframe(x_sphere, y_sphere, z_sphere, color='gray', alpha=0.1, linewidth=0.5)

# Equators
theta_line = np.linspace(0, 2*np.pi, 100)
ax.plot(np.cos(theta_line), np.sin(theta_line), 0, color='gray', alpha=0.4, lw=1, linestyle='--') 
ax.plot(np.cos(theta_line), np.zeros(100), np.sin(theta_line), color='gray', alpha=0.4, lw=1, linestyle='--') 

# --- Axes Lines ---
axis_draw_len = 1.15
ax.plot([-axis_draw_len, axis_draw_len], [0, 0], [0, 0], color='black', alpha=0.7, lw=1)
ax.plot([0, 0], [-axis_draw_len, axis_draw_len], [0, 0], color='black', alpha=0.7, lw=1)
ax.plot([0, 0], [0, 0], [-axis_draw_len, axis_draw_len], color='black', alpha=0.7, lw=1)

# --- Capital Axis Labels (X, Y, Z) ---
# ax.text(1.3, 0, 0, r'$\mathbf{X}$', fontsize=14, fontweight='normal', va='center', ha='center')
# ax.text(0, 1.3, 0, r'$\mathbf{Y}$', fontsize=14, fontweight='normal', va='center', ha='center')
# ax.text(0, 0, 1.3, r'$\mathbf{Z}$', fontsize=14, fontweight='normal', va='center', ha='center')

# --- Basis Kets with New Offsets ---
# Z-basis: |0> shifted right (x-direction) to avoid overlapping with Z
ax.text(0.2, 0, 1.45, r'$|0\rangle$', fontsize=20, ha='left')
ax.text(0, 0, -1.6, r'$|1\rangle$', fontsize=20, ha='center')

# X-basis: Pushed further out
ax.text(1.7, 0, 0, r'$|+\rangle$', fontsize=16, color='darkblue', va='center', ha='center')
ax.text(-1.7, 0, 0, r'$|-\rangle$', fontsize=16, color='darkblue', va='center', ha='center')

# Y-basis: Pushed further out
ax.text(0, 1.7, 0, r'$|i\rangle$', fontsize=16, color='darkgreen', va='center', ha='center')
ax.text(0, -1.7, 0, r'$|-i\rangle$', fontsize=16, color='darkgreen', va='center', ha='center')

# --- State Vector |\psi\rangle (Unit Length) ---
theta_val = np.pi / 3  
phi_val = np.pi / 4    
vector_scale = 5
vx = np.sin(theta_val) * np.cos(phi_val) * vector_scale
vy = np.sin(theta_val) * np.sin(phi_val) * vector_scale
vz = np.cos(theta_val) * vector_scale

arrow_prop = dict(mutation_scale=20, arrowstyle='-|>', color='crimson', shrinkA=0, shrinkB=0, lw=4, zorder=10)
psi_arrow = Arrow3D([0, vx], [0, vy], [0, vz], **arrow_prop)
ax.add_artist(psi_arrow)

# ax.text(vx*1.15, vy*1.15, vz*1.15, r'$|\psi\rangle$', color='crimson', fontsize=18, fontweight='normal')

# --- View Settings ---
limit = 1.9 # Increased limit to accommodate further offsets
ax.set_xlim([-limit, limit])
ax.set_ylim([-limit, limit])
ax.set_zlim([-limit, limit])
ax.view_init(elev=20, azim=45)
ax.set_box_aspect([1, 1, 1])

fig.savefig('bloch_sphere_2.jpg', dpi=300, bbox_inches='tight')