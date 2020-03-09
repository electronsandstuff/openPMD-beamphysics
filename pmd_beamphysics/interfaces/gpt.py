from pmd_beamphysics.units import e_charge

import numpy as np
   
def write_gpt(particle_group,           
               outfile,
               verbose=False): 

    """
    GPT uses a custom binary format GDF for particle data. This can be created with the
    asci2gdf utility as:
    asci2gdf -o particles.gdf particles.txt
    
    This routine makes ASCII particles, with column labels:
        'x', 'y', 'z', 'GBx', 'GBy', 'GBz', 't', 'q', 'nmacro'
    in SI units. 
    
    For now, only electrons are supported.

    """

    assert particle_group.species == 'electron' # TODO: add more species
    q = -e_charge
    
    n = particle_group.n_particle
    gamma = particle_group.gamma
    
    dat = {        
        'x': particle_group.x,
        'y': particle_group.y,
        'z': particle_group.z,
        'GBx': gamma*particle_group.beta_x,
        'GBy': gamma*particle_group.beta_y,
        'GBz': gamma*particle_group.beta_z,
        't': particle_group.t,
        'q': np.full(n, q),
        'nmacro': particle_group.weight/e_charge}
    
    header = ' '.join(list(dat))

    outdat = np.array([dat[k] for k in dat]).T
    
    if verbose:
        print(f'writing {n} particles to {outfile}')
        
    np.savetxt(outfile, outdat, header=header, comments='', fmt = '%20.12e')

        