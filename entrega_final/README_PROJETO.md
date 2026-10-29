# Proteção Inteligente — Motor de Recomendação do Seguro Empresarial

Datathon Proteção Inteligente · BB Seguros · **Desafio: Seguro Empresarial**

## Equipe

| Campo | Valor |
| --- | --- |
| Nome da equipe | Tropa do BB |
| Integrantes | Arthur Marques, Eduardo Augusto, Isabela Martins |
| Instituição / turma | BB, BBTS |
| Desafio | Seguro Empresarial |

## Objetivo

Recomendar, para cada **empresa + estabelecimento**, um plano do Seguro Empresarial (Essencial, Prático ou Total) com coberturas e faixas de valor, de forma **explicável, revisável e reutilizável** em três jornadas: One Click Buy (lote), atendimento assistido (gerente) e agentes autônomos.

O fluxo segue o guia: **sinais → sugestão inicial → confiança → confirmação → recomendação**. Para cada caso, o motor responde:

- O caso é elegível? Se não, por quê (e se deve ir para o Seguro Personalizado Empresarial)?
- Qual plano, quais coberturas (fixas, padrão do plano, específicas da atividade, opcionais) e quais faixas mínima e máxima?
- Quais dados foram **observados**, **derivados**, **estimados** ou **confirmados**?
- Qual a confiança geral e quais perguntas faltam (no máximo 4, priorizadas)?
- Por que esse plano, e qual a **alternativa** com o trade-off?

A abordagem é **baseada em regras explícitas + estimativas por faixa**, com um único modelo estatístico (regressão log-linear da área). Não há aprendizado supervisionado, e o processo é 100% determinístico.

## Arquitetura

O motor é **um só**: recebe um caso, devolve um JSON padrão e não lê nem escreve arquivos. Cada jornada é um **adaptador** fino que só muda a apresentação.

```
             ┌──────────── uma vez por base ────────────┐
CSVs base ─► ajustar_referencias() ─► saida/<TAG>/referencias.json
                                       (modelo de área, aluguel R$/m²)

             ┌──────────────── por caso ────────────────┐
caso + bens + refs ─► preparar() ─► [aplicar_respostas()] ─► decidir() ─► recomendar() → JSON
                                                                              │
                         ┌────────────────────┬───────────────────────────────┤
                    Lote (CSV)       Assistido (Flask + tela)         Agente (LLM)
                    engine.py        gerar_frontend.py               /api/chat
```

| Camada | Funções (`engine.py`) | Papel |
|---|---|---|
| Referências | `ajustar_area`, `ajustar_referencias`, `carregar_referencias` | Aprendidas da base inteira uma vez e salvas em JSON |
| Preparação | `preparar` | Tipo de local, rateio da empresa por folha entre unidades, área estimada, agregados de bens |
| Confirmação | `aplicar_respostas`, `RESPOSTAS_ACEITAS` | Aplica as respostas do cliente/gerente **antes** da decisão |
| Motor | `decidir`, `recomendar`, `recomendar_imovel` | Elegibilidade, plano, faixas, confiança, perguntas, justificativa, alternativa |
| Lote | `processar`, `metricas` | Processa todos os casos e preenche os templates |

### Contrato JSON (`versao_contrato` 1.1)

| Campo | Conteúdo |
|---|---|
| `ids` | `empresa_id`, `imovel_id` |
| `elegivel`, `motivos_inelegibilidade`, `direcionamento` | Elegibilidade; direcionamento ao Seguro Personalizado Empresarial quando a cobertura básica passa de R$ 7,5 mi |
| `plano`, `motivos_plano`, `assistencias` | Plano recomendado, por quê, pacotes de assistência do plano |
| `coberturas[]` | `nome`, `grupo`, `min`, `max`, `confianca`, `dados`, `regra`, `justificativa`, `a_confirmar`, `observacao` |
| `alternativa` | Um plano alternativo, coberturas que entram (com faixas) e que saem, assistências e trade-off |
| `confianca_geral` | ALTA / MEDIA / BAIXA |
| `sinais{}` | Cada dado com `valor`, `origem` (OBSERVADO / DERIVADO / ESTIMADO / CONFIRMADO) e `fonte` |
| `perguntas[]` | `id`, `tipo` (booleano / numero / opcao), `texto` e, quando há, `opcoes` / `campos` |
| `respostas_aplicadas`, `respostas_ignoradas` | O que foi confirmado e o que foi descartado |
| `justificativa` | Texto com as marcas `[DISPONÍVEL]`, `[SUGESTÃO]`, `[CONFIRMADO]`, `[CONFIRMAR]` |
| `template` | As linhas no formato dos CSVs (usado pelo lote) |

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `engine.py` | Motor de recomendação e processamento em lote |
| `testes_coerencia.py` | Testes de reprodutibilidade, coerência, sensibilidade e confirmação |
| `gerar_frontend.py` | Servidor Flask: dashboard, atendimento assistido (API do motor) e assistente com LLM |
| `frontend_CASO.html` | Página gerada para a base comum (abre sem servidor, em modo só leitura) |
| `saida/CASO/` | **Entrega:** templates preenchidos da base comum, `metricas.json`, `referencias.json` |
| `saida/EMP/` | Mesmos arquivos para a base de desenvolvimento |
| `saida/testes_coerencia.json` | Resultado dos testes |
| `requirements.txt`, `.python-version` | Dependências com versão fixa e versão do Python |
| `.env.example` | Variáveis do assistente com LLM (opcional) |

