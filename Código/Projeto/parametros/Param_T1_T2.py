import os
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calcular_T1_T2(input_day: str, input_night: str, output_dir: str) -> float:
    """
    Calcula T1 e T2 a partir de imagens LST diurno e noturno do Sentinel-3

    Parâmetros:
    input_day (str): Caminho para o arquivo LST diurno (GeoTIFF)
    input_night (str): Caminho para o arquivo LST noturno (GeoTIFF)
    output_dir (str): Diretoria para salvar os resultados

    Retorna:
    float: Valor de T1 calculado
    """

    # Função auxiliar
    def fill_leq_zero_with_mean(arr: np.ndarray) -> np.ndarray:
        """Substitui valores <= 0 ou NaN pela média dos > 0 válidos."""
        valid = (~np.isnan(arr)) & (arr > 0)
        if not np.any(valid):
            return arr
        mean_val = np.mean(arr[valid])
        out = arr.copy()
        out[(arr <= 0) | np.isnan(arr)] = mean_val
        return out

    try:
        logger.info(
            f"Iniciando cálculo de T1/T2 com arquivos:\nDiurno: {input_day}\nNoturno: {input_night}"
        )

        # LER LST DIA E NOITE E CONVERTER PARA °C
        def read_lst_celsius(path: str):
            """Lê arquivo LST e converte de Kelvin para Celsius"""
            with rasterio.open(path) as src:
                data = src.read(1).astype(np.float32)  # Ler banda 1
                data = np.where(data == src.nodata, np.nan, data)
                data -= 273.15  # K → °C
                profile = src.profile
            return data, profile

        day, prof_day = read_lst_celsius(input_day)
        night, prof_night = read_lst_celsius(input_night)

        logger.info(
            f"Estatisticas LST (diurno): min={np.nanmin(day):.1f}ºC, max={np.nanmax(day):.1f}ºC"
        )
        logger.info(
            f"Estatisticas LST (noturno): min={np.nanmin(night):.1f}ºC, max={np.nanmax(night):.1f}ºC"
        )

        # Caso resoluções ou grades não coincidam, reprojetar a grade noturna para a grade diurna
        if (
            prof_day["transform"] != prof_night["transform"]
            or prof_day["crs"] != prof_night["crs"]
        ):
            logger.info("Reprojetando imagem noturna para coincidir com diurna...")
            night_rs = np.empty_like(day, dtype=np.float32)
            reproject(
                night,
                night_rs,
                src_transform=prof_night["transform"],
                src_crs=prof_night["crs"],
                dst_transform=prof_day["transform"],
                dst_crs=prof_day["crs"],
                resampling=Resampling.nearest,
                num_threads=2,
            )
            night = night_rs
            prof_night = prof_day

        # MÉDIA PIXEL-A-PIXEL DIA, NOITE, TOTAL
        T_day_mean = day
        T_night_mean = night
        T_mean = 0.5 * (T_day_mean + T_night_mean)

        logger.info(
            f"Estatisticas T_mean: min={np.nanmin(T_mean):.1f}ºC, max={np.nanmax(T_mean):.1f}ºC"
        )

        # CÁLCULO DE Topt, T1, T2
        # calcular Topt
        valid = (~np.isnan(T_mean)) & (T_mean > -50) & (T_mean < 60)

        if np.any(valid):
            Topt = np.nanmean(T_mean[valid])
        else:
            # Valor padrão se nenhum pixel válido for encontrado
            Topt = 20.0
            logger.warning(
                "Nenhum pixel válido encontrado para cálculo de Topt. Usando valor padrão 20.0°C"
            )

        T1 = 0.8 + 0.02 * Topt - 0.0005 * Topt**2

        logger.info(f"Topt calculado: {Topt:.2f}ºC")
        logger.info(f"T1 calculado: {T1:.4f}")

        temp1 = np.exp(0.2 * (Topt - 10 - T_mean))
        temp2 = np.exp(0.3 * (-Topt - 10 + T_mean))
        T2 = 1.1814 / (1 + temp1) * (1 / (1 + temp2))
        T2 = fill_leq_zero_with_mean(T2)

        logger.info(
            f"Estatísticas T2: min={np.nanmin(T2):.4f}, max={np.nanmax(T2):.4f}"
        )

        # SALVAR RASTERS E T1.TXT
        def save_raster(path: str, data: np.ndarray, profile: dict):
            """Salva um raster com o perfil especificado"""
            prof = profile.copy()
            prof.update(dtype=rasterio.float32, count=1, nodata=np.nan, compress="lzw")
            with rasterio.open(path, "w", **prof) as dst:
                dst.write(data.astype(np.float32), 1)
            logger.info(f"Arquivo salvo: {path}")

        os.makedirs(output_dir, exist_ok=True)
        save_raster(os.path.join(output_dir, "T_day_mean.tif"), T_day_mean, prof_day)
        save_raster(
            os.path.join(output_dir, "T_night_mean.tif"), T_night_mean, prof_day
        )
        save_raster(os.path.join(output_dir, "T_mean.tif"), T_mean, prof_day)
        save_raster(os.path.join(output_dir, "T2.tif"), T2, prof_day)

        t1_path = os.path.join(output_dir, "T1.txt")
        with open(t1_path, "w") as f:
            f.write(f"T1 = {T1:.4f}\n")
        logger.info(f"Valor de T1 salvo na diretoria: {t1_path}")

        return T1

    except Exception as e:
        logger.error(f"Erro no cálculo de T1/T2: {str(e)}")
        raise
