# TikTok Big Five (heurístico)

Proyecto académico de dos partes: un scraper de perfiles públicos de TikTok y un análisis heurístico (Big Five, valor y veracidad) sobre los datos extraídos. Este archivo reúne todo: los enunciados, cómo se ejecuta, cómo funciona el código y cómo resolver problemas.

Repositorio: https://github.com/JosephP2001/BigFive.git

## 1. Enunciados

### 1.1 Tarea 1: scraper de TikTok

Al escribir el usuario de la cuenta a analizar, el programa debe extraer:

- número de seguidos (following)
- número de seguidores (followers)
- las últimas 10 publicaciones
- el número de interacciones por publicación

Si las publicaciones son videos o imágenes, no se descargan.

Limitaciones:

1. No usar extensiones del navegador.
2. No usar APIs ya existentes.
3. El único dato de entrada es el usuario de TikTok del objetivo (sin credenciales ni cuenta propia).

Consejo del docente: en Inspeccionar, pestaña Network, buscar la petición FETCH; la cookie puede ser útil.

### 1.2 Tarea 2: Big Five

Usar el modelo Big Five para analizar a los usuarios extraídos y asignarles "valor" y "veracidad". No hace falta que sea preciso: es un análisis heurístico, y basta con que el programa descargue información suficiente para aplicarlo. Los enlaces de la multimedia caducan, pero no importa porque la demostración se hace en clase.

Nota: no se dispone de una definición del docente para "valor" y "veracidad". Los índices de este proyecto son una propuesta propia (sección 6.2) y se pueden ajustar.

## 2. Cómo se cumple cada requisito

| Requisito | Cómo se cumple |
|---|---|
| Seguidos y seguidores | Se leen del JSON que la página de TikTok incrusta en su HTML. Se usa `statsV2` porque trae las cifras exactas; `stats` viene redondeado. |
| Últimas 10 publicaciones | Se abre el perfil en Chromium (Playwright) y se captura la respuesta que la propia página recibe de `/api/post/item_list`. Se ordenan por fecha. |
| Interacciones por publicación | `likes + comentarios + compartidos`. Vistas y guardados se muestran aparte. |
| No descargar videos ni imágenes | Por defecto solo se guardan los enlaces. La descarga existe como opción (`--media`) y está apagada por defecto. |
| Sin extensiones | Playwright es una librería de Python que controla un navegador; no es una extensión. |
| Sin APIs existentes | No se llama a la API oficial de TikTok ni a servicios de terceros. El script no hace peticiones al endpoint interno: lee la respuesta que la propia página ya recibió mientras se carga. Conviene confirmar con el docente que esto es aceptable. |
| Solo el usuario como entrada | Se pasa como argumento o se escribe cuando el programa lo pide. No hay inicio de sesión. |
| Big Five, valor y veracidad | `src/analisis.py`, con fórmulas abiertas y sin servicios externos. |
| IA opcional | Modelo de lenguaje local con Ollama: gratuito, sin tarjeta ni cuenta, y los datos no salen de la computadora (sección 6.4). |

El captcha de TikTok no se resuelve de forma automática: aparece en la ventana visible y se resuelve a mano.

## 3. Estructura del repositorio

```
BigFive/
├── README.md
├── requirements.txt
├── .env.example          plantilla de configuración de la IA local
├── .gitignore
├── src/
│   ├── scraper.py        extracción (requests + Playwright)
│   ├── analisis.py       Big Five, valor y veracidad (solo biblioteca estándar)
│   ├── lexico_es.json    diccionario editable para el Big Five
│   ├── ia.py             cliente de Ollama y estimación Big Five con IA
│   ├── ia_big_five.py    estima el Big Five con la IA y lo compara con el léxico
│   └── asistente.py      preguntas sobre los resultados
└── tests/
    ├── test_analisis.py  12 pruebas automáticas
    └── test_ia.py        13 pruebas con un Ollama simulado
```

Estas carpetas se crean al ejecutar y están en el `.gitignore`, porque pueden contener información de terceros o cookies: `datos/`, `muestras/`, `media/`, `resultados/` y `.perfil_navegador/`. El archivo `.env` (configuración local de la IA) también está ignorado; solo se sube `.env.example`.

## 4. Requisitos e instalación