## Execução

**Pré-requisitos:** Python 3.11 ou superior (testado com **Python 3.14.6**) e as pastas de dados da organização na raiz do projeto: `teste_comum/` (base comum, 144 estabelecimentos) e `desenvolvimento/` (2.978 estabelecimentos). Outra opção é apontar a variável `DADOS_DIR` para a pasta que contém as duas.

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

python engine.py                    # lote: gera saida/CASO e saida/EMP (python engine.py CASO para só a base comum)
python testes_coerencia.py          # testes de coerência, estabilidade e confirmação
python gerar_frontend.py            # http://127.0.0.1:5000 (dashboard + atendimento assistido)
```

O assistente com LLM é opcional: copie `.env.example` para `.env` e preencha `OPENAI_API_KEY`. O padrão é o Gemini no plano gratuito (chave em [aistudio.google.com/apikey](https://aistudio.google.com/apikey)), chamado pela API compatível com a OpenAI. Para usar a OpenAI, apague `OPENAI_BASE_URL`. O lote, os testes e o atendimento assistido funcionam sem chave.

### Demonstração online

A tela também roda num servidor público (Render), sem instalar nada e sem chave: **[link da demonstração](#)**. No primeiro acesso, o servidor pode levar cerca de um minuto para acordar.

O deploy publica só a base comum de teste (`dados_publicos/teste_comum/`); a base de desenvolvimento fica fora. Configuração do serviço no Render:

| Campo | Valor |
|---|---|
| Build | `pip install -r requirements.txt` |
| Start | `gunicorn gerar_frontend:app --bind 0.0.0.0:$PORT --timeout 120` |
| Variáveis | `DADOS_DIR=dados_publicos`, `PYTHON_VERSION=3.14.6`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` (valores do `.env.example`) |

### Exemplos de uso do motor

Um caso isolado, com e sem confirmação:

```python
import engine as E
d, bens, _, _ = E.carregar(E.DATASETS["CASO"])
refs = E.carregar_referencias("CASO")

j = E.recomendar_imovel("IMO_CASO_00002_01", d, bens, refs)
j2 = E.recomendar_imovel("IMO_CASO_00002_01", d, bens, refs, respostas={
    "relacao_imovel": {"relacao": "LOCATARIO", "aluguel_mensal": 6000},
    "area_m2": 200,
    "elegibilidade_local": "SIM",
})
```

Pela API (com o servidor rodando):

```bash
curl "http://127.0.0.1:5000/api/caso/IMO_CASO_00002_01?dataset=CASO"
curl -X POST http://127.0.0.1:5000/api/caso/IMO_CASO_00002_01/confirmar \
     -H "Content-Type: application/json" \
     -d '{"dataset": "CASO", "respostas": {"area_m2": 200, "elegibilidade_local": "SIM"}}'
```

## Como a recomendação é feita

### 1. Elegibilidade (antes de qualquer recomendação)

O caso é **inelegível** quando há imóvel em obra (`EM_OBRA`), situação cadastral irregular (possível imóvel tombado, condenado ou desapropriado), parede externa em material combustível ou atividade rural. Caso inelegível não recebe plano nem coberturas, e o motor pergunta se o impedimento foi resolvido.

Se a estimativa **mínima** de incêndio passa de R$ 7,5 mi, o caso é direcionado ao **Seguro Personalizado Empresarial**. Se só a máxima passa, a faixa é limitada ao teto e o motor pede a confirmação do valor de reposição.

