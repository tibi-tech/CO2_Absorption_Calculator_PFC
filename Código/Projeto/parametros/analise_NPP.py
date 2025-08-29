import numpy as np
import rasterio
from pathlib import Path
import logging
from rasterio.enums import Resampling

# Configura logger
logger = logging.getLogger(__name__)


def analisar_npp(
    npp_input_tif: Path,
    resultados_dir: Path,
    populacao: int,
    emissao_co2_per_capita: float,  # t CO₂/pessoa/mês
    tamanho_pixel_ha: float = None,  # tamanho do pixel em hectares
    fator_conversao: float = 44 / 12,  # C para CO₂
    mes: int = None,  # mês de processamento
    ano_referencia: int = None,  # ano de processamento
):
    """
    Realiza análise completa do resultado do NPP:
    1. Limpa dados (substitui NaN por 0)
    2. Converte para CO₂
    3. Calcula sumatorios e percentuais
    4. Gera relatório

    Args:
        npp_input_tif: Caminho para o raster de NPP resultante
        resultados_dir: Diretoria para salvar saídas
        populacao: População da área de estudo
        emissao_co2_per_capita: Emissões per capita (t CO₂/pessoa/mês)
        tamanho_pixel_ha: Tamanho de cada pixel em hectares (para cálculo por área)
        fator_conversao: Fator de conversão C para CO₂ (padrão 44/12)
    """
    logger.info("--- INICIAR ANALISE DO NPP ---")

    # Cria diretoria de resultados
    resultados_dir.mkdir(parents=True, exist_ok=True)

    # Ler dados de entrada
    with rasterio.open(npp_input_tif) as src:
        profile = src.profile.copy()
        npp_data = src.read(1, out_dtype="float32")
        res = src.res  # pixel (x, y) em unidades do CRS

    # Calcular área do pixel
    area_pixel = None
    if tamanho_pixel_ha is None and res != (0, 0):
        area_pixel = abs(res[0] * res[1]) / 10000  # m² -> hectares
        logger.info(f"Área do pixel calculada: {area_pixel:.4f} ha")
    elif tamanho_pixel_ha:
        area_pixel = tamanho_pixel_ha

    npp_clean = np.nan_to_num(npp_data, nan=0.0)

    # Salvar versão limpa (C)
    npp_limpo_tif = resultados_dir / "NPP_RESULT_C.tif"
    with rasterio.open(npp_limpo_tif, "w", **profile) as dst:
        dst.write(npp_clean.astype(profile["dtype"]), 1)
    logger.info(f"Raster limpo (C) salvo em: {npp_limpo_tif}")

    # Converter para CO₂
    co2_data = npp_clean * fator_conversao

    # Salvar versão limpa (C0₂)
    co2_tif = resultados_dir / "NPP_RESULT_CO2.tif"
    with rasterio.open(co2_tif, "w", **profile) as dst:
        dst.write(co2_data.astype(profile["dtype"]), 1)
    logger.info(f"Raster CO₂ salvo em: {co2_tif}")

    # Calcular métricas
    # Emissões
    emissao_total_co2 = populacao * emissao_co2_per_capita  # t CO₂/mês
    emissao_total_c = emissao_total_co2 / fator_conversao  # t C/mês

    # Absorção pela vegetação
    soma_c = (float(npp_clean.sum()) * 100) / 1e6  # t C / mês
    soma_co2 = (float(co2_data.sum()) * 100) / 1e6  # t CO₂ / mês

    # Percentuais
    perc_abs_c = (soma_c / emissao_total_c) * 100 if emissao_total_c > 0 else 0
    perc_abs_co2 = (soma_co2 / emissao_total_co2) * 100 if emissao_total_co2 > 0 else 0

    # Calcular por área
    relatorio_area = ""
    if area_pixel:
        npp_medio_c = np.mean(npp_clean[npp_clean > 0]) * 10  # g/m² → kg/ha
        npp_medio_co2 = npp_medio_c * fator_conversao

        relatorio_area = f"""
        ---------- POR ÁREA ----------
        Área média por pixel: {area_pixel:.2f} ha
        NPP médio (C): {npp_medio_c:.2f} kg C/ha/mês
        NPP médio (CO₂): {npp_medio_co2:.2f} kg CO₂/ha/mês
        """

    # Gerar relatório
    relatorio_txt = resultados_dir / "RELATORIO_NPP.txt"
    with open(relatorio_txt, "w", encoding="utf-8") as f:
        f.write(
            f"""
        {'----------------------- ANÁLISE DO NPP ----------------------- '}

        Relatório de Análise do NPP - Oeiras, Lisboa, Portugal - {mes} / {ano_referencia}
        
        ---------- PARÂMETROS ----------
        População: {populacao:,} habitantes
        Emissões per capita: {emissao_co2_per_capita} t CO₂/pessoa/mês
        Fator de conversão C→CO₂: {fator_conversao:.4f}
        
        ---------- EMISSÕES TOTAIS ----------
        Carbono (C): {emissao_total_c:.2f} tC/mês
        Dióxido de Carbono (CO₂): {emissao_total_co2:.2f} tCO2/mês
        
        ---------- ABSORÇÃO PELA VEGETAÇÃO ----------
        Carbono (C): {soma_c:.2f} tC/mês
        Dióxido de Carbono (CO₂): {soma_co2:.2f} tCO2/mês
        
        ---------- BALANÇO ----------
        Percentual de carbono absorvido: {perc_abs_c:.2f}%
        Percentual de CO₂ absorvido: {perc_abs_co2:.2f}%
        {relatorio_area}
        {'----------------------- FIM DO RELATÓRIO -----------------------'}
        """
        )

    logger.info(f"Relatorio salvo na DIRETORIA: {relatorio_txt}")
    logger.info("--- ANALISE DO NPP CONCLUÍDA ---")

    return {
        "npp_limpo": npp_limpo_tif,
        "npp_co2": co2_tif,
        "relatorio": relatorio_txt,
        "soma_c": soma_c,
        "soma_co2": soma_co2,
        "perc_abs_c": perc_abs_c,
        "perc_abs_co2": perc_abs_co2,
    }
