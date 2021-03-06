"""This formulation solves the model

    min_x ||Ax - b||_W^2 + ||grad(x)||_2^2

where A is the vectorial ray transform, W is the correlation matrix and grad
is the gradient.
"""

import odl
import numpy as np
import scipy.linalg as spl
from util import cov_matrix, load_data, load_fan_data, inverse_sqrt_matrix

data, geometry, crlb = load_fan_data(return_crlb=True)

space = odl.uniform_discr([-129, -129], [129, 129], [400, 400])

ray_trafo = odl.tomo.RayTransform(space, geometry, impl='astra_cuda')
A = odl.DiagonalOperator(ray_trafo, ray_trafo)

# Compute covariance matrix and matrix power, this is slow.
mat_sqrt_inv = inverse_sqrt_matrix(crlb)

re = ray_trafo.range.element
W = odl.ProductSpaceOperator([[odl.MultiplyOperator(re(mat_sqrt_inv[0, 0])), odl.MultiplyOperator(re(mat_sqrt_inv[0, 1]))],
                              [odl.MultiplyOperator(re(mat_sqrt_inv[1, 0])), odl.MultiplyOperator(re(mat_sqrt_inv[1, 1]))]])
A_corr = W * A

grad = odl.Gradient(space)
L = odl.DiagonalOperator(grad, grad)

lam = 100
op = A_corr.adjoint * A_corr + lam * L.adjoint * L

fbp_op = odl.tomo.fbp_op(ray_trafo, filter_type='Hann', frequency_scaling=0.7)

x = A.domain.element([fbp_op(data[0]), fbp_op(data[1])])
x.show('filtered back-projection')
rhs = A_corr.adjoint(W(data))

func = (odl.solvers.L2NormSquared(A_corr.range) * (A_corr - W(data)) +
        lam * odl.solvers.L2NormSquared(L.range) * L)

callback = (odl.solvers.CallbackShow() &
            odl.solvers.CallbackShow(clim=[0.9, 1.1]) &
            odl.solvers.CallbackPrint(func))

odl.solvers.conjugate_gradient(op, x, rhs, 300,
                               callback=callback)
