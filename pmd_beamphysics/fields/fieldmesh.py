from pmd_beamphysics.units import dimension, dimension_name, SI_symbol, pg_units

from pmd_beamphysics.readers import component_data, expected_record_unit_dimension, field_record_components, decode_attrs, field_paths, component_from_alias, load_field_attrs, component_alias

from pmd_beamphysics.writers import write_pmd_field, pmd_field_init

from pmd_beamphysics import tools

from pmd_beamphysics.plot import plot_fieldmesh_cylindrical_2d

from pmd_beamphysics.interfaces.superfish import write_fish_t7, write_poisson_t7
from pmd_beamphysics.interfaces.gpt import write_gpt_fieldmesh

from h5py import File
import numpy as np
from copy import deepcopy
import os


c_light = 299792458.


#-----------------------------------------
# Classes


axis_labels_from_geometry = {
    'cartesian': ('x', 'y', 'z'),
    'cylindrical': ('r', 'theta', 'z')
}


class FieldMesh:
    """
    Class for openPMD External Field Mesh data.
    
    Initialized on on openPMD beamphysics particle group:
        h5 = open h5 handle, or str that is a file
        data = raw data
        
    The required data is stored in ._data, and consists of dicts:
        'attrs'
        'components'
    
    Component data is always 3D.
    

    
    """
    def __init__(self, h5=None, data=None):
    
        if h5:
            # Allow filename
            if isinstance(h5, str):
                fname = os.path.expandvars(os.path.expanduser(h5))
                assert os.path.exists(fname), f'File does not exist: {fname}'
  
                with File(fname, 'r') as hh5:
                    fp = field_paths(hh5)
                    assert len(fp) == 1, f'Number of field paths in {h5}: {len(fp)}'
                    data = load_field_data(hh5[fp[0]])

            else:
                pass
            
        # Internal data
        self._data = data
            
        # Aliases (Do not set these! Set via slicing: .Bz[:] = 0
        for k in self.components:
            alias = component_alias[k]
            self.__dict__[alias] =  self.components[k]
            
           
    # Direct access to internal data        
    @property
    def attrs(self):
        return self._data['attrs']
    
    @property
    def components(self):
        return self._data['components']  
    
    @property
    def data(self):
        return self._data
    
    
    # Conveniences 
    @property
    def shape(self):
        return tuple(self.attrs['gridSize'])
    
    @property
    def geometry(self):
        return self.attrs['gridGeometry']
    
    @property
    def scale(self):
        return self.attrs['fieldScale']    
    @scale.setter
    def scale(self, val):
        self.attrs['fieldScale']  = val
        
    @property
    def phase(self):
        """
        Returns the complex argument phi = -2*pi*RFphase
        to multiply the oscillating field by. 
        
        Can be set. 
        """
        return self.attrs['RFphase']*2*np.pi
    @phase.setter
    def phase(self, val):
        self.attrs['RFphase']  = val/(2*np.pi)      
    
    @property
    def axis_labels(self):
        """
        
        """
        return axis_labels_from_geometry[self.geometry]
    
    def axis_index(self, key):
        """
        Returns axis index for a named axis label key.
        
        Example:
            .axis_labels == ('x', 'y', 'z')
            .axis_index('z') returns 2
        """
        for i, name in enumerate(self.axis_labels):
            if name == key:
                return i
        raise ValueError(f'Axis not found: {key}')
    
    @property
    def coord_vecs(self):
        """
        Uses gridSpacing, gridSize, and gridOriginOffset to return coordinate vectors.
        """
        return [np.linspace(x0, x1, nx) for x0, x1, nx in zip(self.min, self.max, self.shape)]
        
    def coord_vec(self, key):
        """
        Gets the coordinate vector from a named axis key. 
        """
        i = self.axis_index(key)
        return np.linspace(self.min[i], self.max[i], self.shape[i])
        
    @property 
    def meshgrid(self):
        """
        Usses coordinate vectors to produce a standard numpy meshgrids. 
        """
        vecs = self.coord_vecs
        return np.meshgrid(*vecs, indexing='ij')
        
    
    
    @property 
    def min(self):
        return np.array(self.attrs['gridOriginOffset'])
    @property
    def delta(self):
        return np.array(self.attrs['gridSpacing'])
    @property
    def max(self):
        return self.delta*(np.array(self.attrs['gridSize'])-1) + self.min      
    
    @property
    def frequency(self):
        if self.is_static:
            return 0
        else:
            return self.attrs['harmonic']*self.attrs['fundamentalFrequency']
    
    
    # Logicals
    @property
    def is_pure_electric(self):
        """
        Returns True if there are no non-zero mageneticField components
        """
        klist = [key for key in self.components if not self.component_is_zero(key)]
        return all([key.startswith('electric') for key in klist])
    # Logicals
    @property
    def is_pure_magnetic(self):
        """
        Returns True if there are no non-zero electricField components
        """
        klist = [key for key in self.components if not self.component_is_zero(key)]
        return all([key.startswith('magnetic') for key in klist])
            

        
    @property
    def is_static(self):
        return  self.attrs['harmonic'] == 0
    

    
    def component_is_zero(self, key):
        """
        Returns True if all elements in a component are zero.
        """
        a = self[key]
        return not np.any(a)
    
    
    
    # Fields
    @property
    def B(self):
        if self.geometry=='cylindrical':
            return np.hypot(self['Br'], self['Bz'])
        else:
            raise
            
            
            

    @property
    def E(self):
        if self.geometry=='cylindrical':
            return np.hypot(np.abs(self.Er), np.abs(self.Ez))
        else:
            raise  
            
            
            
            
    @property
    def Br(self):
        key = component_from_alias['Br']
        return self[key]*self.factor
    
    
    def plot(self, component=None, time=None, axes=None, cmap=None, **kwargs):
        
        
        return plot_fieldmesh_cylindrical_2d(self,
                                             component=component,
                                             time=time,
                                             axes=axes,
                                             cmap=cmap, **kwargs)
    
    
    def units(self, key):
        """Returns the units of any key"""
        
        # Fill out aliases 
        if key in component_from_alias:
            key = component_from_alias[key]
        elif key == 'E':
            key = 'electricField'
        elif key == 'B':
            key = 'magneticField'            
        
        return pg_units(key)    
    
    # openPMD    
    def write(self, h5, name=None):
        """
        Writes to an open h5 handle, or new file if h5 is a str.
        
        """
        if isinstance(h5, str):
            fname = os.path.expandvars(os.path.expanduser(h5))
            h5 = File(fname, 'w')
            pmd_field_init(h5, externalFieldPath='/ExternalFieldPath/%T/')
            g = h5.create_group('/ExternalFieldPath/1/')
        else:
            g = h5
    
        write_pmd_field(g, self.data, name=name)   
        
       
    def write_gpt(self, filePath, asci2gdf_bin=None, verbose=True):
        """
        Writes a GPT field file. 
        """
    
        return write_gpt_fieldmesh(self, filePath, asci2gdf_bin=asci2gdf_bin, verbose=verbose)
    
    # Superfish
    def write_superfish(self, filePath, verbose=False):
        """
        Write a Superfish T7 file. 
        
        For static fields, a Poisson T7 file is written.
        
        For dynamic (harmonic /= 0) fields, a Fish T7 file is written
        """
        
        if self.is_static:
            return write_poisson_t7(self, filePath, verbose=verbose)
        else:
            return write_fish_t7(self, filePath, verbose=verbose)
            
        
        
    def __eq__(self, other):
        """
        Checks that all attributes and component internal data are the same
        """
        
        if not tools.data_are_equal(self.attrs, other.attrs):
            return False
        
        return tools.data_are_equal(self.components, other.components)
  

 #  def __setattr__(self, key, value):
 #      print('a', key)
 #      if key in component_from_alias:
 #          print('here', key)
 #          comp = component_from_alias[key]
 #          if comp in self.components:
 #              self.components[comp] = value

 #  def __getattr__(self, key):
 #      print('a')
 #      if key in component_from_alias:
 #          print('here', key)
 #          comp = component_from_alias[key]
 #          if comp in self.components:
 #              return self.components[comp]
    
        
    def __getitem__(self, key):
        """
    
        
        
        """
               
        if key in self.components:
            return self.components[key]
            
        # Aliases
        if key in component_from_alias:
            comp = component_from_alias[key]
            if comp in self.components:
                return self.components[comp]
            
        if key == 'E':
            return self.E
        if key == 'B':
            return self.B
        
        raise ValueError(f'Key not available: {key}')
        
        
    def __repr__(self):
        memloc = hex(id(self))
        return f'<FieldMesh with {self.geometry} geometry and {self.shape} shape at {memloc}>'        

    


    
            
