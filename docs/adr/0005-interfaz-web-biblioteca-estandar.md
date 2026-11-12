# ADR 0005 — Interfaz web con la biblioteca estándar y no con un framework

- **Estado:** aceptado
- **Ámbito:** `web/`

## Contexto

La demo se maneja desde la terminal y hay que editar el código para cambiar los activos, los
pesos o los supuestos de la simulación. Una página web permite probar todas sus funciones sin
programar. Se valoraron Streamlit y Flask, que simplifican la página pero son dependencias nuevas.

## Decisión

La interfaz es un servidor `http.server` de la biblioteca estándar que sirve una página HTML con
JavaScript sin librerías y una API JSON (`/api/<acción>`): catálogo y buscador, datos, cartera,
correlación, Monte Carlo, informe, gráficos y series macro. Los gráficos interactivos se dibujan
en SVG con JavaScript propio, sin librerías externas. Se arranca con `python -m market_toolkit.web`.

## Justificación

- **Plug-and-play (apartado 4.1).** No añade ninguna dependencia ni obliga a instalar nada, y la
  página no carga nada de internet: funciona sin conexión con datos sintéticos.
- **La lógica no depende de la web.** `Aplicacion` tiene un método por acción y devuelve
  diccionarios. Los tests la prueban directamente y el servidor solo traduce HTTP a esos métodos.
- **Seguro por defecto.** Escucha solo en `127.0.0.1`, comprueba la cabecera `Host` y exige
  `Content-Type: application/json`, lo que impide que otra web abierta en el navegador use el
  servidor local.

## Consecuencias

- Hay una sola sesión: el estado (datos y cartera) vive en el proceso, y varias pestañas
  comparten la misma cartera. Es una herramienta local, no un servicio.
- El servidor atiende una petición cada vez (sin hilos), porque matplotlib no es seguro entre
  hilos. Una simulación grande bloquea la página hasta terminar.
- Hace falta mantener a mano el JavaScript de los gráficos; a cambio, la página tiene todas las
  funciones de la demo y no depende de ninguna librería.