Requisitos: Windows 10 u 11, Git, Python 3.10 o superior (probado con 3.14, con "Add python.exe to PATH" marcado al instalar) y unos 600 MB libres para el navegador de Playwright. VS Code es opcional.

Los comandos son para `cmd` (el prompt sin "PS" al inicio) y se ejecutan desde la raíz del repositorio.

1. Clonar y entrar:

   ```bat
   git clone https://github.com/JosephP2001/BigFive.git
   cd BigFive
   ```

2. (Opcional) Crear y activar un entorno virtual. Si se prefiere instalar directamente en el Python base, se omite este paso y todo lo demás funciona igual:

   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instalar dependencias y el navegador:

   ```bat
   pip install -r requirements.txt
   playwright install chromium
   ```

   Durante la descarga puede aparecer `ENOTFOUND playwright.download.prss.microsoft.com`. Es un servidor espejo que la red no resuelve; Playwright reintenta con otra dirección. Si al final cada componente dice "downloaded", no hay que repetir nada.

4. Comprobar que las pruebas pasan (debe terminar con `OK`):

   ```bat
   python -m unittest discover -s tests
   ```

### 4.1 IA local (opcional)

Solo hace falta para `ia_big_five.py` y `asistente.py`.

1. Instalar Ollama desde ollama.com (hay instalador para Windows) y dejarlo abierto. Después de instalar, en una consola nueva:

   ```bat
   ollama --version
   ```

2. Descargar un modelo. Con 8 GB de RAM sirve uno pequeño como `llama3.2` (unos 2 GB de descarga):

   ```bat
   ollama pull llama3.2
   ```

3. Crear el archivo de configuración a partir de la plantilla (no lleva ningún token, porque el modelo corre en la propia computadora):

   ```bat
   copy .env.example .env
   ```

   En `.env` se puede cambiar `OLLAMA_MODEL` si se prueba otro modelo, y `OLLAMA_TIMEOUT` si el equipo es lento.

## 5. Ejecución

### 5.1 Extraer un perfil

```bat
python src\scraper.py nombre_usuario --visible
```

Se escribe el usuario sin `@`. Si no se pasa como argumento, el programa lo pide. Si aparece un captcha, se resuelve en la ventana; el script espera 120 segundos por defecto y continúa solo. La sesión anónima del navegador se guarda en `.perfil_navegador/` y hace que el captcha reaparezca menos.

Resultado: una tabla en la consola y el archivo `datos\salida_<usuario>.json`. Cada ejecución con el mismo usuario sobrescribe ese archivo; para conservar una corrida, copiarlo antes con otro nombre.

### 5.2 Extraer con videos e imágenes

```bat
python src\scraper.py nombre_usuario --visible --media -n 3
```