def load_field_data(h5, verbose=True):
    """
    
    
    If attrs['dataOrder'] == 'F', will transpose.
    
    If attrs['harmonic'] == 0, components will be cast to real by np.real
    
    Returns:
        data dict
    """
    data = {'components':{}}

    # Load attributes
    attrs, other = load_field_attrs(h5.attrs, verbose=verbose)
    attrs.update(other)
    data['attrs'] = attrs
    
    # Loop over records and components
    for g, comps in field_record_components.items():
        if g not in h5:
            continue
        
        # Get the full openPMD unitDimension 
        required_dim = expected_record_unit_dimension[g]
                
        for comp in comps:
            if comp not in h5[g]:
                continue
            name = g+'/'+comp
            cdat = component_data(h5[name])
                
            # Check dimensions
            dim = h5[name].attrs['unitDimension']
            assert np.all(dim == required_dim), f'{name} with dimension {required_dim} expected for {name}, found: {dim}'
            
            # Check shape
            s1 = tuple(attrs['gridSize'])
            s2 = cdat.shape
            assert s1 == s2, f'Expected shape: {s1} != found shape: {s2}'
            
            # Static fields should be real
            if attrs['harmonic'] == 0:
                cdat = np.real(cdat)
            
            # Finally set
            
            data['components'][name] = cdat        
            
    
    return data



