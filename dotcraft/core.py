import cv2
import numpy as np

def create_pixel_art(img_bgr, pixel_size=10, k=8) -> np.ndarray:
    '''
    OpenCV (BGR) 画像をドット絵化してBGRで返す
    
    Parameters
    ----------
    img_bgr : ndarray
        OpenCV (BGR) 画像
    pixel_size : int
        ドットのサイズ
    k : int
        K-means での色数
    Returns
    -------
    dotted : ndarray
        ドット絵化された画像 (BGR)
    '''
    h, w = img_bgr.shape[:2]

    # 1) 縮小
    small = cv2.resize(img_bgr, (w // pixel_size, h // pixel_size),
                       interpolation=cv2.INTER_NEAREST)

    # 2) K‑means で色数を減らす
    data = small.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _ret, labels, centers = cv2.kmeans(data, k, None, criteria, 10,
                                       cv2.KMEANS_RANDOM_CENTERS)
    quant = centers[labels.flatten()].astype(np.uint8).reshape(small.shape)

    # 3) 拡大してドット絵化
    dotted = cv2.resize(quant, (w, h), interpolation=cv2.INTER_NEAREST)
    return dotted

def imread_unicode(path: str, flags=cv2.IMREAD_COLOR):
    '''
    OpenCV で Unicode パスを読み込む
    
    Parameters
    ----------
    path : str
        画像ファイルのパス (Unicode)
    flags : int
        cv2.imread のフラグ (cv2.IMREAD_COLOR など)
    Returns
    -------
    img : ndarray
        読み込んだ画像 (BGR)
    '''
    # numpy.fromfile でバイト列として読み込む
    bytes_data = np.fromfile(path, dtype=np.uint8)
    if bytes_data.size == 0:
        return None
    # imdecode で OpenCV 画像に変換
    return cv2.imdecode(bytes_data, flags)
