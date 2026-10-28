#!/usr/bin/env python3
"""Motor de recomendação – Seguro Empresarial (Datathon Proteção Inteligente).

Entrada : CSVs da base comum (empresas, enderecos, sinais, territorio, bens).
Saída   : template_resultado_times.csv e template_coberturas_times.csv preenchidos
          + metricas.json (evidências) por conjunto de dados.
Execução: python engine.py            (usa /mnt/user-data/uploads -> ./saida/<CONJUNTO>)
Abordagem: regras explícitas + estimativas por faixa (sem ML). 100 % determinística.
Python 3.x ; dependências: pandas, numpy.
"""
import json, os, sys, time
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
UP = os.environ.get("DADOS_DIR", BASE)                      # pasta que contém teste_comum/ e desenvolvimento/
OUT = os.environ.get("SAIDA_DIR", os.path.join(BASE, "saida"))

_NOMES = dict(emp="empresas", end="enderecos_estabelecimentos", sin="sinais_financeiros_operacionais",
              ter="territorio", bens="bens_cadastrados", tpl="template_resultado_times")
DATASETS = {
    "CASO": dict(pasta="teste_comum", **_NOMES),      # base comum de teste (144 estabelecimentos)
    "EMP": dict(pasta="desenvolvimento", **_NOMES),   # base de desenvolvimento (2.978 estabelecimentos)
}

FIXAS = ["INCENDIO_RAIO_EXPLOSAO_FUMACA", "DANOS_ELETRICOS", "PERDA_PAGAMENTO_ALUGUEL",
         "RESPONSABILIDADE_CIVIL_ESTABELECIMENTO", "DESPESAS_FIXAS", "PROTECAO_CIBERNETICA"]
PLANO_COB = {
    "ESSENCIAL": FIXAS,
    "PRATICO": FIXAS + ["ROUBO_FURTO_ARROMBAMENTO", "VENDAVAL_EVENTOS_CORRELATOS"],
    "TOTAL": FIXAS + ["ROUBO_FURTO_ARROMBAMENTO", "VENDAVAL_EVENTOS_CORRELATOS",
                      "RESPONSABILIDADE_CIVIL_EMPREGADOR", "QUEBRA_DE_VIDROS"],
}
TETO_BASICA = 7_500_000  # cobertura básica; acima -> Seguro Personalizado Empresarial

ELETRICOS = {"EQUIPAMENTO_ELETRONICO", "EQUIPAMENTO_INFORMATICA", "EQUIPAMENTO_MEDICO", "EQUIPAMENTO_REFRIGERACAO",
             "SISTEMA_SEGURANCA", "EQUIPAMENTO_BELEZA", "EQUIPAMENTO_COZINHA", "MAQUINA", "EQUIPAMENTO_OFICINA", "LETREIRO"}
PORTATEIS = {"EQUIPAMENTO_ELETRONICO", "EQUIPAMENTO_INFORMATICA", "EQUIPAMENTO_MEDICO", "EQUIPAMENTO_BELEZA",
             "EQUIPAMENTO_OFICINA", "EQUIPAMENTO_COZINHA"}
ALTO_FURTO = {"ELETRONICOS", "VAREJO_MODA", "FARMACIA", "MERCADO"}
RC_FATOR = {"RESTAURANTE": 4, "CLINICA": 6, "FARMACIA": 4, "BELEZA": 4, "MERCADO": 4, "ESCOLA_CURSO": 6,
            "ELETRONICOS": 3, "OFICINA": 4, "ESCRITORIO": 2, "VAREJO_MODA": 3}
FRENTE = {"LOJA_RUA": 0.9, "TERREO": 0.9, "GALERIA": 0.5, "SALA_COMERCIAL": 0.3, "GALPAO": 0.4, "BOX": 0.3}
M2_CONSTR = {"ECONOMICO": (2000, 3000), "NORMAL": (3000, 4500), "SUPERIOR": (4500, 7000)}
COMBUSTIVEL = ("MADEIRA", "COMBUSTIVEL", "PLASTICO", "LONA", "PALHA")


def r(x, step=500):
    """arredonda para múltiplo de step e devolve inteiro (apenas número)."""
    return int(round(float(x) / step) * step)


def tipo_local(row):
    c = str(row.complemento).upper()
    if "GALERIA" in c or row.possui_termo_galeria == "SIM": return "GALERIA"
    if "TORRE" in c or "SALA" in c or "CONJUNTO" in c or row.possui_termo_torre == "SIM" or row.possui_termo_sala == "SIM": return "SALA_COMERCIAL"
    if "GALPAO" in c or "DEPOSITO" in c or "UNIDADE" in c: return "GALPAO"
    if "BOX" in c: return "BOX"
    if "TERREO" in c: return "TERREO"
    if "LOJA" in c or row.possui_termo_loja == "SIM": return "LOJA_RUA"
    return "INDEFINIDO"


def carregar(cfg):
    L = lambda k: pd.read_csv(os.path.join(UP, cfg["pasta"], cfg[k] + ".csv"))
    emp, end, sin, ter, bens, tpl = (L(k) for k in ["emp", "end", "sin", "ter", "bens", "tpl"])
    d = (end.merge(sin, on=["imovel_id", "empresa_id"], how="left", validate="1:1")
            .merge(emp, on="empresa_id", how="left", validate="m:1"))
    return d, bens, tpl, ter


