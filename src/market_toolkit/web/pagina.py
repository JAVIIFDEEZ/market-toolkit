"""Página única de la interfaz web (HTML, CSS y JavaScript sin dependencias externas)."""

PAGINA = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>market-toolkit</title>
<style>
:root {
  --fondo:#f4f6f9; --tarjeta:#ffffff; --texto:#18202b; --suave:#5b6676; --borde:#dde2ea;
  --acento:#1f5fbf; --acento-suave:#e7effb; --error:#b3261e; --error-suave:#fdecea;
  --aviso:#8a5a00; --aviso-suave:#fff5dc; --ok:#1b7a3f; --ok-suave:#e6f4ea;
  --sombra:0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.08);
}
:root[data-tema="oscuro"] {
  --fondo:#11151c; --tarjeta:#1a2029; --texto:#e6e9ee; --suave:#9aa5b5; --borde:#2c3542;
  --acento:#6ea2f0; --acento-suave:#1f2d44; --error:#f2867e; --error-suave:#3a1f1d;
  --aviso:#f0c060; --aviso-suave:#3a3020; --ok:#6fcf97; --ok-suave:#1d3326;
  --sombra:none;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--fondo); color:var(--texto);
       font:15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.contenedor { max-width:1180px; margin:0 auto; padding:0 16px; }
header { background:var(--tarjeta); border-bottom:1px solid var(--borde); }
header .contenedor { display:flex; align-items:center; gap:16px; padding-top:14px;
                     padding-bottom:14px; flex-wrap:wrap; }
h1 { margin:0; font-size:21px; letter-spacing:-.01em; }
header p { margin:0; color:var(--suave); font-size:13px; }
.espacio { flex:1; }
.insignia { font-size:12px; padding:3px 10px; border-radius:999px; background:var(--acento-suave);
            color:var(--acento); font-weight:600; }
nav { position:sticky; top:0; z-index:10; background:var(--fondo);
      border-bottom:1px solid var(--borde); }
nav .contenedor { display:flex; gap:4px; overflow-x:auto; }
nav button { background:none; color:var(--suave); border:0; border-bottom:3px solid transparent;
             border-radius:0; padding:12px 14px; font-weight:600; white-space:nowrap; }
nav button.activa { color:var(--acento); border-bottom-color:var(--acento); }
nav button:disabled { opacity:.4; cursor:not-allowed; }
nav button .num { display:inline-block; width:20px; height:20px; line-height:20px;
                  border-radius:50%; background:var(--borde); color:var(--texto);
                  font-size:12px; text-align:center; margin-right:6px; }
nav button.hecha .num { background:var(--ok); color:#fff; }
main { padding:18px 0 60px; }
.panel { display:none; } .panel.visible { display:block; }
.tarjeta { background:var(--tarjeta); border:1px solid var(--borde); border-radius:10px;
           padding:16px 18px; margin-bottom:16px; box-shadow:var(--sombra); }
.tarjeta h2 { margin:0 0 4px; font-size:17px; }
.tarjeta h3 { margin:14px 0 6px; font-size:14px; }
.tarjeta > .nota:first-of-type { margin-top:0; }
.rejilla { display:grid; gap:16px; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); }
.fila { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; margin:10px 0; }
label { display:flex; flex-direction:column; font-size:12px; color:var(--suave); gap:3px;
        font-weight:600; }
label.check { flex-direction:row; align-items:center; gap:6px; color:var(--texto);
              font-size:14px; font-weight:400; }
input, select { font:inherit; padding:7px 9px; border:1px solid var(--borde); border-radius:6px;
                background:var(--tarjeta); color:var(--texto); }
input:focus, select:focus { outline:2px solid var(--acento); outline-offset:-1px; }
input[type=number] { width:110px; } input[type=date] { width:150px; }
input[type=range] { padding:0; accent-color:var(--acento); }
button { font:inherit; padding:8px 16px; border:0; border-radius:6px; cursor:pointer;
         background:var(--acento); color:#fff; font-weight:600; }
button.secundario { background:transparent; color:var(--acento);
                    border:1px solid var(--acento); padding:7px 14px; }
button.pequeno { padding:4px 10px; font-size:13px; }
button:disabled { opacity:.55; cursor:wait; }
.nota { color:var(--suave); font-size:13px; margin:6px 0; }
.mensajes div { padding:8px 12px; border-radius:6px; margin:8px 0; font-size:14px; }
.mensajes .error { background:var(--error-suave); color:var(--error); }
.mensajes .aviso { background:var(--aviso-suave); color:var(--aviso); }
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; font-size:13px;
        border:1px solid var(--borde); border-radius:999px; background:var(--tarjeta);
        color:var(--texto); cursor:pointer; font-weight:500; }
