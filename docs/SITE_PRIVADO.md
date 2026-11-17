# Panel privado de Cita Clara

[Panel de solicitudes](https://khalil-citas-desk.kabusham.chatgpt.site) y
[ejecuciones del monitor](https://github.com/Kabusham/cita-clara-github-trial/actions/workflows/cita-clara-site.yml).

El Site guarda los datos de los solicitantes cifrados. GitHub Actions recibe
por HTTPS únicamente provincia, localidad, oficina, trámite e intervalo de
búsqueda. El envío de notificaciones reutiliza `TELEGRAM_BOT_TOKEN` y
`TELEGRAM_CHAT_ID`. Los mensajes son genéricos. El estado público
`cita-clara/site` describe solo la comprobación del canal de Telegram.

## Activar la conexión privada

Guarda la credencial de servicio del Site en
**Settings → Secrets and variables → Actions → New repository secret**
con el nombre `CITA_CLARA_SITE_ACCESS`. Usa el valor sin el prefijo
`Bearer`. La credencial se envía a la URL fija del Site en la cabecera
`OAI-Sites-Authorization`; el Site comprueba además la identidad OIDC
del workflow y su rama. Mantén la credencial en el gestor de secretos.

Ejecuta **Cita Clara · Site privado → Run workflow** en la rama `main`.
Al sincronizarse aparece la hora de conexión en el panel. Si Telegram
es accesible, en la página de avisos puedes solicitar una prueba de envío.
El monitor también se ejecuta en segundo plano. GitHub puede retrasar las
ejecuciones programadas.

Las recetas siguen sujetas a su comprobación real en ICP+. El historial
solo suma un intento al iniciar la consulta al portal. Se detiene el
seguimiento ante un bloqueo o un resultado no concluyente. Si el trámite
requiere nombre o documento en el portal, se deriva a revisión manual.
La confirmación de que se reservó una cita se registra al revisar el
justificante oficial en el Site.