# ============================ referências (aprendidas da base, 1 vez) ============================
def _X_area(d, ref):
    cols = [np.ones(len(d)), np.log1p(d.energia_media_mensal_6m), np.log1p(d.folha_pagamento_mensal)]
    for a in ref["atividades"]: cols.append((d.grupo_atividade == a).astype(float))
    for t in ref["tipos"]: cols.append((d.tipo_loc == t).astype(float))
    return np.column_stack(cols)


def ajustar_area(df):
    """Regressão log-linear (OLS) da área nos casos com área de laudo; fallback por atividade."""
    known = df.area_cadastrada_m2 > 0
    ref = dict(atividades=[str(a) for a in sorted(df.grupo_atividade.unique())[1:]],
               tipos=[str(t) for t in sorted(df.tipo_loc.unique())[1:]])
    Xk, yk = _X_area(df[known], ref), np.log(df.loc[known, "area_cadastrada_m2"].values)
    beta, *_ = np.linalg.lstsq(Xk, yk, rcond=None)
    res = yk - Xk @ beta
    sd = float(res.std(ddof=Xk.shape[1])) if known.sum() > Xk.shape[1] + 5 else 0.6
    r2 = 1 - res.var() / yk.var()
    ref.update(beta=beta.tolist(), sd=sd, r2_log=round(float(r2), 3), n_known=int(known.sum()))
    return ref


def estimar_area(df, ref):
    """Aplica o modelo de área salvo: laudo ±10% quando existe; senão predição ± 1 desvio (escala log)."""
    known = df.area_cadastrada_m2 > 0
    pred = np.exp(_X_area(df, ref) @ np.array(ref["beta"]))
    sd = ref["sd"]
    amed = np.where(known, df.area_cadastrada_m2, pred)
    amin = np.where(known, df.area_cadastrada_m2 * 0.9, pred * np.exp(-sd))
    amax = np.where(known, df.area_cadastrada_m2 * 1.1, pred * np.exp(sd))
    clip = lambda a: np.clip(a, 15, 1500)
    return clip(amed), clip(amin), clip(amax)


def _ibge(v):
    """Chave estável do município (int ou float vindo do CSV)."""
    return str(int(v)) if pd.notna(v) else ""


def ajustar_referencias(d):
    """Tudo que depende da base inteira: modelo de área e aluguel de referência por m² (município x tipo de local)."""
    area = ajustar_area(d)
    amed, _, _ = estimar_area(d, area)
    loc = d.valor_aluguel_recorrente > 0
    rpm = pd.DataFrame(dict(ibge=d.codigo_ibge_municipio[loc].map(_ibge), tipo=d.tipo_loc[loc],
                            rpm=d.valor_aluguel_recorrente[loc] / amed[loc.values]))
    rpm_mt = rpm.groupby(["ibge", "tipo"]).rpm.median()
    return dict(area=area,
                rpm_mt={f"{i}|{t}": float(v) for (i, t), v in rpm_mt.items()},
                rpm_t={str(t): float(v) for t, v in rpm.groupby("tipo").rpm.median().items()},
                rpm_all=float(rpm.rpm.median()))


def carregar_referencias(tag):
    return json.load(open(f"{OUT}/{tag}/referencias.json"))


# ============================ preparação do caso ============================
BENS_COLS = ["bens_min", "bens_max", "elet_min", "elet_max", "port_min", "port_max", "let_min", "let_max",
             "n_bens", "tem_eletr_semroubo", "val_baixa", "val_tot", "n_baixa"]


def _agregar_bens(g):
    return pd.Series(dict(
        bens_min=g.loc[g.ok, "valor_bem_ponderado_referencia"].sum(),
        bens_max=g.loc[g.probabilidade_bem_no_imovel_referencia >= 0.48, "valor_cadastrado"].sum(),
        elet_min=g.loc[g.elet & g.ok, "valor_bem_ponderado_referencia"].sum(),
        elet_max=g.loc[g.elet & (g.probabilidade_bem_no_imovel_referencia >= 0.48), "valor_cadastrado"].sum(),
        port_min=g.loc[g.port & g.ok, "valor_bem_ponderado_referencia"].sum(),
        port_max=g.loc[g.port & (g.probabilidade_bem_no_imovel_referencia >= 0.48), "valor_cadastrado"].sum(),
        let_min=g.loc[g.tipo_bem == "LETREIRO", "valor_bem_ponderado_referencia"].sum(),
        let_max=g.loc[g.tipo_bem == "LETREIRO", "valor_cadastrado"].sum(),
        n_bens=len(g), tem_eletr_semroubo=int(g.elet.any()),
        val_baixa=g.loc[g.nivel_confianca_vinculo == "BAIXA", "valor_cadastrado"].sum(),
        val_tot=g.valor_cadastrado.sum(), n_baixa=int((g.nivel_confianca_vinculo == "BAIXA").sum())))


