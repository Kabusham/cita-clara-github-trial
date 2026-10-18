# Cita Clara · prueba gratuita con GitHub

Versión de prueba independiente de `Citasasilo` y sin Render.

## Qué hace esta versión

- Publica una interfaz completamente en español en GitHub Pages.
- Permite seleccionar provincia, localidad, «Cualquier oficina» o una oficina y el trámite del directorio incluido.
- Guarda el registro local de clientes cifrado en el navegador mediante AES-GCM y PBKDF2. No hay cuenta compartida ni recuperación de clave; los datos se quedan en ese navegador.
- Al preparar una búsqueda, abre un formulario de GitHub Issue con solo provincia, localidad, oficina, trámite e intervalo de fechas. El nombre, teléfono, documento y notas del cliente no se envían.
- GitHub Actions se programa cada 10 minutos y mantiene el historial en comentarios del Issue. Para recibir avisos opcionales, configura `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en Settings → Secrets and variables → Actions.
- La ejecución se detiene ante CAPTCHA, petición de verificación humana, bloqueo, respuesta 429 o cambio inesperado del formulario. No reserva citas ni elude medidas del portal.

## Limitación actual: integración oficial todavía no verificada

`config/recipes.json` está vacío a propósito. El enlace oficial informativo abre, pero la consulta de `Acceder al procedimiento` a ICP+ agotó el tiempo de espera en la comprobación disponible. Por eso el flujo automático dejará un comentario indicando que el trámite todavía no se verificó y no afirmará que buscó disponibilidad.

El evento manual «Comprobar acceso al portal oficial» solo comprueba si GitHub Actions puede abrir la página y localizar el enlace oficial. No selecciona provincias/trámites ni comprueba citas. Solo después de verificar de verdad una receta se puede añadir a `config/recipes.json` con `verified: true`.

## Publicación gratuita

1. El código está en el repositorio público `Kabusham/cita-clara-github-trial`. Pages en GitHub Free requiere un repositorio público.
2. En Settings → Pages, selecciona **GitHub Actions** como fuente. Si Pages no aparece activo, habilítalo desde esa sección.
3. En Actions, ejecuta `Publicar interfaz Cita Clara`. La dirección será `https://TU-USUARIO.github.io/cita-clara-github-trial/`.
4. Ejecuta manualmente `Prueba gratuita de búsqueda` con `probe_portal` activado. Consulta el resultado del workflow.
5. Para alertas Telegram, configura los dos secretos mencionados arriba. No pongas claves en archivos del repositorio.
6. Crea una solicitud en la página y abre el enlace «Preparar criterios de búsqueda en GitHub». Comprueba que el Issue solo contiene los criterios y nunca datos personales.

## Coste y límites

No crea servicios de pago. Las ejecuciones estándar de Actions son gratuitas en repositorios públicos. GitHub puede retrasar o dejar de programar ejecuciones en momentos de carga; cada 10 minutos es el intervalo solicitado, no una garantía de puntualidad. Esta prueba no es una base de datos multiusuario: la información personal solo existe en el navegador local cifrado y los criterios publicados en Issues son visibles públicamente.

## Validación local

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m py_compile scripts/monitor.py scripts/probe_portal.py portal.py
node --check site/app.js
```
