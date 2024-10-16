from scipy.constants import mu_0 as u0
from scipy.constants import pi

from matplotlib import pyplot as plt
import numpy as np

from pmd_beamphysics import FieldMesh

def set_axes_equal(ax):

    limits = np.array([ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()])
    
    # Find the max range for all axes
    max_range = np.abs(limits[:, 1] - limits[:, 0]).max() / 2.0
    
    # Calculate midpoints for all axes
    mid_x = np.mean(limits[0])
    mid_y = np.mean(limits[1])
    mid_z = np.mean(limits[2])
    
    # Set limits to be centered and equal in range
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)

def plot_3d_vector(v, 
                   origin=np.array([0,0,0]), 
                   plot_arrow=True,
                   plot_line=False,
                   ax=None, 
                   color='b', 
                   elev=45, 
                   azim=-45):

    # Create a new figure and 3D axes if none are provided
    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        
    if plot_arrow and not plot_line:
        
        # Plot the vector as an arrow
        ax.quiver(
            origin[0], origin[1], origin[2],  # Starting point of the vector
            v[0], v[1], v[2],  # Vector components (dx, dy, dz)
            arrow_length_ratio=0.2,  # Controls the size of the arrowhead
            color=color,  # Color of the vector (blue)
            linewidth=2  # Line width for the vector
        )
        
    elif not plot_arrow and plot_line:
        ax.plot(origin, v, color=color)
        
    else:

        r = v + origin
        ax.scatter(r[0], r[1], r[2])
    
    ax.view_init(elev=elev, azim=azim)

    return ax


def bfield_from_thin_straight_wire(x, y, z, p1, p2, current, plot_wire=False, elev=45, azim=-45, ax=None, return_axes=False):
    
    """
    Calculate the magnetic field generated by a thin, straight current-carrying wire at specified points in 3D space.

    Parameters
    ----------
    x, y, z : ndarray
        Arrays representing the x, y, and z coordinates of the points where the magnetic field is to be computed [m].
        
    p1 : array_like
        The 3D coordinates [x, y, z] of one end of the wire [m].
        
    p2 : array_like
        The 3D coordinates [x, y, z] of the other end of the wire [m].
        
    current : float
        The current flowing through the wire in Amperes [A].
        
    plot_wire : bool, optional
        If True, plots the wire geometry and the field points in 3D space. Default is False.
        
    elev : float, optional
        The elevation angle (in degrees) for the 3D plot. Default is 45 degrees.
        
    azim : float, optional
        The azimuth angle (in degrees) for the 3D plot. Default is -45 degrees.
        
    ax : matplotlib.axes._subplots.Axes3DSubplot, optional
        The axis object on which to plot the wire geometry. If None, a new figure and axis will be created. Default is None.

    Returns
    -------
    Bx, By, Bz : ndarray
        Arrays representing the magnetic field components along the x, y, and z axes at each specified point, with the same shape as the input coordinates [T].
        
    """
    
    # Convert input points to numpy arrays
    p1 = np.array(p1)     # three vector defining beginning of current element
    p2 = np.array(p2)     # three vector defining end of current element
    
    # Ensure the wire is specified by two distinct points
    assert np.linalg.norm(p2 - p1) > 0, 'Line must be specified by 2 distinct points'

    # Create a grid of observation points
    P = np.stack((x, y, z), axis=-1)  # Shape (Nx, Ny, Nz, 3)

    # Vector from p1 to p2 (the wire direction)
    L = p2 - p1
    Lhat = L / np.linalg.norm(L)  # Unit vector along the wire

    # Project P onto the line p1p2 to find the nearest point on the line to P
    tmin = np.dot(P - p1, Lhat)  # Shape (Nx, Ny, Nz)
    lmin = p1 + tmin[..., np.newaxis] * Lhat  # Shape (Nx, Ny, Nz, 3)

    # Calculate the vectors e1, e2, e3
    e1 = Lhat  # Shape (3,)
    e2 = P - lmin
    e2_norm = np.linalg.norm(e2, axis=-1, keepdims=True)
    e2 = e2 / e2_norm  # Normalize e2
    e3 = np.cross(e1, e2)  # Cross product to find e3, shape (Nx, Ny, Nz, 3)

    # Calculate x1 and x2
    x1 = np.dot(p1 - lmin, e1)  # Shape (Nx, Ny, Nz)
    x2 = np.dot(p2 - lmin, e1)  # Shape (Nx, Ny, Nz)

    # Distance R from the line to the point P
    R = e2_norm[..., 0]  # Shape (Nx, Ny, Nz)

    # Calculate the magnetic field magnitude B0
    B0 = (u0 * current / (4 * pi * R)) * (x2 / np.sqrt(x2**2 + R**2) - x1 / np.sqrt(x1**2 + R**2))  # Shape (Nx, Ny, Nz)

    # Final magnetic field vector at each point
    B = B0[..., np.newaxis] * e3  # Shape (Nx, Ny, Nz, 3)

    if plot_wire:
        ax = plot_3d_vector(p2-p1, p1, plot_arrow=True, color='k', elev=45, azim=-45, ax=ax)
        
        ax.set_xlabel('x (m)')
        ax.set_ylabel('y (m)')
        ax.set_zlabel('z (m)')

    if plot_wire and return_axes:
        B[:,:,:,0], B[:,:,:,1], B[:,:,:,2], ax

    else:
        return B[:,:,:,0], B[:,:,:,1], B[:,:,:,2]


