Calculadora de Absorção de CO₂ - Oeiras, Lisboa, Portugal
=========================================================

Esta aplicação calcula a capacidade de absorção de dióxido de carbono (CO₂) pela vegetação no município de Oeiras, utilizando dados de satélite Sentinel-2 e Sentinel-3 da ESA.

Requisitos do Sistema
---------------------
- Python 3.9.x (recomendado 3.9.13)
- Sistema operacional Windows, Linux ou macOS
- Conexão à internet para download de imagens de satélite
- Conta criada no site COPERNICUS DATA SPACE ECOSYSTEM
	(site: https://dataspace.copernicus.eu/)

Instalação
----------
1. Instalar as dependências necessárias:
    ir á pasta do projeto e correr no terminal:
	   pip install -r requirements.txt

2. Execute o programa:
   python interface.py

2. Na interface gráfica:
   - Selecione o ano 2024
   - Selecione o mês desejado (1 a 12)
   - Clique em "Iniciar"

3. No terminal irá aparecer um link clique e coloque a conta criada, anteriormente, site COPERNICUS DATA SPACE ECOSYSTEM

Fluxo de Processamento
----------------------
1. Download de imagens Sentinel-2 e Sentinel-3
2. Recorte das imagens usando shapefile
3. Cálculo sequencial de parâmetros:
   - NDVI e FPAR (índices de vegetação)
   - WSC (coeficiente de estresse hídrico)
   - T1/T2 (parâmetros de temperatura)
   - SOL (radiação solar)
   - E_max (capacidade máxima de absorção)
4. Cálculo da NPP (Produção Primária Líquida)
5. Análise de absorção de CO₂
6. Geração de relatório final

Parâmetros Configuráveis
------------------------
Os seguintes parâmetros podem ser ajustados no código main.py:
- POPULACAO = 172120 (habitantes de Oeiras)
- EMISSOES_CO2_PER_CAPITA = 0.8917 (ton CO₂/pessoa/mês)
- Variação mensal de radiação solar (dicionário VAR_PCT_MES)

Estrutura de Pastas
-------------------
/INPUTS
  /SENTINEL2 - Imagens originais Sentinel-2
  /SENTINEL3 - Imagens originais Sentinel-3

/OUTPUTS - Resultados intermediários em formato GeoTIFF

/RESULT - Relatório final (RELATORIO_NPP.txt)

/OEIRAS - Shapefile do município

/parametros - Módulos de cálculo

/img - Recursos visuais da interface

Saídas Geradas
--------------
- RELATORIO_NPP.txt na pasta RESULT contendo:
  * Área total de vegetação analisada
  * NPP médio mensal (gC/m²)
  * Total de CO₂ absorvido (toneladas)
  * Emissões de CO₂ do município
  * Comparação entre absorção e emissões

Limitações Conhecidas
---------------------
- Dependência de imagens sem cobertura de nuvens
- Necessidade de conexão estável para download
- Processamento pode levar vários minutos

Suporte Técnico
---------------
Para problemas de execução:
- Confira o log na interface gráfica
- Valide o acesso ao Copernicus Open Access Hub