As restrições que a base não permite verificar (comunidade/favela/área rural, outra proposta BB Seguros para o mesmo objeto) viram sempre a primeira pergunta de confirmação. Se o cliente responder "não", o caso passa a inelegível.

### 2. Plano

| Plano | Quando |
|---|---|
| **TOTAL** | Fachada ou vitrine exposta (loja de rua, térreo, galeria) **e** 5 ou mais empregados na unidade **e** exposição a furto ou vendaval |
| **PRÁTICO** | Exposição a furto (atividade, estoque, bens portáteis), local exposto a vendaval, ou coberturas específicas da atividade (refrigeração, delivery, valores em caixa), que só existem no Prático e no Total |
| **ESSENCIAL** | Nenhum dos sinais acima (perfil de baixo estoque ou escritório) |

**Alternativa única para comparação:** Total → Prático; Essencial → Prático; Prático → Total, ou Essencial quando só as coberturas específicas da atividade justificaram o Prático.

### 3. Faixas

Toda cobertura recebe uma faixa em reais, com regra, dados, confiança e o que confirmar. Exemplos:

- **Incêndio:** mínimo = estoque médio + bens de vínculo alto/médio ponderados (+ prédio pela área mínima × custo/m², se próprio); máximo = estoque de pico + bens prováveis (+ prédio pela área máxima). Limitada a R$ 7,5 mi.
- **Perda de aluguel:** 3 a 12 meses do aluguel observado; sem aluguel, usa a mediana de R$/m² de locatários do mesmo município e tipo de local.
- **RC Estabelecimento:** múltiplo do faturamento da unidade conforme a atividade (teto R$ 2 mi).
- **Despesas fixas:** 1 a 3 meses; **Proteção cibernética:** 1 a 3 meses de receita digital (teto R$ 1 mi).
- **Específicas da atividade** (deterioração de mercadorias, delivery, roubo de valores) entram só no Prático/Total, quando os sinais indicam.

Empresas com várias unidades têm faturamento e empregados rateados pela folha de pagamento de cada unidade.

### 4. Confiança e origem dos dados

A confiança geral soma pontos de incerteza: área estimada, vínculo fraco dos bens, faturamento de baixa confiança, endereço divergente do CNPJ, inconsistência entre despesas e faturamento, relação com o imóvel não observada e situação cadastral não regular. Até 2 pontos = ALTA; 3 a 4 = MÉDIA; 5 ou mais = BAIXA.

Cada dado em `sinais` traz a origem: **OBSERVADO** (cadastral), **DERIVADO** (fórmula documentada), **ESTIMADO** (sugestão a partir de sinais) ou **CONFIRMADO** (informado pelo cliente ou gerente). Estimativas nunca são apresentadas como fato.

### 5. Confirmação

As perguntas são priorizadas (no máximo 4 por caso). Cada resposta substitui o sinal correspondente **antes** da decisão, então plano, faixas, confiança e perguntas são recalculados, e o dado passa a `CONFIRMADO`.

| id | Efeito da resposta |
|---|---|
| `elegibilidade_local` | "Não" torna o caso inelegível |
| `impedimento_resolvido` | Obra concluída ou imóvel regularizado: o caso volta a ser avaliado |
| `relacao_imovel` | Proprietário ou locatário (com o aluguel): muda o objeto segurado e a perda de aluguel |
| `area_m2` | Substitui a área estimada; a faixa vira ±10% |
| `endereco_cnpj` | Remove ou mantém a penalidade de confiança |
| `bens_baixa_confianca` | Inclui integralmente ou exclui os bens de vínculo fraco |
| `faturamento_despesas` | Substitui faturamento e despesas fixas |
| `refrigeracao`, `delivery`, `valores_em_caixa` | Ligam ou desligam as coberturas específicas da atividade |
| `valor_reposicao` | Substitui a estimativa de incêndio (±10%) e reavalia o teto de R$ 7,5 mi |

## Jornadas

| Jornada | Como usa o motor |
|---|---|
| **One Click Buy / lote** | `python engine.py` processa todos os casos e preenche os dois templates |
| **Atendimento assistido** | Na tela, o gerente seleciona o caso, vê o plano, as faixas e a origem de cada dado, responde às perguntas e clica em **Confirmar e recalcular**. A tela mostra o que mudou em relação à sugestão inicial e compara com a alternativa |
| **Agente** | O assistente com LLM (`/api/chat`) responde sobre os resultados a partir dos arquivos gerados. O LLM só conversa: elegibilidade, plano e faixas vêm sempre do motor |

