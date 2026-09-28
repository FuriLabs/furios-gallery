import numpy as np

class ColorSpaceStandards:
    SEPIA_MATRIX = np.array([
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131],
    ], dtype=np.float32)

    # ITU-R BT.709 full-range YCbCr coefficients

    # RGB -> Y
    Y_R = 0.2126
    Y_G = 0.7152
    Y_B = 0.0722

    # RGB -> Cb
    CB_R = -0.114572
    CB_G = -0.385428
    CB_B = 0.500000
    CB_OFFSET = 128.0

    # RGB -> Cr
    CR_R = 0.500000
    CR_G = -0.454153
    CR_B = -0.045847
    CR_OFFSET = 128.0

    # YCbCr -> RGB
    R_CR = 1.574800
    G_CB = 0.187324
    G_CR = 0.468124
    B_CB = 1.855600

    @staticmethod
    def rgb_to_ycbcr(rgb: np.ndarray):
        x = rgb.astype(np.float32, copy=False)

        R = x[..., 0]
        G = x[..., 1]
        B = x[..., 2]

        Y = (
            ColorSpaceStandards.Y_R * R +
            ColorSpaceStandards.Y_G * G +
            ColorSpaceStandards.Y_B * B
        )

        Cb = (
            ColorSpaceStandards.CB_R * R +
            ColorSpaceStandards.CB_G * G +
            ColorSpaceStandards.CB_B * B +
            ColorSpaceStandards.CB_OFFSET
        )

        Cr = (
            ColorSpaceStandards.CR_R * R +
            ColorSpaceStandards.CR_G * G +
            ColorSpaceStandards.CR_B * B +
            ColorSpaceStandards.CR_OFFSET
        )

        return Y, Cb, Cr

    @staticmethod
    def ycbcr_to_rgb(Y: np.ndarray, Cb: np.ndarray, Cr: np.ndarray):
        R = Y + ColorSpaceStandards.R_CR * (Cr - ColorSpaceStandards.CR_OFFSET)
        G = (Y - ColorSpaceStandards.G_CB * (Cb - ColorSpaceStandards.CB_OFFSET) - ColorSpaceStandards.G_CR * (Cr - ColorSpaceStandards.CR_OFFSET))
        B = Y + ColorSpaceStandards.B_CB * (Cb - ColorSpaceStandards.CB_OFFSET)

        return np.stack([R, G, B], axis=-1)