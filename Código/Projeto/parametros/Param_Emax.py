import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from pathlib import Path


def calcular_emax(
    caminho_entrada: Path,
    caminho_saida: Path,
    nova_largura: int,
    nova_altura: int,
    substituicoes: dict = None,
    metodo_reamostragem: Resampling = Resampling.nearest,
) -> None:
    """
    Processamento de um raster de uso do solo para introduzir valores de eficiência (Emax)
    com redimensionamento e conversão de classes.

    Parâmetros:
    caminho_entrada (Path): Caminho para o raster de entrada (ex: ESA WorldCover)
    caminho_saida (Path): Caminho para salvar o raster resultante
    nova_largura (int): Número de colunas do raster de saída
    nova_altura (int): Número de linhas do raster de saída
    substituicoes (dict): Dicionário de mapeamento classe->eficiência (padrão: tabela ESA)
    metodo_reamostragem (Resampling): Método de reamostragem (padrão: nearest neighbor)
    """

    # Tabela padrão de eficiência
    tabela_epsilon = substituicoes or {
        10: 1.0,  # treecover
        20: 0.7,  # shrubland
        30: 1.04,  # grassland
        40: 0.9,  # cropland
        60: 0.25,  # bare/sparse vegetation
    }

    with rasterio.open(caminho_entrada) as src:
        src_data = src.read(1)
        src_transform = src.transform
        src_crs = src.crs
        src_nodata = src.nodata
        perfil = src.profile.copy()

        # Calcula nova resolução espacial
        pixel_x = src_transform.a * src.width / nova_largura
        pixel_y = -src_transform.e * src.height / nova_altura
        nova_transform = Affine(
            pixel_x, 0, src_transform.c, 0, -pixel_y, src_transform.f
        )

        # Prepara array para dados redimensionados
        nodata_valor = src_nodata if src_nodata is not None else 0
        dados_redimensionados = np.full(
            (nova_altura, nova_largura), nodata_valor, dtype=src_data.dtype
        )

        # Redimensionamento
        reproject(
            source=src_data,
            destination=dados_redimensionados,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=nova_transform,
            dst_crs=src_crs,
            dst_nodata=src_nodata,
            resampling=metodo_reamostragem,
        )

    # Substituição das classes pelos valores de eficiência
    epsilon_raster = np.zeros_like(dados_redimensionados, dtype=np.float32)
    for codigo, valor in tabela_epsilon.items():
        epsilon_raster[dados_redimensionados == codigo] = valor

    # Converte nodata para 0
    if src_nodata is not None:
        epsilon_raster[dados_redimensionados == src_nodata] = 0

    # Atualiza metadados do arquivo de saída
    perfil.update(
        {
            "height": nova_altura,
            "width": nova_largura,
            "transform": nova_transform,
            "dtype": "float32",
            "nodata": 0,
            "count": 1,
            "compress": "lzw",
        }
    )

    # Salva o raster
    with rasterio.open(caminho_saida, "w", **perfil) as dst:
        dst.write(epsilon_raster, 1)

    print(f"Raster E_max gerado em: {caminho_saida.resolve()}")
