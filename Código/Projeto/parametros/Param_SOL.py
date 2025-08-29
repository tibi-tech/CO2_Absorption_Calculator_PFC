import rasterio
from calendar import monthrange
from venv import logger
from rasterio.mask import mask
from shapely import wkt
from shapely.geometry import mapping
import numpy as np


def calcular_sol(
    projeto_dir,
    outputs_dir,
    mes,
    ano_referencia,
    var_pct_mes,
    fator_conversao,
    resolucao_solar,
):
    """
    Calcula a radiação solar mensal (MJ/m²) para a região de Oeiras

    Args:
        projeto_dir (Path): Diretoria do projeto
        outputs_dir (Path): Pasta de saída
        mes (int): Mês a processar (1-12)
        ano_referencia (int): Ano de referência
        var_pct_mes (dict): Tabela de variação mensal
        fator_conversao (float): Conversão kWh → MJ
        resolucao_solar (float): Resolução espacial
    """
    try:
        # Caminhos dos arquivos
        caminho_tiff = projeto_dir / "INPUTS" / "SOL" / "GHI.tif"
        wkt_path = projeto_dir / "OEIRAS" / "oeiras_wkt_square.wkt"

        if not caminho_tiff.exists():
            raise FileNotFoundError(f"Arquivo GHI não encontrado: {caminho_tiff}")

        with open(wkt_path, encoding="utf-8") as f:
            geom = wkt.loads(f.read().strip())

        with rasterio.open(caminho_tiff) as src:
            recorte, novo_transf = mask(
                src,
                [mapping(geom)],
                crop=True,
                filled=True,
                nodata=src.nodata,
            )
            meta = src.meta.copy()
            meta.update(
                {
                    "height": recorte.shape[1],
                    "width": recorte.shape[2],
                    "transform": novo_transf,
                    "driver": "GTiff",
                    "dtype": "float32",
                }
            )

        pct = var_pct_mes[mes] / 100.0
        ndias_mes = monthrange(ano_referencia, mes)[1]
        fator_total = 1.0 + pct

        # Aplicar transformações
        img_saida = (
            recorte.astype(np.float32)
            * fator_conversao
            * fator_total
            * ndias_mes
            * resolucao_solar
        )

        # Salvar resultado
        out_path = outputs_dir / "SOL.tif"
        meta.update(driver="GTiff", dtype="float32")
        with rasterio.open(out_path, "w", **meta) as dst:
            dst.write(img_saida)

        logger.info(f"Radiacao solar mensal calculada: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Erro no calculo da radiacao solar: {e}")
        raise


def determinar_mes_imagem(tif_path, data_fallback):
    """
    Determina o mês de uma imagem a partir de seus metadados

    Args:
        tif_path (Path): Caminho para o arquivo TIFF
        data_fallback (str): Data de fallback no formato "YYYY-MM-DD"

    Returns:
        int: Mês extraído (1-12)
    """
    from datetime import datetime

    try:
        with rasterio.open(tif_path) as src:
            tags = src.tags()

        data_imagem = None
        for tag in ["TIFFTAG_DATETIME", "DATE", "ACQUISITION_DATE", "SENSING_TIME"]:
            if tag in tags:
                data_imagem = tags[tag]
                break

        if not data_imagem:
            for key, value in tags.items():
                if "date" in key.lower() or "time" in key.lower():
                    data_imagem = value
                    break

        # Processar a data encontrada
        if data_imagem:
            formatos = [
                "%Y%m%d",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%Y/%m/%d",
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ]

            for fmt in formatos:
                try:
                    data_str = (
                        data_imagem.split()[0] if " " in data_imagem else data_imagem
                    )
                    data_obj = datetime.strptime(data_str, fmt)
                    mes = data_obj.month
                    logger.info(f"Data extraída da imagem: {data_imagem} → Mês: {mes}")
                    return mes
                except:
                    continue

        logger.warning(
            "Não foi possível extrair data dos metadados. Usando data de fallback"
        )
        data_obj = datetime.strptime(data_fallback, "%Y-%m-%d")
        return data_obj.month

    except Exception as e:
        logger.error(f"Erro ao determinar mês da imagem: {e}")
        data_obj = datetime.strptime(data_fallback, "%Y-%m-%d")
        return data_obj.month
