import openmc


class FusionSettings(openmc.Settings):
    """A openmc.Settings object with some presets to make it more convenient
    fusion simulations that are 'fixed source' simulations and have 0 inactivate
    particles.
    """

    def __init__(self):

        super().__init__()

        # performed after the super init as these are setting attributes
        self.run_mode = "fixed source"
        self.inactive = 0