def bfield_from_thin_rectangular_coil(X, Y, Z, a, b, y0, current, plot_wire=False, elev=45, azim=-45, ax=None):

    """
    Calculate the magnetic field generated by a thin, rectangular current-carrying coil at specified points in 3D space.

    Parameters
    ----------
    X, Y, Z : ndarray
        Arrays representing the x, y, and z coordinates of the points where the magnetic field is to be computed [m].
        
    a : float
        The horizontal size of the rectangular coil (length along the x-axis) [m].
        
    b : float
        The longitudinal size of the rectangular coil (length along the z-axis) [m].
        
    y0 : float
        The y-coordinate of the coil, representing the vertical position of the coil [m].
        
    current : float
        The current flowing through the rectangular coil in Amperes [A].
        
    plot_wire : bool, optional
        If True, plots the coil geometry and the field points in 3D space. Default is False.
        
    elev : float, optional
        The elevation angle (in degrees) for the 3D plot. Default is 45 degrees.
        
    azim : float, optional
        The azimuth angle (in degrees) for the 3D plot. Default is -45 degrees.
        
    ax : matplotlib.axes._subplots.Axes3DSubplot, optional
        The axis object on which to plot the coil geometry. If None, a new figure and axis will be created. Default is None.

    Returns
    -------
    Bx, By, Bz : ndarray
        Arrays representing the magnetic field components along the x, y, and z axes at each specified point, with the same shape as the input coordinates [T].
    """
    
    p1 = np.array([-a/2, y0, -b/2])
    p2 = np.array([+a/2, y0, -b/2])
    p3 = np.array([+a/2, y0, +b/2])
    p4 = np.array([-a/2, y0, +b/2])
    
    Bx1, By1, Bz1 = bfield_from_thin_straight_wire(X, Y, Z, p1, p2, current, plot_wire=False, elev=elev, azim=azim)    
    Bx2, By2, Bz2 = bfield_from_thin_straight_wire(X, Y, Z, p2, p3, current, plot_wire=False, elev=elev, azim=azim)
    Bx3, By3, Bz3 = bfield_from_thin_straight_wire(X, Y, Z, p3, p4, current, plot_wire=False, elev=elev, azim=azim)
    Bx4, By4, Bz4 = bfield_from_thin_straight_wire(X, Y, Z, p4, p1, current, plot_wire=False, elev=elev, azim=azim)

    if plot_wire:
            
        ax = plot_3d_vector(p2-p1, p1, plot_arrow=True, color='k', elev=elev, azim=azim, ax=ax)
        ax = plot_3d_vector(p3-p2, p2, plot_arrow=True, color='k', elev=elev, azim=azim, ax=ax)
        ax = plot_3d_vector(p4-p3, p3, plot_arrow=True, color='k', elev=elev, azim=azim, ax=ax)
        ax = plot_3d_vector(p1-p4, p4, plot_arrow=True, color='k', elev=elev, azim=azim, ax=ax) 

        ax.set_xlabel('x (m)')
        ax.set_ylabel('y (m)')
        ax.set_zlabel('z (m)')
    
    return (Bx1+Bx2+Bx3+Bx4, By1+By2+By3+By4, Bz1+Bz2+Bz3+Bz4)


def bfield_from_thin_rectangular_corrector(X, Y, Z, a, b, h, current, plot_wire=False, elev=45, azim=-45, ax=None):

    """
    Calculate the magnetic field generated by a thin, rectangular air-core corrector magnet at specified points in 3D space.

    Parameters
    ----------
    X, Y, Z : ndarray
        Arrays representing the x, y, and z coordinates of the points where the magnetic field is to be computed [m].
        
    a : float
        The horizontal size of the rectangular corrector (length along the x-axis) [m].
        
    b : float
        The longitudinal size of the rectangular corrector (length along the z-axis) [m].
        
    h : float
        The vertical separation between the two rectangular coils (distance along the y-axis) [m].
        
    current : float
        The current flowing through the rectangular corrector in Amperes [A].
        
    plot_wire : bool, optional
        If True, plots the coil geometry and the field points in 3D space. Default is False.
        
    elev : float, optional
        The elevation angle (in degrees) for the 3D plot. Default is 45 degrees.
        
    azim : float, optional
        The azimuth angle (in degrees) for the 3D plot. Default is -45 degrees.
        
    ax : matplotlib.axes._subplots.Axes3DSubplot, optional
        The axis object on which to plot the coil geometry. If None, a new figure and axis will be created. Default is None.

    Returns
    -------
    Bx, By, Bz : ndarray
        Arrays representing the magnetic field components along the x, y, and z axes at each specified point, with the same shape as the input coordinates [T].
    """    

    Bx1, By1, Bz1 = bfield_from_thin_rectangular_coil(X, Y, Z, a, b, -h/2, current, plot_wire=plot_wire, elev=elev, azim=azim, ax=ax)

    if plot_wire:
        ax = plt.gca()
    
    Bx2, By2, Bz2 = bfield_from_thin_rectangular_coil(X, Y, Z, a, b, +h/2, current, plot_wire=plot_wire, elev=elev, azim=azim, ax=ax)
    
    return (Bx1+Bx2, By1+By2, Bz1+Bz2)


