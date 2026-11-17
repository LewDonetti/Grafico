# Nossa Carteira

App para duas (ou mais) pessoas acompanharem uma carteira de ações da B3: cada uma
cadastra suas ações e compras, responde um questionário de perfil de investidor, e
vê o resultado (preço médio, valor de mercado, lucro/prejuízo, carteira ao longo do
tempo). As cotações e o resumo da semana são atualizados automaticamente.

**Stack:** site estático (HTML/JS) na **Vercel** · login + banco no **Supabase** ·
cotações (Yahoo Finance) via **GitHub Actions** (cron).

> ⚠️ **Não é recomendação de investimento.** É uma ferramenta de acompanhamento e
> estudo. Cotações vêm do Yahoo Finance (fonte não oficial) e podem atrasar/faltar.

---

## Como colocar no ar (passo a passo)

### 1. Supabase (login + banco) — grátis
1. Crie uma conta em https://supabase.com e um **New project** (guarde a senha do banco).
2. Menu **SQL Editor → New query**, cole todo o conteúdo de [`supabase/schema.sql`](supabase/schema.sql) e clique **Run**.
3. Menu **Project Settings → API**. Copie:
   - **Project URL** (ex.: `https://xxxx.supabase.co`)
   - **anon public** key (é pública, protegida pelas regras do banco)
   - **service_role** key (é **secreta** — só vai no GitHub, nunca no site)
4. Menu **Authentication → Providers → Email**: deixe **Email** ligado (o padrão já
   envia "magic link", login sem senha).
5. Edite [`config.js`](config.js) com a **Project URL** e a **anon key**.

### 2. Vercel (hospedagem) — grátis
1. Suba este repositório no GitHub (veja abaixo) e entre em https://vercel.com com o GitHub.
2. **Add New → Project → Import** o repositório `Grafico`. Framework **Other**, sem build command. **Deploy**.
3. Copie a URL que a Vercel gerar (ex.: `https://grafico-xxxx.vercel.app`).
4. Volte no Supabase em **Authentication → URL Configuration**:
   - **Site URL**: a URL da Vercel.
   - **Redirect URLs**: adicione a URL da Vercel (e `http://localhost:*` se for testar local).

### 3. GitHub Actions (cotações automáticas)
1. No repositório, **Settings → Secrets and variables → Actions → New repository secret**, crie:
   - `SUPABASE_URL` = a Project URL do Supabase
   - `SUPABASE_SERVICE_KEY` = a **service_role** key
2. Aba **Actions**: se pedir, clique para habilitar os workflows.
3. O robô roda sozinho (dias úteis ~18:44 e sábado ~08:36, horário de Brasília). Para
   testar na hora: **Actions → "Cotações e resumo" → Run workflow**.

### 4. Usar
Abra a URL da Vercel → digite seu e-mail → clique no link que chegar → pronto. Faça o
perfil, cadastre ações em **Minha carteira** e registre uma compra. A outra pessoa faz
o mesmo com o e-mail dela. Vocês se veem na aba **Grupo**.

---

## Notas importantes
- **Privacidade:** qualquer pessoa logada enxerga a carteira de todos os membros (feito
  para um grupo pequeno de confiança). As regras do banco (RLS) garantem que cada um só
  **edita** os próprios dados.
- **Resumo de fim de semana:** fica na aba "Resumo da semana" do app. Notificação no
  celular não vem de graça fora do claude.ai; dá para adicionar e-mail/Telegram depois.
- **B3:** use os códigos da bolsa (PETR4, VALE3, ITUB4…). O robô adiciona `.SA` sozinho.

## Rodar/editar localmente
É um site estático. Com um `config.js` preenchido:
```bash
python3 -m http.server 8000   # abra http://localhost:8000
```
(O login por e-mail só funciona na URL publicada; para testar local, adicione
`http://localhost:8000` nas Redirect URLs do Supabase.)

## Estrutura
```
index.html                      # o app (frontend)
config.js                       # URL + anon key do seu Supabase (edite)
supabase/schema.sql             # tabelas + regras de acesso (rode no Supabase)
sync/carteira_sync.py           # robô de cotações + resumo
.github/workflows/cotacoes.yml  # agenda do robô
```
