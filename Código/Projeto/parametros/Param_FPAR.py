import rasterio
import numpy as np
from pathlib import Path


def calcular_ndvi_fpar(input_s2_path, output_dir_path):
    """
    Calcula NDVI e FPAR em sequência
    """
    print("\n" + "=" * 50)
    print("Iniciar calculo do NDVI e FPAR")
    print("=" * 50)

    # Calcular NDVI
    ndvi_file = Path(output_dir_path) / "NDVI.tif"
    calcular_ndvi(input_s2_path, str(ndvi_file))

    # Calcular FPAR
    fpar_file = Path(output_dir_path) / "FPAR.tif"
    calcular_fpar(str(ndvi_file), str(fpar_file))

    print(f"Processo NDVI/FPAR concluido com sucesso!")
    return str(fpar_file)


def calcular_fpar(ndvi_file_path, fpar_output_file_path):
    """
    Calcula FPAR a partir do arquivo NDVI
    """
    with rasterio.open(ndvi_file_path) as src:
        ndvi = src.read(1).astype(np.float32)
        profile = src.profile
        nodata = src.nodata

    # Máscara de dados válidos
    valid_mask = (ndvi != nodata) & (~np.isnan(ndvi))

    # Calcular estatísticas
    if np.count_nonzero(valid_mask) == 0:
        raise ValueError("Nenhum dado valido encontrado no arquivo NDVI")

    NDVImin = np.min(ndvi[valid_mask])
    NDVImax = np.max(ndvi[valid_mask])

    if np.isclose(NDVImax, NDVImin):
        NDVImax = NDVImin + 1e-5

    # Parâmetros FPAR
    FPARmax = 0.95
    FPARmin = 0.001

    # Calcular FPAR
    fpar = np.full(ndvi.shape, nodata, dtype=np.float32)
    fpar[valid_mask] = (
        (ndvi[valid_mask] - NDVImin) * (FPARmax - FPARmin) / (NDVImax - NDVImin)
    ) + FPARmin

    profile.update(dtype=rasterio.float32, count=1, compress="lzw", nodata=nodata)
    with rasterio.open(fpar_output_file_path, "w", **profile) as dst:
        dst.write(fpar, 1)

    print(f"FPAR calculado, salvo em: {fpar_output_file_path}")
    return fpar_output_file_path


def calcular_ndvi(input_s2_path, output_ndvi_path):
    """
    Calcula NDVI a partir de arquivo Sentinel-2 (GeoTIFF)
    """
    with rasterio.open(input_s2_path) as src:
        red = src.read(1).astype(np.float32)
        nir = src.read(2).astype(np.float32)
        profile = src.profile

    # Calcular NDVI
    denominator = nir + red
    ndvi = np.zeros_like(red, dtype=np.float32)
    valid_mask = denominator != 0
    ndvi[valid_mask] = (nir[valid_mask] - red[valid_mask]) / denominator[valid_mask]
    ndvi[~valid_mask] = np.nan

    profile.update(dtype=rasterio.float32, count=1, nodata=np.nan, compress="lzw")
    with rasterio.open(output_ndvi_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    print(f"NDVI calculado, salvo em: {output_ndvi_path}")
    return output_ndvi_path