def rotate_around_e3(theta):
    r"""
    Generate a 3D rotation matrix for a rotation around the z-axis (e3) by an angle theta.

    Parameters
    ----------
    theta : float
        Rotation angle in radians.

    Returns
    -------
    rotation_matrix : ndarray
        A 3x3 rotation matrix representing a counterclockwise rotation by `theta` radians around the z-axis.

    Notes
    -----
    - This function returns the standard 3D rotation matrix for a rotation around the z-axis (also known as the e3 axis).
    - The rotation matrix is given by:
    
      .. math::
         R = \\begin{bmatrix} 
         \cos(\theta) & -\sin(\theta) & 0 \\
         \sin(\theta) &  \cos(\theta) & 0 \\
         0            &  0            & 1 
         \end{bmatrix}

    Examples
    --------
    Generate a rotation matrix for a 90-degree (π/2 radians) rotation around the z-axis:

    >>> theta = np.pi / 2
    >>> R = rotate_around_e3(theta)
    >>> print(R)
    [[ 0.  -1.   0. ]
     [ 1.   0.   0. ]
     [ 0.   0.   1. ]]

    """
    
    C, S = np.cos(theta),np.sin(theta)

    return np.array( [[C, -S, 0],[+S, C, 0], [0,0,0]] )


def get_arc_vectors(h, R, theta, 
                    npts=100, 
                    arc_e3=np.array([0,0,1]) ):

    """
    Calculate the position vectors along a circular arc in 3D space.

    Parameters
    ----------
    h : float
        The height or vertical offset of the arc in the direction of the arc's normal vector [m].
        
    R : float
        The radius of the arc [m].
        
    theta : float
        The opening angle of the arc in radians. Defines the span of the arc.
        
    npts : int, optional
        The number of points to use for discretizing the arc. Default is 100.
        
    arc_e3 : array_like, optional
        The 3D unit vector representing the direction of the normal to the arc's plane. Default is [0, 0, 1] (z-axis).

    Returns
    -------
    arc_points : ndarray
        A 2D array of shape `(npts, 3)` representing the coordinates of the arc in 3D space.
        
    arc_tangents : ndarray
        A 2D array of shape `(npts, 3)` representing the tangent vectors along the arc.

    Notes
    -----
    - The arc is assumed to lie in a plane perpendicular to the `arc_e3` normal vector.
    - The center of the arc is located at a distance `h` along the direction of `arc_e3`, and the arc spans an angle `theta` with radius `R`.
    - The function returns both the points along the arc and the corresponding tangent vectors at those points.

    Examples
    --------
    Generate position vectors and tangents for an arc with radius 1, angle π/2, and height 0.5:

    >>> arc_points, arc_tangents = get_arc_vectors(h=0.5, R=1, theta=np.pi/2, npts=50)

    Generate an arc with a custom normal vector:

    >>> arc_points, arc_tangents = get_arc_vectors(h=0.5, R=1, theta=np.pi/2, npts=50, arc_e3=np.array([0, 1, 0]))
    """

    phi = (np.pi - theta)/2

    #print(phi * 180/np.pi)

    arc_e1 = np.matmul(rotate_around_e3(phi), np.array([1,0,0]))

    assert np.isclose(np.dot(arc_e1, arc_e3), 0)
    
    #arc_e2 = np.cross(arc_e3, arc_e1)

    ths = np.linspace(0, theta, npts)

    ps = np.zeros( (len(ths), 3) ) 

    for ii, th in enumerate(ths):
        ps[ii, :] = np.array([0,0,h])+ R*np.matmul(rotate_around_e3(th), arc_e1)

    return ps
    
        
