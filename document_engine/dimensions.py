"""Central unit system (spec section 34). All conversions live here."""
PT_PER_IN = 72.0


class Units:
    def __init__(self, dpi=300):
        self.dpi = dpi

    def in_to_px(self, inches):
        return int(round(inches * self.dpi))

    def px_to_in(self, px):
        return px / self.dpi

    def in_to_pt(self, inches):
        return inches * PT_PER_IN

    @staticmethod
    def page_pt(width_in, height_in):
        return (width_in * PT_PER_IN, height_in * PT_PER_IN)

    def margins_px(self, margins_in):
        return {k: self.in_to_px(v) for k, v in margins_in.items()}