def preparar(d, bens, refs=None):
    """Sinais derivados por estabelecimento. d deve conter todas as unidades de cada empresa (rateio).
    Sem refs (modo lote), as referências são ajustadas sobre o próprio d."""
    d = d.copy()
    d["tipo_loc"] = d.apply(tipo_local, axis=1)
    # --- alocação empresa -> estabelecimento (folha como chave de rateio)
    tot_folha = d.groupby("empresa_id").folha_pagamento_mensal.transform("sum").replace(0, np.nan)
    share = (d.folha_pagamento_mensal / tot_folha).fillna(1 / d.groupby("empresa_id").imovel_id.transform("count"))
    d["fat_un"] = d.faturamento_mensal * share
    d["func_un"] = np.maximum(1, np.round(d.quantidade_funcionarios_estimada * share)).astype(int)
    d["multi"] = d.groupby("empresa_id").imovel_id.transform("count") > 1
    if refs is None: refs = ajustar_referencias(d)
    d["amed"], d["amin"], d["amax"] = estimar_area(d, refs["area"])
    d["area_imputada"] = d.area_cadastrada_m2 <= 0
    # --- bens por imóvel
    b = bens[bens.imovel_id_referencia.isin(d.imovel_id)].copy()
    b["elet"] = b.tipo_bem.isin(ELETRICOS); b["port"] = b.tipo_bem.isin(PORTATEIS)
    b["ok"] = b.nivel_confianca_vinculo.isin(["ALTA", "MEDIA"])
    ba = (b.groupby("imovel_id_referencia").apply(_agregar_bens, include_groups=False) if len(b)
          else pd.DataFrame(columns=BENS_COLS, dtype=float))
    d = d.merge(ba, left_on="imovel_id", right_index=True, how="left")
    for c in ba.columns: d[c] = d[c].fillna(0)
    d["share_baixa"] = np.where(d.val_tot > 0, d.val_baixa / d.val_tot.replace(0, np.nan), 0)
    d["share_baixa"] = d.share_baixa.fillna(0)
    return d, refs


# ============================ motor (1 caso) ============================
def recomendar(x, refs):
    """Motor: um estabelecimento preparado -> recomendação. Não lê nem escreve arquivos."""
    R, C = decidir(x, refs)
    return dict(resultado=R, coberturas=C)


def recomendar_imovel(imovel_id, d, bens, refs):
    """Atalho para jornadas: recomenda um estabelecimento usando só as unidades da própria empresa + refs salvas."""
    emp = d.loc[d.imovel_id == imovel_id, "empresa_id"].iloc[0]
    caso, _ = preparar(d[d.empresa_id == emp], bens, refs)
    return recomendar(next(caso[caso.imovel_id == imovel_id].itertuples(index=False)), refs)


# ============================ lote (todos os casos -> templates) ============================
def processar(tag):
    t0 = time.time()
    cfg = DATASETS[tag]
    d, bens, tpl, ter = carregar(cfg)
    d, refs = preparar(d, bens)
    res, cob = [], []
    for row in d.itertuples(index=False):
        rec = recomendar(row, refs)
        res.append(rec["resultado"]); cob.extend(rec["coberturas"])
    res = pd.DataFrame(res); cob = pd.DataFrame(cob)
    # alinhar com o template (mesma ordem/colunas)
    out = tpl[["empresa_id", "imovel_id"]].merge(res, on=["empresa_id", "imovel_id"], how="left")
    out = out[list(tpl.columns)]
    cob_cols = ["empresa_id", "imovel_id", "cobertura", "faixa_valor_min", "faixa_valor_max", "confianca_estimativa",
                "dados_utilizados", "regra_calculo_utilizada", "justificativa", "informacao_a_confirmar", "observacao"]
    cob = cob[cob_cols] if len(cob) else pd.DataFrame(columns=cob_cols)
    os.makedirs(f"{OUT}/{tag}", exist_ok=True)
    out.to_csv(f"{OUT}/{tag}/template_resultado_times.csv", index=False, encoding="utf-8")
    cob.to_csv(f"{OUT}/{tag}/template_coberturas_times.csv", index=False, encoding="utf-8")
    json.dump(refs, open(f"{OUT}/{tag}/referencias.json", "w"), indent=2, ensure_ascii=False)
    area_info = dict(r2_log=refs["area"]["r2_log"], sd_log=round(refs["area"]["sd"], 3), n_known=refs["area"]["n_known"])
    met = metricas(tag, d, out, cob, area_info, time.time() - t0, tpl)
    json.dump(met, open(f"{OUT}/{tag}/metricas.json", "w"), indent=2, ensure_ascii=False)
    return d, out, cob, met