def plot_arc_vectors(ps, color='k', elev=45, azim=-45, ax=None):

    for ii in range(ps.shape[0]-1):

        p1 = ps[ii,:]
        p2 = ps[ii+1,:]

        if ax is None:
            ax = plot_3d_vector(p2-p1, 
                                origin=p1, 
                                color='k', 
                                elev=elev, azim=azim, 
                                plot_arrow=True, plot_line=False)
        else:
            ax = plot_3d_vector(p2-p1, 
                                origin=p1, 
                                color='k', 
                                elev=elev, azim=azim, 
                                plot_arrow=True, plot_line=False, 
                                ax=ax)

    return ax
    

def bfield_from_thin_wire_arc(X, Y, Z, h, R, theta, npts=100, current=1, plot_wire=False, elev=45, azim=-45, ax=None):

    ps = get_arc_vectors(h, R, theta, npts=npts)

    Bx = np.zeros(X.shape)
    By = np.zeros(Y.shape)
    Bz = np.zeros(Z.shape)

    for ii in range(ps.shape[0]-1):

        p1 = ps[ii,:]
        p2 = ps[ii+1,:]

        if ii == 1 and plot_wire:
            ax = plt.gca()

        Bxii, Byii, Bzii = bfield_from_thin_straight_wire(X, Y, Z, p1, p2, current, plot_wire=plot_wire, elev=elev, azim=azim, ax=ax)

        Bx = Bx + Bxii
        By = By + Byii
        Bz = Bz + Bzii

    return Bx, By, Bz


def bfield_from_thin_saddle_coil(X, Y, Z, L, R, theta, current, npts=10, plot_wire=False, elev=45, azim=-45, ax=None):

    phi = (np.pi - theta)/2

    Bx = np.zeros(X.shape)
    By = np.zeros(Y.shape)
    Bz = np.zeros(Z.shape)

    BxA1, ByA1, BzA1 = bfield_from_thin_wire_arc(X, Y, Z, -L/2, R, +theta, npts=npts, current=current, plot_wire=plot_wire, ax=ax, elev=elev, azim=azim)

    if plot_wire:
        ax = plt.gca()
        
    BxA2, ByA2, BzA2 = bfield_from_thin_wire_arc(X, Y, Z, +L/2, R, -theta, npts=npts, current=current, plot_wire=plot_wire, ax=ax, elev=elev, azim=azim)

    Bx += BxA1 + BxA2
    By += ByA1 + ByA2
    Bz += BzA1 + BzA2

    # Straight section 1
    p11 = np.array([R*np.cos(phi), R*np.sin(phi), +L/2])
    p21 = np.array([R*np.cos(phi), R*np.sin(phi), -L/2])

    BxS1, ByS1, BzS1 = bfield_from_thin_straight_wire(X, Y, Z, p11, p21, current=current, plot_wire=plot_wire, ax=ax, elev=elev, azim=azim)

    # Straight section 2
    p12 = np.array([-R*np.cos(phi), R*np.sin(phi), -L/2])
    p22 = np.array([-R*np.cos(phi), R*np.sin(phi), +L/2])

    BxS2, ByS2, BzS2 = bfield_from_thin_straight_wire(X, Y, Z, p12, p22, current=current, plot_wire=plot_wire, ax=ax, elev=elev, azim=azim)

    Bx += BxS1 + BxS2
    By += ByS1 + ByS2
    Bz += BzS1 + BzS2

    return (Bx, By, Bz)


def bfield_from_thin_saddle_corrector(X, Y, Z, L, R, theta, current, npts=10, plot_wire=False, elev=45, azim=-45, ax=None):

    Bx1, By1, Bz1 = bfield_from_thin_saddle_coil(X, Y, Z, +L, +R, theta, current, npts=npts, plot_wire=plot_wire, elev=elev, azim=azim, ax=ax)

    if plot_wire:
        ax = plt.gca()
    Bx2, By2, Bz2 = bfield_from_thin_saddle_coil(X, Y, Z, -L, -R, theta, current, npts=npts, plot_wire=plot_wire, elev=elev, azim=azim, ax=ax)
    
    return Bx1+Bx2, By1+By2, Bz1+Bz2


