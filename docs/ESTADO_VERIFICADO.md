# Estado verificado de Cita Clara

Fecha de comprobación: 22/10/2026, 01:53 (Europe/Madrid).

## Comprobación real desde GitHub Actions

Ejecución: https://github.com/Kabusham/cita-clara-github-trial/actions/runs/39696147967

| Componente | Resultado observado |
| --- | --- |
| Ubuntu 24.04 y Chromium de Playwright | Instalación completada |
| Página informativa oficial de extranjería | HTTP 200 |
| Enlace «Acceder al procedimiento» | Localizado en la página oficial |
| Entrada ICP+ | Sin respuesta inicial antes del límite de 45 segundos |
| Provincias comprobadas dentro de ICP+ | Ninguna |
| Trámites con disponibilidad comprobada | Ninguno |

No se ha demostrado que la causa del tiempo de espera sea un bloqueo de IP.
La prueba no envió datos personales, no reservó citas y no eludió verificaciones.

## Alcance actual

- Interfaz en español publicada mediante GitHub Pages.
- Datos privados cifrados con AES-GCM en el navegador, protegidos por una clave derivada con PBKDF2.
- Los datos no se sincronizan entre dispositivos ni se entregan al propietario del sitio.
- La clave local no sustituye un sistema de cuentas o autenticación de servidor.
- Los criterios enviados como GitHub Issues son públicos y excluyen datos personales.
- El monitor solo procesa solicitudes creadas por el propietario del repositorio.
- La programación solicita ejecuciones cada 10 minutos; no garantiza su puntualidad.
- El catálogo de oficinas no es evidencia de disponibilidad ni de trámites verificados en ICP+.
- El archivo config/recipes.json sigue vacío: no hay ninguna integración de búsqueda verificada.
- Telegram tiene código de integración, pero no se ha verificado aquí el envío de avisos.
- Los campos de teléfono y correo son de contacto local. No activan avisos de WhatsApp ni correo.

## Trabajo pendiente para una búsqueda real

Se necesita obtener acceso normal al formulario oficial y comprobar una combinación de provincia,
oficina y trámite de principio a fin antes de habilitarla. Si se requieren datos personales
en el servidor, debe añadirse un canal privado autenticado; nunca deben publicarse en Issues,
el repositorio, los registros de ejecución o los artefactos públicos.
