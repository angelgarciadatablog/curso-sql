#!/usr/bin/env python3
"""
Genera el sitio del curso SQL desde el vault.

Fuente:  ~/infinity-memory/vault/asesorias-material/sql/
Salida:  este repo -> index.html y <slug>/index.html

El HTML no se edita a mano: se regenera. Ver README.md.
"""
import re, json, argparse
from pathlib import Path
from datetime import date
import frontmatter, markdown

SRC        = Path.home()/"infinity-memory"/"vault"/"asesorias-material"/"sql"
ROOT       = Path(__file__).parent
ASSETS     = ROOT/"assets"
CURSO_JSON = ROOT/"curso.json"
BASE_URL   = "https://www.angelgarciadatablog.com"
BASE_PATH  = "/curso-sql"
PUBLICABLES = {"listo", "publicado"}
EXCLUIR_DIRS = {"plan"}

ap = argparse.ArgumentParser()
ap.add_argument("--todo",  action="store_true", help="incluir borradores")
ap.add_argument("--slug",  help="regenerar un solo tema")
args = ap.parse_args()

# ─── LEER LA RUTA DEL CURSO (00-index.md) ─────────────────────────────────────
index_md = (SRC/"00-index.md").read_text(encoding="utf-8")
nombres_bloque, desc_tema, orden_idx = {}, {}, []

# El total lo declara el propio índice del vault ("11 bloques · 57 temas"),
# no se deduce contando filas: hay entradas con sufijo (51b, 51c) que no suman.
mtot = re.search(r"\*\*(\d+) bloques · (\d+) temas", index_md)
TOTAL_TEMAS = int(mtot.group(2)) if mtot else 0
mh = re.search(r"aproximadamente \*\*(\d+) horas\*\*", index_md)
HORAS = mh.group(1) if mh else ""
bloque_actual = None
for linea in index_md.splitlines():
    mb = re.match(r"^## Bloque (\d+) — (.+)$", linea)
    if mb:
        bloque_actual = mb.group(1)
        nombres_bloque[bloque_actual] = mb.group(2).strip()
        continue
    mt = re.match(r"^\|\s*(\d+[a-z]?)\s*\|\s*`([a-z0-9-]+)`\s*\|\s*(.*?)\s*\|", linea)
    if mt and bloque_actual is not None:
        desc_tema[mt.group(2)] = re.sub(r"\*\*|`", "", mt.group(3)).strip()
        # (número, slug, bloque) — la ruta completa, incluidos los temas aún sin escribir
        orden_idx.append((mt.group(1), mt.group(2), bloque_actual))

# ─── LEER LOS TEMAS ───────────────────────────────────────────────────────────
temas = []
for f in sorted(SRC.glob("*/*.md")):
    if f.parent.name in EXCLUIR_DIRS or f.name == "00-index.md":
        continue
    post = frontmatter.load(f)
    meta = post.metadata
    if "orden" not in meta or "bloque" not in meta:
        continue
    titulo = next((l[2:].strip() for l in post.content.splitlines() if l.startswith("# ")), f.stem)
    temas.append({
        "slug": f.stem, "titulo": titulo,
        "bloque": str(meta["bloque"]), "orden": int(meta["orden"]),
        "status": str(meta.get("status", "borrador")),
        "meta": meta, "content": post.content,
    })
temas.sort(key=lambda t: t["orden"])
por_slug = {t["slug"]: t for t in temas}

YT_URL = (r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s)]*v=[A-Za-z0-9_-]{11}[^\s)]*"
          r"|youtu\.be/[A-Za-z0-9_-]{11}[^\s)]*)")
# Un video solo en su línea: sintaxis de embed de Obsidian ![Título](url) o la URL pelada.
VIDEO_LINEA = re.compile(rf"^[ \t]*(?:!\[(?P<tit>[^\]]*)\]\((?P<url1>{YT_URL})\)"
                         rf"|(?P<url2>{YT_URL}))[ \t]*$")
MARCA_VIDEO = "@@video-%d@@"


def datos_video(url):
    """(id, segundo_de_inicio) de una URL de YouTube. El `t=13s` de los enlaces
    compartidos se traduce a `start=13` en el embed."""
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    vid = m.group(1) if m else url
    ms = re.search(r"[?&]t=(\d+)s?", url)
    return vid, int(ms.group(1)) if ms else 0


def extraer_video_id(url):
    """Extrae el video ID de una URL de YouTube."""
    return datos_video(url)[0]


