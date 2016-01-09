
import lasagne
import numpy as np
import theano.tensor as T
from lasagne.nonlinearities import *

from senti.utils.keras_ import *

__all__ = ['CNNChar']


class CNNChar(Graph):
    def create_model(self, emb_X, input_size, output_size, static_mode):
        self.inputs = [T.imatrix('input')]
        self.target = T.ivector('target')
        l = lasagne.layers.InputLayer((self.batch_size, input_size), self.inputs[0])
        l = lasagne.layers.EmbeddingLayer(l, emb_X.shape[0], emb_X.shape[1], W=emb_X)
        if static_mode == 0:
            self.constraints[l.W] = lambda u, v: u
        l = lasagne.layers.DimshuffleLayer(l, (0, 2, 1))
        conv_params = [(256, 7, 3), (256, 7, 3), (256, 3, None), (256, 3, None), (256, 3, None), (256, 3, 3)]
        for num_filters, filter_size, k in conv_params:
            l = lasagne.layers.Conv1DLayer(l, num_filters, filter_size, nonlinearity=rectify)
            if k is not None:
                l = lasagne.layers.MaxPool1DLayer(l, k, ignore_border=False)
        l = lasagne.layers.FlattenLayer(l)
        dense_params = [(1024, 1), (1024, 20)]
        for num_units, max_norm in dense_params:
            l = lasagne.layers.DenseLayer(l, num_units, nonlinearity=rectify)
            if max_norm:
                self.constraints[l.W] = lambda u, v: lasagne.updates.norm_constraint(v, max_norm)
            l = lasagne.layers.DropoutLayer(l)
        l = lasagne.layers.DenseLayer(l, 3, nonlinearity=log_softmax)
        self.probs = T.exp(lasagne.layers.get_output(l, deterministic=True))
        self.loss = T.mean(categorical_crossentropy_exp(lasagne.layers.get_output(l), self.target, self.batch_size))
        params = lasagne.layers.get_all_params(l, trainable=True)
        self.updates = lasagne.updates.adadelta(self.loss, params)
        self.network = l

    def gen_batch(self, X, y=None):
        input_size = self.kwargs['input_size']
        return np.vstack(np.pad(x[input_size - 1::-1], (0, max(input_size - x.size, 0)), 'constant') for x in X), y