## Métricas e resultados

| Métrica | Base comum (CASO) | Desenvolvimento (EMP) |
|---|---|---|
| Casos processados | 144 / 144 (100%) | 2.978 / 2.978 (100%) |
| Elegíveis / inelegíveis | 137 / 7 | 2.848 / 130 |
| Planos (Essencial / Prático / Total) | 14 / 99 / 24 | 207 / 2.125 / 516 |
| Confiança (Alta / Média / Baixa) | 47 / 72 / 18 | 1.025 / 1.292 / 531 |
| % confiança baixa | 13,1% | 18,6% |
| Média de perguntas de confirmação | 3,14 | 3,12 |
| % recomendações com justificativa | 100% | 100% |
| Linhas de cobertura / faixas válidas (mín ≤ máx) | 1.297 / 100% | 26.947 / 100% |
| % planos com todas as coberturas fixas | 100% | 100% |
| Área imputada (sem laudo) | 60,4% | 61,7% |
| Modelo de área: R² (escala log) / n com laudo | 0,758 / 57 | 0,837 / 1.140 |
| Tempo de execução do lote | 0,12 s | 2,3 s |

Inelegíveis na base comum: 6 imóveis em obra e 1 com situação cadastral irregular.

### Testes (`saida/testes_coerencia.json`)

| Teste | CASO | EMP |
|---|---|---|
| Reprodutibilidade (hash do CSV igual em duas execuções) | ✅ | ✅ |
| Inelegíveis sem cobertura | ✅ | ✅ |
| Faixas válidas e sem nulos | 100% | 100% |
| Planos aninhados (Essencial ⊂ Prático ⊂ Total) | ✅ | ✅ |
| Consistência entre semelhantes (mesma atividade e tipo de local → plano modal) | 87,7% | 70,2% |
| Sensibilidade: estoque +20% → troca de plano / variação do máximo de incêndio | 0,7% / +1,1% | 0,2% / +1,5% |
| Sensibilidade: estoque −20% → troca de plano / variação do máximo de incêndio | 0% / −1,1% | 0,3% / −1,4% |
| Confirmação: área vira CONFIRMADO, "não" no local → inelegível, faixas válidas, determinismo (137 casos) | 0 falhas | — |

Não há métricas de acurácia: o problema não tem rótulo supervisionado. Os testes mostram consistência e estabilidade das regras, não a correção comercial das faixas.

## Premissas

- Custo de reconstrução por m² conforme o padrão construtivo (econômico R$ 2.000–3.000; normal R$ 3.000–4.500; superior R$ 4.500–7.000) é premissa interna; o CUB não foi consultado.
- Sem pagamento de aluguel recorrente, a relação sugerida é **proprietário**, sempre com pergunta de confirmação.
- Bens com probabilidade de vínculo ≥ 0,48 entram no máximo; só os de vínculo alto/médio entram no mínimo.
- Refrigeração (probabilidade ≥ 0,5), delivery (probabilidade ≥ 0,4 ou receita de delivery ≥ 15%) e valores em caixa (recebimentos digitais ≤ 50% em atividades de varejo e serviços) ativam as coberturas específicas.
- Faturamento e empregados da empresa são rateados entre unidades pela folha de pagamento.
- Os planos são uma sugestão de pacote; as assistências acompanham o plano e não entram no template de coberturas.

## Limitações

- Mais de 60% das áreas são estimadas por regressão; as coberturas dependentes de área têm confiança baixa até a confirmação.
- Não há índice territorial de vendaval, alagamento ou furto: o risco usa só o tipo de local. Os endereços são fictícios ou perturbados.
- Comunidade/favela, área rural do imóvel e outra proposta BB Seguros não estão na base; dependem da confirmação.
- As faixas são estimativas de importância segurada, não preço, prêmio nem decisão de subscrição. Em caso de conflito, prevalecem as condições contratuais oficiais.
- O assistente com LLM ainda não chama o motor como ferramenta; responde a partir dos arquivos gerados.

## Dados externos

