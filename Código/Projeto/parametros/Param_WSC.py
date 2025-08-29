import numpy as np
import rasterio


def calculate_WSC_from_tif(tif_path, output_path):
    """
    Calcula o Water Canopy Stress (WSC) a partir de um arquivo .tif
    """
    try:
        # Abrir o arquivo .tif
        with rasterio.open(tif_path) as src:
            band_descriptions = src.descriptions
            band_names = [
                desc or f"band_{i+1}" for i, desc in enumerate(band_descriptions)
            ]
            print("Bandas disponiveis:", band_names)

            # Encontrar índices das bandas SWIR (B11 e B12)
            band11_idx = None
            band12_idx = None

            for i, name in enumerate(band_names):
                if "B11" in name or "11" in name:
                    band11_idx = i + 1
                elif "B12" in name or "12" in name:
                    band12_idx = i + 1

            if band11_idx is None or band12_idx is None:
                if len(band_names) >= 4:
                    band11_idx = 3
                    band12_idx = 4
                    print("Utilizar as bandas por posição (idx 3 e 4)")
                else:
                    raise ValueError(
                        f"Bandas SWIR (B11/B12) não encontradas. Bandas disponiveis: {band_names}"
                    )

            print(
                f"Utilizando banda B11: índice {band11_idx} - {band_names[band11_idx-1]}"
            )
            print(
                f"Utilizando banda B12: índice {band12_idx} - {band_names[band12_idx-1]}"
            )

            # Ler as bandas SWIR
            b11 = src.read(band11_idx).astype(np.float32)
            b12 = src.read(band12_idx).astype(np.float32)

            # Normalizar valores
            b11 = b11 / 10000.0
            b12 = b12 / 10000.0

            # Calcular SIMI
            simi = 0.7071 * np.sqrt(np.square(b11) + np.square(b12))

            # Normalizar SIMI
            simi_valid = simi[np.isfinite(simi)]
            simi_min = np.min(simi_valid)
            simi_max = np.max(simi_valid)
            nsimi = (simi - simi_min) / (simi_max - simi_min)

            # Calcular WSC
            wsc = 0.5 + 0.5 * (1 - nsimi)
            wsc[~np.isfinite(wsc)] = np.nan

            # Perfil do arquivo de saída
            profile = src.profile
            profile.update(
                {"count": 1, "dtype": "float32", "nodata": np.nan, "compress": "lzw"}
            )

            # Salvar como GeoTIFF
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(wsc.astype(np.float32), 1)

        return output_path

    except Exception as e:
        print(f"Erro no calculo do WSC: {str(e)}")
        raise