# ----------------------------------------------------------------------------------------------
def decidir(x, refs):
    ident = dict(empresa_id=x.empresa_id, imovel_id=x.imovel_id)
    loc = x.tipo_loc
    locatario = x.pagamento_aluguel_recorrente == "SIM"
    relacao = "LOCATARIO" if locatario else "PROPRIETARIO"
    # ---------------- elegibilidade (guia 10.1) ----------------
    motivos = []
    if x.situacao_imovel_cadastral == "EM_OBRA": motivos.append("Imóvel em construção/reforma/reconstrução (situacao_imovel_cadastral=EM_OBRA)")
    if x.situacao_imovel_cadastral == "IRREGULAR": motivos.append("Situação cadastral IRREGULAR do imóvel (possível imóvel condenado/desapropriado/tombado)")
    if any(k in str(x.material_parede_externa_cadastrado).upper() for k in COMBUSTIVEL): motivos.append("Parede externa em material combustível")
    rural = any(k in str(x.descricao_cnae).lower() for k in ("agricult", "pecuari", "rural", "lavoura"))
    if rural: motivos.append("Atividade rural")
    base = dict(**ident, tipo_localizacao_sugerido=loc, relacao_imovel_sugerida=relacao)
    q_fixa = ("Confirme: (i) parede externa em material incombustível, (ii) imóvel fora de comunidade/favela/área rural "
              "e não tombado/condenado, (iii) sem outra proposta de seguro empresarial BB Seguros para o mesmo objeto.")
    if motivos:
        R = dict(base, elegivel="NAO", motivo_inelegibilidade="; ".join(motivos), plano_recomendado="NAO_SE_APLICA",
                 coberturas_recomendadas="NAO_SE_APLICA", confianca_geral="ALTA",
                 justificativa_recomendacao="[DISPONIVEL] " + "; ".join(motivos) + ". Regra do guia: não elegível; não há recomendação de plano nem faixas. "
                 "[SUGESTAO] Reavaliar quando o impedimento cessar.",
                 perguntas_confirmacao="A obra/reforma foi concluída e há habite-se/regularização do imóvel? Se sim, reenviar para nova análise.",
                 fontes_publicas_adicionais="NAO_UTILIZADA")
        return R, []

    # ---------------- sinais derivados ----------------
    fat, n = x.fat_un, x.func_un
    est_med, est_pico = x.estoque_medio_estimado, x.estoque_pico_estimado
    cnpj_ok = x.endereco_cnpj_compativel == "SIM"
    decl = x.despesa_fixa_mensal_estimada
    recomp = x.folha_pagamento_mensal + x.valor_aluguel_recorrente + x.energia_media_mensal_6m + x.pagamentos_software_mensais
    incons_fin = (decl > x.faturamento_mensal) if not x.multi else False
    incons_comp = decl < recomp * 0.95
    if x.multi:
        tot = x.faturamento_mensal; incons_fin = False  # consolidado por empresa não é comparável por unidade
    # prédio (somente proprietário)
    padr = x.padrao_construtivo_cadastrado
    cmin, cmax = M2_CONSTR.get(padr, (2500, 5000))
    pred_min = x.amin * cmin * (0.5 if loc in ("SALA_COMERCIAL", "GALERIA", "BOX") else 1.0)
    pred_max = x.amax * cmax * (0.5 if loc in ("SALA_COMERCIAL", "GALERIA", "BOX") else 1.0)
    cont_min = est_med + x.bens_min
    cont_max = max(est_pico + x.bens_max, cont_min)
    if not locatario:
        inc_min, inc_max = cont_min + pred_min, cont_max + pred_max
        objeto = "prédio+conteúdo"
    else:
        inc_min, inc_max = cont_min, cont_max
        objeto = "conteúdo (prédio é do locador)"
    inc_min, inc_max = max(inc_min, 20000), max(inc_max, inc_min * 1.3, 40000)
    acima_teto = inc_max > TETO_BASICA
    if inc_min > TETO_BASICA:  # fora do produto: direcionar ao Seguro Personalizado Empresarial
        mot = "Estimativa mínima de incêndio acima de R$ 7,5 mi: direcionar ao Seguro Personalizado Empresarial"
        return dict(**ident, tipo_localizacao_sugerido=loc, relacao_imovel_sugerida=relacao, elegivel="NAO", motivo_inelegibilidade=mot,
                    plano_recomendado="NAO_SE_APLICA", coberturas_recomendadas="NAO_SE_APLICA", confianca_geral="MEDIA",
                    justificativa_recomendacao="[SUGESTAO] " + mot + ".", perguntas_confirmacao="Confirme o valor de reposição de prédio e conteúdo.",
                    fontes_publicas_adicionais="NAO_UTILIZADA"), []
    if acima_teto: inc_max = TETO_BASICA
    # ---------------- plano ----------------
    vend_rel = loc in ("LOJA_RUA", "TERREO", "GALPAO")
    theft_rel = (x.grupo_atividade in ALTO_FURTO) or (est_pico + x.port_max >= 100000) or (loc in ("LOJA_RUA", "TERREO") and est_pico >= 30000)
    vidro_rel = loc in ("LOJA_RUA", "TERREO", "GALERIA")
    emp_rel = n >= 5
    refrig = x.probabilidade_refrigeracao_referencia >= 0.5
    deliv = (x.probabilidade_delivery_referencia >= 0.4) or (x.percentual_receita_delivery_est >= 0.15)
    cash_heavy = x.percentual_recebimentos_digitais <= 0.5 and x.grupo_atividade in ("MERCADO", "FARMACIA", "RESTAURANTE", "BELEZA", "VAREJO_MODA", "OFICINA", "ELETRONICOS")
    espec = refrig or deliv or cash_heavy
    if vidro_rel and emp_rel and (theft_rel or vend_rel):
        plano = "TOTAL"
    elif theft_rel or vend_rel or espec:
        plano = "PRATICO"
    else:
        plano = "ESSENCIAL"
    motivos_plano = []
    if theft_rel: motivos_plano.append("exposição a roubo/furto (atividade/estoque/bens portáteis)")
    if vend_rel: motivos_plano.append(f"local {loc} exposto a vendaval")
    if espec: motivos_plano.append("coberturas específicas da atividade só existem no Prático/Total")
    if plano == "TOTAL": motivos_plano.append(f"fachada/vitrine ({loc}) e {n} empregados na unidade justificam quebra de vidros e RC empregador")
    if plano == "ESSENCIAL": motivos_plano.append("sem sinais de exposição a furto/vendaval/vitrine; perfil de baixo estoque/escritório")
    alt = {"TOTAL": "PRATICO (sem quebra de vidros e RC empregador)", "PRATICO": "TOTAL (adiciona vidros e RC empregador) ou ESSENCIAL (sem furto/vendaval)",
           "ESSENCIAL": "PRATICO (adiciona furto e vendaval)"}[plano]

    C = []
    def add(nome, mn, mx, conf, dados, regra, just, conf_info, obs=""):
        mn, mx = r(mn, 500), r(mx, 500)
        if mx < mn: mx = mn
        C.append(dict(**ident, cobertura=nome, faixa_valor_min=mn, faixa_valor_max=mx, confianca_estimativa=conf,
                      dados_utilizados=dados, regra_calculo_utilizada=regra, justificativa=just,
                      informacao_a_confirmar=conf_info, observacao=obs))

    c_area = "ALTA" if not x.area_imputada else "BAIXA"
    c_bens = "BAIXA" if x.share_baixa > 0.4 or x.n_bens == 0 else ("ALTA" if x.share_baixa < 0.15 else "MEDIA")
    ordem = {"ALTA": 3, "MEDIA": 2, "BAIXA": 1}; inv = {3: "ALTA", 2: "MEDIA", 1: "BAIXA"}
    minc = lambda *a: inv[min(ordem[i] for i in a)]
    c_fat = x.confianca_faturamento
    area_txt = (f"área {x.area_cadastrada_m2:.0f} m² (laudo)" if not x.area_imputada
                else f"área imputada {x.amed:.0f} m² (faixa {x.amin:.0f}-{x.amax:.0f}; regressão sobre energia, folha, atividade e tipo de local)")

    # --- fixas
    add("INCENDIO_RAIO_EXPLOSAO_FUMACA", inc_min, inc_max, minc(c_area if not locatario else "ALTA", c_bens),
        f"estoque_medio/pico; bens ponderados/cadastrados (prob>=0.48); {area_txt}; relação={relacao}; padrão={padr}",
        f"min = estoque_médio + bens ALTA/MÉDIA ponderados{' + prédio (área mín × R$'+str(cmin)+'/m²)' if not locatario else ''}; "
        f"max = estoque_pico + bens (prob≥0.48, valor cadastrado){' + prédio (área máx × R$'+str(cmax)+'/m²)' if not locatario else ''}; piso 20k/40k",
        f"Objeto segurado: {objeto}. Faixa máxima R$ {r(inc_max)}" + (" limitada ao teto de R$ 7,5 mi da cobertura básica; acima disso, Seguro Personalizado Empresarial." if acima_teto else " dentro do teto de R$ 7,5 mi da cobertura básica."),
        "Valor de reposição do prédio e do conteúdo; relação com o imóvel" if not locatario else "Valor de reposição do conteúdo; endereço dos bens de baixa confiança",
        "Custo/m² é premissa interna (CUB não consultado)" if not locatario else "")
    el_min = x.elet_min; el_max = max(x.elet_max, el_min)
    if el_max <= 0:
        el_min, el_max = 12 * x.energia_media_mensal_6m * 0.5, 36 * x.energia_media_mensal_6m
        rg, dd, cf = "sem bens elétricos: min = 6×energia mensal; max = 36×energia mensal", "energia_media_mensal_6m", "BAIXA"
    else:
        rg, dd, cf = "min = bens elétricos/equipamentos ALTA/MÉDIA ponderados; max = valor cadastrado (prob≥0.48)", "bens_cadastrados (tipos elétricos), probabilidade de vínculo", c_bens
    add("DANOS_ELETRICOS", max(el_min, 10000), max(el_max, el_min * 1.3, 20000), cf, dd, rg + "; piso 10k/20k",
        "Equipamentos dependentes de energia elétrica no estabelecimento.", "Lista de equipamentos eletrônicos/refrigeração e valores de reposição")
    if locatario:
        a_min, a_max = 3 * x.valor_aluguel_recorrente, 12 * x.valor_aluguel_recorrente
        add("PERDA_PAGAMENTO_ALUGUEL", a_min, a_max, "ALTA", "valor_aluguel_recorrente", "min = 3 × aluguel mensal; max = 12 × aluguel mensal",
            f"Aluguel recorrente observado de R$ {x.valor_aluguel_recorrente:.0f}/mês; período indenitário de 3 a 12 meses.", "Valor do aluguel vigente e prazo contratual")
    else:
        rpm = refs["rpm_mt"].get(f"{_ibge(x.codigo_ibge_municipio)}|{loc}", np.nan)
        origem = "mediana R$/m² de locatários no mesmo município e tipo de local"
        if np.isnan(rpm): rpm, origem = refs["rpm_t"].get(loc, refs["rpm_all"]), "mediana R$/m² de locatários do mesmo tipo de local (sem amostra municipal)"
        add("PERDA_PAGAMENTO_ALUGUEL", 3 * x.amin * rpm, 12 * x.amax * rpm, "BAIXA", f"{origem}; {area_txt}; sem aluguel recorrente observado",
            "min = 3 × (área mín × R$/m² ref.); max = 12 × (área máx × R$/m² ref.)",
            "Sem aluguel observado: relação sugerida PROPRIETÁRIO; faixa representa aluguel de reposição/perda de aluguel de referência.",
            "Confirmar se o estabelecimento é próprio, alugado (valor do aluguel) ou cedido", "Se próprio e sem locação a terceiros, a cobertura pode ter pouca utilidade")
    k = RC_FATOR.get(x.grupo_atividade, 3)
    add("RESPONSABILIDADE_CIVIL_ESTABELECIMENTO", max(50000, 0.5 * k * fat), min(2_000_000, max(100000, 1.5 * k * fat)), minc(c_fat, "MEDIA"),
        f"faturamento alocado à unidade (R$ {fat:.0f}/mês, rateio por folha), grupo_atividade={x.grupo_atividade}",
        f"min = {0.5*k:.1f} × faturamento mensal da unidade; max = {1.5*k:.1f} × (teto 2 mi); piso 50k/100k",
        "Limite proporcional ao fluxo de público da atividade e ao porte da unidade.", "Fluxo diário de clientes e eventuais sinistros anteriores")
    d_lo = decl; d_hi = max(decl, recomp)
    add("DESPESAS_FIXAS", 1 * d_lo, 3 * d_hi, minc("MEDIA" if (incons_fin or incons_comp) else "ALTA", c_fat),
        "despesa_fixa_mensal_estimada; folha, aluguel, energia e software mensais", "min = 1 × despesa fixa declarada; max = 3 × maior entre declarada e soma dos componentes",
        f"Despesa fixa mensal estimada R$ {decl:.0f} (componentes observados somam R$ {recomp:.0f}); cobre 1 a 3 meses de paralisação.",
        "Despesas fixas mensais reais e prazo máximo de reabertura",
        "Despesa fixa > faturamento mensal da empresa: revisar" if incons_fin else "")
    base_dig = fat * max(x.percentual_recebimentos_digitais, x.indice_receita_digital)
    add("PROTECAO_CIBERNETICA", max(20000, base_dig), min(1_000_000, max(50000, 3 * base_dig * (1 + x.indice_exposicao_digital))), "BAIXA" if c_fat == "MEDIA" else "MEDIA",
        "percentual_recebimentos_digitais, indice_receita_digital, indice_exposicao_digital, faturamento da unidade",
        "min = max(20k; 1 mês de receita digital); max = max(50k; 3 meses de receita digital × (1+exposição digital)); teto 1 mi",
        f"Receita digital estimada R$ {base_dig:.0f}/mês; exposição digital {x.indice_exposicao_digital:.2f} (referência de dependência, não probabilidade de ataque).",
        "Uso de maquininha/e-commerce/sistemas em nuvem e tratamento de dados de clientes", "Índice de exposição digital não mede risco cibernético")
    # --- Prático / Total
    if plano in ("PRATICO", "TOTAL"):
        pt_min = 0.3 * (est_med + x.port_min); pt_max = 0.7 * (est_pico + x.port_max)
        add("ROUBO_FURTO_ARROMBAMENTO", max(pt_min, 10000), max(pt_max, pt_min * 1.3, 20000), minc(c_bens, "MEDIA"),
            "estoque_medio/pico; bens portáteis (eletrônicos, informática, médicos, beleza, oficina, cozinha); atividade",
            "min = 30% × (estoque médio + portáteis ALTA/MÉDIA); max = 70% × (estoque pico + portáteis prob≥0.48); piso 10k/20k (primeiro risco)",
            "Limite de primeiro risco proporcional ao estoque e aos bens subtraíveis.", "Sistemas de segurança existentes (alarme, câmeras, grades) e valores em estoque")
        v_min = 0.4 * cont_min + (0.2 * pred_min if not locatario else 0)
        v_max = 0.8 * cont_max + (0.5 * pred_max if not locatario else 0)
        add("VENDAVAL_EVENTOS_CORRELATOS", max(v_min, 10000), max(v_max, v_min * 1.3, 20000), minc(c_bens, c_area if not locatario else "ALTA"),
            f"conteúdo (estoque+bens), tipo de local {loc}" + ("; prédio estimado" if not locatario else ""),
            "min = 40% do conteúdo mín (+20% prédio mín se próprio); max = 80% do conteúdo máx (+50% prédio máx se próprio); piso 10k/20k",
            "Fração do patrimônio exposta a vento/granizo; sem índice territorial público utilizado.", "Tipo de cobertura/telhado e histórico de eventos climáticos no local",
            "Sem enriquecimento territorial (INMET/Defesa Civil); faixas sensíveis ao tipo de local")
    if plano == "TOTAL":
        add("RESPONSABILIDADE_CIVIL_EMPREGADOR", max(50000, 10000 * n), min(2_000_000, max(100000, 40000 * n)), "MEDIA",
            f"quantidade de funcionários alocada à unidade ({n}); folha da unidade", "min = max(50k; 10k × empregados); max = max(100k; 40k × empregados); teto 2 mi",
            "Limite proporcional ao número de empregados na unidade.", "Número real de empregados (CLT/terceiros) no estabelecimento",
            "Funcionários da empresa rateados por folha entre unidades" if x.multi else "")
        fr = FRENTE.get(loc, 0.4)
        g_min = fr * np.sqrt(x.amin) * 2.5; g_max = fr * np.sqrt(x.amax) * 2.5
        add("QUEBRA_DE_VIDROS", max(5000, g_min * 900), max(15000, g_max * 1800), minc(c_area, "MEDIA"),
            f"{area_txt}; tipo de local {loc}", f"vidro m² = fator frente({fr}) × √área × 2,5 m; min = m² × R$900; max = m² × R$1.800; piso 5k/15k",
            "Vidros/vitrines/fachada proporcionais à frente estimada do imóvel.", "Metragem de vitrines/portas/janelas de vidro")
    # --- adicionais aplicáveis (específicas da atividade: Prático/Total; opcionais: qualquer plano)
    adic = []
    if plano != "ESSENCIAL" and refrig:
        add("DETERIORACAO_MERCADORIAS_FRIGORIFICADAS", max(5000, 0.3 * est_med), max(10000, 0.6 * est_pico), "MEDIA" if x.probabilidade_refrigeracao_referencia >= 0.7 else "BAIXA",
            f"probabilidade_refrigeracao_referencia={x.probabilidade_refrigeracao_referencia:.2f}; estoque_medio/pico",
            "min = 30% estoque médio; max = 60% estoque pico (parcela refrigerada); piso 5k/10k", "Refrigeração relevante para a atividade; perda de mercadorias por falta de energia/falha do equipamento.",
            "Possui câmaras/balcões refrigerados? Qual % do estoque é refrigerado?"); adic.append("DETERIORACAO_MERCADORIAS_FRIGORIFICADAS")
    if plano != "ESSENCIAL" and deliv:
        dr = fat * x.percentual_receita_delivery_est
        add("DELIVERY", max(3000, dr / 30 * 5), max(10000, dr / 30 * 15), "BAIXA",
            f"probabilidade_delivery_referencia={x.probabilidade_delivery_referencia:.2f}; percentual_receita_delivery_est={x.percentual_receita_delivery_est:.2f}",
            "min = 5 dias de receita de delivery; max = 15 dias; piso 3k/10k", "Mercadorias em trânsito em entregas.", "Realiza entregas próprias? Volume médio diário")
        adic.append("DELIVERY")
    if plano != "ESSENCIAL" and cash_heavy:
        cash = fat * (1 - x.percentual_recebimentos_digitais) / 30
        add("ROUBO_FURTO_VALORES_ARROMBAMENTO", max(1000, cash), max(5000, 3 * cash), "BAIXA",
            f"percentual_recebimentos_digitais={x.percentual_recebimentos_digitais:.2f}; faturamento da unidade",
            "min = 1 dia de recebimento em espécie; max = 3 dias; piso 1k/5k", "Recebimentos majoritariamente não digitais sugerem valores em caixa.", "Valor médio mantido em caixa/cofre")
        adic.append("ROUBO_FURTO_VALORES_ARROMBAMENTO")
    if x.let_max > 0:
        add("LETREIROS_ANUNCIOS_LUMINOSOS", max(x.let_min, 3000), max(x.let_max, 6000), minc(c_bens, "MEDIA"), "bens_cadastrados tipo LETREIRO",
            "min = valor ponderado; max = valor cadastrado; piso 3k/6k", "Bem do tipo letreiro cadastrado para o estabelecimento.", "Valor e localização do letreiro")
        adic.append("LETREIROS_ANUNCIOS_LUMINOSOS")
    if x.grupo_atividade in ("CLINICA", "ESCRITORIO", "ESCOLA_CURSO"):
        add("RECOMPOSICAO_REGISTROS_DOCUMENTOS", max(10000, 0.1 * fat), max(30000, 0.3 * fat), "BAIXA", "grupo_atividade; faturamento da unidade",
            "min = 10% do faturamento mensal; max = 30%; piso 10k/30k", "Atividade com guarda intensiva de prontuários/documentos.", "Existência de backup físico/digital dos registros")
        adic.append("RECOMPOSICAO_REGISTROS_DOCUMENTOS")

    # ---------------- confiança geral ----------------
    pts = 0
    pts += 0 if not x.area_imputada else 2
    pts += 0 if c_bens == "ALTA" else (1 if c_bens == "MEDIA" else 2)
    pts += 0 if c_fat == "ALTA" else 1
    pts += 1 if not cnpj_ok else 0
    pts += 1 if (incons_fin or incons_comp) else 0
    pts += 1 if not locatario else 0
    pts += 1 if x.situacao_imovel_cadastral != "REGULAR" else 0
    conf = "ALTA" if pts <= 2 else ("MEDIA" if pts <= 4 else "BAIXA")

    # ---------------- perguntas (priorizadas, máx. 4) ----------------
    Q = [(1, q_fixa)]
    if not locatario: Q.append((2, "O estabelecimento é próprio ou alugado? Se alugado, qual o valor do aluguel e quem é o locador (beneficiário do prédio)?"))
    if x.area_imputada: Q.append((3, f"Qual a área do estabelecimento em m²? (estimada em ~{x.amed:.0f} m², faixa {x.amin:.0f}-{x.amax:.0f})"))
    if not cnpj_ok: Q.append((4, "O endereço do estabelecimento confere com o endereço do CNPJ/filial informado?"))
    if x.share_baixa > 0.25 and x.n_baixa: Q.append((5, f"{x.n_baixa} bem(ns) cadastrados com vínculo de baixa confiança (~{x.share_baixa:.0%} do valor): estão neste endereço?"))
    if incons_fin or incons_comp: Q.append((6, "Confirme faturamento mensal e despesas fixas (os valores informados estão inconsistentes entre si)."))
    if 0.3 <= x.probabilidade_refrigeracao_referencia < 0.7 and plano != "ESSENCIAL": Q.append((7, "Há equipamentos de refrigeração com mercadorias perecíveis?"))
    if 0.2 <= x.probabilidade_delivery_referencia < 0.5: Q.append((8, "A empresa realiza entregas (delivery)?"))
    if acima_teto: Q.append((0, 'Valor de reposição de prédio e conteúdo pode superar R$ 7,5 mi: confirmar para eventual direcionamento ao Seguro Personalizado Empresarial.'))
    Q = [q for _, q in sorted(Q)][:4]

    ev = [f"[DISPONÍVEL] {x.grupo_atividade}, local {loc}, {n} empregados na unidade, {'aluguel R$ %.0f/mês' % x.valor_aluguel_recorrente if locatario else 'sem aluguel recorrente'}, "
          f"estoque médio/pico R$ {est_med:.0f}/{est_pico:.0f}, {x.n_bens:.0f} bens vinculados"]
    ev.append(f"[SUGESTÃO] plano {plano}: " + "; ".join(motivos_plano) + f". Relação sugerida: {relacao}. " +
              (f"Área estimada ~{x.amed:.0f} m²." if x.area_imputada else f"Área de laudo {x.area_cadastrada_m2:.0f} m²."))
    ev.append(f"[CONFIRMAR] {len(Q)} pergunta(s) priorizada(s). Alternativa: {alt}.")
    R = dict(base, elegivel="SIM", motivo_inelegibilidade="", plano_recomendado=plano,
             coberturas_recomendadas="|".join(PLANO_COB[plano] + adic), confianca_geral=conf,
             justificativa_recomendacao=" ".join(ev), perguntas_confirmacao=" | ".join(Q),
             fontes_publicas_adicionais="NAO_UTILIZADA (sugeridas: IBGE malha municipal, INMET, Defesa Civil, SSP; ver README)")
    return R, C


