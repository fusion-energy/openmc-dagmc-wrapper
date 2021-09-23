
import openmc


class FusionSettings(openmc.Settings):
    """A openmc.Settings object with some presets to make it more convenient
    fusion simulations that are 'fixed source' simulations and have 0 inactivate
    particles.
    """

    def __init__(self, batches, particles):

        super().__init__()

        # performed after the super init as these are setting attributes
        self.run_mode = 'fixed source'
        self.inactive = 0
        self.batches = batches
        self.particles = particles

        self.checks()

    def checks(self):
        if self.batches < 2:
            raise ValueError('FussionSettings.batches must be set to 2 or more')
