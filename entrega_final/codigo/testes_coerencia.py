"""Testes de coerência, estabilidade (reprodutibilidade) e sensibilidade. Uso: python testes_coerencia.py"""
import json, hashlib, os
import numpy as np, pandas as pd
import engine as E

def h(p): return hashlib.md5(open(p, "rb").read()).hexdigest()
rel = {}
for tag in E.DATASETS:
    d, out, cob, met = E.processar(tag); p = f"{E.OUT}/{tag}/template_coberturas_times.csv"; h1 = h(p)
    E.processar(tag); h2 = h(p)
    t = {"reprodutivel_hash_igual": h1 == h2}
    el = out[out.elegivel == "SIM"]
    t["inelegiveis_sem_cobertura"] = bool(not cob.merge(out[out.elegivel == "NAO"], on=["empresa_id", "imovel_id"]).shape[0])
    t["min<=max_pct"] = round(100 * float((cob.faixa_valor_min <= cob.faixa_valor_max).mean()), 2)
    t["sem_nulos_min_max"] = bool(cob[["faixa_valor_min", "faixa_valor_max"]].notna().all().all())
    # monotonicidade de planos: coberturas ESSENCIAL ⊂ PRATICO ⊂ TOTAL
    t["planos_aninhados"] = set(E.PLANO_COB["ESSENCIAL"]) < set(E.PLANO_COB["PRATICO"]) < set(E.PLANO_COB["TOTAL"])
    # consistência entre semelhantes: mesmo grupo+tipo local+porte -> plano modal
    m = el.merge(d[["imovel_id", "grupo_atividade", "tipo_loc", "porte"]], on="imovel_id")
    cons = m.groupby(["grupo_atividade", "tipo_loc"]).plano_recomendado.agg(lambda s: s.value_counts(normalize=True).iloc[0]).mean()
    t["consistencia_plano_semelhantes(%plano modal)"] = round(100 * float(cons), 1)
    # sensibilidade: ±20% em estoque e bens -> variação das faixas e troca de plano
    import copy
    base_plano = el.set_index("imovel_id").plano_recomendado
    base_inc = cob[cob.cobertura == "INCENDIO_RAIO_EXPLOSAO_FUMACA"].set_index("imovel_id")
    orig = E.carregar
    sens = {}
    for nome, f in {"estoque+20%": 1.2, "estoque-20%": 0.8}.items():
        def novo(cfg, f=f):
            dd, bb, tt, ter = orig(cfg)
            dd["estoque_medio_estimado"] *= f; dd["estoque_pico_estimado"] *= f
            return dd, bb, tt, ter
        E.carregar = novo; _, o2, c2, _ = E.processar(tag); E.carregar = orig
        p2 = o2[o2.elegivel == "SIM"].set_index("imovel_id").plano_recomendado
        i2 = c2[c2.cobertura == "INCENDIO_RAIO_EXPLOSAO_FUMACA"].set_index("imovel_id")
        sens[nome] = dict(pct_troca_plano=round(100 * float((p2 != base_plano.reindex(p2.index)).mean()), 2),
                          var_mediana_incendio_max_pct=round(100 * float(((i2.faixa_valor_max / base_inc.faixa_valor_max.reindex(i2.index)) - 1).median()), 1))
    t["sensibilidade"] = sens
    E.processar(tag)  # restaura saída original
    rel[tag] = t

# confirmação (passo 3): cada resposta recalcula o caso, vira CONFIRMADO e tira a pergunta da lista
d, b, _, _ = E.carregar(E.DATASETS["CASO"]); refs = E.carregar_referencias("CASO")
falhas = {"area_confirmada": 0, "local_negado_inelegivel": 0, "faixas_validas": 0, "deterministico": 0}
n_area = n_el = 0
for i in d.imovel_id:
    j = E.recomendar_imovel(i, d, b, refs)
    if not j["elegivel"]: continue
    n_el += 1
    ids = [p["id"] for p in j["perguntas"]]
    resp = {"elegibilidade_local": True, "delivery": True}
    if "area_m2" in ids:
        n_area += 1; resp["area_m2"] = 150
    z = E.recomendar_imovel(i, d, b, refs, resp)
    if "area_m2" in resp and (z["sinais"]["area_m2"]["origem"] != "CONFIRMADO" or "area_m2" in [p["id"] for p in z["perguntas"]]):
        falhas["area_confirmada"] += 1
    falhas["faixas_validas"] += any(c["min"] > c["max"] for c in z["coberturas"])
    falhas["deterministico"] += json.dumps(z, sort_keys=True, default=str) != json.dumps(E.recomendar_imovel(i, d, b, refs, resp), sort_keys=True, default=str)
    n = E.recomendar_imovel(i, d, b, refs, {"elegibilidade_local": "NAO"})
    falhas["local_negado_inelegivel"] += n["elegivel"] or bool(n["coberturas"])
rel["confirmacao_CASO"] = dict(casos_elegiveis=n_el, casos_com_area_confirmada=n_area, falhas=falhas)
json.dump(rel, open(f"{E.OUT}/testes_coerencia.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps(rel, indent=1, ensure_ascii=True))