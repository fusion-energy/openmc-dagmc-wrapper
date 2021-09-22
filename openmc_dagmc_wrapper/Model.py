import openmc


class Model(openmc.model.Model):
    def __init__(self, materials, geometry, settings, tallies):
        self.materials = materials
        self.geometry = geometry
        self.settings = settings
        self.tallies = tallies

        self.add_filters_to_tallies()

        super().__init__(self.materials, self.geometry, self.settings, self.tallies)

    # def add_filters_to_tallies(self):
    #     for tally in tallies:
    #         if isinstance(tally, odw.CellTally):
    #             tally.filter = 