**Nenhuma fonte externa foi utilizada.** Todos os sinais vêm dos CSVs disponibilizados pela organização (`empresas`, `enderecos_estabelecimentos`, `sinais_financeiros_operacionais`, `territorio`, `bens_cadastrados`). A coluna `fontes_publicas_adicionais` registra `NAO_UTILIZADA` e sugere fontes para evolução (IBGE malha municipal, INMET, Defesa Civil, SSP), que exigiriam registrar fonte, data de acesso, licença, método e limitações.

## Privacidade e responsabilidade

- Usa apenas os dados disponibilizados; não usa atributos pessoais nem dados sensíveis como atalho para risco ou patrimônio.
- Elegibilidade é aplicada antes de recomendar.
- Toda faixa traz dados, regra e o que confirmar; a origem de cada dado é explícita.
- O gerente ou o cliente confirma as informações e pode desfazer respostas; a decisão final é humana.
- O LLM só conversa; não decide plano nem valores. O conteúdo dos registros é tratado como dado, não como instrução.
- A chave da API fica em `.env`, fora do repositório; no servidor público, fica nas variáveis secretas do Render.

## Uso de inteligência artificial

- **No desenvolvimento:** usamos assistentes de IA (Claude Code) como apoio para refatorar o motor, implementar o ciclo de confirmação, a tela do atendimento assistido, os testes e esta documentação. Todas as regras, premissas e resultados foram revisados pela equipe, que é capaz de explicar, executar e defender a solução.
- **No produto:** o assistente de dados da tela usa um LLM por API compatível com a OpenAI (Gemini por padrão; provedor e modelo configuráveis em `OPENAI_BASE_URL` e `OPENAI_MODEL`) para responder perguntas sobre os resultados. Ele não participa da recomendação.

## Próximos passos

- Agente autônomo: expor `recomendar` e `confirmar` como ferramentas (function calling) para o LLM conduzir a conversa com o cliente.
- Enriquecimento territorial (INMET, Defesa Civil, SSP) para vendaval e furto.
- CUB por UF para o custo de reconstrução.
- Calibrar as regras com histórico real de contratação e sinistros.

## Materiais finais da entrega

O diretório [`entrega_final/`](entrega_final/) reúne somente os arquivos que devem ser enviados. As bases fornecidas pela organização, ambientes virtuais e credenciais não fazem parte do pacote.

| Material | Link |
|---|---|
| Instruções e inventário do pacote | [`entrega_final/README.md`](entrega_final/README.md) |
| Documentação completa dentro do pacote | [`README_PROJETO.md`](entrega_final/README_PROJETO.md) |
| Resultado consolidado da base comum | [`template_resultado_times.csv`](entrega_final/resultados/template_resultado_times.csv) |
| Detalhamento das coberturas | [`template_coberturas_times.csv`](entrega_final/resultados/template_coberturas_times.csv) |
| Métricas da base comum | [`metricas.json`](entrega_final/evidencias/metricas.json) |
| Testes de coerência e reprodutibilidade | [`testes_coerencia.json`](entrega_final/evidencias/testes_coerencia.json) |
| Demonstração navegável | [`frontend_CASO.html`](entrega_final/demonstracao/frontend_CASO.html) |
| Motor de recomendação | [`engine.py`](entrega_final/codigo/engine.py) |
| Servidor e gerador do frontend | [`gerar_frontend.py`](entrega_final/codigo/gerar_frontend.py) |
| Testes automatizados | [`testes_coerencia.py`](entrega_final/codigo/testes_coerencia.py) |
| Dependências | [`requirements.txt`](entrega_final/codigo/requirements.txt) |
| Versão do Python | [`.python-version`](entrega_final/codigo/.python-version) |
| Configuração opcional do assistente | [`.env.example`](entrega_final/codigo/.env.example) |
| Roteiro textual da apresentação | [`ROTEIRO_APRESENTACAO.md`](entrega_final/ROTEIRO_APRESENTACAO.md) |

O vídeo de até 5 minutos deve ser gravado a partir do roteiro acima e seu arquivo ou link acrescentado ao pacote antes do envio definitivo.

## Relato

Partimos de um script único de lote. Separamos o motor (um caso → JSON) do lote para que a mesma lógica atendesse as três jornadas, validando que os CSVs ficassem byte a byte iguais e que o caso isolado fosse idêntico ao lote. Depois limitamos também o mínimo das faixas aos tetos das coberturas, reduzimos as alternativas para uma única comparação clara e criamos o ciclo de confirmação, em que a resposta recalcula a recomendação em vez de só ser registrada. Optamos por regras explícitas porque a base não tem rótulo para um modelo supervisionado.
