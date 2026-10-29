# Pacote final — Proteção Inteligente

Equipe **Tropa do BB** · Desafio **Seguro Empresarial**

Este diretório contém os materiais finais da solução. As bases de entrada fornecidas pela organização não são redistribuídas e devem ser disponibilizadas separadamente nas pastas `teste_comum/` e `desenvolvimento/` para uma nova execução.

## Conteúdo

- `resultados/`: os dois templates obrigatórios preenchidos para os 144 casos da base comum.
- `evidencias/`: métricas, referências do modelo de área e resultados dos testes.
- `codigo/`: motor, servidor de demonstração, testes e dependências.
- `demonstracao/`: frontend autossuficiente da base comum.
- `README_PROJETO.md`: documentação completa da solução.
- `ROTEIRO_APRESENTACAO.md`: roteiro cronometrado para o vídeo e o pitch.

## Execução

Na raiz do projeto completo, com as bases de entrada disponíveis:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r entrega_final/codigo/requirements.txt
DADOS_DIR="$PWD" SAIDA_DIR="$PWD/saida" python entrega_final/codigo/engine.py CASO
DADOS_DIR="$PWD" SAIDA_DIR="$PWD/saida" python entrega_final/codigo/testes_coerencia.py
DADOS_DIR="$PWD" SAIDA_DIR="$PWD/saida" python entrega_final/codigo/gerar_frontend.py
```

Para a demonstração sem servidor, basta abrir `demonstracao/frontend_CASO.html` em um navegador.

## Checklist antes do envio

- Templates da base comum: incluídos.
- Código e dependências: incluídos.
- Métricas e testes: incluídos.
- Demonstração: incluída.
- Roteiro da apresentação: incluído.
- Vídeo de até 5 minutos: deve ser gravado e anexado ou ter seu link registrado antes do envio.
- Credenciais e bases da organização: não incluídas.

A documentação completa, com arquitetura, premissas, limitações, resultados, privacidade e uso de IA, está em `README_PROJETO.md`.