def make_rectangular_dipole_corrector_fieldmesh(*,
                                                a=None, b=None, h=None, 
                                                current=1, 
                                                xmin=None, xmax=None, nx=101,
                                                ymin=None, ymax=None, ny=101,
                                                zmin=None, zmax=None, nz=101,
                                                plot_wire=False):

    """
    Generates a 3D magnetic field mesh for a rectangular dipole corrector magnet.

    Parameters
    ----------
    a : float, optional
        Horizontal size of the rectangular coil in the x direction [m]. Default is None.
        
    b : float, optional
        Longitudinal size of the rectangular coil in the z direction [m]. Default is None.
        
    h : float, optional
        Vertical distance between the rectangular coils in the y direction [m]. Default is None.
        
    current : float, optional
        The current (in Amperes) flowing through the rectangular dipole corrector. Default is 1 A.
        
    xmin : float, optional
        Minimum x-coordinate of the mesh grid in [m]. If None, a default value is chosen based on the coil geometry. Default is None.
        
    xmax : float, optional
        Maximum x-coordinate of the mesh grid in [m]. If None, a default value is chosen based on the coil geometry. Default is None.
        
    nx : int, optional
        Number of points along the x-axis of the mesh grid. Default is 101.
        
    ymin : float, optional
        Minimum y-coordinate of the mesh grid in [m]. If None, a default value is chosen based on the coil geometry. Default is None.
        
    ymax : float, optional
        Maximum y-coordinate of the mesh grid in [m]. If None, a default value is chosen based on the coil geometry. Default is None.
        
    ny : int, optional
        Number of points along the y-axis of the mesh grid. Default is 101.
        
    zmin : float, optional
        Minimum z-coordinate of the mesh grid in [m]. If None, a default value is chosen based on the coil geometry. Default is None.
        
    zmax : float, optional
        Maximum z-coordinate of the mesh grid in [m]. If None, a default value is chosen based on the coil geometry. Default is None.
        
    nz : int, optional
        Number of points along the z-axis of the mesh grid. Default is 101.
        
    plot_wire : bool, optional
        If True, plots the wire geometry of the rectangular dipole corrector. Useful for visualizing the coil shape. Default is False.

    Returns
    -------
    Bx, By, Bz : ndarray
        Arrays representing the magnetic field components along the x, y, and z axes at each point in the 3D mesh grid.
        
    x, y, z : ndarray
        Arrays representing the x, y, and z coordinates of the mesh grid.

    Notes
    -----
    - This function models the magnetic field of a rectangular dipole corrector based on specified coil parameters `a`, `b`, and `h`.
    - The `plot_wire` option enables a 3D visualization of the wire geometry for verification of the coil design.

    Examples
    --------
    Create a field mesh for a rectangular dipole corrector magnet:

    >>> FM = make_rectangular_dipole_corrector_fieldmesh(current=10,
    ...                                                  a=0.5, b=1.0, h=0.2,
    ...                                                  xmin=-1, xmax=1, nx=101,
    ...                                                  ymin=-1, ymax=1, ny=101,
    ...                                                  zmin=-1, zmax=1, nz=101)

    Plot the wire geometry for a rectangular dipole corrector magnet:

    >>> FM = make_rectangular_dipole_corrector_fieldmesh(current=10,
    ...                                                  a=0.5, b=1.0, h=0.2,
    ...                                                  xmin=-1, xmax=1, nx=101,
    ...                                                  ymin=-1, ymax=1, ny=101,
    ...                                                  zmin=-1, zmax=1, nz=101,
    ...                                                  plot_wire=True)
    """

    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymin, ymax, ny)
    zs = np.linspace(zmin, zmax, nz)
    
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')

    Bx, By, Bz = bfield_from_thin_rectangular_corrector(X, Y, Z, a, b, h, current, plot_wire=True)
    
    dx = np.diff(xs)[0]
    dy = np.diff(ys)[0]
    dz = np.diff(zs)[0]
    
    attrs = {}
    attrs['gridOriginOffset'] = (xs[0], ys[0], zs[0])
    attrs['gridSpacing'] = (dx, dy, dz)
    attrs['gridSize'] = Bx.shape
    attrs['eleAnchorPt'] = 'center'
    attrs['gridGeometry'] = 'rectangular'
    attrs['axisLabels'] = ('x', 'y', 'z')
    attrs['gridLowerBound'] = (0, 0, 0)
    attrs['harmonic'] = 0
    attrs['fundamentalFrequency'] = 0

    components = {}
    components['magneticField/x'] = Bx
    components['magneticField/y'] = By
    components['magneticField/z'] = Bz

    data = dict(attrs=attrs, components=components)

    return FieldMesh(data=data)


