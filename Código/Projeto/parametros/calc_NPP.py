import os
import numpy as np
import rasterio
from PIL import Image
from pathlib import Path
import logging

# Configura logging
logger = logging.getLogger(__name__)


def redimensionar_imagens(input_dir: Path, tamanho_alvo=(1032, 876)):
    """Redimensiona todas as imagens TIFF no diretório especificado"""
    logger.info("--- A INICIAR REDIMENSIONAMENTO ---")

    for arquivo in input_dir.glob("*.tif*"):
        try:
            with Image.open(arquivo) as img:
                if img.size != tamanho_alvo:
                    logger.info(
                        f"A redimensionar: {arquivo.name} ({img.size} → {tamanho_alvo})"
                    )
                    img_redim = img.resize(tamanho_alvo, Image.Resampling.NEAREST)
                    img_redim.save(arquivo, format="TIFF", compression="tiff_deflate")
                else:
                    logger.debug(f"Tamanho OK: {arquivo.name}")
        except Exception as e:
            logger.error(f"ERRO ao processar {arquivo.name}: {str(e)}")

    logger.info("--- REDIMENSIONAMENTO CONCLUÍDO ---")


def calcular_npp(outputs_dir: Path, results_dir: Path):
    """Calcula o NPP usando as imagens processadas"""
    logger.info("---INICIO DO CALCULO DO NPP ---")

    # Carrega valor T1 do arquivo
    t1_path = outputs_dir / "T1.txt"
    try:
        with open(t1_path, "r") as f:
            conteudo = f.read().strip()
            T1 = float(conteudo.split("=")[1])
            logger.info(f"Valor T1 carregado: {T1:.4f}")
    except Exception as e:
        logger.error(f"ERRO ao ler T1: {str(e)}")
        raise

    arquivos_necessarios = ["FPAR.tif", "T2.tif", "WSC.tif", "SOL.tif", "E_max.tif"]
    caminhos = {}

    for arquivo in arquivos_necessarios:
        caminho = outputs_dir / arquivo
        if not caminho.exists():
            logger.error(f"Arquivo nao encontrado: {caminho}")
            raise FileNotFoundError(f"Arquivo {arquivo} não encontrado")
        caminhos[arquivo.split(".")[0]] = caminho

    # Processa as imagens e calcular NPP
    try:
        with rasterio.open(caminhos["FPAR"]) as src_fpar, rasterio.open(
            caminhos["T2"]
        ) as src_t2, rasterio.open(caminhos["WSC"]) as src_wsc, rasterio.open(
            caminhos["SOL"]
        ) as src_sol, rasterio.open(
            caminhos["E_max"]
        ) as src_emax:

            # Carregar dados
            def carregar_banda(src):
                data = src.read(1).astype(np.float32)
                nodata = src.nodata if src.nodata is not None else np.nan
                return np.where(data == nodata, np.nan, data)

            FPAR = carregar_banda(src_fpar)
            T2 = carregar_banda(src_t2)
            WSC = carregar_banda(src_wsc)
            SOL = carregar_banda(src_sol)
            Emax = carregar_banda(src_emax)

            # Cálculo do NPP
            npp = 0.5 * SOL * FPAR * T1 * T2 * WSC * Emax

            # Salvar resultado
            perfil = src_fpar.profile
            perfil.update(dtype=rasterio.float32, count=1, nodata=np.nan)

            results_dir.mkdir(exist_ok=True)
            caminho_npp = results_dir / "NPP_RESULT.tif"

            with rasterio.open(caminho_npp, "w", **perfil) as dst:
                dst.write(npp.astype(np.float32), 1)

            logger.info(f"NPP salvo em: {caminho_npp}")
            return caminho_npp

    except Exception as e:
        logger.error(f"ERRO durante o calculo do NPP: {str(e)}")
        raise


def executar_calculo_npp(projeto_dir: Path):
    """Função principal para executar o calculo do NPP"""
    outputs_dir = projeto_dir / "OUTPUTS"
    results_dir = projeto_dir / "RESULT"

    redimensionar_imagens(outputs_dir)

    return calcular_npp(outputs_dir, results_dir)
