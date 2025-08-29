from calendar import monthrange
from shapely import wkt
from shapely.geometry import mapping
import logging
import traceback
import sys
from pathlib import Path
import rasterio
import numpy as np
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from datetime import date, timedelta

from Download import download_sentinel_data
from parametros.Param_FPAR import calcular_ndvi_fpar
from parametros.Param_WSC import calculate_WSC_from_tif
from parametros.Param_T1_T2 import calcular_T1_T2
from parametros.Param_SOL import calcular_sol, determinar_mes_imagem
from parametros.calc_NPP import executar_calculo_npp
from parametros.analise_NPP import analisar_npp
from App_Shapefile import aplicar_mascara_shapefile
from parametros.Param_Emax import calcular_emax

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main(ano: int, mes: int):
    projeto_dir = Path(__file__).parent.resolve()
    logger.info(f"Diretoria do projeto: {projeto_dir}")

    # Data inicial
    data_inicial = date(ano, mes, 1)
    data_final = data_inicial + timedelta(days=7)
    data_alternativa = data_inicial + timedelta(days=8)
    data_alternativa_fim = data_inicial.replace(day=28)

    data = [data_inicial.isoformat(), data_final.isoformat()]
    data2 = [data_alternativa.isoformat(), data_alternativa_fim.isoformat()]

    # Constantes de configuração
    POPULACAO = 172120  # N atual de pessoas em oeiras
    EMISSOES_CO2_PER_CAPITA = 0.8917  # t CO₂/pessoa/mês

    # Variação percentual (relativa à média diária anual) fornecida pelo utilizador
    VAR_PCT_MES = {
        1: -53.57138918,
        2: -35.49327248,
        3: -17.53257806,
        4: 21.45016561,
        5: 52.10518815,
        6: 42.992943,
        7: 63.0189765,
        8: 55.56084036,
        9: 20.07604713,
        10: -32.22469972,
        11: -49.63097221,
        12: -49.23973522,
    }

    ANO_REFERENCIA = ano
    FATOR_CONVERSAO = 44 / 12
    RESOLUCAO_SOLAR = 1.0

    # Diretórios
    sentinel2_dir = projeto_dir / "INPUTS" / "SENTINEL2"
    sentinel3_dir = projeto_dir / "INPUTS" / "SENTINEL3"
    outputs_dir = projeto_dir / "OUTPUTS"
    resultados_dir = projeto_dir / "RESULT"
    oeiras_dir = projeto_dir / "OEIRAS"

    sentinel2_dir.mkdir(parents=True, exist_ok=True)
    sentinel3_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    resultados_dir.mkdir(parents=True, exist_ok=True)
    oeiras_dir.mkdir(parents=True, exist_ok=True)

    geojson_file = projeto_dir / "coordenadas.txt"
    shapefile_path = oeiras_dir / "oeiras_shapefile.shp"

    # Download Sentinel-2
    s2_tif_original = sentinel2_dir / "Sentinel2_B04_B08_B11_B12_ORIGINAL.tif"
    s2_tif_masked = sentinel2_dir / "Sentinel2_B04_B08_B11_B12_MASKED.tif"

    # Variável para armazenar qual data foi usada
    data_efetiva = None

    try:
        download_sentinel_data(
            sentinel_version=2,
            geojson_file=str(geojson_file),
            cloud_coverage=10,
            bands=["B04", "B08", "B11", "B12"],
            date_interval=data,
            output_filename=str(s2_tif_original),
        )
        logger.info(f"Download Sentinel-2 feito: {s2_tif_original}")
        data_efetiva = data[0]

        aplicar_mascara_shapefile(
            shapefile_path=str(shapefile_path),
            raster_path=str(s2_tif_original),
            output_path=str(s2_tif_masked),
            nodata=0,
        )
        logger.info(f"Imagem Sentinel-2 recortada: {s2_tif_masked}")

    except Exception as e:
        logger.error(f"Erro no download Sentinel-2: {e}")
        logger.info("Tentando intervalo alternativo para Sentinel-2...")
        try:
            download_sentinel_data(
                sentinel_version=2,
                geojson_file=str(geojson_file),
                cloud_coverage=20,
                bands=["B04", "B08", "B11", "B12"],
                date_interval=data2,
                output_filename=str(s2_tif_original),
            )
            logger.info(
                f"Download alternativo bem-sucedido (Sentinel-2): {s2_tif_original}"
            )
            data_efetiva = data2[0]

            aplicar_mascara_shapefile(
                shapefile_path=str(shapefile_path),
                raster_path=str(s2_tif_original),
                output_path=str(s2_tif_masked),
                nodata=0,
            )
            logger.info(f"Imagem Sentinel-2 alternativa recortada: {s2_tif_masked}")

        except Exception as e2:
            logger.error(f"FALHA CRITICA no download Sentinel-2: {e2}")
            sys.exit(1)

    # Download LST diurno e noturno (Sentinel-3)
    lst_day_tif_original = sentinel3_dir / "Sentinel3_LST_day_ORIGINAL.tif"
    lst_day_tif_masked = sentinel3_dir / "Sentinel3_LST_day_MASKED.tif"
    lst_night_tif_original = sentinel3_dir / "Sentinel3_LST_night_ORIGINAL.tif"
    lst_night_tif_masked = sentinel3_dir / "Sentinel3_LST_night_MASKED.tif"

    # Download LST diurno
    try:
        download_sentinel_data(
            sentinel_version=3,
            geojson_file=str(geojson_file),
            cloud_coverage=10,
            bands=["LST"],
            date_interval=data,
            output_filename=str(lst_day_tif_original),
            s3_day_night="day",
        )
        logger.info(f"Download Sentinel-3 LST feito: {lst_day_tif_original}")

        aplicar_mascara_shapefile(
            shapefile_path=str(shapefile_path),
            raster_path=str(lst_day_tif_original),
            output_path=str(lst_day_tif_masked),
            nodata=0,
        )
        logger.info(f"LST diurno recortado: {lst_day_tif_masked}")

    except Exception as e:
        logger.error(f"Erro no download LST diurno: {e}")
        logger.info("Tentando intervalo alternativo para LST diurno...")
        try:
            download_sentinel_data(
                sentinel_version=3,
                geojson_file=str(geojson_file),
                cloud_coverage=20,
                bands=["LST"],
                date_interval=data2,
                output_filename=str(lst_day_tif_original),
                s3_day_night="day",
            )
            logger.info(
                f"Download alternativo bem-sucedido (LST diurno): {lst_day_tif_original}"
            )

            aplicar_mascara_shapefile(
                shapefile_path=str(shapefile_path),
                raster_path=str(lst_day_tif_original),
                output_path=str(lst_day_tif_masked),
                nodata=0,
            )
            logger.info(f"LST diurno alternativo recortado: {lst_day_tif_masked}")

        except Exception as e2:
            logger.error(f"FALHA no download LST diurno: {e2}")
            sys.exit(1)

    # Download LST noturno
    try:
        download_sentinel_data(
            sentinel_version=3,
            geojson_file=str(geojson_file),
            cloud_coverage=10,
            bands=["LST"],
            date_interval=data,
            output_filename=str(lst_night_tif_original),
            s3_day_night="night",
        )
        logger.info(f"Download Sentinel-3 LST feito: {lst_night_tif_original}")

        aplicar_mascara_shapefile(
            shapefile_path=str(shapefile_path),
            raster_path=str(lst_night_tif_original),
            output_path=str(lst_night_tif_masked),
            nodata=0,
        )
        logger.info(f"LST noturno recortado: {lst_night_tif_masked}")

    except Exception as e:
        logger.error(f"FALHA no download LST noturno: {e}")
        logger.info("Tentando intervalo alternativo para LST noturno...")
        try:
            download_sentinel_data(
                sentinel_version=3,
                geojson_file=str(geojson_file),
                cloud_coverage=20,
                bands=["LST"],
                date_interval=data2,
                output_filename=str(lst_night_tif_original),
                s3_day_night="night",
            )
            logger.info(
                f"Download alternativo bem-sucedido (LST noturno): {lst_night_tif_original}"
            )

            aplicar_mascara_shapefile(
                shapefile_path=str(shapefile_path),
                raster_path=str(lst_night_tif_original),
                output_path=str(lst_night_tif_masked),
                nodata=0,
            )
            logger.info(f"LST noturno alternativo recortado: {lst_night_tif_masked}")

        except Exception as e2:
            logger.error(f"FALHA no download LST noturno: {e2}")
            sys.exit(1)

    # Calcular NDVI e FPAR
    try:
        fpar_file = calcular_ndvi_fpar(str(s2_tif_masked), str(outputs_dir))
        logger.info(f"FPAR calculado com sucesso: {fpar_file}")
    except Exception as e:
        logger.error(f"FALHA no cálculo FPAR: {e}")
        sys.exit(1)

    # Calcular WSC
    try:
        wsc_out = outputs_dir / "WSC.tif"
        calculate_WSC_from_tif(str(s2_tif_masked), str(wsc_out))
        logger.info(f"WSC calculado com sucesso: {wsc_out}")
    except Exception as e:
        logger.error(f"FALHA no cálculo WSC: {e}")
        sys.exit(1)

    # Calcular parâmetros de temperatura
    try:
        T1 = calcular_T1_T2(
            str(lst_day_tif_original), str(lst_night_tif_original), str(outputs_dir)
        )
        logger.info(f"T1 calculado com sucesso: {T1:.4f}")
    except Exception as e:
        logger.error(f"FALHA CRÍTICA no cálculo de temperatura: {e}")
        sys.exit(1)

    try:
        mes_processamento = determinar_mes_imagem(
            tif_path=s2_tif_masked,
            data_fallback=data_efetiva,  # Usa a data efetivamente transferida
        )
        logger.info(f"Mês de processamento determinado: {mes_processamento}")

    except Exception as e:
        logger.error(f"Erro ao determinar mês: {e}")
        sys.exit(1)

    # Calcular radiação solar (SOL)
    try:
        sol_output = calcular_sol(
            projeto_dir=projeto_dir,
            outputs_dir=outputs_dir,
            mes=mes_processamento,
            ano_referencia=ANO_REFERENCIA,
            var_pct_mes=VAR_PCT_MES,
            fator_conversao=FATOR_CONVERSAO,
            resolucao_solar=RESOLUCAO_SOLAR,
        )
    except Exception as e:
        logger.error(f"FALHA no cálculo da radiação solar: {e}")
        sys.exit(1)

    # CALCULAR E_max
    try:
        # Obter dimensões da imagem Sentinel-2 recortada
        with rasterio.open(s2_tif_masked) as src:
            nova_largura = src.width
            nova_altura = src.height

        # Caminhos para E_max
        emax_input = (
            projeto_dir
            / "INPUTS"
            / "Subset_ESA_WorldCover_10m_2021_v200_N36W012_Map.tif"
        )
        emax_output = outputs_dir / "E_max.tif"

        # Verificar se o arquivo de entrada existe
        if not emax_input.exists():
            logger.error(f"Arquivo de entrada para E_max não encontrado: {emax_input}")
            sys.exit(1)

        # Executar cálculo do E_max
        calcular_emax(
            caminho_entrada=emax_input,
            caminho_saida=emax_output,
            nova_largura=nova_largura,
            nova_altura=nova_altura,
        )
        logger.info(f"E_max calculado com sucesso: {emax_output}")

    except Exception as e:
        logger.error(f"FALHA no cálculo de E_max: {e}")
        sys.exit(1)

    # Calcular NPP
    try:
        npp_result = executar_calculo_npp(projeto_dir)
        logger.info(f"Cálculo do NPP completo: {npp_result}")
    except Exception as e:
        logger.error(f"FALHA no cálculo do NPP: {e}")
        sys.exit(1)

    # Análise do NPP
    try:
        resultados = analisar_npp(
            npp_input_tif=npp_result,
            resultados_dir=resultados_dir,
            populacao=POPULACAO,
            emissao_co2_per_capita=EMISSOES_CO2_PER_CAPITA,
            tamanho_pixel_ha=0.01,  # para imagens de 10m x 10m
            mes=mes_processamento,
            ano_referencia=ANO_REFERENCIA,
        )
        logger.info(f"Analise do NPP completa. Relatório: {resultados['relatorio']}")
    except Exception as e:
        logger.error(f"FALHA na análise do NPP: {e}")
        sys.exit(1)

    logger.info("Processo completo com sucesso!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"ERRO NÃO TRATADO: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