Descarga a `media\<usuario>\`. Los enlaces están firmados y caducan en horas, por eso se descarga en la misma ejecución. Conviene empezar con pocas publicaciones porque los videos pesan. Si una descarga falla se imprime `[media] ... HTTP <código>` y se continúa con las demás.

### 5.3 Analizar

```bat
python src\analisis.py
```

Sin argumentos analiza todos los `datos\salida_*.json`. También acepta un archivo concreto (`python src\analisis.py datos\salida_nombre_usuario.json`) o un léxico alternativo (`--lexico mi_lexico.json`).

Resultado: `resultados\analisis_<usuario>.json` por cuenta y `resultados\resumen.csv` con todas.

### 5.4 Varios usuarios seguidos

```bat
for %u in (usuario1 usuario2 usuario3) do python src\scraper.py %u --visible
python src\analisis.py
```

Dentro de un archivo `.bat` el `%u` se escribe `%%u`.

### 5.5 Opciones del scraper

| Opción | Efecto |
|---|---|
| `--visible` | Muestra la ventana del navegador. Necesaria si aparece un captcha. |
| `--espera N` | Segundos que se espera para resolver el captcha (120 por defecto). Solo aplica con `--visible`. |
| `--media` | Descarga los videos o imágenes a `media\<usuario>\`. |
| `--debug` | Guarda las respuestas crudas de TikTok en `muestras\`. |
| `-n N` | Cantidad de publicaciones (10 por defecto). |

Sin `--visible` el navegador corre oculto, y si TikTok pide un captcha el script espera solo 20 segundos y termina sin publicaciones.

### 5.6 Estimar el Big Five con la IA y hacer preguntas

Requiere haber extraído al menos una cuenta (5.1) y tener Ollama abierto con un modelo descargado (4.1).

```bat
python src\ia_big_five.py
python src\asistente.py nombre_usuario
```

- `ia_big_five.py` lee los `datos\salida_*.json`, pide al modelo una estimación por rasgo y la guarda en `resultados\ia_<usuario>.json`, junto a los puntajes del diccionario para comparar. Opción: `--modelo` para usar otro modelo.
- `asistente.py` abre una conversación sobre una cuenta. Responde solo con los datos de `datos\` y `resultados\`; si algo no está ahí, dice que no está en los datos. Se escribe 'salir' para terminar. Con `--pregunta "..."` hace una sola pregunta y termina.
- Con un equipo sin tarjeta gráfica, un modelo pequeño puede tardar entre varios segundos y un par de minutos por respuesta.

## 6. Cómo funciona

### 6.1 `src/scraper.py`

1. **Perfil.** Descarga el HTML de `tiktok.com/@usuario` con `requests` y lee el JSON de la etiqueta `__UNIVERSAL_DATA_FOR_REHYDRATION__`. De ahí salen seguidores, seguidos, videos, likes totales y biografía. Prefiere `statsV2` (cifras exactas, como texto) y usa `stats` solo como respaldo.
2. **Publicaciones.** TikTok las carga con una petición interna que lleva parámetros firmados por su propio JavaScript. En vez de falsificar esa firma, el script abre el perfil en Chromium con Playwright y guarda la respuesta que la página recibe.
3. **Captcha.** Si detecta un captcha visible, espera a que se resuelva y recarga la página una vez para que se pidan las publicaciones. Usa una sesión persistente del navegador en `.perfil_navegador/`.
4. **Orden.** Junta las respuestas sin duplicados y las ordena por fecha de creación, porque las publicaciones fijadas pueden ser antiguas.
5. **Medios (opcional).** Con `--media` descarga cada archivo usando la sesión del propio navegador y el encabezado `Referer`.

Funciones principales:

| Función | Qué hace |
|---|---|
| `descargar_html` | Pide la página del perfil con `requests`. |
| `extraer_estado` | Saca el JSON incrustado en el HTML. |
| `extraer_perfil` | Obtiene las cifras y datos del perfil. |
| `obtener_posts` | Abre Chromium, espera el captcha y captura `item_list`. |
| `hay_captcha` | Detecta un captcha visible en la página. |
| `armar_posts` | Junta y ordena las publicaciones. |
| `normalizar_post` | Convierte cada publicación en un diccionario simple. |
| `extraer_medios` | Obtiene los enlaces de video, portada o imágenes. |
| `descargar_medios` | Guarda los archivos en `media\`. |
| `mostrar` | Imprime el perfil y la tabla en la consola. |

Las publicaciones de imágenes (carruseles) se detectan por el campo `imagePost` y su enlace usa `/photo/` en lugar de `/video/`.

Estructura del archivo `datos\salida_<usuario>.json`:

- `perfil`: usuario, nombre, verificado, privada, biografía, enlace de la bio, idioma, región, fecha de creación, seguidores, siguiendo, likes totales y videos.
- `publicaciones`: por cada una, id, tipo, url, fecha, descripción, hashtags, música, duración, si está fijada, vistas, likes, comentarios, compartidos, guardados, interacciones y `medios` (video, portada, imágenes). Con `--media` se añade `archivos` con las rutas descargadas.
- `corpus_texto`: la biografía y las descripciones juntas, listo para el análisis.

### 6.2 `src/analisis.py`

Usa solo la biblioteca estándar de Python y no llama a servicios externos. Las constantes están al inicio del archivo y se pueden ajustar.

**Big Five heurístico.** Busca en el texto raíces de palabras del diccionario `src/lexico_es.json`, con una lista "alto" y otra "bajo" por rasgo. Antes de comparar, pasa el texto a minúsculas y le quita las tildes. Para cada rasgo, con `a` aciertos de la lista alta y `b` de la baja:

```
puntaje = 50 + 50 * (a - b) / (a + b + 3)
```

- Sin ningún acierto el puntaje es 50 (neutro).
- El 3 del denominador acerca el resultado a 50 cuando hay poca evidencia.
- La **confianza del texto** es `min(1, palabras / 300)`. Con menos de 100 palabras el script avisa de que los puntajes son poco fiables.
- Para cada rasgo se guardan también las palabras que sumaron o restaron, así se puede comprobar de dónde sale el puntaje.

**Valor (alcance e influencia):**

```
valor = 100 * (0.40 * interacción + 0.35 * alcance + 0.25 * seguidores)
```

| Componente | Cálculo | Referencia |
|---|---|---|
| interacción | mediana de `interacciones / vistas`, dividida entre 0.10 | 10 % se toma como "muy alta" |
| alcance | `log10(1 + vistas medianas) / 6` | 1 millón de vistas = 1 |
| seguidores | `log10(1 + seguidores) / 7` | 10 millones = 1 |

Cada componente se limita a 1.

**Veracidad (autenticidad aparente de la cuenta).** Se interpreta como qué tan coherentes son las métricas con un comportamiento orgánico. No mide si la persona dice la verdad.

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

Los pesos y las referencias son supuestos del proyecto, no valores establecidos. Conviene validarlos con quien califica el trabajo.

### 6.3 `src/lexico_es.json`

Cada rasgo tiene una lista `alto` y una `bajo`. Cada entrada es una raíz: coincide con cualquier palabra que empiece así (por ejemplo, `celebr` encuentra "celebramos" y "celebración"). Es un diccionario mínimo de demostración, no está validado psicométricamente. Para ampliarlo, se agregan raíces en las listas y se anota el cambio en este README.

### 6.4 IA local con Ollama

**Por qué local.** Las opciones gratuitas de API en la nube implican enviar el texto de las cuentas a un tercero. En el plan gratuito de la API de Gemini, la documentación de Google indica que el contenido se usa para mejorar sus productos, lo que no es adecuado para datos de terceros. Un modelo local es gratuito sin tarjeta ni cuenta, no tiene límites de uso, funciona sin internet durante la demostración y no hay ningún token que pueda filtrarse. El costo es la velocidad y que un modelo pequeño es menos capaz que uno en la nube.

**Qué hace.**

1. `ia.py` habla con Ollama por su API local (`/api/chat` en `localhost:11434`) y lee la configuración de `.env`.
2. La estimación Big Five se pide con un esquema JSON fijo: por rasgo, si es determinable, un puntaje de 0 a 100, la confianza y hasta 3 citas del texto.
3. El texto de la cuenta se entrega como dato, con la instrucción de ignorar órdenes que aparezcan dentro, para que una biografía no pueda dar instrucciones al modelo.
4. **Verificación de citas.** Cada cita que devuelve el modelo debe aparecer en el texto original. Las que no aparecen se descartan, y si un rasgo se queda sin ninguna cita válida pasa a "no determinable". El resultado guarda cuántas citas se descartaron.
5. Los puntajes se acotan entre 0 y 100.

**Límites.** Un modelo de lenguaje puede sonar seguro con muy poca evidencia, y la verificación de citas comprueba que el texto exista, no que la interpretación sea correcta. Un modelo pequeño tiene más errores. La estimación no es una evaluación psicológica y debe presentarse con la evidencia y el modelo usado. El asistente puede equivocarse al leer cifras: conviene contrastar sus respuestas con los archivos.

## 7. Archivos que genera el proyecto

| Ruta | Contenido | ¿Va a Git? |
|---|---|---|
| `datos/salida_<usuario>.json` | Perfil, publicaciones y `corpus_texto` | No |
| `resultados/` | Análisis por usuario, `resumen.csv` y estimaciones de la IA (`ia_<usuario>.json`) | No |
| `muestras/` | Respuestas crudas de TikTok (solo con `--debug`) | No |
| `media/` | Videos e imágenes (solo con `--media`) | No |
| `.perfil_navegador/` | Cookies, historial y caché del navegador | No, nunca |
| `.env` | Configuración local de la IA | No, nunca (se sube `.env.example`) |

## 8. Estado de verificación

Esta tabla separa lo que se comprobó ejecutándolo de lo que aún no. Debe actualizarse a medida que se verifique cada punto.

| Función | Estado | Observación |
|---|---|---|
| Lectura del perfil con cifras exactas desde `statsV2` | Verificado | Octubre de 2026. |
| Captura de las 10 últimas publicaciones con sus métricas | Verificado | Con `--visible` y captcha resuelto a mano. |
| Distinción entre video e imagen | Verificado | Aparecieron publicaciones de imágenes en cuentas de prueba. |
| Instalación desde cero en una segunda máquina Windows | Verificado | Clonado, entorno virtual, dependencias y Chromium. |
| `analisis.py` con una salida real del scraper | Verificado | En una cuenta con poco texto: confianza baja y aviso de texto corto. |
| Biografía, hashtags, música, duración y enlaces de medios con datos reales | Pendiente | Hay que revisar los campos en el JSON y compararlos con la página. |
| Descarga de archivos con `--media` | Pendiente | Solo se probó con una descarga simulada. |
| `ia.py`, `ia_big_five.py` y `asistente.py` con un Ollama simulado | Verificado | 13 pruebas automáticas y una corrida completa contra un servidor simulado. |
| Los mismos programas con Ollama y un modelo real | Pendiente | Hay que instalar Ollama, descargar el modelo y comprobar tiempos y calidad. |
| Ejecución sin `--visible` sin que aparezca captcha | No se logró | Sin ventana el captcha no se puede resolver. |

Entorno de las pruebas verificadas: Windows, Python 3.14, Playwright 1.64.0, Chromium 156.0.8078.4, Git 2.51.2.

Después de cada ejecución conviene comprobar:

1. Abrir el perfil en el navegador y comparar seguidores y seguidos con la consola. Pueden diferir en unidades porque cambian en vivo.
2. Abrir uno o dos enlaces del campo `url` y comparar likes y comentarios con la página.
3. Revisar en el JSON que `biografia`, `hashtags` y `medios` tengan contenido. Si alguno sale vacío, repetir con `--debug` y buscar el campo en `muestras\`:

   ```bat
   findstr /i "signature textExtra playAddr imageURL" muestras\<usuario>_item_list_1.json
   ```

4. Después de `analisis.py`, leer los avisos del resultado: indican texto corto o pocas publicaciones.

## 9. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Python was not found; run without arguments to install from the Microsoft Store` | El atajo de la Microsoft Store intercepta el comando | Desactivar los alias de `python.exe` y `python3.exe` en Configuración, Aplicaciones, Configuración avanzada de aplicaciones, Alias de ejecución de aplicaciones. Abrir una consola nueva. |
| `'python' is not recognized` o `'code' is not recognized` | El PATH no se actualizó | Cerrar la consola y abrir una nueva. Si sigue, reinstalar marcando la opción de PATH. |
| `'Remove-Item' is not recognized` (y similares) | Comandos de PowerShell usados en `cmd` | En `cmd`: `del`, `ren`, `copy`. En PowerShell: `Remove-Item`, `Rename-Item`, `Copy-Item`. |
| `can't open file '...\src\scraper.py'` | Se está en una carpeta que no es la raíz del repo | Entrar a la carpeta que contiene `src` y volver a ejecutar. |
| `Falta Playwright` o `ModuleNotFoundError` | Faltan dependencias, o se usa un entorno virtual que no está activo | Ejecutar `pip install -r requirements.txt` (y `venv\Scripts\activate` antes, si se usa un entorno virtual). |
| `ENOTFOUND` al instalar Chromium | El servidor espejo no se resuelve | Es normal si luego dice "downloaded" (paso 3 de la sección 4). |
| `[captcha] detectado; vuelve a correr con --visible` | Sin ventana el captcha no se puede resolver | Ejecutar con `--visible`. |
| `ÚLTIMAS 0 PUBLICACIONES` | Captcha sin resolver, o TikTok devolvió la lista vacía | Repetir con `--visible --debug --espera 180`, resolver el captcha y revisar `muestras\`. |
| `[media] ... HTTP 403` | TikTok rechazó la descarga | Anotarlo como hallazgo con captura. Probar con otra publicación. |
| `No se pudo conectar con Ollama` | Ollama no está abierto o no está instalado | Abrir la aplicación de Ollama y comprobar con `ollama list`. |
| `El modelo '...' no está descargado` | Falta bajar el modelo | Ejecutar `ollama pull <modelo>` con el nombre que indica el mensaje. |
| `Ollama no respondió en N s` | El modelo es muy grande para el equipo | Probar un modelo más pequeño o subir `OLLAMA_TIMEOUT` en `.env`. |
| Muchos rasgos salen `no determinable` | El texto es corto o el modelo no encuentra evidencia en él | Es lo esperado con poco texto; probar una cuenta con más descripciones. |
| Seguidores o likes con ceros al final (por ejemplo 60,300) | Se leyeron las cifras redondeadas de `stats` | El código usa `statsV2`. Si reaparece, revisar `extraer_perfil` y el JSON de `muestras\`. |
| `git add .` agrega `.perfil_navegador/` | El `.gitignore` no se llama exactamente `.gitignore` | Renombrarlo con el punto inicial, deshacer con `git rm -r --cached . -q` y repetir `git add .`. |
| PowerShell: "la ejecución de scripts está deshabilitada" al activar el entorno | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, una sola vez. En `cmd` no ocurre. |

## 10. Privacidad y uso responsable

- Una cuenta pública sigue siendo información personal. Conviene usar cuentas de negocios o de personas que den su permiso.
- Analizar la personalidad de alguien es un uso sensible. La ley de protección de datos personales de Ecuador podría aplicar; no es asesoría legal, hay que consultarlo con el docente.
- La IA corre en la propia computadora: el texto de las cuentas no se envía a ningún tercero. Si algún día se cambia a un servicio en la nube, hay que revisar si usa los datos para entrenamiento, y no pegar nunca un token en el chat ni subirlo a Git.
- Los términos de TikTok restringen la extracción automatizada: pocas consultas y solo con fines académicos.
- No se resuelven captchas de forma automática.
- Los datos, resultados, videos e imágenes se quedan en la máquina local y no se suben al repositorio. Borrarlos cuando termine la demostración.

## 11. Limitaciones

- **Captcha:** TikTok puede mostrarlo a visitantes sin sesión y hay que resolverlo a mano.
- **Estructura de la página:** las rutas del JSON pueden cambiar sin aviso.
- **Cifras:** son las que TikTok entrega en el momento y cambian con el tiempo.
- **Big Five:** el diccionario es mínimo; una misma palabra repetida en varias publicaciones cuenta cada vez y puede inflar un rasgo; no interpreta ironía ni contexto; en cuentas de negocio el texto describe a la marca y no a una persona. No se analizan rostros ni voz.
- **Valor y veracidad:** los pesos y referencias son supuestos. Un puntaje bajo de veracidad es una razón para mirar la cuenta con más cuidado, no una conclusión; una cuenta real puede tener poca cobertura por razones normales.
- **IA:** un modelo pequeño local es menos capaz que uno en la nube, puede equivocarse y sonar seguro, y la verificación de citas solo comprueba que el texto citado exista.
- **Resultados:** son estimaciones exploratorias, no una evaluación psicológica ni una prueba de que una cuenta sea falsa.

## 12. Flujo con Git

1. Antes de cada commit:

   ```bat
   git add .
   git status --short
   ```

   Solo deben aparecer archivos de código y documentación. Si aparece algo de `.perfil_navegador/`, `datos/`, `muestras/`, `media/` o `resultados/`, no hacer commit.

2. Confirmar que la sesión del navegador queda ignorada:

   ```bat
   git check-ignore -v .perfil_navegador
   ```

3. Commit y subida:

   ```bat
   git commit -m "Descripción del cambio"
   git push
   ```

## 13. Limpieza y reversión

- Borrar datos locales: `rmdir /s /q datos resultados muestras media`
- Cerrar la sesión del navegador: `rmdir /s /q .perfil_navegador` (el captcha puede reaparecer).
- Deshacer un `git add` equivocado: `git rm -r --cached . -q`
- Volver al último commit en un archivo: `git restore src\scraper.py`

## 14. Evidencias para el informe

Reunir solo evidencia real, con fecha. No documentar lo que no se comprobó.

1. Captura del perfil en el navegador, junto a la salida de consola de la misma hora.
2. Captura del captcha.
3. Verificación manual de al menos dos publicaciones (captura de la página y fila de la tabla).
4. Fragmento del JSON crudo donde se vean `stats` y `statsV2`, que respalda la corrección de las cifras redondeadas.
5. Salida de `python --version` y `pip show playwright`.
6. Resultado de `python -m unittest discover -s tests`.
7. Si se usa `--media`: la salida de consola, incluidos los errores de descarga.
8. `resultados\resumen.csv` y los avisos de cada análisis.
9. Si se usa la IA: la salida de `ollama list`, la de `ia_big_five.py` (con las evidencias y el modelo usado) y una conversación de ejemplo con el asistente.
