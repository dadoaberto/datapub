from typing import Dict


class HomePage:
    """Gera o HTML da página inicial (landing) da API.

    Mantém a mesma aparência e comportamento, mas isolado em uma classe
    para facilitar manutenção e organização do código.
    """

    @staticmethod
    def render(base: str, db_overview: Dict[str, str], neo4j_url: str) -> str:
        services = [
            {
                "name": "Swagger UI",
                "desc": "Documentação interativa da API.",
                "url": f"{base}:8000/docs",
                "service": "datapub",
                "cta": "/docs",
            },
            {
                "name": "OpenAPI JSON",
                "desc": "Especificação OpenAPI da API.",
                "url": f"{base}:8000/openapi.json",
                "service": "datapub",
                "cta": "/openapi.json",
            },
            {
                "name": "Métricas Prometheus",
                "desc": "Métricas HTTP da API.",
                "url": f"{base}:8000/metrics",
                "service": "datapub",
                "cta": "/metrics",
            },
            {
                "name": "Health",
                "desc": "Sinal de vida da API.",
                "url": f"{base}:8000/health",
                "service": "datapub",
                "cta": "/health",
            },
            {
                "name": "Health Config",
                "desc": "Configurações e status (DB, migrações, versões).",
                "url": f"{base}:8000/health/config",
                "service": "datapub",
                "cta": "/health/config",
            },
            {
                "name": "Swagger UI (externo)",
                "desc": "Interface Swagger apontando para a API (container swagger-ui).",
                "url": f"{base}:8080/?url={base}:8000/openapi.json",
                "service": "swagger-ui",
                "cta": "Abrir",
                "card_id": "card-swagger",
                "status_id": "status-swagger",
            },
            {
                "name": "pgAdmin",
                "desc": "Administração do PostgreSQL do compose.",
                "url": f"{base}:5050",
                "service": "pgadmin",
                "cta": "Abrir",
                "card_id": "card-pgadmin",
                "status_id": "status-pgadmin",
            },
            {
                "name": "Neo4j Browser",
                "desc": "Exploração do grafo de conhecimento (APOC/GDS habilitados).",
                "url": f"{base}:7474",
                "service": "neo4j",
                "cta": "Abrir",
            },
            {
                "name": "Prometheus",
                "desc": "Coleta e consulta de métricas.",
                "url": f"{base}:9090",
                "service": "prometheus",
                "cta": "Abrir",
                "card_id": "card-prometheus",
                "status_id": "status-prometheus",
            },
            {
                "name": "Grafana",
                "desc": "Dashboards e visualização de métricas.",
                "url": f"{base}:3000",
                "service": "grafana",
                "cta": "Abrir",
            },
        ]

        cards_list = []
        for s in services:
            status_line = ""
            status_id = s.get("status_id")
            if status_id:
                status_line = (
                    f"<div class=\\\"mt-2 text-xs text-gray-600 dark:text-gray-300\\\">Status: "
                    f"<span id=\\\"{status_id}\\\" class=\\\"inline-flex items-center rounded-md bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-[11px] font-medium text-gray-700 dark:text-gray-200\\\">checando...</span></div>"
                )
            card_id = s.get("card_id", "")
            cards_list.append(
                f"""
                <a id=\"{card_id}\" href=\"{s['url']}\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"block rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm hover:shadow-md transition\">
                  <div class=\"flex items-center justify-between\">
                    <h3 class=\"text-lg font-semibold text-gray-900 dark:text-gray-100\">{s['name']}</h3>
                    <span class=\"inline-flex items-center gap-2 rounded-md bg-blue-50 dark:bg-blue-900/30 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-200 ring-1 ring-inset ring-blue-600/10 dark:ring-blue-500/30\">{s['service']}</span>
                  </div>
                  <p class=\"mt-2 text-sm text-gray-600 dark:text-gray-300\">{s['desc']}</p>
                  {status_line}
                  <div class=\"mt-4\">
                    <span class=\"inline-flex items-center gap-2 text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline\">{s['cta']} →</span>
                  </div>
                </a>
                """
            )
        cards = "".join(cards_list)

        html = f"""
        <!doctype html>
        <html lang=\"pt-br\">
        <head>
          <meta charset=\"utf-8\">
          <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
          <title>DataPub • Serviços</title>
          <script src=\"https://cdn.tailwindcss.com\"></script>
          <script>
            // Tailwind Play CDN config: enable class-based dark mode
            tailwind.config = {{ darkMode: 'class' }};
          </script>
          <script>
            // Apply preferred theme early to avoid flashes
            (function() {{
              try {{
                var stored = localStorage.getItem('theme');
                var prefers = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                var useDark = stored ? (stored === 'dark') : prefers;
                if (useDark) document.documentElement.classList.add('dark');
                else document.documentElement.classList.remove('dark');
              }} catch (e) {{}}
            }})();
          </script>
        </head>
        <body class=\"bg-gray-50 dark:bg-gray-900\">
          <main class=\"mx-auto max-w-6xl p-6\">
            <header class=\"mb-8 flex items-start justify-between gap-4\">
              <div class=\"flex items-center gap-3\">
                <div class=\"h-9 w-9 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-sm\" aria-hidden=\"true\">
                  <svg class=\"h-5 w-5\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M13 2.05v6.02a7.002 7.002 0 015.995 5.994H21a9 9 0 00-8-8.94V2.05zM11 2.05V1a1 1 0 112 0v1.05A9.002 9.002 0 0121.95 11H23a1 1 0 110 2h-1.05A9.002 9.002 0 0113 21.95V23a1 1 0 11-2 0v-1.05A9.002 9.002 0 012.05 13H1a1 1 0 110-2h1.05A9.002 9.002 0 0111 2.05zM4.062 13a7.002 7.002 0 005.938 5.938V13H4.062zM18 11a7 7 0 00-7-7v7h7z\"/></svg>
                </div>
                <div>
                  <h1 class=\"text-2xl font-bold text-gray-900 dark:text-gray-100\">DataPub • Serviços</h1>
                  <p class=\"mt-1 text-sm text-gray-600 dark:text-gray-300\">Links rápidos para serviços do docker-compose. Base: <code class=\"font-mono\">{base}</code></p>
                </div>
              </div>
              <button id=\"theme-toggle\" data-theme-toggle class=\"inline-flex items-center gap-2 rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition\" type=\"button\">
                <span class=\"sr-only\">Alternar tema</span>
                <svg class=\"h-4 w-4 hidden dark:block\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path d=\"M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4.22 1.78a1 1 0 011.415 1.414l-.707.708a1 1 0 11-1.415-1.415l.707-.707zM17 9a1 1 0 100 2h1a1 1 0 100-2h-1zM4.072 4.072a1 1 0 011.415 0l.707.707A1 1 0 014.78 6.194l-.707-.707a1 1 0 010-1.415zM10 15a5 5 0 100-10 5 5 0 000 10zm-7-4H2a1 1 0 110-2h1a1 1 0 110 2zm11.121 3.536l.707.707a1 1 0 001.415-1.414l-.707-.707a1 1 0 10-1.415 1.414zM10 17a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM4.464 14.536a1 1 0 10-1.414 1.415l.707.707a1 1 0 001.415-1.414l-.708-.708z\"/></svg>
                <svg class=\"h-4 w-4 dark:hidden\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path d=\"M17.293 13.293A8 8 0 116.707 2.707 8.001 8.001 0 0017.293 13.293z\"/></svg>
                <span>Alternar tema</span>
              </button>
            </header>
            <section class=\"grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-6\">{cards}</section>
            <section class=\"grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-6\">
              <div class=\"rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4\">
                <h3 class=\"text-base font-semibold text-gray-900 dark:text-gray-100\">Banco de Dados (APP)</h3>
                <p class=\"mt-1 text-sm text-gray-600 dark:text-gray-300\">Base relacional usada pela API (SQLAlchemy/Alembic).</p>
                <div class=\"mt-3 text-sm text-gray-700 dark:text-gray-200\">
                  <div>Dialeto: <code class=\"font-mono\">{db_overview['dialect']}</code></div>
                  <div>Destino: <code class=\"font-mono\">{db_overview['target']}</code></div>
                </div>
                <div class=\"mt-4 flex gap-2\">
                  <a href=\"/health/config\" class=\"inline-flex items-center rounded-md border border-gray-300 dark:border-gray-600 px-2.5 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700\">Ver /health/config</a>
                  <a href=\"{base}:5050\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"inline-flex items-center rounded-md border border-blue-200 dark:border-blue-700/40 px-2.5 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-200 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/40\">Abrir pgAdmin</a>
                </div>
              </div>
              <div id=\"card-neo4j\" class=\"rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4\">
                <h3 class=\"text-base font-semibold text-gray-900 dark:text-gray-100\">Neo4j</h3>
                <p class=\"mt-1 text-sm text-gray-600 dark:text-gray-300\">Banco de grafo para o conhecimento (APOC/GDS).</p>
                <div class=\"mt-3 text-sm text-gray-700 dark:text-gray-200\">
                  <div>URL: <code class=\"font-mono\">{neo4j_url}</code></div>
                  <div>Status: <span id=\"neo4j-status\" class=\"inline-flex items-center rounded-md bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-200\">checando...</span></div>
                </div>
                <div class=\"mt-4 flex gap-2\">
                  <a href=\"{base}:7474\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"inline-flex items-center rounded-md border border-emerald-200 dark:border-emerald-700/40 px-2.5 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-200 bg-emerald-50 dark:bg-emerald-900/30 hover:bg-emerald-100 dark:hover:bg-emerald-900/40\">Abrir Neo4j Browser</a>
                  <a href=\"/health/config\" class=\"inline-flex items-center rounded-md border border-gray-300 dark:border-gray-600 px-2.5 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700\">Ver /health/config</a>
                </div>
              </div>
              <div class=\"rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4\">
                <h3 class=\"text-base font-semibold text-gray-900 dark:text-gray-100\">Scheduler</h3>
                <p class=\"mt-1 text-sm text-gray-600 dark:text-gray-300\">Agendador (APScheduler) para pipelines diárias.</p>
                <div class=\"mt-3 text-sm text-gray-700 dark:text-gray-200\">
                  <div>Cron: <code id=\"sched-cron\" class=\"font-mono\">—</code></div>
                  <div>Entidades: <code id=\"sched-entities\" class=\"font-mono\">—</code></div>
                </div>
                <div class=\"mt-4 flex gap-2\">
                  <a href=\"/scheduler/info\" class=\"inline-flex items-center rounded-md border border-gray-300 dark:border-gray-600 px-2.5 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700\">Ver /scheduler/info</a>
                  <a href=\"{base}:9090\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"inline-flex items-center rounded-md border border-purple-200 dark:border-purple-700/40 px-2.5 py-1.5 text-xs font-medium text-purple-700 dark:text-purple-200 bg-purple-50 dark:bg-purple-900/30 hover:bg-purple-100 dark:hover:bg-purple-900/40\">Abrir Prometheus</a>
                </div>
              </div>
            </section>
            <section class=\"grid grid-cols-1 gap-4\">
              <div id=\"db-migrations\" class=\"rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4\">
                <h3 class=\"text-base font-semibold text-gray-900 dark:text-gray-100\">Status de Migrações <span id=\"migr-count-badge\" class=\"ml-2 inline-flex items-center rounded-md bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-200\">—</span></h3>
                <p class=\"mt-1 text-sm text-gray-600 dark:text-gray-300\">Verifica se há migrações pendentes no banco relacional.</p>
                <div class=\"mt-3 text-sm\">
                  <span id=\"migr-pending\" class=\"inline-flex items-center gap-2 rounded-md px-2 py-1 font-medium ring-1 ring-inset\"></span>
                </div>
                <div class=\"mt-2 text-xs text-gray-500 dark:text-gray-400\">
                  <code>revision atual: <span id=\"migr-current\">—</span></code>
                  <span class=\"mx-2\">•</span>
                  <code>latest: <span id=\"migr-latest\">—</span></code>
                </div>
              </div>
            </section>
            <footer class=\"mt-8 text-xs text-gray-500 dark:text-gray-400\">
              <span>API v<span id=\"api-version\">—</span></span>
              <span class=\"mx-2\">•</span>
              <span>Cognee v<span id=\"cognee-version\">—</span></span>
            </footer>
          </main>
          <script>
            (function() {{
              var btn = document.getElementById('theme-toggle');
              if (!btn) return;
              btn.addEventListener('click', function() {{
                var el = document.documentElement;
                var isDark = el.classList.toggle('dark');
                try {{ localStorage.setItem('theme', isDark ? 'dark' : 'light'); }} catch (e) {{}}
              }});
            }})();
          </script>
          <script>
            // Fetch health/config and populate status + versions
            (async function() {{
              try {{
                const res = await fetch('/health/config');
                if (!res.ok) return;
                const data = await res.json();
                const apiV = document.getElementById('api-version');
                const cogV = document.getElementById('cognee-version');
                if (apiV) apiV.textContent = data.api_version || '—';
                if (cogV) cogV.textContent = data.cognee_version || '—';

                const mig = (data.db && data.db.migrations) || {{}};
                const pending = mig.pending;
                const el = document.getElementById('migr-pending');
                const cur = document.getElementById('migr-current');
                const lat = document.getElementById('migr-latest');
                if (cur) cur.textContent = mig.current_revision || '—';
                if (lat) lat.textContent = mig.latest_revision || '—';
                const mc = document.getElementById('migr-count-badge');
                if (mc && typeof mig.count === 'number') {{ mc.textContent = String(mig.count); }}
                if (el) {{
                  // reset
                  el.textContent = '';
                  el.className = 'inline-flex items-center gap-2 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset';
                  if (pending === true) {{
                    el.textContent = 'pendente';
                    el.classList.add('bg-amber-50','text-amber-800','ring-amber-600/20','dark:bg-amber-900/30','dark:text-amber-200','dark:ring-amber-500/30');
                  }} else if (pending === false) {{
                    el.textContent = 'ok';
                    el.classList.add('bg-green-50','text-green-800','ring-green-600/20','dark:bg-green-900/30','dark:text-green-200','dark:ring-green-500/30');
                  }} else {{
                    el.textContent = 'indefinido';
                    el.classList.add('bg-gray-50','text-gray-700','ring-gray-600/20','dark:bg-gray-800','dark:text-gray-200','dark:ring-gray-500/30');
                  }}
                }}
              }} catch (e) {{
                // ignore
              }}
            }})();
            // Fetch scheduler info
            (async function() {{
              try {{
                const res = await fetch('/scheduler/info');
                if (!res.ok) return;
                const data = await res.json();
                const cron = document.getElementById('sched-cron');
                const ents = document.getElementById('sched-entities');
                if (cron) cron.textContent = data.cron_pipeline || '—';
                if (ents) ents.textContent = data.entities || '—';
              }} catch (e) {{}}
            }})();
            // Fetch Neo4j status
            ;(async function() {{
              try {{
                const res = await fetch('/health/neo4j');
                if (!res.ok) return;
                const data = await res.json();
                const badge = document.getElementById('neo4j-status');
                const card = document.getElementById('card-neo4j');
                if (!badge) return;
                badge.className = 'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium';
                if (data.ok) {{
                  badge.textContent = 'online';
                  badge.classList.add('bg-green-50','text-green-800','dark:bg-green-900/30','dark:text-green-200');
                  if (card) {{ card.classList.add('ring-1','ring-inset','ring-green-600/20','dark:ring-green-500/30'); }}
                }} else {{
                  badge.textContent = 'offline';
                  badge.classList.add('bg-red-50','text-red-800','dark:bg-red-900/30','dark:text-red-200');
                  if (card) {{ card.classList.add('ring-1','ring-inset','ring-red-600/20','dark:ring-red-500/30'); }}
                }}
              }} catch (e) {{}}
            }})();
            // Fetch Swagger and Prometheus status
            ;(async function() {{
              try {{
                const res = await fetch('/health/swagger');
                if (res.ok) {{
                  const data = await res.json();
                  const badge = document.getElementById('status-swagger');
                  const card = document.getElementById('card-swagger');
                  if (badge) {{
                    badge.className = 'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium';
                    if (data.ok) {{
                      badge.textContent = 'online';
                      badge.classList.add('bg-green-50','text-green-800','dark:bg-green-900/30','dark:text-green-200');
                      if (card) {{ card.classList.add('ring-1','ring-inset','ring-green-600/20','dark:ring-green-500/30'); }}
                    }} else {{
                      badge.textContent = 'offline';
                      badge.classList.add('bg-red-50','text-red-800','dark:bg-red-900/30','dark:text-red-200');
                      if (card) {{ card.classList.add('ring-1','ring-inset','ring-red-600/20','dark:ring-red-500/30'); }}
                    }}
                  }}
                }}
              }} catch (e) {{}}
              try {{
                const res2 = await fetch('/health/prometheus');
                if (res2.ok) {{
                  const data2 = await res2.json();
                  const badge2 = document.getElementById('status-prometheus');
                  const card2 = document.getElementById('card-prometheus');
                  if (badge2) {{
                    badge2.className = 'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium';
                    if (data2.ok) {{
                      badge2.textContent = 'online';
                      badge2.classList.add('bg-green-50','text-green-800','dark:bg-green-900/30','dark:text-green-200');
                      if (card2) {{ card2.classList.add('ring-1','ring-inset','ring-green-600/20','dark:ring-green-500/30'); }}
                    }} else {{
                      badge2.textContent = 'offline';
                      badge2.classList.add('bg-red-50','text-red-800','dark:bg-red-900/30','dark:text-red-200');
                      if (card2) {{ card2.classList.add('ring-1','ring-inset','ring-red-600/20','dark:ring-red-500/30'); }}
                    }}
                  }}
                }}
              }} catch (e) {{}}
            }})();
          </script>
        </body>
        </html>
        """
        return html