.chip small { color:var(--suave); }
.chip.elegido { background:var(--acento); border-color:var(--acento); color:#fff; }
.chip.elegido small { color:#dce7fb; }
.chip .quitar { font-weight:700; }
.seleccion { min-height:42px; padding:8px; border:1px dashed var(--borde); border-radius:8px; }
.vacio { color:var(--suave); font-size:13px; padding:4px; }
.buscador { position:relative; flex:1; min-width:260px; }
.buscador input { width:100%; }
.sugerencias { position:absolute; left:0; right:0; top:100%; z-index:20; margin-top:4px;
               background:var(--tarjeta); border:1px solid var(--borde); border-radius:8px;
               box-shadow:0 8px 24px rgba(0,0,0,.15); max-height:320px; overflow:auto; }
.sugerencias div { padding:8px 12px; cursor:pointer; display:flex; gap:10px; }
.sugerencias div:hover, .sugerencias div.marcada { background:var(--acento-suave); }
.sugerencias b { min-width:80px; }
.sugerencias small { color:var(--suave); margin-left:auto; }
details.grupo { border:1px solid var(--borde); border-radius:8px; padding:8px 12px;
                margin:8px 0; }
details.grupo summary { cursor:pointer; font-weight:600; font-size:14px; }
details.grupo .chips { margin-top:8px; }
.segmentado { display:inline-flex; border:1px solid var(--borde); border-radius:7px;
              overflow:hidden; }
.segmentado button { background:transparent; color:var(--texto); border-radius:0;
                     padding:7px 12px; font-weight:500; }
.segmentado button.activo { background:var(--acento); color:#fff; }
.kpis { display:grid; gap:10px; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));
        margin:12px 0; }
.kpi { border:1px solid var(--borde); border-radius:8px; padding:10px 12px;
       background:var(--tarjeta); }
.kpi span { display:block; font-size:12px; color:var(--suave); font-weight:600; }
.kpi b { font-size:20px; } .kpi b.pos { color:var(--ok); } .kpi b.neg { color:var(--error); }
.tabla { overflow-x:auto; }
table { border-collapse:collapse; width:100%; margin:8px 0; font-size:14px; }
th, td { padding:6px 9px; border-bottom:1px solid var(--borde); text-align:right;
         white-space:nowrap; }
th:first-child, td:first-child { text-align:left; }
th { color:var(--suave); font-weight:600; font-size:12px; }
th.ordenable { cursor:pointer; } th.ordenable:hover { color:var(--acento); }
td.pos { color:var(--ok); } td.neg { color:var(--error); }
.barra { display:inline-block; height:8px; background:var(--acento); border-radius:4px;
         vertical-align:middle; margin-left:6px; opacity:.7; }
.peso { display:grid; grid-template-columns:110px 1fr 90px; gap:10px; align-items:center;
        margin:6px 0; }
.peso input[type=number] { width:90px; }
.suma { height:8px; border-radius:4px; background:var(--borde); overflow:hidden; margin:6px 0; }
.suma div { height:100%; background:var(--aviso); transition:width .2s; }
.suma.ok div { background:var(--ok); }
.grafico { position:relative; }
.grafico svg { width:100%; height:auto; display:block; }
.grafico .eje { stroke:var(--borde); }
.grafico text { fill:var(--suave); font-size:11px; }
.leyenda { display:flex; flex-wrap:wrap; gap:6px 14px; font-size:13px; margin:6px 0; }
.leyenda span { cursor:pointer; user-select:none; display:inline-flex; align-items:center;
                gap:5px; }
.leyenda span.oculta { opacity:.35; text-decoration:line-through; }
.leyenda i { width:12px; height:3px; border-radius:2px; display:inline-block; }
.tooltip { position:absolute; pointer-events:none; background:var(--tarjeta);
           border:1px solid var(--borde); border-radius:6px; padding:6px 9px; font-size:12px;
           box-shadow:0 4px 12px rgba(0,0,0,.15); display:none; z-index:5; white-space:nowrap; }
.mapa td { text-align:center; font-weight:600; color:#10151c; min-width:62px; }
.mapa th { text-align:center; }
.galeria { display:grid; gap:14px; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); }
.galeria figure { margin:0; border:1px solid var(--borde); border-radius:8px; padding:8px;
                  background:#fff; cursor:zoom-in; }
.galeria img { width:100%; display:block; }
.galeria figcaption { font-size:13px; color:#5b6676; margin-top:4px; }
#lupa { position:fixed; inset:0; background:rgba(0,0,0,.8); display:none; z-index:50;
        align-items:center; justify-content:center; cursor:zoom-out; padding:20px; }
#lupa img { max-width:100%; max-height:100%; background:#fff; border-radius:6px; }
iframe { width:100%; height:720px; border:1px solid var(--borde); border-radius:8px;
         background:#fff; }
pre { background:var(--fondo); padding:12px; overflow:auto; border-radius:6px; font-size:13px;
      max-height:640px; }
#avisoFlotante { position:fixed; right:16px; bottom:16px; z-index:60; max-width:380px;
                 padding:10px 14px; border-radius:8px; color:#fff; background:#2c3542;
                 box-shadow:0 8px 24px rgba(0,0,0,.25); display:none; font-size:14px; }
#avisoFlotante.error { background:#b3261e; }
.girando { display:inline-block; width:14px; height:14px; border:2px solid #fff;
           border-right-color:transparent; border-radius:50%; vertical-align:-2px;
           animation:girar .7s linear infinite; margin-right:6px; }
@keyframes girar { to { transform:rotate(360deg); } }
.oculto { display:none !important; }
@media (max-width:640px) { .peso { grid-template-columns:80px 1fr 80px; } iframe { height:520px; } }
</style>
</head>
<body>
<header>
  <div class="contenedor">
    <div>
      <h1>market-toolkit</h1>
      <p>Datos de mercado, carteras, simulación de Monte Carlo e informes desde el navegador.</p>
    </div>
    <div class="espacio"></div>
    <span class="insignia" id="modoDatos">Sin datos</span>
    <button class="secundario pequeno" id="botonTema" onclick="cambiarTema()">Tema oscuro</button>
  </div>
</header>
<nav>
  <div class="contenedor" id="pestanas">
    <button data-panel="activos" class="activa"><span class="num">1</span>Activos</button>
    <button data-panel="cartera" disabled><span class="num">2</span>Cartera</button>
    <button data-panel="analisis" disabled><span class="num">3</span>Correlación y gráficos</button>
    <button data-panel="montecarlo" disabled><span class="num">4</span>Monte Carlo</button>
    <button data-panel="informe" disabled><span class="num">5</span>Informe</button>
    <button data-panel="macro"><span class="num">6</span>Macro (FRED)</button>
  </div>
</nav>
<main class="contenedor">

<!-- ======================= 1. Activos ======================= -->
<section class="panel visible" id="panel-activos">
  <div class="rejilla">
    <div class="tarjeta">
      <h2>Elige los activos</h2>
      <p class="nota">Busca por nombre o ticker, o elige del catálogo. Pulsa Intro para añadir un
        ticker escrito a mano.</p>
      <div class="fila">
        <div class="buscador">
          <input type="text" id="busqueda" placeholder="Ej.: Apple, Santander, oro, SPY..."
            autocomplete="off">
          <div class="sugerencias oculto" id="sugerencias"></div>
        </div>
      </div>
      <h3>Tu selección <span class="nota" id="cuentaSeleccion"></span></h3>
      <div class="seleccion chips" id="seleccion"></div>
      <div class="fila">
        <button class="secundario pequeno" onclick="limpiarSeleccion()">Vaciar</button>
        <button class="secundario pequeno" onclick="cargarEjemplo()">Cartera de ejemplo</button>
      </div>
      <div id="catalogo"></div>
    </div>

    <div class="tarjeta">
      <h2>Periodo y referencia</h2>
      <div class="fila">
        <label>Desde <input type="date" id="inicio" value="2022-01-01"></label>
        <label>Hasta <input type="date" id="fin" value="2024-12-31"></label>
      </div>
      <div class="fila" id="periodosRapidos">
        <button class="secundario pequeno" onclick="periodo(1)">1 año</button>
        <button class="secundario pequeno" onclick="periodo(3)">3 años</button>
        <button class="secundario pequeno" onclick="periodo(5)">5 años</button>
        <button class="secundario pequeno" onclick="periodo(10)">10 años</button>
        <button class="secundario pequeno" onclick="periodo(20)">20 años</button>
      </div>
      <div class="fila">
        <label>Índice de referencia
          <select id="indice" onchange="cambioIndice()"></select></label>
        <label id="indiceOtro" class="oculto">Ticker del índice
          <input type="text" id="indiceManual" placeholder="^IXIC"></label>
      </div>
      <p class="nota">El índice no entra en la cartera: sirve para comparar (beta, alfa, tracking
        error) y como línea de referencia en los gráficos.</p>
      <h3>Origen de los datos</h3>
      <label class="check"><input type="checkbox" id="sintetico" __SINTETICO__
        onchange="actualizarModo()"> Datos sintéticos (sin conexión ni claves)</label>
      <p class="nota" id="notaClaves"></p>
      <div class="fila">
        <button id="botonDatos" onclick="cargarDatos()">Cargar datos</button>
      </div>
      <div class="mensajes" id="mensajesDatos"></div>
    </div>
  </div>

  <div class="tarjeta oculto" id="resultadoDatos">
    <div class="fila">
      <h2 style="margin:0">Series obtenidas</h2>
      <div class="espacio"></div>
      <button class="secundario pequeno" onclick="descargarPrecios()">Descargar precios (CSV)
      </button>
    </div>
    <div class="tabla" id="tablaSeries"></div>
    <h3>Evolución en base 100</h3>
    <p class="nota">Pulsa en la leyenda para ocultar o mostrar una serie. Pasa el ratón para ver
      los valores.</p>
    <div id="graficoPrecios"></div>
    <div class="fila"><button onclick="irA('cartera')">Siguiente: crear la cartera →</button></div>
  </div>
</section>

<!-- ======================= 2. Cartera ======================= -->
<section class="panel" id="panel-cartera">
  <div class="rejilla">
    <div class="tarjeta">
      <h2>Pesos iniciales</h2>
      <div id="pesos"></div>
      <div class="suma" id="barraSuma"><div></div></div>
      <div class="fila">
        <span class="nota" id="textoSuma"></span>
        <div class="espacio"></div>
        <button class="secundario pequeno" onclick="pesosIguales()">Partes iguales</button>
        <button class="secundario pequeno" onclick="pesosInversaVol()"
          title="Más peso a los activos menos volátiles">Inversa de la volatilidad</button>
        <button class="secundario pequeno" onclick="normalizarPesos()">Ajustar a 100 %</button>
      </div>
    </div>
    <div class="tarjeta">
      <h2>Opciones</h2>
      <div class="fila">
        <label>Rebalanceo
          <select id="rebalanceoCartera">
            <option value="nunca">Nunca (los pesos derivan)</option>
            <option value="mensual">Mensual</option>
            <option value="trimestral">Trimestral</option>
            <option value="anual">Anual</option>
          </select></label>
        <label>Fechas en que no cotizan todos
          <select id="alineacion">
            <option value="eliminacion">Eliminarlas</option>
            <option value="relleno">Rellenar con el último precio</option>
          </select></label>
      </div>
      <p class="nota">Con rebalanceo, la cartera vuelve a los pesos iniciales al principio de cada
        periodo. Los activos en otra moneda se pasan a dólares.</p>
      <div class="fila"><button id="botonCartera" onclick="crearCartera()">Crear cartera</button></div>
      <div class="mensajes" id="mensajesCartera"></div>
    </div>
  </div>

  <div class="oculto" id="resultadoCartera">
    <div class="tarjeta">
      <h2>Resumen</h2>
      <div class="kpis" id="kpisCartera"></div>
      <h3>Evolución de la cartera (base 100)</h3>
      <div id="graficoCartera"></div>
      <div class="rejilla">
        <div><h3>Drawdown</h3><div id="graficoDrawdown"></div></div>
        <div><h3>Evolución de los pesos (%)</h3><div id="graficoPesos"></div></div>
      </div>
      <h3>Activos</h3>
      <div class="tabla" id="tablaCartera"></div>
      <div class="fila">
        <button onclick="irA('analisis')">Correlación y gráficos →</button>
        <button class="secundario" onclick="irA('montecarlo')">Monte Carlo →</button>
        <button class="secundario" onclick="irA('informe')">Informe →</button>
      </div>
    </div>
  </div>
</section>

<!-- ======================= 3. Análisis ======================= -->
<section class="panel" id="panel-analisis">
  <div class="tarjeta">
    <h2>Correlación entre los activos</h2>
    <p class="nota">Correlación de los rendimientos diarios en USD. Cerca de 1, se mueven juntos;
      cerca de 0 o negativa, diversifican.</p>
    <div class="fila">
      <label>Ventana
        <select id="anios" onchange="verCorrelacion()">
          <option value="0.5">Últimos 6 meses</option>
          <option value="1" selected>Último año</option>
          <option value="2">Últimos 2 años</option>
          <option value="3">Últimos 3 años</option>
          <option value="5">Últimos 5 años</option>
          <option value="10">Últimos 10 años</option>
        </select></label>
    </div>
    <div class="mensajes" id="mensajesCorrelacion"></div>
    <div class="tabla" id="mapaCorrelacion"></div>
  </div>
  <div class="tarjeta">
    <div class="fila">
      <h2 style="margin:0">Gráficos del informe</h2>
      <div class="espacio"></div>
      <label class="check"><input type="checkbox" id="indiceGraficos" checked>
        Con el índice de referencia</label>
      <button id="botonGraficos" onclick="verGraficos()">Generar los 6 gráficos</button>
    </div>
    <p class="nota">Los mismos que genera plots_report(). Pulsa en uno para ampliarlo.</p>
    <div class="mensajes" id="mensajesGraficos"></div>
    <div class="galeria" id="galeria"></div>
  </div>
</section>

<!-- ======================= 4. Monte Carlo ======================= -->
<section class="panel" id="panel-montecarlo">
  <div class="tarjeta">
    <h2>Simulación de Monte Carlo</h2>
    <div class="fila">
      <label>Qué simular <select id="objetivo" onchange="cambioObjetivo()"></select></label>
      <label>Simulaciones <input type="number" id="nSim" value="5000" min="1" step="1000"></label>
      <label>Horizonte
        <select id="horizonte">
          <option value="21">1 mes</option>
          <option value="63">3 meses</option>
          <option value="126">6 meses</option>
          <option value="252" selected>1 año</option>
          <option value="756">3 años</option>
          <option value="1260">5 años</option>
        </select></label>
      <label>Valor inicial <input type="number" id="valorInicial" placeholder="automático"></label>
      <label>Semilla <input type="number" id="semilla" value="42"></label>
    </div>
    <div class="fila">
      <label>Distribución de los choques
        <span class="segmentado" id="distribucion">
          <button data-valor="normal" class="activo">Normal</button>
          <button data-valor="t">t de Student</button>
          <button data-valor="bootstrap">Bootstrap histórico</button>
        </span></label>
      <label id="campoGrados" class="oculto">Grados de libertad
        <input type="number" id="grados" placeholder="estimados" min="2.1" step="0.5"></label>
      <label class="check" id="campoRebalanceo"><input type="checkbox" id="rebalanceo">
        Pesos constantes (rebalanceo diario)</label>
    </div>
    <details class="grupo">
      <summary>Supuestos de rentabilidad y volatilidad (opcional)</summary>
      <p class="nota">Vacío = el histórico. Los valores por activo mandan sobre los generales.
        Todos en % anual.</p>
      <div class="fila">
        <label>Rentabilidad general (%)
          <input type="number" id="rentabilidad" placeholder="histórica" step="0.5"></label>
        <label>Volatilidad general (%)
          <input type="number" id="volatilidad" placeholder="histórica" step="0.5" min="0"></label>
      </div>
      <div class="tabla" id="tablaSupuestos"></div>
      <div class="fila">
        <span class="nota">Escenarios rápidos:</span>
        <button class="secundario pequeno" onclick="escenario('base')">Histórico</button>
        <button class="secundario pequeno" onclick="escenario('estres')">
          Estrés: volatilidad × 1,5 y rentabilidad 0 %</button>
        <button class="secundario pequeno" onclick="escenario('calma')">
          Calma: volatilidad × 0,7</button>
      </div>
    </details>
    <div class="fila">
      <label class="check"><input type="checkbox" id="comparar" checked>
        Comparar las tres distribuciones</label>
      <div class="espacio"></div>
      <button id="botonMc" onclick="simular()">Simular</button>
    </div>
    <div class="mensajes" id="mensajesMc"></div>
  </div>
  <div class="tarjeta oculto" id="resultadoMc">
    <h2 id="tituloMc">Resultado</h2>
    <div class="kpis" id="kpisMc"></div>
    <div class="rejilla">
      <div><h3>Abanico de percentiles</h3><div id="graficoAbanico"></div></div>
      <div><h3>Distribución del valor final</h3><div id="graficoHistograma"></div>
        <p class="nota">En rojo, los escenarios con pérdidas.</p></div>
    </div>
    <div id="comparacionMc"></div>
    <details class="grupo">
      <summary>Gráficos de matplotlib (los que guarda la librería)</summary>
      <div class="galeria" id="galeriaMc"></div>
    </details>
  </div>
</section>

<!-- ======================= 5. Informe ======================= -->
<section class="panel" id="panel-informe">
  <div class="tarjeta">
    <h2>Informe de la cartera</h2>
    <div class="fila">
      <label>Formato
        <span class="segmentado" id="formato">
          <button data-valor="html" class="activo">HTML</button>
          <button data-valor="markdown">Markdown</button>
        </span></label>
      <label>Tipo libre de riesgo (%) <input type="number" id="tasa" value="4" step="0.1"></label>
      <label>Simulaciones <input type="number" id="simInforme" value="5000" min="1"></label>
    </div>
    <div class="fila">
      <label class="check"><input type="checkbox" id="usarIndice" checked>
        Comparar con el índice</label>
      <label class="check"><input type="checkbox" id="incluirMc" checked>
        Incluir Monte Carlo</label>
      <label class="check"><input type="checkbox" id="incluirGraficos" checked>
        Incluir gráficos (HTML)</label>
    </div>
    <details class="grupo">
      <summary>Umbrales de las advertencias</summary>
      <p class="nota">Vacío = el valor por defecto de report().</p>
      <div class="fila">
        <label>Volatilidad máxima (%)
          <input type="number" id="maxVol" placeholder="30" step="1"></label>
        <label>Drawdown máximo (%) <input type="number" id="maxDd" placeholder="20" step="1"></label>
        <label>Sharpe mínimo <input type="number" id="minSharpe" placeholder="1" step="0.1"></label>
        <label>Concentración máxima (%)
          <input type="number" id="maxConc" placeholder="50" step="1"></label>
        <label>Correlación máxima (%)
          <input type="number" id="maxCorr" placeholder="80" step="1"></label>
        <label>Confianza del ES (%)
          <input type="number" id="confianza" placeholder="95" step="1"></label>
      </div>
    </details>
    <div class="fila">
      <button id="botonInforme" onclick="generarInforme()">Generar informe</button>
      <button class="secundario oculto" id="botonPestana" onclick="abrirInforme()">
        Abrir en otra pestaña</button>
      <button class="secundario oculto" id="botonDescargar" onclick="descargarInforme()">
        Descargar</button>
    </div>
    <div class="mensajes" id="mensajesInforme"></div>
    <div id="resultadoInforme"></div>
  </div>
</section>

<!-- ======================= 6. Macro ======================= -->
<section class="panel" id="panel-macro">
  <div class="tarjeta">
    <h2>Series macroeconómicas de FRED</h2>
    <p class="nota" id="notaMacro"></p>
    <div class="chips" id="seriesMacro"></div>
    <div class="fila">
      <label>Desde <input type="date" id="inicioMacro" value="2015-01-01"></label>
      <label>Hasta <input type="date" id="finMacro" value="2024-12-31"></label>
      <button id="botonMacro" onclick="descargarMacro()">Descargar series</button>
    </div>
    <div class="mensajes" id="mensajesMacro"></div>
    <div id="resultadoMacro"></div>
  </div>
</section>
</main>

<div id="lupa" onclick="this.style.display='none'"><img alt="Gráfico ampliado"></div>
<div id="avisoFlotante"></div>

<script>
// ===================================================================
// Utilidades
// ===================================================================
const COLORES = ["#1f5fbf", "#e8590c", "#2b8a3e", "#9c36b5", "#c92a2a", "#0b7285",
                 "#5f3dc4", "#a61e4d", "#5c940d", "#d9480f", "#364fc7", "#087f5b"];
const estado = { catalogo: null, seleccion: [], datos: null, cartera: null, informe: null,
                 nombres: {}, macroElegidas: ["us10y", "vix"] };

function $(id) { return document.getElementById(id); }
function escapar(texto) {
  return String(texto === null || texto === undefined ? "" : texto)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function pct(valor, decimales) {
  if (valor === null || valor === undefined) return "–";
  return (valor * 100).toFixed(decimales === undefined ? 2 : decimales).replace(".", ",") + " %";
}
function num(valor, decimales) {
  if (valor === null || valor === undefined) return "–";
  return Number(valor).toLocaleString("es-ES", {
    minimumFractionDigits: decimales === undefined ? 2 : decimales,
    maximumFractionDigits: decimales === undefined ? 2 : decimales });
}
function signo(valor) { return valor === null || valor === undefined ? "" : (valor < 0 ? "neg" : "pos"); }
function valorCampo(id) {
  const texto = $(id).value.trim();
  return texto === "" ? null : Number(texto);
}
function avisar(texto, esError) {
  const caja = $("avisoFlotante");
  caja.textContent = texto;
  caja.className = esError ? "error" : "";
  caja.style.display = "block";
  clearTimeout(avisar.temporizador);
  avisar.temporizador = setTimeout(() => { caja.style.display = "none"; }, esError ? 6000 : 2500);
}
function mensajes(id, errores, avisos) {
  let html = "";
  for (const texto of errores || []) html += '<div class="error">' + escapar(texto) + "</div>";
  for (const texto of avisos || []) html += '<div class="aviso">' + escapar(texto) + "</div>";
  $(id).innerHTML = html;
}
function kpis(lista) {
  return lista.map(k => '<div class="kpi"><span>' + escapar(k[0]) + '</span><b class="' +
    (k[2] || "") + '">' + k[1] + "</b></div>").join("");
}
function descargarTexto(texto, tipo, nombre) {
  const url = URL.createObjectURL(new Blob([texto], { type: tipo }));
  const enlace = document.createElement("a");
  enlace.href = url; enlace.download = nombre;
  document.body.appendChild(enlace); enlace.click(); enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function llamar(accion, datos, boton) {
  let textoBoton = null;
  if (boton) {
    textoBoton = boton.innerHTML;
    boton.disabled = true;
    boton.innerHTML = '<span class="girando"></span>Trabajando...';
  }
  try {
    const respuesta = await fetch("/api/" + accion, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos || {}) });
    const resultado = await respuesta.json();
    if (!respuesta.ok) return { error: resultado.error || "Error desconocido" };
    return resultado;
  } catch (error) {
    return { error: "No se ha podido contactar con el servidor: " + error };
  } finally {
    if (boton) { boton.disabled = false; boton.innerHTML = textoBoton; }
  }
}

// ===================================================================
// Tema y pestañas
// ===================================================================
function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  $("botonTema").textContent = tema === "oscuro" ? "Tema claro" : "Tema oscuro";
}
function cambiarTema() {
  const nuevo = document.documentElement.dataset.tema === "oscuro" ? "claro" : "oscuro";
  aplicarTema(nuevo);
  try { localStorage.setItem("tema", nuevo); } catch (e) { /* sin almacenamiento */ }
}
(function () {
  let tema = null;
  try { tema = localStorage.getItem("tema"); } catch (e) { tema = null; }
  if (!tema) tema = matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
  aplicarTema(tema);
})();

document.querySelectorAll("#pestanas button").forEach(b => {
  b.addEventListener("click", () => irA(b.dataset.panel));
});
function irA(panel) {
  const boton = document.querySelector('#pestanas button[data-panel="' + panel + '"]');
  if (boton.disabled) return;
  document.querySelectorAll("#pestanas button").forEach(b => b.classList.remove("activa"));
  boton.classList.add("activa");
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("visible"));
  $("panel-" + panel).classList.add("visible");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (panel === "analisis" && estado.cartera && !$("mapaCorrelacion").innerHTML) verCorrelacion();
}
function habilitar(panel, si) {
  document.querySelector('#pestanas button[data-panel="' + panel + '"]').disabled = !si;
}
function marcarHecha(panel, si) {
  const boton = document.querySelector('#pestanas button[data-panel="' + panel + '"]');
  boton.classList.toggle("hecha", si);
}
document.querySelectorAll(".segmentado").forEach(grupo => {
  grupo.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    grupo.querySelectorAll("button").forEach(o => o.classList.remove("activo"));
    b.classList.add("activo");
    if (grupo.id === "distribucion") $("campoGrados").classList.toggle("oculto", b.dataset.valor !== "t");
  }));
});
function segmentado(id) { return document.querySelector("#" + id + " button.activo").dataset.valor; }

