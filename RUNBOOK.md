# Runbook: extracción y análisis heurístico de perfiles de TikTok

Procedimiento para instalar, ejecutar y verificar el proyecto en Windows. Los comandos están escritos para `cmd` (el prompt sin "PS" al inicio). Se ejecutan desde la raíz del repositorio.

## 1. Propósito y alcance

- **Extraer** de un perfil público: seguidores, seguidos, biografía, últimas publicaciones con sus interacciones y enlaces de medios. Opcionalmente, descargar videos e imágenes.
- **Analizar** lo extraído: Big Five heurístico, índice de valor e índice de veracidad (ver `docs/metodologia.md`).
- Restricciones: sin extensiones de navegador, sin APIs existentes, sin credenciales propias. El único dato de entrada es el usuario de la cuenta.

## 2. Estado de verificación

Esta tabla separa lo que se comprobó ejecutándolo de lo que aún no. Actualízala a medida que se verifique cada punto, y adjunta las capturas reales antes de entregar.

| Función | Estado | Observación |
|---|---|---|
| Lectura del perfil (seguidores, seguidos, videos, likes) con cifras exactas desde `statsV2` | Verificado | Ejecuciones del 20 y 21 de octubre de 2026. |
| Captura de las 10 últimas publicaciones con sus métricas | Verificado | Con `--visible` y captcha resuelto a mano. |
| Distinción entre publicaciones de video y de imágenes | Verificado | Una cuenta de prueba mostró una publicación de imágenes. |
| Instalación desde cero en una segunda máquina Windows | Verificado | Clonado del repositorio, entorno virtual, dependencias y Chromium. |
| Biografía, hashtags, música, duración y enlaces de medios con datos reales | Pendiente | Se probó solo con datos sintéticos. |
| Descarga de archivos con `--media` | Pendiente | Se probó solo con una descarga simulada. |
| `analisis.py` con salidas reales del scraper | Pendiente | Las pruebas automáticas con datos sintéticos pasan (12 de 12). |
| Ejecución sin `--visible` sin que aparezca captcha | No se logró | Sin ventana visible el captcha no se puede resolver. |

Entorno de las pruebas verificadas: Windows, Python 3.14, Playwright 1.64.0, Chromium 156.0.8078.4, Git 2.51.2.

## 3. Requisitos

- Windows 10 u 11, conexión a internet.
- Git.
- Python 3.10 o superior (probado con 3.14), con "Add python.exe to PATH" marcado al instalar.
- VS Code (opcional, para editar).
- Unos 600 MB libres para el navegador de Playwright.

## 4. Instalación

1. Comprobar las herramientas:

   ```bat
   git --version
   python --version
   ```

2. Clonar y entrar al proyecto:

   ```bat
   git clone <URL-del-repositorio>
   cd tiktok-bigfive
   ```

