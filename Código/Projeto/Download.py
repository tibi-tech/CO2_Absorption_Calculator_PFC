import openeo
import json
from pathlib import Path
import logging
from datetime import datetime, timedelta
import re

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_sentinel_data(
    sentinel_version: int,
    geojson_file: str,
    cloud_coverage: float,
    bands: list,
    date_interval: list,
    output_filename: str = None,
    s3_day_night: str = "both",  # 'day', 'night' ou 'both'
) -> Path:
    """
    Download dados do Sentinel como GeoTIFF processados
    """
    try:
        # Conectar ao backend
        conn = openeo.connect(
            "https://openeo.dataspace.copernicus.eu"
        ).authenticate_oidc()
        logger.info("Conexao com openEO estabelecida")

        # Carregar geometria
        with open(geojson_file) as f:
            geojson_data = json.load(f)
        logger.info(f"Geometria carregada de {geojson_file}")

        # Determinar coleção
        collections = {2: "SENTINEL2_L2A", 3: "SENTINEL3_SLSTR_L2_LST"}
        collection = collections.get(sentinel_version)
        if not collection:
            raise ValueError(f"Versao Sentinel inválida: {sentinel_version}")

        # Carregar coleção com filtros mínimos
        load_params = {
            "temporal_extent": date_interval,
            "spatial_extent": geojson_data,
            "bands": bands,
        }

        # Apenas para Sentinel-2: filtro de nuvens
        if sentinel_version == 2:
            load_params["properties"] = {
                "eo:cloud_cover": lambda v: v <= cloud_coverage
            }
            datacube = conn.load_collection(collection, **load_params)
        else:  # Sentinel-3
            # Usar banda de confiança para máscara de qualidade
            confidence_band = "confidence_in"
            original_bands = bands.copy()
            if confidence_band not in bands:
                bands.append(confidence_band)

            load_params["bands"] = bands
            datacube = conn.load_collection(collection, **load_params)

            # Filtrar por dia/noite usando a hora de aquisição
            if s3_day_night != "both":
                valid_options = ["day", "night"]
                if s3_day_night not in valid_options:
                    raise ValueError(
                        f"Opçao invalida para s3_day_night: '{s3_day_night}'. Use 'day', 'night' ou 'both'"
                    )

                if s3_day_night == "day":
                    # Filtrar para horas entre 06:00 e 19:00 UTC
                    datacube = datacube.filter_temporal(
                        start_date=f"{date_interval[0]}T06:00:00Z",
                        end_date=f"{date_interval[1]}T19:00:00Z",
                    )
                else:
                    datacube = datacube.filter_temporal(
                        start_date=f"{date_interval[0]}T20:00:00Z",
                        end_date=f"{date_interval[1]}T06:00:00Z",
                    )

                logger.info(f"Filtro temporal aplicado para imagens de {s3_day_night}")

            # Criar máscara de qualidade
            confidence_flags = datacube.band(confidence_band)
            mask = (confidence_flags & 1 == 1) & (  # Bit 0: Land flag (1=land)
                confidence_flags & 2 == 0
            )  # Bit 1: Cloud flag (0=no cloud)

            # Aplicar máscara e manter bandas originais
            datacube = datacube.filter_bands(original_bands).mask(mask)
            logger.info("Máscara de Terra aplicada para Sentinel-3")

        # Composição temporal
        reducer = "median" if sentinel_version == 2 else "mean"
        composicao = datacube.reduce_dimension(dimension="t", reducer=reducer)
        logger.info(f"Redução temporal aplicada com {reducer}")

        # Nome do arquivo de saída
        if not output_filename:
            band_str = "_".join(original_bands if sentinel_version == 3 else bands)
            dn_suffix = (
                f"_{s3_day_night}"
                if sentinel_version == 3 and s3_day_night != "both"
                else ""
            )

            # Sanitizar nome do arquivo
            clean_band_str = re.sub(r"[^a-zA-Z0-9_]", "", band_str)
            output_filename = f"Sentinel{sentinel_version}_{clean_band_str}{dn_suffix}_{date_interval[0]}_{date_interval[1]}.tif"

        # Configurações de download
        download_options = {
            "sample_by_feature": True,
            "data_type": "Float32" if sentinel_version == 3 else "uint16",
        }

        # Garantir diretoria de saída
        output_path = Path(output_filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"A iniciar download para {output_path}")
        composicao.download(str(output_path), format="GTiff", options=download_options)
        logger.info(f"Download completo: {output_path}")

        return output_path.resolve()

    except Exception as e:
        logger.error(f"Erro no download de dados Sentinel-{sentinel_version}: {str(e)}")
        raise