// ===================================================================
// Gráficos interactivos (SVG)
// ===================================================================
function escalaBonita(minimo, maximo, marcas) {
  if (minimo === maximo) { minimo -= 1; maximo += 1; }
  const bruto = (maximo - minimo) / marcas;
  const potencia = Math.pow(10, Math.floor(Math.log10(bruto)));
  const paso = [1, 2, 2.5, 5, 10].map(f => f * potencia).find(p => p >= bruto);
  const desde = Math.floor(minimo / paso) * paso;
  const hasta = Math.ceil(maximo / paso) * paso;
  const valores = [];
  for (let v = desde; v <= hasta + paso / 2; v += paso) valores.push(Number(v.toFixed(10)));
  return valores;
}

function graficoLineas(contenedor, datos, opciones) {
  opciones = opciones || {};
  const formato = opciones.formato || (v => num(v));
  const ancho = opciones.ancho || 860, alto = opciones.alto || 320;
  const margen = { izq: 58, der: 16, arr: 12, aba: 28 };
  const nombres = Object.keys(datos.series);
  const colores = {};
  nombres.forEach((n, i) => { colores[n] = (opciones.colores && opciones.colores[n]) ||
                                            COLORES[i % COLORES.length]; });
  const ocultas = new Set();
  const n = datos.etiquetas.length;
  contenedor.innerHTML = '<div class="grafico"><div class="leyenda"></div>' +
    '<svg viewBox="0 0 ' + ancho + " " + alto + '" role="img"></svg>' +
    '<div class="tooltip"></div></div>';
  const svg = contenedor.querySelector("svg");
  const leyenda = contenedor.querySelector(".leyenda");
  const tooltip = contenedor.querySelector(".tooltip");
  if (nombres.length > 1 || opciones.leyenda) {
    leyenda.innerHTML = nombres.map(nm => '<span data-serie="' + escapar(nm) + '"><i style="background:' +
      colores[nm] + '"></i>' + escapar(nm) + "</span>").join("");
    leyenda.querySelectorAll("span").forEach(s => s.addEventListener("click", () => {
      const nm = s.dataset.serie;
      if (ocultas.has(nm)) ocultas.delete(nm); else ocultas.add(nm);
      s.classList.toggle("oculta");
      dibujar();
    }));
  }
  let x, y;
  function dibujar() {
    const visibles = nombres.filter(nm => !ocultas.has(nm));
    let minimo = Infinity, maximo = -Infinity;
    for (const nm of visibles) for (const v of datos.series[nm]) {
      if (v === null) continue;
      if (v < minimo) minimo = v;
      if (v > maximo) maximo = v;
    }
    if (opciones.referencia !== undefined) {
      minimo = Math.min(minimo, opciones.referencia); maximo = Math.max(maximo, opciones.referencia);
    }
    if (!isFinite(minimo)) { minimo = 0; maximo = 1; }
    const marcas = escalaBonita(minimo, maximo, 5);
    const yMin = marcas[0], yMax = marcas[marcas.length - 1];
    x = i => margen.izq + (n <= 1 ? 0 : i * (ancho - margen.izq - margen.der) / (n - 1));
    y = v => margen.arr + (yMax - v) * (alto - margen.arr - margen.aba) / (yMax - yMin);
    let s = "";
    for (const m of marcas) {
      s += '<line class="eje" x1="' + margen.izq + '" x2="' + (ancho - margen.der) + '" y1="' +
        y(m) + '" y2="' + y(m) + '"/><text x="' + (margen.izq - 6) + '" y="' + (y(m) + 4) +
        '" text-anchor="end">' + escapar(formato(m)) + "</text>";
    }
    const nEtiquetas = Math.min(6, n);
    for (let k = 0; k < nEtiquetas; k++) {
      const i = Math.round(k * (n - 1) / Math.max(1, nEtiquetas - 1));
      s += '<text x="' + x(i) + '" y="' + (alto - 8) + '" text-anchor="' +
        (k === 0 ? "start" : (k === nEtiquetas - 1 ? "end" : "middle")) + '">' +
        escapar(datos.etiquetas[i]) + "</text>";
    }
    if (opciones.referencia !== undefined) {
      s += '<line x1="' + margen.izq + '" x2="' + (ancho - margen.der) + '" y1="' +
        y(opciones.referencia) + '" y2="' + y(opciones.referencia) +
        '" stroke="currentColor" stroke-dasharray="4 4" opacity=".45"/>';
    }
    if (opciones.banda) {   // Banda entre dos series (p. ej. percentiles 5 y 95)
      for (const par of opciones.banda) {
        const [a, b, opacidad] = par;
        if (ocultas.has(a) || ocultas.has(b)) continue;
        let puntos = "";
        datos.series[a].forEach((v, i) => { puntos += x(i) + "," + y(v) + " "; });
        for (let i = n - 1; i >= 0; i--) puntos += x(i) + "," + y(datos.series[b][i]) + " ";
        s += '<polygon points="' + puntos + '" fill="' + colores[a] + '" opacity="' + opacidad +
          '"/>';
      }
    }
    for (const nm of visibles) {
      let d = "", abierto = false;
      datos.series[nm].forEach((v, i) => {
        if (v === null) { abierto = false; return; }
        d += (abierto ? "L" : "M") + x(i).toFixed(1) + "," + y(v).toFixed(1);
        abierto = true;
      });
      if (opciones.relleno) {
        s += '<path d="' + d + "L" + x(n - 1) + "," + y(0) + "L" + x(0) + "," + y(0) +
          'Z" fill="' + colores[nm] + '" opacity=".18"/>';
      }
      const grosor = (opciones.gruesas && opciones.gruesas.includes(nm)) ? 2.6 : 1.6;
      const discontinua = (opciones.discontinuas && opciones.discontinuas.includes(nm)) ?
        ' stroke-dasharray="6 4"' : "";
      s += '<path d="' + d + '" fill="none" stroke="' + colores[nm] + '" stroke-width="' + grosor +
        '"' + discontinua + ' stroke-linejoin="round"/>';
    }
    s += '<line id="cursor" y1="' + margen.arr + '" y2="' + (alto - margen.aba) +
      '" stroke="currentColor" opacity="0" />';
    svg.innerHTML = s;
  }
  dibujar();
  svg.addEventListener("mousemove", ev => {
    const caja = svg.getBoundingClientRect();
    const px = (ev.clientX - caja.left) * ancho / caja.width;
    let i = Math.round((px - margen.izq) * (n - 1) / (ancho - margen.izq - margen.der));
    i = Math.max(0, Math.min(n - 1, i));
    const cursor = svg.querySelector("#cursor");
    cursor.setAttribute("x1", x(i)); cursor.setAttribute("x2", x(i));
    cursor.setAttribute("opacity", ".35");
    let html = "<b>" + escapar(datos.etiquetas[i]) + "</b>";
    for (const nm of nombres) {
      if (ocultas.has(nm)) continue;
      html += '<br><span style="color:' + colores[nm] + '">●</span> ' + escapar(nm) + ": " +
        escapar(formato(datos.series[nm][i]));
    }
    tooltip.innerHTML = html;
    tooltip.style.display = "block";
    const izquierda = ev.clientX - caja.left + 14;
    tooltip.style.left = Math.min(izquierda, caja.width - tooltip.offsetWidth - 4) + "px";
    tooltip.style.top = (ev.clientY - caja.top + 30) + "px";
  });
  svg.addEventListener("mouseleave", () => {
    tooltip.style.display = "none";
    const cursor = svg.querySelector("#cursor");
    if (cursor) cursor.setAttribute("opacity", "0");
  });
}

