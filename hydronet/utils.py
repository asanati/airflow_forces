import numpy as np
import sys

def print_obj(obj):
    test = np.array(obj)
    np.set_printoptions(threshold=sys.maxsize)
    np.set_printoptions(linewidth=np.inf)
    print(test)