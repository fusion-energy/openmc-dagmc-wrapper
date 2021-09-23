import openmc


class Model(openmc.model.Model):
    def __init__(self, materials, geometry, settings, tallies):
        self.materials = materials
        self.geometry = geometry
        self.settings = settings
        self.tallies = tallies


        super().__init__(self.geometry, self.materials, self.settings, self.tallies)