function graficoHistograma(contenedor, histograma) {
  const ancho = 520, alto = 330, margen = { izq: 46, der: 12, arr: 10, aba: 28 };
  const conteos = histograma.conteos, bordes = histograma.bordes;
  const maximo = Math.max(...conteos);
  const xMin = bordes[0], xMax = bordes[bordes.length - 1];
  const x = v => margen.izq + (v - xMin) * (ancho - margen.izq - margen.der) / (xMax - xMin);
  const y = v => alto - margen.aba - v * (alto - margen.arr - margen.aba) / maximo;
  let s = "";
  for (const m of escalaBonita(0, maximo, 4)) {
    if (m > maximo) continue;
    s += '<line class="eje" x1="' + margen.izq + '" x2="' + (ancho - margen.der) + '" y1="' + y(m) +
      '" y2="' + y(m) + '"/><text x="' + (margen.izq - 6) + '" y="' + (y(m) + 4) +
      '" text-anchor="end">' + m + "</text>";
  }
  conteos.forEach((c, i) => {
    const centro = (bordes[i] + bordes[i + 1]) / 2;
    const color = centro < histograma.valor_inicial ? "#e03131" : "#2b8a3e";
    s += '<rect x="' + (x(bordes[i]) + 0.5) + '" y="' + y(c) + '" width="' +
      Math.max(0.5, x(bordes[i + 1]) - x(bordes[i]) - 1) + '" height="' + (alto - margen.aba - y(c)) +
      '" fill="' + color + '" opacity=".8"><title>' + num(bordes[i]) + " – " + num(bordes[i + 1]) +
      ": " + c + " simulaciones</title></rect>";
  });
  for (const m of escalaBonita(xMin, xMax, 6)) {
    if (m < xMin || m > xMax) continue;
    s += '<text x="' + x(m) + '" y="' + (alto - 8) + '" text-anchor="middle">' + num(m, 0) + "</text>";
  }
  s += '<line x1="' + x(histograma.valor_inicial) + '" x2="' + x(histograma.valor_inicial) +
    '" y1="' + margen.arr + '" y2="' + (alto - margen.aba) +
    '" stroke="currentColor" stroke-dasharray="4 4" opacity=".6"/>';
  contenedor.innerHTML = '<div class="grafico"><svg viewBox="0 0 ' + ancho + " " + alto + '">' + s +
    "</svg></div>";
}

