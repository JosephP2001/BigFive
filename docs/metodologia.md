# Metodología

Este documento describe qué calcula `src/analisis.py`, con qué fórmulas y qué límites tiene. Las constantes están al inicio del archivo y se pueden ajustar.

## 1. Datos de entrada

`analisis.py` lee los archivos `datos/salida_<usuario>.json` que genera `scraper.py`:

- `perfil`: usuario, seguidores, siguiendo, biografía y otros campos.
- `publicaciones`: por cada una, fecha, descripción, hashtags, vistas, likes, comentarios, compartidos, guardados e interacciones.
- `corpus_texto`: biografía y descripciones concatenadas.

## 2. Big Five heurístico

Se busca en el texto raíces de palabras de un diccionario en español (`src/lexico_es.json`), con una lista de raíces "alto" y otra "bajo" por rasgo. El texto se pasa a minúsculas y se le quitan las tildes antes de comparar.

Para cada rasgo, con `a` aciertos de la lista alta y `b` de la baja:

```
puntaje = 50 + 50 * (a - b) / (a + b + 3)
```

- Sin ningún acierto el puntaje es 50 (neutro).
- El 3 del denominador acerca el resultado a 50 cuando hay poca evidencia.
- Con muchos aciertos de un solo lado el puntaje tiende a 0 o a 100.

**Confianza del texto** = `min(1, palabras / 300)`. Con menos de 100 palabras el script avisa de que los puntajes son poco fiables.

### Límites

- El diccionario es mínimo y de demostración: no está validado psicométricamente.
- Una misma palabra repetida en varias publicaciones cuenta cada vez, y puede inflar un rasgo.
- No interpreta ironía, contexto ni lo que no está en el texto.
- En cuentas de negocio, el texto describe a la marca y no a una persona.
- No se analizan rostros ni voz.

## 3. Valor (alcance e influencia)

```
valor = 100 * (0.40 * interacción + 0.35 * alcance + 0.25 * seguidores)
```

| Componente | Cálculo | Referencia |
|---|---|---|
| interacción | mediana de `interacciones / vistas`, dividida entre 0.10 | 10 % se toma como "muy alta" |
| alcance | `log10(1 + vistas medianas) / 6` | 1 millón de vistas = 1 |
| seguidores | `log10(1 + seguidores) / 7` | 10 millones = 1 |

Cada componente se limita a 1. Los pesos y las referencias son supuestos del proyecto, no valores establecidos: conviene validarlos con quien califica el trabajo.

## 4. Veracidad (autenticidad aparente de la cuenta)

"Veracidad" se interpreta aquí como qué tan coherentes son las métricas de la cuenta con un comportamiento orgánico. **No mide si la persona dice la verdad.**

```
veracidad = 100 * (0.35 * cobertura + 0.25 * coherencia + 0.25 * regularidad + 0.15 * perfil)
```

| Componente | Cálculo |
|---|---|
| cobertura | `vistas medianas / seguidores`, dividido entre 0.05 (tope 1). Muchos seguidores y pocas vistas es una señal débil. |
| coherencia | Mediana de `likes / vistas`. Vale 1 entre 1 % y 20 %; baja fuera de ese rango. |
| regularidad | `1 / (1 + cv)`, con `cv` el coeficiente de variación de los intervalos entre publicaciones. Vale 0.5 si hay pocos datos. |
| perfil | 1 si la cuenta tiene biografía, 0.5 si no. |

Se necesitan al menos 3 publicaciones con vistas; si no, no se calcula.

### Límites

- Una cuenta real puede tener una cobertura baja por razones normales (audiencia antigua, cambios del algoritmo).
- Un puntaje bajo es una razón para mirar la cuenta con más cuidado, no una conclusión.
- Las constantes salen de supuestos razonables, no de un estudio.

## 5. Consideraciones éticas

- Analizar la personalidad de una persona a partir de sus publicaciones es un uso sensible, aunque la cuenta sea pública. La ley de protección de datos personales de Ecuador podría aplicar; no es asesoría legal, hay que consultarlo con el docente.
- Para pruebas conviene usar cuentas de negocios o cuentas cuyos dueños den permiso.
- Los datos extraídos y los videos o imágenes se quedan en la máquina local y no se suben al repositorio.
- Los resultados se presentan siempre como estimaciones, junto con sus avisos.