def make_saddle_dipole_corrector_fieldmesh(*,
                                           R=None, L=None, theta=None, 
                                           current=1, 
                                           xmin=None, xmax=None, nx=101,
                                           ymin=None, ymax=None, ny=101,
                                           zmin=None, zmax=None, nz=101, 
                                           npts=20, plot_wire=False):

    """
    Generates a 3D magnetic field mesh for a saddle dipole corrector based on specified coil geometry.

    Parameters
    ----------
    R : float, optional
        Radius of the saddle coil in meters. Defines the curvature of the coil. Default is None.
        
    L : float, optional
        Length of the saddle coil along the z-axis in meters. Default is None.
        
    theta : float, optional
        Opening angle of the saddle coil in radians. Determines how wide the coil opens. Default is None.
        
    current : float, optional
        The current (in Amperes) flowing through the saddle dipole corrector. Default is 1 A.
        
    xmin : float, optional
        Minimum x-coordinate of the mesh grid in meters. If None, a default value is chosen based on the coil geometry. Default is None.
        
    xmax : float, optional
        Maximum x-coordinate of the mesh grid in meters. If None, a default value is chosen based on the coil geometry. Default is None.
        
    nx : int, optional
        Number of points along the x-axis of the mesh grid. Default is 101.
        
    ymin : float, optional
        Minimum y-coordinate of the mesh grid in meters. If None, a default value is chosen based on the coil geometry. Default is None.
        
    ymax : float, optional
        Maximum y-coordinate of the mesh grid in meters. If None, a default value is chosen based on the coil geometry. Default is None.
        
    ny : int, optional
        Number of points along the y-axis of the mesh grid. Default is 101.
        
    zmin : float, optional
        Minimum z-coordinate of the mesh grid in meters. If None, a default value is chosen based on the coil geometry. Default is None.
        
    zmax : float, optional
        Maximum z-coordinate of the mesh grid meters. If None, a default value is chosen based on the coil geometry. Default is None.
        
    nz : int, optional
        Number of points along the z-axis of the mesh grid. Default is 101.
        
    npts : int, optional
        Number of discrete points used to model the saddle coil geometry. Default is 20.
        
    plot_wire : bool, optional
        If True, plots the wire geometry of the saddle coil. Useful for visualizing the coil shape. Default is False.

    Returns
    -------
    FM : FieldMesh Object
        Object representing the magnetic field components along the x, y, and z axes at each point in the 3D mesh grid.

    Notes
    -----
    - This function models the magnetic field of a saddle-shaped dipole corrector, using coil parameters `R`, `L`, and `theta`.
    - The `npts` parameter controls the discretization of the saddle coil in the numerical model.
    - If `plot_wire` is set to True, the wire geometry of the saddle dipole will be visualized.

    Examples
    --------
    Create a saddle dipole corrector field mesh:

    >>> FM = make_saddle_dipole_corrector_fieldmesh(current=5,
    ...                                             R=0.5, L=1.0, theta=np.pi/4,
    ...                                             xmin=-1, xmax=1, nx=101,
    ...                                             ymin=-1, ymax=1, ny=101,
    ...                                             zmin=-1, zmax=1, nz=101, 
    ...                                             npts=50)
    
    Plot the wire geometry of the saddle dipole corrector:

    >>> FM = make_saddle_dipole_corrector_fieldmesh(current=5,
    ...                                             R=0.5, L=1.0, theta=np.pi/4,
    ...                                             xmin=-1, xmax=1, nx=101,
    ...                                             ymin=-1, ymax=1, ny=101,
    ...                                             zmin=-1, zmax=1, nz=101, 
    ...                                             npts=50, plot_wire=True)
    """

    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymin, ymax, ny)
    zs = np.linspace(zmin, zmax, nz)

    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    
    Bx, By, Bz = bfield_from_thin_saddle_corrector(X, Y, Z, L, R, theta, npts=npts, current=current, plot_wire=plot_wire)

    if plot_wire:
        ax = plt.gca()
        set_axes_equal(ax)
    
    dx = np.diff(xs)[0]
    dy = np.diff(ys)[0]
    dz = np.diff(zs)[0]

    shape = Bx.shape
    
    attrs = {}
    attrs['gridOriginOffset'] = (xs[0], ys[0], zs[0])
    attrs['gridSpacing'] = (dx, dy, dz)
    attrs['gridSize'] = shape
    attrs['eleAnchorPt'] = 'center'
    attrs['gridGeometry'] = 'rectangular'
    attrs['axisLabels'] = ('x', 'y', 'z')
    attrs['gridLowerBound'] = (0, 0, 0)
    attrs['harmonic'] = 0
    attrs['fundamentalFrequency'] = 0

    components = {}
    components['magneticField/x'] = Bx
    components['magneticField/y'] = By
    components['magneticField/z'] = Bz

    data = dict(attrs=attrs, components=components)

    return FieldMesh(data=data)


