# Scraper de Produtos Capilares

Sistema de scraping para coleta e analise de produtos capilares de diversas marcas brasileiras.

## Funcionalidades

### Scraper Python
- Coleta automatica de produtos de sites de cosmeticos
- Parser generico que funciona com a maioria dos e-commerces
- Extracao de: nome, marca, descricao, ingredientes, modo de uso, imagens
- Deteccao automatica de claims (vegano, sem sulfato, cruelty-free, etc)
- Classificacao de cronograma capilar (Hidratacao/Nutricao/Reconstrucao)
- Score de adequacao para cabelos finos
- Exportacao em Excel e JSON

### Dashboard React
- Visualizacao de todos os produtos coletados
- Filtros por marca, status, dados incompletos
- Edicao manual de dados faltantes
- Persistencia de edicoes no navegador
- Exportacao de dados editados
- Indicadores visuais de completude

## Estrutura do Projeto

```
scrapper/
├── scraper_capilar.py      # Scraper principal
├── brand_urls_full.txt     # Lista completa de URLs (~400 marcas)
├── brand_urls_test.txt     # Lista de teste
├── produtos_capilares.json # Dados coletados
├── produtos_capilares.xlsx # Dados em Excel
└── product-dashboard/      # Dashboard React
    ├── src/
    │   ├── App.jsx         # Componente principal
    │   └── data.json       # Dados para visualizacao
    └── package.json
```

## Instalacao

### Scraper (Python)

```bash
# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Instalar dependencias
pip install requests beautifulsoup4 pandas openpyxl
```

### Dashboard (React)

```bash
cd product-dashboard
npm install
```

## Uso

### Executar Scraper

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Rodar com arquivo de URLs
python scraper_capilar.py brand_urls_full.txt

# Ou com arquivo de teste
python scraper_capilar.py brand_urls_test.txt
```

### Executar Dashboard

```bash
cd product-dashboard
npm run dev
# Acesse http://localhost:5173
```

### Atualizar Dashboard com Novos Dados

```bash
cp produtos_capilares.json product-dashboard/src/data.json
```

## Claims Detectados

- Sem sulfato
- Sem parabenos
- Vegano
- Cruelty-free
- Organico
- Natural
- Low Poo / No Poo
- Protecao termica
- Filtro UV
- Dermatologicamente testado

## Cronograma Capilar

O sistema classifica automaticamente os produtos em:
- **H** - Hidratacao (humectantes)
- **N** - Nutricao (oleos)
- **R** - Reconstrucao (proteinas)

## Limitacoes

- Sites que usam JavaScript para carregar produtos (React/Vue/Angular) podem nao funcionar com o parser atual
- Alguns sites podem bloquear requisicoes automaticas
- A extracao de ingredientes depende da estrutura do site

## Contribuicao

1. Fork o repositorio
2. Crie uma branch para sua feature
3. Faca commit das alteracoes
4. Abra um Pull Request

## Licenca

MIT
