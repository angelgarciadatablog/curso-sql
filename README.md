# curso-sql

Sitio del curso **SQL desde cero** sobre PostgreSQL + Northwind.
Servido en <https://www.angelgarciadatablog.com/curso-sql/> (GitHub Pages, project site que hereda el dominio).

## Cómo funciona

La fuente de verdad es el vault, **no este repo**:

    ~/infinity-memory/vault/asesorias-material/sql/
      00-index.md              ← ruta del curso: bloques, orden, descripciones
      <NN-bloque>/<slug>.md    ← un tema por archivo
      plan/                    ← documentos internos, NUNCA se publican

`publish_curso.py` lee esa carpeta y genera aquí `index.html` y `<slug>/index.html`.
**El HTML no se edita a mano**: se regenera.

## Publicar

    ./venv/bin/python publish_curso.py            # solo los temas con status listo/publicado
    ./venv/bin/python publish_curso.py --todo     # incluye borradores (previsualizar)
    ./venv/bin/python publish_curso.py --slug X   # regenera un solo tema

## Reglas

- **El slug es inmutable.** El nombre del archivo en el vault es la URL para siempre.
- **`status` manda.** Sin `status: listo` o `publicado` en el frontmatter, un tema no se genera.
  Un tema sin el campo se trata como borrador.
- **La ruta es plana**: `/curso-sql/<slug>/`. El bloque es metadato, no ruta — si un tema
  cambia de bloque, su URL no se rompe.
- **El índice se genera** desde `00-index.md`. No se escribe a mano.
- **Los enlaces cruzados** (slugs en backticks, `requiere`, `temas-relacionados`) solo se
  renderizan como enlace si el destino está publicado. Si no, quedan como texto.
- **Al tocar `assets/curso.css` hay que subir el `?v=N`** del template, o la CDN sirve la copia vieja.
