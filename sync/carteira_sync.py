#!/usr/bin/env python3
"""Nossa Carteira — robô de cotações.
Lê as ações cadastradas no Supabase, busca cotações no Yahoo Finance e grava
as tabelas `quotes` e `summary`. Roda no GitHub Actions (ver .github/workflows/cotacoes.yml).
Precisa das variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY."""
import json, os, re, time, urllib.request, urllib.error, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
SB_URL = os.environ["SUPABASE_URL"].rstrip("/")
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
HJSON = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY, "Content-Type": "application/json"}


def sb_get(path):
    req = urllib.request.Request(SB_URL + "/rest/v1/" + path, headers=HJSON)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def sb_upsert(table, rows, on_conflict):
    h = dict(HJSON); h["Prefer"] = "resolution=merge-duplicates,return=minimal"
    data = json.dumps(rows).encode()
    req = urllib.request.Request(SB_URL + "/rest/v1/" + table + "?on_conflict=" + on_conflict,
                                 data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def yahoo_symbol(t):
    t = t.upper().strip()
    return t + ".SA" if re.fullmatch(r"[A-Z]{4}\d{1,2}", t) else t


def fetch(sym):
    d = None; err = None
    for host in ("query1", "query2"):
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r); break
        except Exception as e:
            err = e; time.sleep(1)
    if d is None:
        raise err
    res = d.get("chart", {}).get("result") or []
    if not res:
        raise RuntimeError(d.get("chart", {}).get("error") or "sem resultado")
    r = res[0]; m = r["meta"]; ts = r.get("timestamp") or []
    closes = r["indicators"]["quote"][0].get("close") or []
    pts = [(datetime.datetime.fromtimestamp(t, TZ).date().isoformat(), round(c, 2))
           for t, c in zip(ts, closes) if c is not None]
    if len(pts) < 2:
        raise RuntimeError("historico insuficiente")
    c = [p[1] for p in pts]
    def var(n):
        return round((c[-1] / c[-1 - n] - 1) * 100, 2) if len(c) > n else None
    return {
        "ticker": sym.replace(".SA", ""),
        "nome": m.get("longName") or m.get("shortName") or sym,
        "preco": round(float(m.get("regularMarketPrice") or c[-1]), 2),
        "varDia": round(float(m["regularMarketChangePercent"]), 2) if m.get("regularMarketChangePercent") is not None else var(1),
        "varSemana": var(5), "varMes": var(21),
        "ultimoPregao": pts[-1][0],
        "historico": [{"data": p[0], "fechamento": p[1]} for p in pts[-42:]],
    }


