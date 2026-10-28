# Motor de Recomendação — Seguro Empresarial

## Pré-requisitos

- Python 3.11 ou superior.
- Arquivos CSV das bases `teste_comum/` e `desenvolvimento/`.

Cada pasta deve conter os seguintes arquivos:

```text
empresas.csv
enderecos_estabelecimentos.csv
sinais_financeiros_operacionais.csv
territorio.csv
bens_cadastrados.csv
template_resultado_times.csv
```

## Instalação

Na pasta do projeto, crie e ative um ambiente virtual.

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Execução

Execute os comandos na pasta do projeto, com o ambiente virtual ativado.

```bash
python engine.py
```

Processa as bases e gera os resultados na pasta `saida/`.

```bash
python testes_coerencia.py
```

Executa os testes de coerência e estabilidade.

```bash
python gerar_frontend.py
```

Inicia o servidor e disponibiliza o dashboard em `http://127.0.0.1:5000`.

Para processar apenas a base CASO:

```bash
python engine.py CASO
```

Para gerar o dashboard da base EMP, utilize o seletor disponível na página ou execute o comando correspondente suportado pelo script.

## Resultados

Os arquivos são gerados na pasta `saida/`:

- `CASO/` — resultados da base de teste.
- `EMP/` — resultados da base de desenvolvimento.
- `testes_coerencia.json` — resultados dos testes de validação.

Os arquivos CSV contêm as recomendações, a elegibilidade, os planos e as coberturas calculadas para cada estabelecimento.