def html_video(titulo, url):
    """Un bloque de video. Sin título no se pinta la etiqueta — dentro del cuerpo
    el encabezado de la sección ya dice de qué va."""
    vid, start = datos_video(url)
    src = f"https://www.youtube.com/embed/{vid}" + (f"?start={start}" if start else "")
    tit = (titulo or "").strip()
    etiqueta = f'<div class="tema-video-tit">{tit}</div>' if tit else ""
    return (f'<div class="tema-video">{etiqueta}<iframe src="{src}"'
            f' title="{tit or "Video del tema"}" loading="lazy" allowfullscreen></iframe></div>')


def extraer_videos_inline(cuerpo):
    """Saca los videos que van dentro del cuerpo y los deja como marcador.

    Devuelve (cuerpo_con_marcadores, [(titulo, url), ...]). Se sustituye antes de
    convertir a Markdown para que el HTML del iframe no pase por el conversor;
    lo que hay dentro de un bloque de código no se toca."""
    videos, salida, en_codigo = [], [], False
    for linea in cuerpo.splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        if not en_codigo:
            m = VIDEO_LINEA.match(linea)
            if m:
                videos.append((m.group("tit") or "", m.group("url1") or m.group("url2")))
                salida += ["", MARCA_VIDEO % (len(videos) - 1), ""]
                continue
        salida.append(linea)
    return "\n".join(salida), videos


def normalizar_videos(value):
    """Normaliza `video-youtube` a una lista de dicts {titulo, url}.

    Campo polimórfico, misma convención que publish.py del blog:
    - "" / None            -> []  (sin video)
    - "https://..."        -> un video con título por defecto
    - ["url1", "url2"]     -> varios videos sin título explícito
    - [{titulo, url}, ...] -> varios videos, cada uno con su etiqueta
    """
    if not value:
        return []
    if isinstance(value, str):
        return [{"titulo": "Video explicativo", "url": value}]
    videos = []
    for item in value:
        if isinstance(item, str):
            videos.append({"titulo": "Video explicativo", "url": item})
        elif isinstance(item, dict) and item.get("url"):
            videos.append({"titulo": item.get("titulo") or "Video explicativo",
                           "url": item["url"]})
    return videos


def nb(b):
    """Número de bloque visible. Desde el 2026-08-30 el vault numera desde 1,
    igual que la web: el desfase de +1 que había aquí no llegaba a la prosa de
    los temas, que cita números del vault. La numeración la manda el vault."""
    return str(b)


def publicable(t):
    return args.todo or t["status"] in PUBLICABLES

publicados = [t for t in temas if publicable(t)]
slugs_pub  = {t["slug"] for t in publicados}
if not publicados:
    print("No hay temas con status listo/publicado. Usa --todo para previsualizar borradores.")
    raise SystemExit

# ─── MARKDOWN → HTML ──────────────────────────────────────────────────────────
# codehilite colorea en el build con Pygments (sin CDN, sin parpadeo).
# guess_lang=False es deliberado: los bloques sin lenguaje son salidas de psql,
# y deben quedarse en texto plano — solo se colorea lo que es código.
md = markdown.Markdown(extensions=["fenced_code", "tables", "codehilite"],
                       extension_configs={"codehilite": {"guess_lang": False,
                                                         "css_class": "hl"}})

def enlazar_slugs(html, slug_actual):
    """`slug-en-backticks` -> enlace, solo si el destino está publicado."""
    def repl(mo):
        s = mo.group(1)
        if s == slug_actual or s not in por_slug:
            return mo.group(0)
        if s in slugs_pub:
            return f'<a class="xref" href="../{s}/">{s}</a>'
        return f'<span class="xref-pend" title="Aún no publicado">{s}</span>'
    return re.sub(r"<code>([a-z0-9-]{6,})</code>", repl, html)

def render(txt, slug):
    md.reset()
    return enlazar_slugs(md.convert(txt), slug)

def anclar(t):
    return re.sub(r"[^a-z0-9]+", "-", re.sub("<[^>]+>", "", t).lower()).strip("-")

tema_tpl  = (ASSETS/"tema_template.html").read_text(encoding="utf-8")
index_tpl = (ASSETS/"index_template.html").read_text(encoding="utf-8")

