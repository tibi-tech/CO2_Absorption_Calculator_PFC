import os
import json
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import shape, mapping


def aplicar_mascara_shapefile(shapefile_path, raster_path, output_path, nodata=0):
    """
    Aplica uma máscara de shapefile a um raster TIFF e salva o resultado,
    preservando os nomes das bandas originais.
    """
    os.environ["SHAPE_RESTORE_SHX"] = "YES"

    try:
        # Carregar o shapefile
        gdf = gpd.read_file(shapefile_path)
        print(f"Shapefile carregado: {shapefile_path}")

        # Abrir o raster
        with rasterio.open(raster_path) as src:
            print(f"Raster aberto: {raster_path}")
            print(f"Nomes originais das bandas: {src.descriptions}")

            # Converter CRS se necessário
            if gdf.crs != src.crs:
                print(f"Convertendo CRS: {gdf.crs} -> {src.crs}")
                gdf = gdf.to_crs(src.crs)

            # Combinar geometrias (suporta múltiplos polígonos)
            geoms = (
                [mapping(gdf.unary_union)]
                if len(gdf) > 1
                else [mapping(geom) for geom in gdf.geometry]
            )

            # Aplicar a máscara
            out_image, out_transform = mask(
                src, geoms, crop=True, filled=True, nodata=nodata
            )

            # Atualizar metadados
            out_meta = src.meta.copy()
            out_meta.update(
                {
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "nodata": nodata,
                }
            )

        # Salvar resultado preservando nomes das bandas
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)

            for i in range(1, src.count + 1):
                dest.set_band_description(i, src.descriptions[i - 1] or f"band_{i}")

            if src.tags():
                dest.update_tags(**src.tags())

            print(f"Nomes das bandas preservados: {dest.descriptions}")

        print(f"Raster recortado salvo em: {output_path}")
        return output_path

    except Exception as e:
        print(f"Erro ao aplicar mascara: {str(e)}")
        raise


def aplicar_mascara_txt(txt_path, raster_path, output_path, nodata=0):
    """
    Aplica uma máscara a um raster TIFF utilizando um polígono em formato GeoJSON contido num arquivo .txt
    e salva o resultado, preservando os nomes das bandas originais.
    """
    try:
        # Carregar geometria do arquivo .txt
        with open(txt_path, "r") as f:
            geojson_data = json.load(f)
            print(f"Geometria carregada do .txt: {txt_path}")

        geom = shape(geojson_data)  # Converte para objeto shapely
        geoms = [mapping(geom)]  # Prepara geometria para o rasterio.mask

        # Abrir o raster
        with rasterio.open(raster_path) as src:
            print(f"Raster aberto: {raster_path}")
            print(f"Nomes originais das bandas: {src.descriptions}")

            # Aplicar a máscara
            out_image, out_transform = mask(
                src, geoms, crop=True, filled=True, nodata=nodata
            )

            # Atualizar metadados
            out_meta = src.meta.copy()
            out_meta.update(
                {
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "nodata": nodata,
                }
            )

        # Salvar o novo raster
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)

            for i in range(1, src.count + 1):
                dest.set_band_description(i, src.descriptions[i - 1] or f"band_{i}")

            if src.tags():
                dest.update_tags(**src.tags())

            print(f"Nomes das bandas preservados: {dest.descriptions}")

        print(f"Raster recortado salvo em: {output_path}")
        return output_path

    except Exception as e:
        print(f"Erro ao aplicar mascara: {str(e)}")
        raise