3. Crear y activar el entorno virtual. El prompt debe mostrar `(venv)`:

   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```

4. Instalar las dependencias y el navegador:

   ```bat
   pip install -r requirements.txt
   playwright install chromium
   ```

   Durante la descarga puede aparecer `ENOTFOUND playwright.download.prss.microsoft.com`. Es un servidor espejo que la red no resuelve. Playwright reintenta con otra dirección; si al final cada componente dice "downloaded", no hay que repetir nada.

5. Comprobar que las pruebas automáticas pasan:

   ```bat
   python -m unittest discover -s tests
   ```

   Debe terminar con `OK`.

## 5. Operación

### 5.1 Extraer un perfil

```bat
python src\scraper.py nombre_usuario --visible
```

- Escribir el usuario sin `@`.
- Si aparece un captcha, resolverlo en la ventana. El script espera 120 segundos por defecto (`--espera 180` para más) y sigue solo.
- La sesión anónima del navegador se guarda en `.perfil_navegador/` y reduce las veces que reaparece el captcha.
- Opciones útiles: `--debug` (guarda el JSON crudo en `muestras/`) y `-n 5` (cantidad de publicaciones).

Resultado: consola con el perfil y una tabla de publicaciones, y el archivo `datos/salida_<usuario>.json`. Cada ejecución con el mismo usuario sobrescribe ese archivo; para conservar una corrida, copiarlo antes con otro nombre.

### 5.2 Extraer con videos e imágenes

```bat
python src\scraper.py nombre_usuario --visible --media -n 3
```

- Descarga a `media\<usuario>\`. Los enlaces están firmados y caducan en horas, por eso se descargan en la misma ejecución.
- Empezar con pocas publicaciones: los videos pesan.
- Si una descarga falla se imprime `[media] ... HTTP <código>` y se continúa con las demás.

### 5.3 Analizar

```bat
python src\analisis.py
```

Sin argumentos analiza todos los `datos\salida_*.json`. También acepta un archivo concreto:

```bat
python src\analisis.py datos\salida_nombre_usuario.json
```

Resultado: `resultados\analisis_<usuario>.json` por cuenta y `resultados\resumen.csv` con todas.

### 5.4 Varios usuarios seguidos

```bat
for %u in (usuario1 usuario2 usuario3) do python src\scraper.py %u --visible
python src\analisis.py
```

Dentro de un archivo `.bat` el `%u` se escribe `%%u`.

## 6. Archivos que genera el proyecto

| Ruta | Contenido | ¿Va a Git? |
|---|---|---|
| `datos/salida_<usuario>.json` | Perfil, publicaciones y `corpus_texto` | No |
| `resultados/` | Análisis por usuario y `resumen.csv` | No |
| `muestras/` | Respuestas crudas de TikTok (solo con `--debug`) | No |
| `media/` | Videos e imágenes (solo con `--media`) | No |
| `.perfil_navegador/` | Cookies, historial y caché del navegador | No, nunca |

## 7. Verificación después de una ejecución

1. Abrir el perfil en el navegador y comparar seguidores y seguidos con la consola. Los números pueden diferir en unidades porque cambian en vivo.
2. Abrir uno o dos enlaces de `url` del JSON y comparar likes y comentarios con la página.
3. En `datos/salida_<usuario>.json`, revisar que `biografia`, `hashtags` y `medios` tengan contenido. Si alguno sale vacío, repetir con `--debug` y buscar el campo en `muestras\`:

   ```bat
   findstr /i "signature textExtra playAddr imageURL" muestras\<usuario>_item_list_1.json
   ```

4. Después de `analisis.py`, revisar los `avisos` del resultado: indican texto corto o pocas publicaciones.

## 8. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Python was not found; run without arguments to install from the Microsoft Store` | El atajo de la Microsoft Store intercepta el comando | Desactivar los alias de `python.exe` y `python3.exe` en Configuración, Aplicaciones, Configuración avanzada de aplicaciones, Alias de ejecución de aplicaciones. Abrir una consola nueva. |
| `'code' is not recognized` o `'python' is not recognized` | El PATH no se actualizó | Cerrar la consola y abrir una nueva. Si sigue, reinstalar marcando la opción de PATH. |
| `'Remove-Item' is not recognized` (y similares) | Comandos de PowerShell usados en `cmd` | En `cmd`: `del`, `ren`, `copy`. En PowerShell: `Remove-Item`, `Rename-Item`, `Copy-Item`. |
| `Falta Playwright` o `ModuleNotFoundError` | El entorno virtual no está activo o faltan dependencias | Ejecutar `venv\Scripts\activate` y `pip install -r requirements.txt`. |
| `ENOTFOUND` al instalar Chromium | El servidor espejo no se resuelve | Ver el paso 4.4: es normal si luego dice "downloaded". |
| `[captcha] detectado; vuelve a correr con --visible` | Sin ventana el captcha no se puede resolver | Ejecutar con `--visible`. |
| `ÚLTIMAS 0 PUBLICACIONES` | Captcha sin resolver, o TikTok devolvió la lista vacía | Repetir con `--visible --debug --espera 180`, resolver el captcha y revisar `muestras\`. |
| `[media] ... HTTP 403` | TikTok rechazó la descarga | Anotarlo como hallazgo con captura. Probar con otra publicación o repetir en la misma sesión del navegador. |
| Seguidores o likes con ceros al final (60,300) | Se leyeron las cifras redondeadas de `stats` | El código usa `statsV2` (exactas). Si reaparece, revisar `extraer_perfil` y el JSON de `muestras\`. |
| `git add .` agrega `.perfil_navegador/` | El `.gitignore` no se llama exactamente `.gitignore` | Renombrarlo con el punto inicial, deshacer con `git rm -r --cached . -q` y repetir `git add .`. |
| PowerShell: "la ejecución de scripts está deshabilitada" al activar el entorno | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, una sola vez. |

## 9. Privacidad y uso responsable

- Usar cuentas de negocios o de personas que den su permiso. Una cuenta pública sigue siendo información personal.
- Los términos de TikTok restringen la extracción automatizada: pocas consultas, solo con fines académicos.
- No resolver captchas de forma automática: se resuelven a mano.
- Los datos, resultados, videos e imágenes se quedan en la máquina local. Borrarlos cuando termine la demostración.
- Analizar la personalidad de alguien es un uso sensible; la ley de protección de datos de Ecuador podría aplicar. Consultarlo con el docente.

## 10. Flujo con Git

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

## 11. Limpieza y reversión

- Borrar datos locales: `rmdir /s /q datos resultados muestras media`
- Cerrar la sesión del navegador: `rmdir /s /q .perfil_navegador` (el captcha puede reaparecer).
- Deshacer un `git add` equivocado: `git rm -r --cached . -q`
- Volver al último commit en un archivo: `git restore src\scraper.py`

## 12. Evidencias para el informe

Reunir solo evidencia real, con fecha. No documentar lo que no se comprobó.

1. Captura del perfil en el navegador, junto a la salida de consola de la misma hora.
2. Captura del captcha.
3. Verificación manual de al menos dos publicaciones (captura de la página y fila de la tabla).
4. Fragmento del JSON crudo donde se vean `stats` y `statsV2`, que respalda la corrección de las cifras redondeadas.
5. Salida de `python --version` y `pip show playwright`.
6. Resultado de `python -m unittest discover -s tests`.
7. Si se usa `--media`: la salida de consola, incluidos los errores de descarga.
8. `resultados\resumen.csv` y los avisos de cada análisis.
