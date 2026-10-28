# Motor de recomendação – Seguro Empresarial (Datathon Proteção Inteligente)

**Equipe:** _[preencher nome da equipe e integrantes]_ · **Desafio:** Seguro Empresarial

Para cada empresa-estabelecimento, o projeto decide se o caso é elegível, recomenda um plano (Essencial, Prático ou Total), detalha as coberturas com faixa mínima e máxima em reais e lista poucas perguntas de confirmação. É feito só com regras explícitas, sem machine learning, e o resultado é sempre o mesmo a cada execução.

---

## Como rodar (passo a passo)

### 1. Pré-requisitos
- **Python 3.11 ou superior** ([python.org](https://www.python.org/downloads/)). No Windows, marque "Add Python to PATH" ao instalar.
- Um terminal na pasta do projeto (no VS Code: Terminal > New Terminal).

### 2. Pastas de dados
Os CSVs da organização não vêm no repositório. Crie estas duas pastas ao lado de `engine.py` e copie os arquivos para dentro delas, **com estes nomes exatos**:

```
Datathon/
├── engine.py
├── testes_coerencia.py
├── gerar_frontend.py
├── requirements.txt
├── teste_comum/          ← base comum de teste (144 estabelecimentos, IDs "CASO_")
│   ├── empresas.csv
│   ├── enderecos_estabelecimentos.csv
│   ├── sinais_financeiros_operacionais.csv
│   ├── territorio.csv
│   ├── bens_cadastrados.csv
│   └── template_resultado_times.csv
└── desenvolvimento/      ← base de desenvolvimento (2.978 estabelecimentos, IDs "EMP_")
    └── (os mesmos 6 arquivos)
```

Outros arquivos podem ficar nas pastas, o motor os ignora. Para conferir qual é qual, o `enderecos_estabelecimentos.csv` da `teste_comum` tem cerca de 145 linhas e o da `desenvolvimento` cerca de 2.979.

### 3. Ambiente virtual e dependências
**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Se o PowerShell bloquear a ativação, rode antes `Set-ExecutionPolicy -Scope Process RemoteSigned`.

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Quando o ambiente estiver ativo, aparece `(venv)` no início da linha do terminal. Se o `requirements.txt` der erro de versão, use `pip install pandas numpy`.

### 4. Executar
Com o ambiente ativo, dentro da pasta do projeto:

| Comando | O que faz |
|---|---|
| `python engine.py` | Processa as duas bases (cerca de 15 s) |
| `python engine.py CASO` | Só a base comum de teste |
| `python testes_coerencia.py` | Testes de coerência, estabilidade e sensibilidade |
| `python gerar_frontend.py` | Gera `frontend_CASO.html` |
| `python gerar_frontend.py EMP` | Gera o front da base de desenvolvimento (arquivo de cerca de 17 MB) |

Rode primeiro o `engine.py`, porque o front e os testes dependem da pasta `saida/`.

### 5. Onde ver os resultados
- `saida/CASO/` (base comum, **é a que vale para a entrega**) e `saida/EMP/` (desenvolvimento). Cada pasta tem:
  - `template_resultado_times.csv`: uma linha por estabelecimento, com elegibilidade, plano, justificativa e perguntas.
  - `template_coberturas_times.csv`: uma linha por cobertura, com faixa mínima e máxima, confiança, regra de cálculo e o que confirmar.
  - `metricas.json`: totais e indicadores de qualidade.
- `saida/testes_coerencia.json`: resultado dos testes.
- `frontend_CASO.html`: dê dois cliques para abrir no navegador, sem servidor. Escolha um estabelecimento na lista para ver o plano, os motivos, as perguntas e as coberturas.

Os CSVs são gravados em UTF-8. No Excel, importe por Dados > De Texto/CSV com UTF-8, senão os acentos aparecem quebrados.

### 6. Problemas comuns
| Mensagem | Causa e solução |
|---|---|
| `FileNotFoundError ... .csv` | Arquivo com nome diferente ou fora de `teste_comum/` ou `desenvolvimento/`. Confira a estrutura do passo 2. |
| `ModuleNotFoundError: pandas` | Ambiente virtual desativado ou dependências não instaladas. Refaça o passo 3. |
| `FileNotFoundError ... saida` ao gerar o front | Rode `python engine.py` antes. |
| A ativação do venv é bloqueada no Windows | Use o comando `Set-ExecutionPolicy` do passo 3. |
| O VS Code usa outro Python | Ctrl+Shift+P > "Python: Select Interpreter" e escolha o do `venv`. |

---

## Como o motor decide

1. **Junta** empresa, endereço, sinais financeiros e bens de cada estabelecimento.
2. **Elegibilidade** (guia 10.1): é inelegível o imóvel em obra (`EM_OBRA`) ou `IRREGULAR`, com parede externa combustível, de atividade rural ou com estimativa mínima de incêndio acima de R$ 7,5 mi (vai para o Seguro Personalizado Empresarial). O que não vem nos dados vira uma única pergunta de confirmação.
3. **Contexto:** o tipo de local (loja de rua, térreo, galeria, sala comercial, galpão, box) vem do complemento do endereço. Quem paga aluguel é tratado como locatário, e quem não paga como proprietário provável, a confirmar.
4. **Rateio:** faturamento e funcionários, que estão no nível da empresa, são divididos entre as unidades pela folha de pagamento de cada uma.
5. **Plano:**
   - **Total:** local com fachada ou vitrine, 5 ou mais empregados na unidade e exposição a furto ou vendaval.
   - **Prático:** exposição a furto ou vendaval, ou cobertura específica da atividade (refrigeração, delivery, valores em espécie).
   - **Essencial:** os demais casos.
6. **Coberturas:** as seis fixas do guia, que incluem a Proteção Cibernética (ela falta no catálogo de coberturas, mas o guia a exige), mais as coberturas do plano e os adicionais aplicáveis. Cada linha traz a fórmula usada em `regra_calculo_utilizada`.
7. **Área ausente** (cerca de 60% dos casos): estimada por regressão com energia, folha, atividade e tipo de local, e a confiança fica baixa.
8. **Perguntas:** no máximo 4 por caso, em ordem de impacto.

Cada justificativa separa **[DISPONÍVEL]** (o que está nos dados), **[SUGESTÃO]** (o que foi inferido) e **[CONFIRMAR]** (o que precisa de resposta do cliente).

## Premissas e limitações
- Custo de construção por m² (R$ 2.000 a 7.000), múltiplos de responsabilidade civil, 3 a 12 meses de aluguel e frações de furto e vendaval são **premissas internas**, não calibradas com sinistros reais nem com a tabela oficial do produto. Precisam de revisão atuarial.
- `IRREGULAR` foi tratado como inelegível por interpretação nossa, porque o guia não diz isso de forma explícita.
- Nenhuma fonte externa foi usada. Não há índices de alagamento, vendaval ou furto. Sugestões para evoluir: IBGE (malha municipal), INMET, Defesa Civil e SSP.
- O índice de exposição digital não mede risco cibernético e só dimensiona a faixa de Proteção Cibernética.
- A inconsistência financeira (despesa maior que faturamento) só é testada em empresas de uma unidade.
- Os manuais oficiais e as Condições Gerais não foram consultados item a item.

## Métricas
| Base | Casos | Elegíveis / Inelegíveis | Planos (Prático / Total / Essencial) | Confiança baixa | Perguntas (média) | Linhas de cobertura |
|---|---|---|---|---|---|---|
| CASO | 144 | 137 / 7 | 99 / 24 / 14 | 13,1% | 3,14 | 1.297 |
| EMP | 2.978 | 2.848 / 130 | 2.125 / 516 / 207 | 18,6% | 3,12 | 26.947 |

- 100% dos casos foram processados e justificados, e todas as faixas têm mínimo menor ou igual ao máximo.
- Duas execuções geram arquivos idênticos.
- O plano coincide em 87,7% (CASO) e 70,2% (EMP) dos casos de mesma atividade e tipo de local.
- Com estoque ±20%, no máximo 0,73% dos casos mudam de plano, e a faixa máxima de incêndio varia cerca de ±1%.
- Os testes verificam coerência e estabilidade, não a precisão dos valores, porque a base não tem gabarito de sinistros.

## Uso em canais
- **One Click Buy:** plano e faixas já calculados, com no máximo 4 perguntas.
- **Atendimento assistido:** justificativa e alternativa em texto, para o gerente explicar ao cliente.
- **Agente autônomo:** saídas estruturadas e regras auditáveis, com confirmação humana antes de contratar.

## Tecnologias e uso de IA
Python 3.12, pandas e numpy (versões em `requirements.txt`). O front é HTML e JavaScript puros. Uma ferramenta de IA (Claude, da Anthropic) apoiou a leitura das bases, a escrita do código e deste README. A equipe deve entender, revisar e ser capaz de defender as regras e premissas.