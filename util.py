import numpy as np
from scipy import signal
import scipy.io as sio
import os
import odl


def load_data():
    """Get the data from disk.

    Returns
    -------
    mat1_sino, mat2_sino : numpy.ndarray
        projection of material 1 and 2
    geometry : odl.tomo.Geometry
        Geometry of the data
    """
    current_path = os.path.dirname(os.path.realpath(__file__))
    data_path = os.path.join(current_path,
                             'data',
                             'aux_corr_in_real_ct_image.mat')

    try:
        data_mat = sio.loadmat(data_path)
    except IOError:
        raise IOError('data/aux_corr_in_real_ct_image.mat missing, contact '
                      'developers for a copy of the data or use another data '
                      'source.')

    data = data_mat['decomposedBasisProjectionsmmObj']
    data = data.swapaxes(0, 2)

    angle_partition = odl.uniform_partition(0, np.pi, 180)
    detector_partition = odl.uniform_partition(-150 * np.sqrt(2),
                                               150 * np.sqrt(2),
                                               853)
    geometry = odl.tomo.Parallel2dGeometry(angle_partition, detector_partition)

    return data, geometry


def load_fan_data():
    current_path = os.path.dirname(os.path.realpath(__file__))
    data_path = os.path.join(current_path,
                             'data', 'simulated_images_2017_01_06',
                             'head_image.mat')

    try:
        data_mat = sio.loadmat(data_path)
    except IOError:
        raise IOError('data/simulated_images_2017_01_06/head_image.mat missing, '
                      'contact '
                      'developers for a copy of the data or use another data '
                      'source.')

    # print(sorted(data_mat.keys()))
    data = data_mat['decomposedbasisProjectionsmm']
    data = data.swapaxes(0, 2)

    # Create approximate fan flat geometry.
    det_size = np.deg2rad(0.0573) * 883 * (500 + 500)

    angle_partition = odl.uniform_partition(0.5 * np.pi, 2.5 * np.pi, 360)
    detector_partition = odl.uniform_partition(-det_size / 2.0,
                                               det_size / 2.0,
                                               883)

    geometry = odl.tomo.FanFlatGeometry(angle_partition, detector_partition,
                                        src_radius=500,
                                        det_radius=500)

    # Convert to true fan flat geometry
    tmp_space = odl.uniform_discr_frompartition(geometry.partition,
                                                interp='linear')
    rot_angles = tmp_space.meshgrid[0]
    fan_angles = tmp_space.meshgrid[1]
    data = list(data)
    data[0] = tmp_space.element(data[0])
    data[1] = tmp_space.element(data[1])
    fan_dist = 1000 * np.arctan(fan_angles / 1000)
    data[0] = data[0].interpolation((rot_angles, fan_dist),
                                    bounds_check=False)
    data[0] = data[0][::-1]
    data[1] = data[1].interpolation((rot_angles, fan_dist),
                                    bounds_check=False)
    data[1] = data[1][::-1]

    return data, geometry


def estimate_cov(I1, I2):
    """Estiamte the covariance of I1 and I2."""
    assert I1.shape == I2.shape

    H, W = I1.shape

    M = np.array([[1, -2, 1],
                  [-2, 4., -2],
                  [1, -2, 1]])

    sigma = np.sum(signal.convolve2d(I1, M) * signal.convolve2d(I2, M))
    sigma /= (W * H - 1)

    return sigma / 36.0  # unknown factor, too lazy to solve


def cov_matrix(data):
    """Estimate the covariance matrix from data.

    Parameters
    ----------
    data : kxnxm `numpy.ndarray`
        Estimates the covariance along the first dimension.

    Returns
    -------
    cov_mat : kxk `numpy.ndarray`
        Covariance matrix.
    """
    n = len(data)

    cov_mat = np.zeros([n, n])
    for i in range(n):
        for j in range(n):
            cov_mat[i, j] = estimate_cov(data[i], data[j])

    return cov_mat


if __name__ == '__main__':
    # Example
    I1 = np.random.randn(50, 50)
    I2 = 3 * np.random.randn(50, 50)
    corr_variable = (I1 + I2)

    print(estimate_cov(I1, I1))  # should be 1
    print(estimate_cov(I1, I2))  # should be 0
    print(estimate_cov(I2, I1))  # should be 0
    print(estimate_cov(I2, I2))  # should be 9
    print(estimate_cov(I1, corr_variable))  # should be 1