function tablaOrdenable(contenedor, columnas, filas) {
  // columnas: [titulo, funcionDeFormato, claseOpcional]; filas: listas de valores en bruto
  let orden = { columna: -1, sube: true };
  function pintar() {
    const lista = filas.slice();
    if (orden.columna >= 0) {
      lista.sort((a, b) => {
        const va = a[orden.columna], vb = b[orden.columna];
        const r = (typeof va === "number" && typeof vb === "number") ? va - vb :
          String(va).localeCompare(String(vb));
        return orden.sube ? r : -r;
      });
    }
    let html = "<table><tr>" + columnas.map((c, i) => '<th class="ordenable" data-i="' + i + '">' +
      escapar(c[0]) + (orden.columna === i ? (orden.sube ? " ▲" : " ▼") : "") + "</th>").join("") +
      "</tr>";
    for (const fila of lista) {
      html += "<tr>" + fila.map((v, i) => {
        const clase = columnas[i][2] ? columnas[i][2](v) : "";
        return '<td class="' + clase + '">' + columnas[i][1](v) + "</td>";
      }).join("") + "</tr>";
    }
    contenedor.innerHTML = html + "</table>";
    contenedor.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
      const i = Number(th.dataset.i);
      orden = { columna: i, sube: orden.columna === i ? !orden.sube : false };
      pintar();
    }));
  }
  pintar();
}
const texto = v => escapar(v);

// ===================================================================
// 1. Activos: catálogo, buscador y selección
// ===================================================================
async function iniciar() {
  const r = await llamar("catalogo", {});
  if (r.error) { avisar(r.error, true); return; }
  estado.catalogo = r;
  let html = "";
  for (const g of r.grupos) {
    html += '<details class="grupo"' + (g.grupo.startsWith("Tecnol") ? " open" : "") +
      "><summary>" + escapar(g.grupo) + " (" + g.activos.length + ")</summary><div class=\"chips\">";
    for (const a of g.activos) {
      estado.nombres[a.ticker] = a.nombre;
      html += '<span class="chip" data-ticker="' + escapar(a.ticker) + '" title="' +
        escapar(a.nombre) + '">' + escapar(a.ticker) + " <small>" + escapar(a.nombre) +
        "</small></span>";
    }
    html += "</div></details>";
  }
  $("catalogo").innerHTML = html;
  $("catalogo").querySelectorAll(".chip").forEach(c => c.addEventListener("click", () =>
    alternar(c.dataset.ticker)));
  let opciones = "";
  for (const i of r.indices) {
    estado.nombres[i.ticker] = i.nombre;
    opciones += '<option value="' + escapar(i.ticker) + '">' + escapar(i.nombre) + " (" +
      escapar(i.ticker) + ")</option>";
  }
  $("indice").innerHTML = opciones + '<option value="__otro">Otro...</option>' +
    '<option value="">Ninguno</option>';
  // Series macro
  $("seriesMacro").innerHTML = r.macro.map(m => '<span class="chip' +
    (estado.macroElegidas.includes(m.alias) ? " elegido" : "") + '" data-alias="' +
    escapar(m.alias) + '">' + escapar(m.nombre) + " <small>" + escapar(m.alias) + "</small></span>")
    .join("");
  $("seriesMacro").querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => {
    const alias = c.dataset.alias;
    const i = estado.macroElegidas.indexOf(alias);
    if (i >= 0) estado.macroElegidas.splice(i, 1); else estado.macroElegidas.push(alias);
    c.classList.toggle("elegido");
  }));
  $("notaMacro").textContent = r.claves.fred ?
    "Hay clave de FRED en el .env: elige las series y el periodo." :
    "Para descargar series de FRED hace falta FRED_API_KEY en el .env (es gratuita).";
  if (r.sin_red) $("sintetico").checked = true;
  actualizarModo();
  cargarEjemplo();
}