def make_dipole_corrector_fieldmesh(*,
                                    current=1,
                                    xmin=None, xmax=None, nx=101,
                                    ymin=None, ymax=None, ny=101,
                                    zmin=None, zmax=None, nz=101, 
                                    mode='rectangular',
                                    a=None, b=None, h=None,                   # Parameters for rectangular dipole corrector
                                    R=None, L=None, theta=None, npts=None,    # Parameters for saddle dipole corrector
                                    plot_wire=False):

    """
    Generates a 3D magnetic field mesh for a dipole corrector based on either a rectangular or saddle coil design.

    Parameters
    ----------
    current : float, optional
        The current (in Amperes) flowing through the dipole corrector. Default is 1 A.
        
    xmin : float, optional
        Minimum x-coordinate of the mesh grid in meters. If None, a default value is chosen based on the mode. Default is None.
        
    xmax : float, optional
        Maximum x-coordinate of the mesh grid in meters. If None, a default value is chosen based on the mode. Default is None.
        
    nx : int, optional
        Number of points along the x-axis of the mesh grid. Default is 101.
        
    ymin : float, optional
        Minimum y-coordinate of the mesh grid in meters. If None, a default value is chosen based on the mode. Default is None.
        
    ymax : float, optional
        Maximum y-coordinate of the mesh grid in meters. If None, a default value is chosen based on the mode. Default is None.
        
    ny : int, optional
        Number of points along the y-axis of the mesh grid. Default is 101.
        
    zmin : float, optional
        Minimum z-coordinate of the mesh grid in meters. If None, a default value is chosen based on the mode. Default is None.
        
    zmax : float, optional
        Maximum z-coordinate of the mesh grid in meters. If None, a default value is chosen based on the mode. Default is None.
        
    nz : int, optional
        Number of points along the z-axis of the mesh grid. Default is 101.
        
    mode : {'rectangular', 'saddle'}, optional
        The design of the dipole corrector to use. Can be either 'rectangular' or 'saddle'. Default is 'rectangular'.
        
    a : float, optional
        Length of the rectangular coil along the x-axis in meters. Only used in 'rectangular' mode. Default is None.
        
    b : float, optional
        Length of the rectangular coil along the z-axis in meters. Only used in 'rectangular' mode. Default is None.
        
    h : float, optional
        Vertical separation of rectangular coils along the y-axis in meters. Only used in 'rectangular' mode. Default is None.
        
    R : float, optional
        Radius of the saddle coil in meters. Only used in 'saddle' mode. Default is None.
        
    L : float, optional
        Length of the saddle coil along the z-axis in meters. Only used in 'saddle' mode. Default is None.
        
    theta : float, optional
        Opening angle of the saddle coil in radians. Only used in 'saddle' mode. Default is None.
        
    npts : int, optional
        Number of discrete points used to model the saddle coil. Only used in 'saddle' mode. Default is None.
        
    plot_wire : bool, optional
        If True, plots the wire geometry of the dipole corrector. Default is False.

    Returns
    -------
    FM : FieldMesh Object
        Class representing the magnetic field components along the x, y, and z axes at each point in the 3D mesh grid.
        

    Notes
    -----
    - In 'rectangular' mode, the magnetic field is computed based on a rectangular coil design with dimensions specified by
      `a`, `b`, and `h`.
    - In 'saddle' mode, the magnetic field is computed based on a saddle coil design, defined by the parameters `R`, `L`, `theta`, and `npts`.
    - If `plot_wire` is set to True, a plot of the wire geometry will be generated, useful for visualizing the coil shape.
    
    Examples
    --------
    Create a rectangular dipole corrector field mesh:
    
    >>> FM = make_dipole_corrector_fieldmesh(current=10, 
    ...                                      xmin=-1, xmax=1, nx=101,
    ...                                      ymin=-1, ymax=1, ny=101,
    ...                                      zmin=-1, zmax=1, nz=101,
    ...                                      mode='rectangular', 
    ...                                      a=0.5, b=0.5, h=0.5)
    
    Create a saddle dipole corrector field mesh:
    
    >>> FM = make_dipole_corrector_fieldmesh(current=10, 
                                             xmin=-1, xmax=1, nx=101,
    ...                                      ymin=-1, ymax=1, ny=101,
    ...                                      zmin=-1, zmax=1, nz=101,
    ...                                      mode='saddle', 
    ...                                      R=0.5, L=1.0, theta=np.pi/4, npts=100)
    """

    

    if mode == 'rectangular':
        if a is None or b is None or h is None:
            raise ValueError("Parameters 'a', 'b', and 'h' must be provided for rectangular mode.")

        f = 0.99
        
        if xmin is None:
            xmin = -f*a

        if ymin is None: 
            ymin = -f*h/2

        if zmin is None:
            zmin = -5*b

        if xmax is None:
            xmax = +f*a

        if ymax is None: 
            ymax = +f*h/2

        if zmax is None:
            zmax = +5*b
            
        # Call the rectangular dipole corrector function
        return make_rectangular_dipole_corrector_fieldmesh(a=a, b=b, h=h, current=current, 
                                                           xmin=xmin, xmax=xmax, nx=nx,
                                                           ymin=ymin, ymax=ymax, ny=ny,
                                                           zmin=zmin, zmax=zmax, nz=nz,
                                                           plot_wire=plot_wire)

    elif mode == 'saddle':
        
        if xmin is None:
            xmin = -R

        if ymin is None: 
            ymin = -R

        if zmin is None:
            zmin = -5*L/2

        if xmax is None:
            xmax = +R

        if ymax is None: 
            ymax = +R

        if zmax is None:
            zmax = +5*L/2
        
        # Check that necessary parameters are provided
        if R is None or L is None or theta is None:
            raise ValueError("Parameters 'R', 'L', and 'theta' must be provided for saddle mode.")

        #if plot_wire:
        #    ax = plt.gca()
        #    set_axes_equal(ax)
        
        # Call the saddle dipole corrector function
        return make_saddle_dipole_corrector_fieldmesh(R=R, L=L, theta=theta, current=current, 
                                                      xmin=xmin, xmax=xmax, nx=nx,
                                                      ymin=ymin, ymax=ymax, ny=ny,
                                                      zmin=zmin, zmax=zmax, nz=nz,
                                                      npts=npts, plot_wire=plot_wire)
    
    else:
        raise ValueError("Invalid mode. Choose either 'rectangular' or 'saddle'.")    
    

