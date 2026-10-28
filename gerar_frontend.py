#!/usr/bin/env python3
"""Gera frontend_<CONJUNTO>.html (página única, sem servidor) a partir de saida/<CONJUNTO>.
Uso: python gerar_frontend.py            # CASO (base comum)
     python gerar_frontend.py EMP        # base de desenvolvimento (arquivo grande)
"""
import json, os, sys
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
PASTA = {"CASO": "teste_comum", "EMP": "desenvolvimento"}

HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Recomendação – Seguro Empresarial</title>
<style>
:root{color-scheme:light;--bg:#f6f7f9;--card:#fff;--tx:#1b1f24;--mut:#667085;--bd:#e3e6eb;--ac:#0b57d0;--ok:#1a7f4b;--no:#b42318;--wa:#b54708}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#14171c;--card:#1d2127;--tx:#e8eaed;--mut:#9aa3af;--bd:#2c323a;--ac:#8ab4f8;--ok:#5fd08d;--no:#f97066;--wa:#fdb022}}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--tx)}
header{padding:16px 20px;border-bottom:1px solid var(--bd);background:var(--card)}h1{margin:0;font-size:18px}header p{margin:2px 0 0;color:var(--mut)}
main{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:16px;padding:16px 20px;max-width:1500px;margin:auto}
@media(max-width:950px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:12px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--mut);font-size:12px}
.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:6px 0 2px;background:var(--bd)}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
input,select{background:var(--bg);color:var(--tx);border:1px solid var(--bd);border-radius:6px;padding:6px 8px;font:inherit}
.list{max-height:70vh;overflow:auto}table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--bd);vertical-align:top}th{position:sticky;top:0;background:var(--card);font-size:12px;color:var(--mut)}
tbody tr{cursor:pointer}tbody tr:hover,tr.sel{background:var(--bg)}.tw{overflow-x:auto}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;border:1px solid var(--bd)}
.ok{color:var(--ok)}.no{color:var(--no)}.wa{color:var(--wa)}.n{text-align:right;white-space:nowrap}
h2{font-size:15px;margin:14px 0 6px}h3{font-size:13px;margin:12px 0 4px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.just span{display:block;margin:3px 0}.q li{margin:3px 0}details{margin:2px 0}summary{cursor:pointer;color:var(--ac)}
.det{color:var(--mut);font-size:12px;padding:4px 0 6px}.muted{color:var(--mut)}
</style></head><body>
<header><h1>Recomendação de proteção – Seguro Empresarial</h1><p id="sub"></p></header>
<main><section class="card"><div class="kpis" id="kpis"></div><div id="bar"></div>
<div class="filters"><input id="q" placeholder="Buscar ID, atividade ou cidade"><select id="fp"><option value="">Plano</option></select>
<select id="fe"><option value="">Elegibilidade</option><option>SIM</option><option>NAO</option></select><select id="fc"><option value="">Confiança</option></select></div>
<div class="list tw"><table><thead><tr><th>Estabelecimento</th><th>Atividade</th><th>Cidade</th><th>Plano</th><th>Conf.</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section class="card" id="det"><p class="muted">Selecione um estabelecimento na lista para ver a recomendação, as coberturas e as perguntas.</p></section></main>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const brl=n=>new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:0}).format(n);
const cc={ALTA:"ok",MEDIA:"wa",BAIXA:"no"},pc={ESSENCIAL:"#98a2b3",PRATICO:"#0b57d0",TOTAL:"#1a7f4b"};
$("#sub").textContent=D.titulo+" · "+D.casos.length+" estabelecimentos · dados fictícios";
const uniq=k=>[...new Set(D.casos.map(c=>c[k]).filter(Boolean))].sort();
uniq("plano").forEach(v=>$("#fp").add(new Option(v,v)));uniq("conf").forEach(v=>$("#fc").add(new Option(v,v)));
function kpis(L){const el=L.filter(c=>c.elegivel==="SIM"),n=a=>a.length,cnt=p=>el.filter(c=>c.plano===p).length;
$("#kpis").innerHTML=[[n(L),"casos"],[n(el),"elegíveis"],[n(L)-n(el),"inelegíveis"],[el.filter(c=>c.conf==="BAIXA").length,"confiança baixa"]].map(([a,b])=>`<div class="kpi"><b>${a}</b><span>${b}</span></div>`).join("");
$("#bar").innerHTML=`<div class="bar">${["ESSENCIAL","PRATICO","TOTAL"].map(p=>`<div style="width:${n(el)?100*cnt(p)/n(el):0}%;background:${pc[p]}"></div>`).join("")}</div><span class="muted">${["ESSENCIAL","PRATICO","TOTAL"].map(p=>p+" "+cnt(p)).join(" · ")}</span>`}
function lista(){const q=$("#q").value.toLowerCase(),fp=$("#fp").value,fe=$("#fe").value,fc=$("#fc").value;
const L=D.casos.filter(c=>(!q||(c.imovel+" "+c.ativ+" "+c.mun).toLowerCase().includes(q))&&(!fp||c.plano===fp)&&(!fe||c.elegivel===fe)&&(!fc||c.conf===fc));
kpis(L);$("#rows").innerHTML=L.map(c=>`<tr data-i="${esc(c.imovel)}"><td>${esc(c.imovel)}</td><td>${esc(c.ativ)}</td><td>${esc(c.mun)}/${esc(c.uf)}</td><td>${c.elegivel==="SIM"?`<span class="tag">${esc(c.plano)}</span>`:`<span class="tag no">inelegível</span>`}</td><td class="${cc[c.conf]||""}">${esc(c.conf)}</td></tr>`).join("")}
function detalhe(id){const c=D.casos.find(x=>x.imovel===id);document.querySelectorAll("tr.sel").forEach(r=>r.classList.remove("sel"));
const tr=document.querySelector(`tr[data-i="${CSS.escape(id)}"]`);tr&&tr.classList.add("sel");
let h=`<h2>${esc(c.imovel)} <span class="muted">· ${esc(c.ativ)} · ${esc(c.mun)}/${esc(c.uf)} · ${esc(c.porte)}</span></h2>
<p>Local: <b>${esc(c.tipo_local)}</b> · Relação sugerida: <b>${esc(c.relacao)}</b> · Confiança: <b class="${cc[c.conf]||""}">${esc(c.conf)}</b></p>`;
if(c.elegivel!=="SIM")h+=`<p class="no"><b>Não elegível:</b> ${esc(c.motivo)}</p>`;else h+=`<p>Plano recomendado: <span class="tag" style="border-color:${pc[c.plano]}">${esc(c.plano)}</span></p>`;
h+=`<h3>Justificativa</h3><div class="just">${c.just.split(/(?=\[(?:DISPON|SUGEST|CONFIRM))/).map(t=>`<span>${esc(t.trim())}</span>`).join("")}</div>`;
h+=`<h3>Perguntas de confirmação (${c.perguntas.length})</h3><ol class="q">${c.perguntas.map(p=>`<li>${esc(p)}</li>`).join("")}</ol>`;
if(c.cob.length){h+=`<h3>Coberturas e faixas</h3><div class="tw"><table><thead><tr><th>Cobertura</th><th class="n">Mínimo</th><th class="n">Máximo</th><th>Conf.</th></tr></thead><tbody>`+
c.cob.map(k=>`<tr><td>${esc(k.nome)}<details><summary>como foi calculado</summary><div class="det"><b>Dados:</b> ${esc(k.dados)}<br><b>Regra:</b> ${esc(k.regra)}<br><b>Por quê:</b> ${esc(k.just)}<br><b>Confirmar:</b> ${esc(k.confirmar)}${k.obs?`<br><b>Obs.:</b> ${esc(k.obs)}`:""}</div></details></td><td class="n">${brl(k.min)}</td><td class="n">${brl(k.max)}</td><td class="${cc[k.conf]||""}">${esc(k.conf)}</td></tr>`).join("")+`</tbody></table></div>`}
$("#det").innerHTML=h}
["q","fp","fe","fc"].forEach(i=>$("#"+i).addEventListener("input",lista));
$("#rows").addEventListener("click",e=>{const t=e.target.closest("tr");t&&detalhe(t.dataset.i)});
lista();
</script></body></html>"""


def main(tag):
    pasta = os.path.join(BASE, PASTA[tag]); saida = os.path.join(BASE, "saida", tag)
    res = pd.read_csv(f"{saida}/template_resultado_times.csv").fillna("")
    cob = pd.read_csv(f"{saida}/template_coberturas_times.csv").fillna("")
    emp = pd.read_csv(f"{pasta}/empresas.csv")[["empresa_id", "grupo_atividade", "porte"]]
    end = pd.read_csv(f"{pasta}/enderecos_estabelecimentos.csv")[["imovel_id", "municipio_real", "uf_real"]]
    d = res.merge(emp, on="empresa_id", how="left").merge(end, on="imovel_id", how="left")
    g = {k: v for k, v in cob.groupby("imovel_id")}
    casos = []
    for r in d.itertuples(index=False):
        cs = g.get(r.imovel_id)
        lst = [] if cs is None else [dict(nome=c.cobertura, min=int(c.faixa_valor_min), max=int(c.faixa_valor_max), conf=c.confianca_estimativa,
               dados=c.dados_utilizados, regra=c.regra_calculo_utilizada, just=c.justificativa, confirmar=c.informacao_a_confirmar, obs=c.observacao)
               for c in cs.itertuples(index=False)]
        casos.append(dict(imovel=r.imovel_id, empresa=r.empresa_id, ativ=r.grupo_atividade, porte=r.porte, mun=r.municipio_real, uf=r.uf_real,
                          tipo_local=r.tipo_localizacao_sugerido, relacao=r.relacao_imovel_sugerida, elegivel=r.elegivel, motivo=r.motivo_inelegibilidade,
                          plano=r.plano_recomendado if r.elegivel == "SIM" else "", conf=r.confianca_geral, just=r.justificativa_recomendacao,
                          perguntas=[p.strip() for p in str(r.perguntas_confirmacao).split(" | ") if p.strip()], cob=lst))
    data = json.dumps(dict(titulo="Base " + ("comum de teste" if tag == "CASO" else "de desenvolvimento"), casos=casos), ensure_ascii=False).replace("</", "<\\/")
    out = os.path.join(BASE, f"frontend_{tag}.html")
    open(out, "w", encoding="utf-8").write(HTML.replace("__DATA__", data))
    print("Gerado:", out, f"({os.path.getsize(out)/1e6:.1f} MB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "CASO")