function actualizarModo() {
  const c = estado.catalogo;
  if (!c) return;
  const notas = [];
  if ($("sintetico").checked) {
    notas.push("Datos sintéticos: precios simulados con un factor de mercado común, " +
      "reproducibles y sin conexión.");
  } else {
    notas.push("Acciones, ETF e índices de Yahoo Finance.");
    notas.push(c.claves.alphavantage ? "Materias primas de Alpha Vantage." :
      "Sin clave de Alpha Vantage: no se pueden descargar materias primas.");
    notas.push(c.claves.fred ? "Tipo libre de riesgo de FRED (letras a 3 meses)." :
      "Sin clave de FRED: tipo libre de riesgo del 4 %.");
  }
  $("notaClaves").textContent = notas.join(" ");
}

function pintarSeleccion() {
  const sel = estado.seleccion;
  $("seleccion").innerHTML = sel.length === 0 ?
    '<span class="vacio">Todavía no has elegido ningún activo.</span>' :
    sel.map(t => '<span class="chip elegido" data-ticker="' + escapar(t) + '" title="Quitar">' +
      escapar(t) + (estado.nombres[t] ? " <small>" + escapar(estado.nombres[t]) + "</small>" : "") +
      ' <span class="quitar">×</span></span>').join("");
  $("seleccion").querySelectorAll(".chip").forEach(c => c.addEventListener("click", () =>
    alternar(c.dataset.ticker)));
  $("catalogo").querySelectorAll(".chip").forEach(c =>
    c.classList.toggle("elegido", sel.includes(c.dataset.ticker)));
  $("cuentaSeleccion").textContent = sel.length ? "(" + sel.length + " activos)" : "";
}
function alternar(ticker) {
  ticker = ticker.trim().toUpperCase();
  if (!ticker) return;
  if (ticker.startsWith("^")) {
    avisar(ticker + " es un índice: se usa como referencia, no en la cartera.", true);
    return;
  }
  const i = estado.seleccion.indexOf(ticker);
  if (i >= 0) estado.seleccion.splice(i, 1); else estado.seleccion.push(ticker);
  pintarSeleccion();
}
function limpiarSeleccion() { estado.seleccion = []; pintarSeleccion(); }
function cargarEjemplo() {
  estado.seleccion = ["AAPL", "MSFT", "JPM", "KO"];
  pintarSeleccion();
}