def make_thin_straight_wire_fieldmesh(p1, p2, *,
                                      current=1,
                                      xmin=None, xmax=None, nx=101,
                                      ymin=None, ymax=None, ny=101,
                                      zmin=None, zmax=None, nz=101,
                                      plot_wire=False):

    """
    Generate a 3D magnetic field mesh for a thin, straight, current-carrying wire.

    Parameters
    ----------
    p1 : array_like
        The 3D coordinates [x, y, z] of one end of the wire [m].
        
    p2 : array_like
        The 3D coordinates [x, y, z] of the other end of the wire [m].
        
    current : float, optional
        The current flowing through the wire in Amperes. Default is 1 A.
        
    xmin : float, optional
        Minimum x-coordinate of the field mesh grid. Default is None.
        
    xmax : float, optional
        Maximum x-coordinate of the field mesh grid. Default is None.
        
    nx : int, optional
        Number of grid points along the x-axis. Default is 101.
        
    ymin : float, optional
        Minimum y-coordinate of the field mesh grid. Default is None.
        
    ymax : float, optional
        Maximum y-coordinate of the field mesh grid. Default is None.
        
    ny : int, optional
        Number of grid points along the y-axis. Default is 101.
        
    zmin : float, optional
        Minimum z-coordinate of the field mesh grid. Default is None.
        
    zmax : float, optional
        Maximum z-coordinate of the field mesh grid. Default is None.
        
    nz : int, optional
        Number of grid points along the z-axis. Default is 101.
        
    plot_wire : bool, optional
        If True, plots the wire geometry in 3D space. Default is False.

    Returns
    -------
    FM : FieldMesh object
        Arrays representing the magnetic field components along the x, y, and z axes at each point in the 3D field mesh.

    Notes
    -----
    - The magnetic field is computed using the Biot-Savart law for a thin, straight wire.
    - The wire is modeled as a straight line segment between points `p1` and `p2` with current `current` flowing through it.
    - The field mesh is defined by the grid bounds (`xmin`, `xmax`, `ymin`, `ymax`, `zmin`, `zmax`) and resolution (`nx`, `ny`, `nz`).

    Examples
    --------
    Generate the field mesh for a wire between two points with a current of 10 A:

    >>> p1 = [0, 0, -1]
    >>> p2 = [0, 0, 1]
    >>> FM = make_thin_straight_wire_fieldmesh(p1, p2, current=10,
    ...                                        xmin=-1, xmax=1, nx=101,
    ...                                        ymin=-1, ymax=1, ny=101,
    ...                                        zmin=-1, zmax=1, nz=101)

    Plot the wire geometry:

    >>> FM = make_thin_straight_wire_fieldmesh(p1, p2, current=10, plot_wire=True)

    """

    assert xmin is not None, 'No xmin specified'
    assert ymin is not None, 'No ymin specified'
    assert zmin is not None, 'No zmin specified'
    
    assert xmax is not None, 'No xmax specified'
    assert ymax is not None, 'No ymax specified'
    assert zmax is not None, 'No zmax specified'

    assert nx is not None, 'No nx specified'
    assert ny is not None, 'No ny specified'
    assert nz is not None, 'No nz specified'

    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymin, ymax, ny)
    zs = np.linspace(zmin, zmax, nz)

    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')

    Bx, By, Bz = bfield_from_thin_straight_wire(X, Y, Z, p1, p2, current, plot_wire=plot_wire)

    dx = np.diff(xs)[0]
    dy = np.diff(ys)[0]
    dz = np.diff(zs)[0]
    
    attrs = {}
    attrs['gridOriginOffset'] = (xs[0], ys[0], zs[0])
    attrs['gridSpacing'] = (dx, dy, dz)
    attrs['gridSize'] = Bx.shape
    attrs['eleAnchorPt'] = 'center'
    attrs['gridGeometry'] = 'rectangular'
    attrs['axisLabels'] = ('x', 'y', 'z')
    attrs['gridLowerBound'] = (0, 0, 0)
    attrs['harmonic'] = 0
    attrs['fundamentalFrequency'] = 0

    components = {}
    components['magneticField/x'] = Bx
    components['magneticField/y'] = By
    components['magneticField/z'] = Bz

    data = dict(attrs=attrs, components=components)

    return FieldMesh(data=data)

    