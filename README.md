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

## Videos

Un video se pone **donde toca dentro del cuerpo del tema**, solo en su línea, con la sintaxis
de embed de Obsidian — así se ve embebido tanto en el vault como en la web:

```markdown
![Conectarse a la base del curso con DBeaver](https://www.youtube.com/watch?v=OPHykPx5Px8)
```

- **Cuantos quieras por tema.** Cada línea con un video se convierte en su propio reproductor,
  en el punto exacto donde está escrita.
- **El texto entre corchetes es la etiqueta** que sale encima del reproductor. Vacío
  (`![](url)`) no pinta etiqueta — útil cuando el encabezado de la sección ya lo dice todo.
- **Formatos aceptados**: `youtube.com/watch?v=` y `youtu.be/`. Si la URL trae `&t=13s`,
  el video arranca en el segundo 13.
- **Solo se detecta si el video está solo en su línea.** Una URL de YouTube dentro de una
  frase, o dentro de un bloque de código, se queda como está.
- **`video-youtube` en el frontmatter sigue funcionando** (uno o varios, ver `normalizar_videos`),
  pero pone los videos arriba del tema, sin control de posición. Si el cuerpo trae videos, el
  frontmatter se ignora y el generador lo avisa.
