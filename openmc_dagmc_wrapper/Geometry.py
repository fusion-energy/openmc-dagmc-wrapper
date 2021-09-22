import openmc
import dagmc_h5m_file_inspector as di


class Geometry(openmc.Geometry):
    def __init__(self, h5m_filename=None, reflective_angles=None):
        self.h5m_filename = h5m_filename
        self.reflective_angles = reflective_angles
        super().__init__(root=self.make_root())

    def make_root(self):
        # this is the underlying geometry container that is filled with the
        # faceted DAGMC CAD model
        dag_univ = openmc.DAGMCUniverse(self.h5m_filename)

        if self.reflective_angles is None:
            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if 'graveyard' not in di.get_materials_from_h5m(self.h5m_filename):
                vac_surfs = self.create_graveyard_surfaces()
                region = -vac_surfs[0] & -vac_surfs[1] & + \
                    vac_surfs[2] & -vac_surfs[3]

                containing_cell = openmc.Cell(
                    cell_id=9999,
                    region=region,
                    fill=dag_univ
                )
                root = [containing_cell]
            else:
                root = dag_univ
        else:
            reflective_1 = openmc.Plane(
                a=sin(self.reflective_angles[0]),
                b=-cos(self.reflective_angles[0]),
                c=0.0,
                d=0.0,
                surface_id=9995,
                boundary_type='reflective'
            )

            reflective_2 = openmc.Plane(
                a=sin(self.reflective_angles[1]),
                b=-cos(self.reflective_angles[1]),
                c=0.0,
                d=0.0,
                surface_id=9994,
                boundary_type='reflective'
            )

            # if a graveyard is not found in the dagmc geometry a CSG one is
            # made
            if 'graveyard' in di.get_materials_from_h5m(self.h5m_filename):
                region = -reflective_1 & +reflective_2
            else:
                vac_surfs = self.create_graveyard_surfaces()
                region = -vac_surfs[0] & -vac_surfs[1] & +vac_surfs[2] & - \
                    vac_surfs[3] & -reflective_1 & +reflective_2

            containing_cell = openmc.Cell(
                cell_id=9999,
                region=region,
                fill=dag_univ
            )

            root = [containing_cell]
        return root
