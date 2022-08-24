import scipy
import pygsp
import numpy as np

class Graph_Fourier_MMD:
    def __init__(self, Graph = None):
        if Graph != None:
            self.G = Graph
            self.T = self.G.L.trace()
        else:
            raise ValueError("Graph Required")
            
    def feature_map(self, signals, method, filter_name):
        recip_filter = pygsp.filters.Filter(self.G, kernels = [lambda x : [i**(-1/2) if i != 0 else 0 for i in x]])
        heat_filter = pygsp.filters.Heat(self.G)

        if filter_name == 'heat':
            use_filter = heat_filter
        elif filter_name == "default":
            use_filter = recip_filter
        else:
            raise NameError("Filter name must either be 'heat' or 'default'")
        
        if method == "chebyshev":
            return use_filter.filter(signals, method = 'chebyshev') * (self.T)**(1/2)
        else:
            return use_filter.filter(signals, method = 'exact') * (self.T)**(1/2)

    def locality(self, signals, method='chebyshev', filter_name='default'):
        transformed = self.feature_map(signals, method, filter_name)
        return [np.linalg.norm(t) for t in transformed.T]

    def distance(self, signals, method='chebyshev', filter_name='default'):
        n = signals.shape[1]

        if n == 1:
            raise ValueError("Need more than two signals to compare")
            return False 

        transformed = self.feature_map(signals, method, filter_name)
        distance_array = scipy.spatial.distance.pdist(transformed.T)
        distances = scipy.spatial.distance.squareform(distance_array)

        if n == 2:
            return distances[0,1]
        else:
            return distances