# ─── SIDEBAR (compartido por todas las páginas de tema) ───────────────────────
def sidebar(slug_actual, bloque_actual):
    out = []
    for b in sorted(nombres_bloque, key=int):
        dentro = [t for t in temas if t["bloque"] == b]
        if not dentro:
            continue
        items = []
        for t in dentro:
            if t["slug"] == slug_actual:
                items.append(f'<li><span class="activo">{t["titulo"]}</span></li>')
            elif t["slug"] in slugs_pub:
                items.append(f'<li><a href="../{t["slug"]}/">{t["titulo"]}</a></li>')
            else:
                items.append(f'<li><span class="bloqueado">{t["titulo"]}</span></li>')
        abierto = " open" if b == bloque_actual else ""
        out.append(f'<details{abierto}><summary><span class="bnum">{nb(b)}</span>'
                   f'{nombres_bloque[b]}</summary><ul>{"".join(items)}</ul></details>')
    return "\n".join(out)

# ─── GENERAR CADA TEMA ────────────────────────────────────────────────────────
generados = []
for i, t in enumerate(publicados):
    if args.slug and t["slug"] != args.slug:
        continue
    cuerpo = t["content"]
    # partir soluciones: ancla = el encabezado (el '---' previo falta en 11 temas)
    soluciones = ""
    m = re.search(r"^## Soluciones\s*$", cuerpo, re.M)
    if m:
        soluciones = cuerpo[m.end():].strip()
        cuerpo = cuerpo[:m.start()].rstrip().rstrip("-").rstrip()
    cuerpo = re.sub(r"^# .+\n", "", cuerpo, count=1)          # el h1 lo pone el template
    cuerpo, videos_inline = extraer_videos_inline(cuerpo)

    cuerpo_html = render(cuerpo, t["slug"])
    for n, (tit, url) in enumerate(videos_inline):
        cuerpo_html = cuerpo_html.replace(f"<p>{MARCA_VIDEO % n}</p>", html_video(tit, url))
    sol_html    = render(soluciones, t["slug"]) if soluciones else ""

    # TOC + anclas en los h2
    toc = re.findall(r"<h2>(.*?)</h2>", cuerpo_html)
    for h in toc:
        limpio = re.sub("<[^>]+>", "", h)
        cuerpo_html = cuerpo_html.replace(f"<h2>{h}</h2>",
                                          f'<h2 id="{anclar(h)}">{limpio}</h2>', 1)
    toc_html = "\n".join(f'<a href="#{anclar(h)}">{re.sub("<[^>]+>","",h)}</a>' for h in toc)

    prev = publicados[i-1] if i > 0 else None
    nxt  = publicados[i+1] if i < len(publicados)-1 else None

    req = t["meta"].get("requiere") or []
    req_html = ""
    if req:
        ls = [f'<a href="../{s}/">{s}</a>' if s in slugs_pub else f'<span class="xref-pend">{s}</span>'
              for s in req]
        req_html = ('<div class="requiere"><span class="lbl">Requiere</span>'
                    + " ".join(ls) + "</div>")

    sol_block = (f'<details class="soluciones"><summary><span class="sol-ic">✓</span> Soluciones'
                 f'<span class="sol-hint">Resuélvelos antes de abrir</span></summary>'
                 f'<div class="post-body">{sol_html}</div></details>') if sol_html else ""

    # Video(s) de YouTube. Si el tema pone videos dentro del cuerpo, mandan esos y
    # la cabecera se queda vacía; el campo del frontmatter es la vía sin posición.
    video_html = ""
    if not videos_inline:
        for v in normalizar_videos(t["meta"].get("video-youtube", "")):
            video_html += html_video(v["titulo"], v["url"])
    elif t["meta"].get("video-youtube"):
        print(f"  ! {t['slug']}: tiene videos en el cuerpo — se ignora `video-youtube` del frontmatter")

    descripcion = desc_tema.get(t["slug"], t["titulo"])
    canonical   = f"{BASE_URL}{BASE_PATH}/{t['slug']}/"
    html = (tema_tpl
        .replace("{{TITULO}}", t["titulo"])
        .replace("{{OGTITULO}}", t["titulo"])
        .replace("{{DESCRIPCION}}", descripcion)
        .replace("{{CANONICAL}}", canonical)
        .replace("{{ASSETS}}", "../assets")
        .replace("{{RAIZ}}", "../")
        .replace("{{BLOQUE_NUM}}", nb(t["bloque"]))
        .replace("{{BLOQUE_NOMBRE}}", nombres_bloque.get(t["bloque"], ""))
        .replace("{{ORDEN}}", str(t["orden"]))
        .replace("{{TOTAL}}", str(TOTAL_TEMAS))
        .replace("{{MOTOR}}", str(t["meta"].get("motor", "")))
        .replace("{{DATASET}}", str(t["meta"].get("dataset", "")))
        .replace("{{REQUIERE}}", req_html)
        .replace("{{VIDEO}}", video_html)
        .replace("{{SIDEBAR}}", sidebar(t["slug"], t["bloque"]))
        .replace("{{TOC}}", toc_html)
        .replace("{{CUERPO}}", cuerpo_html)
        .replace("{{SOLUCIONES}}", sol_block)
        .replace("{{PREV}}", f'<a class="nav-prev" href="../{prev["slug"]}/"><span>Anterior</span>'
                             f'<strong>{prev["titulo"]}</strong></a>' if prev else "<span></span>")
        .replace("{{NEXT}}", f'<a class="nav-next" href="../{nxt["slug"]}/"><span>Siguiente</span>'
                             f'<strong>{nxt["titulo"]}</strong></a>' if nxt else "<span></span>"))

    destino = ROOT/t["slug"]
    destino.mkdir(exist_ok=True)
    (destino/"index.html").write_text(html, encoding="utf-8")
    generados.append(t)
    print(f"  ✓ {t['orden']:>2}. {t['slug']}")