def main():
    profiles = sb_get("profiles?select=id,ativos,perfil")
    purchases = sb_get("purchases?select=user_id,ticker,quantidade,preco,data")
    existing = sb_get("quotes?select=ticker")

    tickers = set()
    for p in profiles:
        for t in (p.get("ativos") or []):
            tickers.add(t.upper())
    for c in purchases:
        tickers.add(str(c["ticker"]).upper())
    for q in existing:
        tickers.add(str(q["ticker"]).upper())

    itens = {}; erros = {}
    for t in sorted(tickers):
        try:
            itens[t] = fetch(yahoo_symbol(t)); time.sleep(0.4)
        except Exception as e:
            erros[t] = str(e)[:150]

    if not itens and tickers:
        raise SystemExit("Nenhuma cotacao obtida; nada gravado. Erros: " + json.dumps(erros, ensure_ascii=False))

    carimbo = datetime.datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")

    rows = [{
        "ticker": t, "nome": v["nome"], "preco": v["preco"],
        "var_dia": v["varDia"], "var_semana": v["varSemana"], "var_mes": v["varMes"],
        "ultimo_pregao": v["ultimoPregao"], "historico": v["historico"], "updated_at": carimbo,
    } for t, v in itens.items()]
    if rows:
        sb_upsert("quotes", rows, "ticker")

    # resumo da semana (mesma lógica da versão original, agora por user_id)
    membros = {p["id"]: {"ativos": p.get("ativos") or [], "perfil": p.get("perfil")} for p in profiles}
    for m in membros.values():
        m["compras"] = []
    for c in purchases:
        if c["user_id"] in membros:
            membros[c["user_id"]]["compras"].append(c)

    validos = [v for v in itens.values() if v.get("varSemana") is not None]
    subiram = [v for v in validos if v["varSemana"] > 0]
    cairam = [v for v in validos if v["varSemana"] < 0]
    ordem = sorted(validos, key=lambda v: v["varSemana"], reverse=True)

    por_membro = {}
    for uid, m in membros.items():
        pos = {}
        for c in m["compras"]:
            t = str(c["ticker"]).upper(); q = float(c["quantidade"]); p = float(c["preco"])
            pos.setdefault(t, {"qtd": 0.0, "inv": 0.0})
            pos[t]["qtd"] += q; pos[t]["inv"] += q * p
        inv = sum(x["inv"] for x in pos.values())
        hoje = sum(x["qtd"] * itens[t]["preco"] for t, x in pos.items() if t in itens)
        cobertos = all(t in itens for t in pos)
        acoes = []
        for t, x in sorted(pos.items(), key=lambda kv: -kv[1]["inv"]):
            it = itens.get(t); vh = x["qtd"] * it["preco"] if it else None
            acoes.append({"ticker": t, "qtd": x["qtd"], "investido": round(x["inv"], 2),
                          "valorHoje": round(vh, 2) if vh is not None else None,
                          "resultado": round(vh - x["inv"], 2) if vh is not None else None,
                          "varSemana": it["varSemana"] if it else None})
        por_membro[uid] = {"investido": round(inv, 2),
                           "valorHoje": round(hoje, 2) if cobertos else None,
                           "resultado": round(hoje - inv, 2) if cobertos else None,
                           "resultadoPct": round((hoje / inv - 1) * 100, 2) if cobertos and inv else None,
                           "acoes": acoes, "acompanha": [t.upper() for t in m["ativos"]],
                           "perfil": (m["perfil"] or {}).get("classe") if m["perfil"] else None}

    if validos:
        fim = max(v["ultimoPregao"] for v in validos)
        def br(s): p = s.split("-"); return f"{p[2]}/{p[1]}"
        hist = ordem[0]["historico"]; ini = hist[-6]["data"] if len(hist) >= 6 else hist[0]["data"]
        frases = [f"Semana de {br(ini)} a {br(fim)}: {len(validos)} ações acompanhadas, {len(subiram)} subiram e {len(cairam)} caíram."]
        if ordem:
            frases.append(f"Maior alta: {ordem[0]['ticker']} ({ordem[0]['varSemana']:+.2f}%). Maior baixa: {ordem[-1]['ticker']} ({ordem[-1]['varSemana']:+.2f}%).")
        media = sum(v["varSemana"] for v in validos) / len(validos)
        frases.append(f"Média das variações: {media:+.2f}%.")
        texto = " ".join(frases)
    else:
        ini = fim = None
        texto = "Ninguém cadastrou ações ainda. Adicione ações em 'Minha carteira' e o próximo resumo cobre elas."

    summary = {"geradoEm": carimbo, "semanaInicio": ini, "semanaFim": fim, "texto": texto,
               "ranking": [{"ticker": v["ticker"], "nome": v["nome"], "preco": v["preco"],
                            "varDia": v["varDia"], "varSemana": v["varSemana"], "varMes": v["varMes"]} for v in ordem],
               "porMembro": por_membro, "erros": erros}
    sb_upsert("summary", [{"id": "latest", "data": summary, "updated_at": carimbo}], "id")

    ultima = max((v["ultimoPregao"] for v in itens.values()), default="-")
    print(f"ok: {len(itens)} cotações, {len(erros)} erros {erros if erros else ''}, {len(por_membro)} membros, último pregão {ultima}")


if __name__ == "__main__":
    main()
