#!/usr/bin/env python3
"""Cria (ou atualiza a senha de) uma conta no Supabase, já CONFIRMADA e sem enviar
e-mail nenhum. Usa a chave de serviço (Admin API). Rodado pelo workflow criar-conta.yml.
Variáveis: SUPABASE_URL, SUPABASE_SERVICE_KEY, CONTA_EMAIL, CONTA_SENHA."""
import json, os, urllib.request, urllib.error

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
EMAIL = os.environ["CONTA_EMAIL"].strip().lower()
SENHA = os.environ["CONTA_SENHA"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + "/auth/v1/" + path, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:200]}


def main():
    if "@" not in EMAIL:
        raise SystemExit("E-mail inválido.")
    if len(SENHA) < 6:
        raise SystemExit("A senha precisa ter pelo menos 6 caracteres.")

    st, body = req("POST", "admin/users", {"email": EMAIL, "password": SENHA, "email_confirm": True})
    if st in (200, 201):
        print("OK: conta criada e já confirmada para", EMAIL, "- pode entrar com e-mail e senha.")
        return

    # já existe: localizar o id e atualizar a senha
    uid = None
    page = 1
    while page <= 20:
        st2, lst = req("GET", "admin/users?page=%d&per_page=200" % page)
        users = lst.get("users") if isinstance(lst, dict) else lst
        if not users:
            break
        for u in users:
            if (u.get("email") or "").lower() == EMAIL:
                uid = u.get("id"); break
        if uid or len(users) < 200:
            break
        page += 1
    if not uid:
        raise SystemExit("Não consegui criar nem localizar a conta (%s): %s" % (st, json.dumps(body)[:200]))

    st3, upd = req("PUT", "admin/users/" + uid, {"password": SENHA, "email_confirm": True})
    if st3 == 200:
        print("OK: conta já existia — senha atualizada e confirmada para", EMAIL, "- pode entrar.")
    else:
        raise SystemExit("Falha ao atualizar a conta (%s): %s" % (st3, json.dumps(upd)[:200]))


if __name__ == "__main__":
    main()