# ─── ÍNDICE DEL CURSO ─────────────────────────────────────────────────────────
bloques_html = []
for b in sorted(nombres_bloque, key=int):
    filas_idx = [(n, sl) for n, sl, bb in orden_idx if bb == b]
    if not filas_idx:
        continue
    filas = []
    for n, sl in filas_idx:
        t = por_slug.get(sl)
        titulo = t["titulo"] if t else sl.replace("-", " ").capitalize()
        if sl in slugs_pub:
            filas.append(f'<li><a href="{sl}/"><span class="n">{n}</span>'
                         f'<span class="t">{titulo}</span></a></li>')
        else:
            filas.append(f'<li><span class="no"><span class="n">{n}</span>'
                         f'<span class="t">{titulo}</span></span></li>')
    disp = sum(1 for n, sl in filas_idx if sl in slugs_pub)
    clase = "tarjeta lista" if disp else "tarjeta"
    bloques_html.append(
        f'<section class="{clase}"><div class="t-cab">'
        f'<span class="bnum">{nb(b)}</span><h3>{nombres_bloque[b]}</h3>'
        f'<span class="t-cuantos">{disp}/{len(filas_idx)}</span></div>'
        f'<ul class="t-temas">{"".join(filas)}</ul></section>')

lead = ("La ruta completa de SQL sobre PostgreSQL, usando Northwind como único dataset "
        "de principio a fin. Cada consulta del material está ejecutada contra la base "
        "antes de escribirse.")
(ROOT/"index.html").write_text(index_tpl
    .replace("{{TITULO}}", "Curso SQL desde cero · Angel García")
    .replace("{{OGTITULO}}", "Curso SQL desde cero, sobre una base real")
    .replace("{{DESCRIPCION}}", lead)
    .replace("{{CANONICAL}}", f"{BASE_URL}{BASE_PATH}/")
    .replace("{{ASSETS}}", "assets")
    .replace("{{LEAD}}", lead)
    .replace("{{BLOQUES}}", str(len(nombres_bloque)))
    .replace("{{TOTAL}}", str(TOTAL_TEMAS))
    .replace("{{PUBLICADOS}}", str(len(slugs_pub)))
    .replace("{{HORAS}}", HORAS)
    .replace("{{BLOQUES_HTML}}", "\n".join(bloques_html)), encoding="utf-8")

# ─── ÍNDICE MÁQUINA + SITEMAP ─────────────────────────────────────────────────
CURSO_JSON.write_text(json.dumps(
    [{"slug": t["slug"], "titulo": t["titulo"], "bloque": t["bloque"],
      "orden": t["orden"], "url": f"{BASE_URL}{BASE_PATH}/{t['slug']}/"} for t in publicados],
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

hoy = date.today().isoformat()
urls = [f"{BASE_URL}{BASE_PATH}/"] + [f"{BASE_URL}{BASE_PATH}/{t['slug']}/" for t in publicados]
(ROOT/"sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{hoy}</lastmod></url>\n" for u in urls)
    + "</urlset>\n", encoding="utf-8")

print(f"\n{len(generados)} temas generados · índice con {TOTAL_TEMAS} temas "
      f"({len(slugs_pub)} disponibles) · sitemap con {len(urls)} URLs")