def metricas(tag, d, out, cob, area_info, tempo, tpl):
    el = out[out.elegivel == "SIM"]
    n = len(out)
    cnt_perg = el.perguntas_confirmacao.str.count(r"\|") + 1
    # consistência plano x coberturas
    cons_ok = 0
    for (e, i), g in cob.groupby(["empresa_id", "imovel_id"]):
        pl = out[(out.empresa_id == e) & (out.imovel_id == i)].plano_recomendado.iloc[0]
        cons_ok += set(PLANO_COB[pl]).issubset(set(g.cobertura))
    faixas_ok = int(((cob.faixa_valor_min <= cob.faixa_valor_max) & cob.faixa_valor_min.notna()).sum())
    return dict(
        conjunto=tag, casos_template=n, casos_processados=int(out.elegivel.notna().sum()), pct_processados=round(100 * out.elegivel.notna().mean(), 2),
        elegiveis=int((out.elegivel == "SIM").sum()), inelegiveis=int((out.elegivel == "NAO").sum()),
        inelegiveis_por_motivo=out[out.elegivel == "NAO"].motivo_inelegibilidade.value_counts().to_dict(),
        distribuicao_planos=el.plano_recomendado.value_counts().to_dict(),
        confianca_geral=el.confianca_geral.value_counts().to_dict(), pct_confianca_baixa=round(100 * (el.confianca_geral == "BAIXA").mean(), 2),
        media_perguntas=round(float(cnt_perg.mean()), 2), pct_com_justificativa=round(100 * (out.justificativa_recomendacao.str.len() > 20).mean(), 2),
        linhas_coberturas=len(cob), faixas_validas=faixas_ok, pct_faixas_validas=round(100 * faixas_ok / max(len(cob), 1), 2),
        pct_planos_com_todas_coberturas_fixas=round(100 * cons_ok / max(len(el), 1), 2),
        coberturas_adicionais_linhas=int((~cob.cobertura.isin(FIXAS + ["ROUBO_FURTO_ARROMBAMENTO", "VENDAVAL_EVENTOS_CORRELATOS", "RESPONSABILIDADE_CIVIL_EMPREGADOR", "QUEBRA_DE_VIDROS"])).sum()),
        area_imputada_pct=round(100 * d.area_imputada.mean(), 1), modelo_area=area_info,
        casos_multiunidade=int(d.multi.sum()), tempo_execucao_s=round(tempo, 2))


if __name__ == "__main__":
    for t in (sys.argv[1:] or list(DATASETS)):
        _, _, _, m = processar(t)
        print(json.dumps(m, indent=1, ensure_ascii=True))