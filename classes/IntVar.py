

class IntVar:
    def __init__(self, val=0):
        self.val = val

    def __add__(self, other):
        return self.val + other

    def __iadd__(self, other):
        self.val += other
        return self

    def __sub__(self, other):
        return self.val - other

    def __isub__(self, other):
        self.val -= other
        return self

    def __gt__(self, other):
        return self.val > other

    def __ge__(self, other):
        return self.val >= other

    def __eq__(self, other):
        return self.val == other

    def __lt__(self, other):
        return self.val < other

    def __le__(self, other):
        return self.val <= other

    def __str__(self):
        return str(self.val)
