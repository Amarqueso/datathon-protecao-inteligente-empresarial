# Roteiro da apresentação — até 5 minutos

## 0:00–0:30 — Problema

Empresas diferentes possuem necessidades de proteção distintas, mas a contratação precisa ser rápida, clara e responsável. O desafio é transformar sinais cadastrais, financeiros, operacionais e patrimoniais em uma recomendação explicável de plano, coberturas e faixas de valores.

## 0:30–1:00 — Solução

O Proteção Inteligente é um motor determinístico de recomendação para Seguro Empresarial. Ele segue cinco etapas: sinais, sugestão inicial, confiança, confirmação e recomendação. A mesma lógica atende processamento em lote, atendimento assistido e, futuramente, agentes autônomos.

## 1:00–1:35 — Funcionamento

O motor verifica primeiro a elegibilidade. Casos em obra, com situação irregular, material combustível ou atividade não aceita não recebem recomendação. Nos casos elegíveis, combina atividade, estoque, bens, faturamento, empregados, área e tipo de estabelecimento para recomendar os planos Essencial, Prático ou Total.

## 1:35–2:05 — Explicabilidade

Cada recomendação informa quais dados foram observados, derivados ou estimados. Cada cobertura possui faixa mínima e máxima, confiança, dados utilizados, regra de cálculo, justificativa e informação a confirmar. Assim, uma estimativa nunca é apresentada como fato confirmado.

## 2:05–3:00 — Demonstração

1. Abrir `demonstracao/frontend_CASO.html`.
2. Mostrar o painel geral e selecionar um caso elegível.
3. Exibir plano, coberturas, faixas, justificativa e alternativa.
4. Mostrar as perguntas de confirmação.
5. No atendimento assistido, confirmar área ou relação com o imóvel e recalcular.
6. Mostrar rapidamente um caso inelegível.

Mensagem-chave: a recomendação não é uma caixa-preta; gerente e cliente conseguem entender, revisar e corrigir os sinais.

## 3:00–3:35 — Resultados

Foram processados 144 de 144 estabelecimentos da base comum: 137 elegíveis e 7 inelegíveis, com 1.297 linhas de coberturas. Todas as faixas são válidas, todas as recomendações possuem justificativa e 100% dos planos contêm as coberturas fixas obrigatórias.

## 3:35–4:05 — Qualidade

A solução foi testada quanto a reprodutibilidade, consistência, sensibilidade e confirmação. Duas execuções geram os mesmos resultados, casos inelegíveis nunca recebem coberturas e as confirmações recalculam a recomendação de forma determinística.

## 4:05–4:30 — Responsabilidade

A solução usa somente os dados fornecidos, não utiliza atributos sensíveis, diferencia estimativa de confirmação e mantém o controle humano. As faixas representam importância segurada sugerida, não preço, prêmio ou decisão final de subscrição.

## 4:30–5:00 — Evolução e fechamento

Os próximos passos incluem CUB por estado, sinais públicos de vendaval e segurança e integração do motor como ferramenta de agentes autônomos.

Fechamento sugerido: “Proteção Inteligente é uma única lógica, reutilizável em diferentes canais, capaz de transformar dados em uma proteção empresarial clara, comparável e revisável.”
