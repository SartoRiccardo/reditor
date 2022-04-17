import os
import sys
import unittest
parent_dir = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir, ".."))
sys.path.append(parent_dir)


class TestCaseExtended(unittest.TestCase):
    def assertFileExists(self, path):
        if not os.path.exists(path):
            raise AssertionError("File does not exist: %s" % str(path))