let temporizadorBusqueda = null, marcada = -1;
$("busqueda").addEventListener("input", () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(buscar, 300);
});
$("busqueda").addEventListener("keydown", ev => {
  const items = $("sugerencias").querySelectorAll("div[data-ticker]");
  if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
    ev.preventDefault();
    if (!items.length) return;
    marcada = (marcada + (ev.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
    items.forEach((it, i) => it.classList.toggle("marcada", i === marcada));
  } else if (ev.key === "Enter") {
    ev.preventDefault();
    if (marcada >= 0 && items[marcada]) elegirSugerencia(items[marcada].dataset.ticker,
                                                         items[marcada].dataset.nombre);
    else elegirSugerencia($("busqueda").value, null);
  } else if (ev.key === "Escape") {
    $("sugerencias").classList.add("oculto");
  }
});
document.addEventListener("click", ev => {
  if (!ev.target.closest(".buscador")) $("sugerencias").classList.add("oculto");
});
async function buscar() {
  const texto = $("busqueda").value.trim();
  marcada = -1;
  if (!texto) { $("sugerencias").classList.add("oculto"); return; }
  const r = await llamar("buscar", { texto: texto, local: $("sintetico").checked });
  if (r.error || texto !== $("busqueda").value.trim()) return;
  let html = r.resultados.map(a => '<div data-ticker="' + escapar(a.ticker) + '" data-nombre="' +
    escapar(a.nombre) + '"><b>' + escapar(a.ticker) + "</b>" + escapar(a.nombre) + "<small>" +
    escapar(a.grupo) + "</small></div>").join("");
  if (!r.resultados.length) {
    html = '<div class="vacio">Sin resultados. Pulsa Intro para añadir "' + escapar(texto) +
      '" tal cual.</div>';
  }
  if (r.aviso) html += '<div class="vacio">' + escapar(r.aviso) + "</div>";
  $("sugerencias").innerHTML = html;
  $("sugerencias").classList.remove("oculto");
  $("sugerencias").querySelectorAll("div[data-ticker]").forEach(d => d.addEventListener("click",
    () => elegirSugerencia(d.dataset.ticker, d.dataset.nombre)));
}
function elegirSugerencia(ticker, nombre) {
  ticker = (ticker || "").trim().toUpperCase();
  if (!ticker) return;
  if (nombre) estado.nombres[ticker] = nombre;
  if (ticker.startsWith("^")) {   // Un índice: se propone como referencia
    let existe = false;
    for (const o of $("indice").options) if (o.value === ticker) existe = true;
    if (!existe) {
      $("indice").insertAdjacentHTML("afterbegin", '<option value="' + escapar(ticker) + '">' +
        escapar(nombre || ticker) + " (" + escapar(ticker) + ")</option>");
    }
    $("indice").value = ticker;
    cambioIndice();
    avisar(ticker + " se usará como índice de referencia.");
  } else if (!estado.seleccion.includes(ticker)) {
    alternar(ticker);
  }
  $("busqueda").value = "";
  $("sugerencias").classList.add("oculto");
}
function cambioIndice() { $("indiceOtro").classList.toggle("oculto", $("indice").value !== "__otro"); }
function indiceElegido() {
  return $("indice").value === "__otro" ? $("indiceManual").value.trim() : $("indice").value;
}
function periodo(anios) {
  const fin = new Date();
  fin.setDate(fin.getDate() - 1);
  const inicio = new Date(fin);
  inicio.setFullYear(fin.getFullYear() - anios);
  $("fin").value = fin.toISOString().slice(0, 10);
  $("inicio").value = inicio.toISOString().slice(0, 10);
}

async function cargarDatos() {
  if (estado.seleccion.length < 2) {
    mensajes("mensajesDatos", ["Elige al menos dos activos."]);
    return;
  }
  const datos = { tickers: estado.seleccion, indice: indiceElegido(), inicio: $("inicio").value,
                  fin: $("fin").value, sintetico: $("sintetico").checked };
  const r = await llamar("datos", datos, $("botonDatos"));
  if (r.error) { mensajes("mensajesDatos", [r.error]); return; }
  mensajes("mensajesDatos", [], r.avisos);
  estado.datos = r;
  estado.cartera = null;
  $("modoDatos").textContent = r.datos_reales ? "Datos reales" : "Datos sintéticos";
  $("tasa").value = r.tasa_libre_riesgo.toFixed(2);
  const filas = r.series.map(s => [s.activo, s.nombre || "", s.tipo + (s.en_cartera ? "" :
    " (referencia)"), s.moneda || "", s.inicio + " → " + s.fin, s.observaciones,
    s.rentabilidad_anualizada, s.volatilidad_anualizada, s.max_drawdown]);
  tablaOrdenable($("tablaSeries"), [
    ["Activo", v => "<b>" + escapar(v) + "</b>"], ["Nombre", texto], ["Tipo", texto],
    ["Moneda", texto], ["Periodo", texto], ["Sesiones", v => num(v, 0)],
    ["Rent. anual", v => pct(v), signo], ["Volatilidad", v => pct(v)],
    ["Máx. caída", v => pct(v), () => "neg"]], filas);
  graficoLineas($("graficoPrecios"), r.evolucion, { referencia: 100, formato: v => num(v, 1),
    discontinuas: r.indice ? [r.indice] : [] });
  $("resultadoDatos").classList.remove("oculto");
  prepararCartera();
  habilitar("cartera", true);
  ["analisis", "montecarlo", "informe"].forEach(p => { habilitar(p, false); marcarHecha(p, false); });
  marcarHecha("activos", true);
  marcarHecha("cartera", false);
  avisar("Datos cargados: " + r.series.length + " series.");
}
async function descargarPrecios() {
  const r = await llamar("precios_csv", {});
  if (r.error) { avisar(r.error, true); return; }
  descargarTexto(r.csv, "text/csv", r.nombre);
}

// ===================================================================
// 2. Cartera
// ===================================================================
function prepararCartera() {
  const activos = estado.datos.activos;
  $("pesos").innerHTML = activos.map(a => '<div class="peso"><b title="' +
    escapar(estado.nombres[a] || a) + '">' + escapar(a) + '</b><input type="range" min="0" ' +
    'max="100" step="0.5" data-activo="' + escapar(a) + '"><input type="number" min="0" ' +
    'max="100" step="0.5" data-activo="' + escapar(a) + '"></div>').join("");
  $("pesos").querySelectorAll("input").forEach(entrada => entrada.addEventListener("input", () => {
    $("pesos").querySelectorAll('input[data-activo="' + entrada.dataset.activo + '"]')
      .forEach(o => { if (o !== entrada) o.value = entrada.value; });
    sumarPesos();
  }));
  pesosIguales();
  $("resultadoCartera").classList.add("oculto");
  mensajes("mensajesCartera", []);
}
function fijarPesos(pesos) {
  for (const activo in pesos) {
    $("pesos").querySelectorAll('input[data-activo="' + activo + '"]')
      .forEach(o => { o.value = Math.round(pesos[activo] * 100) / 100; });
  }
  sumarPesos();
}
function repartir(bruto) {   // Reparto en % con dos decimales que suma exactamente 100
  const activos = Object.keys(bruto);
  const total = activos.reduce((s, a) => s + bruto[a], 0);
  const pesos = {};
  let acumulado = 0;
  activos.forEach((a, i) => {
    pesos[a] = i === activos.length - 1 ? Math.round((100 - acumulado) * 100) / 100 :
      Math.round(bruto[a] / total * 10000) / 100;
    acumulado += pesos[a];
  });
  return pesos;
}
function pesosIguales() {
  const bruto = {};
  estado.datos.activos.forEach(a => { bruto[a] = 1; });
  fijarPesos(repartir(bruto));
}
function pesosInversaVol() {
  const bruto = {};
  for (const s of estado.datos.series) {
    if (s.en_cartera && s.volatilidad_anualizada) bruto[s.activo] = 1 / s.volatilidad_anualizada;
  }
  fijarPesos(repartir(bruto));
}
function pesosActuales() {
  const pesos = {};
  $("pesos").querySelectorAll('input[type=number]').forEach(c => {
    pesos[c.dataset.activo] = Number(c.value || 0);
  });
  return pesos;
}
function normalizarPesos() {
  const pesos = pesosActuales();
  const total = Object.values(pesos).reduce((a, b) => a + b, 0);
  if (total <= 0) { pesosIguales(); return; }
  fijarPesos(repartir(pesos));
}
function sumarPesos() {
  const total = Object.values(pesosActuales()).reduce((a, b) => a + b, 0);
  const correcto = Math.abs(total - 100) < 0.011;
  $("textoSuma").textContent = "Suma: " + num(total) + " %" + (correcto ? " ✓" : "");
  $("barraSuma").classList.toggle("ok", correcto);
  $("barraSuma").firstElementChild.style.width = Math.min(100, total) + "%";
}

async function crearCartera() {
  const datos = { pesos: pesosActuales(), rebalanceo: $("rebalanceoCartera").value,
                  alineacion: $("alineacion").value };
  const r = await llamar("cartera", datos, $("botonCartera"));
  if (r.error) { mensajes("mensajesCartera", [r.error]); return; }
  mensajes("mensajesCartera", [], r.avisos);
  estado.cartera = r;
  const s = r.resumen;
  $("kpisCartera").innerHTML = kpis([
    ["Rentabilidad anualizada", pct(s.rentabilidad_anualizada), signo(s.rentabilidad_anualizada)],
    ["Rentabilidad total", pct(s.rentabilidad_total), signo(s.rentabilidad_total)],
    ["Volatilidad anualizada", pct(s.volatilidad_anualizada)],
    ["Ratio de Sharpe", num(s.sharpe), signo(s.sharpe)],
    ["Máxima caída", pct(s.max_drawdown), "neg"],
    ["Periodo", '<small style="font-size:15px">' + s.inicio + " → " + s.fin + "</small>"],
    ["Sesiones", num(s.observaciones, 0)],
    ["Rebalanceos", num(s.rebalanceos, 0)]]);
  const nombres = Object.keys(r.evolucion.series);
  graficoLineas($("graficoCartera"), r.evolucion, { referencia: 100, formato: v => num(v, 1),
    gruesas: ["Cartera"], discontinuas: nombres.slice(1), leyenda: true });
  graficoLineas($("graficoDrawdown"), r.drawdown, { formato: v => num(v, 1) + " %", alto: 300,
    ancho: 520, relleno: true, colores: { "Drawdown (%)": "#e03131" } });
  graficoLineas($("graficoPesos"), r.pesos, { formato: v => num(v, 0) + " %", alto: 300,
    ancho: 520 });
  const maximo = Math.max(...r.activos.map(a => a.peso_actual), ...r.activos.map(a => a.peso_inicial));
  tablaOrdenable($("tablaCartera"), [
    ["Activo", v => "<b>" + escapar(v) + "</b>"],
    ["Peso inicial", v => pct(v) + '<span class="barra" style="width:' + (v / maximo * 60) + 'px">' +
      "</span>"],
    ["Peso al cierre", v => pct(v) + '<span class="barra" style="width:' + (v / maximo * 60) +
      'px"></span>'],
    ["Rent. anual", v => pct(v), signo], ["Volatilidad", v => pct(v)]],
    r.activos.map(a => [a.activo, a.peso_inicial, a.peso_actual, a.rentabilidad_anualizada,
                        a.volatilidad_anualizada]));
  $("resultadoCartera").classList.remove("oculto");
  ["analisis", "montecarlo", "informe"].forEach(p => habilitar(p, true));
  marcarHecha("cartera", true);
  $("mapaCorrelacion").innerHTML = "";
  $("galeria").innerHTML = "";
  $("resultadoMc").classList.add("oculto");
  $("resultadoInforme").innerHTML = "";
  prepararMonteCarlo();
  avisar("Cartera creada.");
}

// ===================================================================
// 3. Correlación y gráficos
// ===================================================================
function colorCorrelacion(v) {
  const a = Math.min(1, Math.abs(v));
  return v >= 0 ? "rgba(31,95,191," + (0.12 + a * 0.75) + ")" : "rgba(224,49,49," +
    (0.12 + a * 0.75) + ")";
}
async function verCorrelacion() {
  const r = await llamar("correlacion", { anios: Number($("anios").value) });
  if (r.error) { mensajes("mensajesCorrelacion", [r.error]); return; }
  mensajes("mensajesCorrelacion", [], r.avisos);
  let html = '<table class="mapa"><tr><th></th>' + r.activos.map(a => "<th>" + escapar(a) + "</th>")
    .join("") + "</tr>";
  r.matriz.forEach((fila, i) => {
    html += "<tr><th>" + escapar(r.activos[i]) + "</th>" + fila.map((v, j) => {
      const fondo = i === j ? "transparent" : colorCorrelacion(v);
      const color = (i !== j && Math.abs(v) > 0.55) ? "#fff" : "inherit";
      return '<td style="background:' + fondo + ";color:" + color + '">' + num(v) + "</td>";
    }).join("") + "</tr>";
  });
  $("mapaCorrelacion").innerHTML = html + "</table>";
}
function galeria(contenedor, lista) {
  contenedor.innerHTML = lista.map(g => '<figure><img alt="' + escapar(g.titulo) + '" src="' +
    g.imagen + '"><figcaption>' + escapar(g.titulo) + "</figcaption></figure>").join("");
  contenedor.querySelectorAll("figure").forEach(f => f.addEventListener("click", () => {
    $("lupa").querySelector("img").src = f.querySelector("img").src;
    $("lupa").style.display = "flex";
  }));
}
async function verGraficos() {
  const r = await llamar("graficos", { usar_indice: $("indiceGraficos").checked },
                         $("botonGraficos"));
  if (r.error) { mensajes("mensajesGraficos", [r.error]); return; }
  mensajes("mensajesGraficos", []);
  galeria($("galeria"), r.graficos);
}
document.addEventListener("keydown", ev => { if (ev.key === "Escape") $("lupa").style.display = "none"; });

// ===================================================================
// 4. Monte Carlo
// ===================================================================
function prepararMonteCarlo() {
  let opciones = '<option value="cartera">La cartera</option>';
  for (const s of estado.datos.series) {
    opciones += '<option value="' + escapar(s.activo) + '">' + escapar(s.activo) + " · " +
      escapar(s.nombre || "") + "</option>";
  }
  $("objetivo").innerHTML = opciones;
  cambioObjetivo();
}
function cambioObjetivo() {
  const cartera = $("objetivo").value === "cartera";
  $("campoRebalanceo").classList.toggle("oculto", !cartera);
  const activos = cartera ? estado.cartera.activos.map(a => a.activo) : [$("objetivo").value];
  let html = "<table><tr><th>Activo</th><th>Rent. histórica</th><th>Rentabilidad (%)</th>" +
    "<th>Vol. histórica</th><th>Volatilidad (%)</th></tr>";
  for (const a of activos) {
    const s = estado.datos.series.find(x => x.activo === a);
    html += "<tr><td><b>" + escapar(a) + "</b></td><td>" + pct(s.rentabilidad_anualizada) +
      '</td><td><input type="number" step="0.5" data-activo="' + escapar(a) +
      '" data-clave="rentabilidad"></td><td>' + pct(s.volatilidad_anualizada) +
      '</td><td><input type="number" step="0.5" min="0" data-activo="' + escapar(a) +
      '" data-clave="volatilidad"></td></tr>';
  }
  $("tablaSupuestos").innerHTML = html + "</table>";
}
function escenario(tipo) {
  $("rentabilidad").value = ""; $("volatilidad").value = "";
  $("tablaSupuestos").querySelectorAll("input").forEach(c => {
    const s = estado.datos.series.find(x => x.activo === c.dataset.activo);
    c.value = "";
    if (tipo === "estres") {
      if (c.dataset.clave === "volatilidad") c.value = (s.volatilidad_anualizada * 150).toFixed(1);
      else c.value = "0";
    } else if (tipo === "calma" && c.dataset.clave === "volatilidad") {
      c.value = (s.volatilidad_anualizada * 70).toFixed(1);
    }
  });
  avisar(tipo === "base" ? "Se usará el histórico." : "Escenario aplicado: pulsa Simular.");
}
function supuestosPorActivo() {
  const supuestos = {};
  $("tablaSupuestos").querySelectorAll("input").forEach(c => {
    if (c.value.trim() === "") return;
    supuestos[c.dataset.activo] = supuestos[c.dataset.activo] || {};
    supuestos[c.dataset.activo][c.dataset.clave] = Number(c.value);
  });
  return supuestos;
}
async function simular() {
  const distribucion = segmentado("distribucion");
  const datos = { objetivo: $("objetivo").value, n_simulaciones: valorCampo("nSim"),
    horizonte: Number($("horizonte").value), distribucion: distribucion,
    grados_libertad: distribucion === "t" ? valorCampo("grados") : null,
    rebalanceo: $("rebalanceo").checked, semilla: valorCampo("semilla"),
    rentabilidad: valorCampo("rentabilidad"), volatilidad: valorCampo("volatilidad"),
    supuestos: supuestosPorActivo(), valor_inicial: valorCampo("valorInicial"),
    comparar: $("comparar").checked };
  const r = await llamar("montecarlo", datos, $("botonMc"));
  if (r.error) { mensajes("mensajesMc", [r.error]); return; }
  mensajes("mensajesMc", []);
  const s = r.resumen;
  const nombreDist = { normal: "normal", t: "t de Student (ν = " + num(s.grados_libertad, 1) + ")",
                       bootstrap: "bootstrap histórico" }[s.distribucion];
  $("tituloMc").textContent = "Resultado: " + s.objetivo + " · " + num(s.n_simulaciones, 0) +
    " simulaciones · " + s.horizonte_sesiones + " sesiones · " + nombreDist;
  $("kpisMc").innerHTML = kpis([
    ["Valor inicial", num(s.valor_inicial)],
    ["Valor final mediano", num(s.valor_final_mediano), signo(s.valor_final_mediano - s.valor_inicial)],
    ["Percentil 5 – 95", num(s.valor_final_p5) + " – " + num(s.valor_final_p95)],
    ["Rentabilidad media", pct(s.rentabilidad_media), signo(s.rentabilidad_media)],
    ["Probabilidad de pérdida", pct(s.probabilidad_perdida, 1)],
    ["VaR 95 %", pct(s.var_95, 1), "neg"], ["CVaR 95 %", pct(s.cvar_95, 1), "neg"],
    ["VaR 99 %", pct(r.var_99, 1), "neg"], ["CVaR 99 %", pct(r.cvar_99, 1), "neg"]]);
  graficoLineas($("graficoAbanico"), r.percentiles, { formato: v => num(v), ancho: 520,
    referencia: s.valor_inicial, banda: [["p5", "p95", 0.12], ["p25", "p75", 0.2]],
    gruesas: ["p50"], colores: { p5: "#1f5fbf", p25: "#1f5fbf", p50: "#18202b", p75: "#1f5fbf",
                                 p95: "#1f5fbf" }, leyenda: true });
  graficoHistograma($("graficoHistograma"), r.histograma);
  if (r.comparacion) {
    const maximo = Math.max(...r.comparacion.map(f => f.cvar_99));
    const barra = v => pct(v, 1) + '<span class="barra" style="background:#e03131;width:' +
      (v / maximo * 70) + 'px"></span>';
    let html = "<h3>Riesgo de cola según la distribución</h3><p class=\"nota\">Misma rentabilidad " +
      "y volatilidad; solo cambia la forma de las colas. La normal suele quedarse corta.</p>";
    html += '<div class="tabla"><table><tr><th>Distribución</th><th>VaR 95 %</th><th>CVaR 95 %</th>' +
      "<th>VaR 99 %</th><th>CVaR 99 %</th><th>Prob. pérdida</th><th>Valor mediano</th></tr>";
    for (const f of r.comparacion) {
      html += "<tr><td>" + escapar(f.distribucion) + "</td><td>" + barra(f.var_95) + "</td><td>" +
        barra(f.cvar_95) + "</td><td>" + barra(f.var_99) + "</td><td>" + barra(f.cvar_99) +
        "</td><td>" + pct(f.probabilidad_perdida, 1) + "</td><td>" + num(f.valor_final_mediano) +
        "</td></tr>";
    }
    $("comparacionMc").innerHTML = html + "</table></div>";
  } else {
    $("comparacionMc").innerHTML = "";
  }
  galeria($("galeriaMc"), r.graficos);
  $("resultadoMc").classList.remove("oculto");
  marcarHecha("montecarlo", true);
}

// ===================================================================
// 5. Informe
// ===================================================================
async function generarInforme() {
  const datos = { formato: segmentado("formato"), tasa_libre_riesgo: valorCampo("tasa"),
    usar_indice: $("usarIndice").checked, incluir_montecarlo: $("incluirMc").checked,
    simulaciones: valorCampo("simInforme"), incluir_graficos: $("incluirGraficos").checked,
    max_volatilidad: valorCampo("maxVol"), max_drawdown: valorCampo("maxDd"),
    min_sharpe: valorCampo("minSharpe"), max_concentracion: valorCampo("maxConc"),
    max_correlacion: valorCampo("maxCorr"), confianza_es: valorCampo("confianza") };
  const r = await llamar("informe", datos, $("botonInforme"));
  if (r.error) { mensajes("mensajesInforme", [r.error]); return; }
  mensajes("mensajesInforme", []);
  estado.informe = r;
  if (r.formato === "html") {
    $("resultadoInforme").innerHTML = '<iframe id="marco" sandbox title="Informe"></iframe>';
    $("marco").srcdoc = r.contenido;
  } else {
    $("resultadoInforme").innerHTML = "<pre>" + escapar(r.contenido) + "</pre>";
  }
  $("botonPestana").classList.toggle("oculto", r.formato !== "html");
  $("botonDescargar").classList.remove("oculto");
  marcarHecha("informe", true);
}
function descargarInforme() {
  const r = estado.informe;
  if (r.formato === "html") descargarTexto(r.contenido, "text/html", "informe.html");
  else descargarTexto(r.contenido, "text/markdown", "informe.md");
}
function abrirInforme() {
  const url = URL.createObjectURL(new Blob([estado.informe.contenido], { type: "text/html" }));
  window.open(url, "_blank");
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

// ===================================================================
// 6. Macro
// ===================================================================
async function descargarMacro() {
  const datos = { series: estado.macroElegidas, inicio: $("inicioMacro").value,
                  fin: $("finMacro").value };
  const r = await llamar("macro", datos, $("botonMacro"));
  if (r.error) { mensajes("mensajesMacro", [r.error]); return; }
  mensajes("mensajesMacro", [], r.avisos);
  let html = '<div class="tabla"><table><tr><th>Serie</th><th>Nombre</th><th>Unidad</th>' +
    "<th>Periodo</th><th>Último</th><th>Media</th><th>Desv. típica</th></tr>";
  for (const s of r.series) {
    html += "<tr><td><b>" + escapar(s.id) + "</b></td><td>" + escapar(s.nombre) + "</td><td>" +
      escapar(s.unidad || "") + "</td><td>" + escapar(s.inicio) + " → " + escapar(s.fin) +
      "</td><td>" + num(s.ultimo_valor) + "</td><td>" + num(s.media) + "</td><td>" +
      num(s.desviacion_tipica) + "</td></tr>";
  }
  html += '</table></div><div class="rejilla" id="graficosMacro"></div>';
  $("resultadoMacro").innerHTML = html;
  r.series.forEach((s, i) => {
    const caja = document.createElement("div");
    caja.innerHTML = "<h3>" + escapar(s.nombre) + "</h3><div></div>";
    $("graficosMacro").appendChild(caja);
    const colores = {};
    colores[s.id] = COLORES[i % COLORES.length];
    graficoLineas(caja.lastElementChild, s.grafico, { alto: 300, ancho: 520, colores: colores });
  });
}

iniciar();
</script>
</body>
</html>
"""
