# Scouts: integración del menú

Este paquete agrega un menú general y submenús para elegir consultas y parámetros.
Está preparado sobre el archivo "Scouts-main (3).zip" revisado. No contiene datos,
esquemas ni cargadores nuevos.

## Qué copiar

Copia estos archivos a la raíz REAL de tu proyecto, conservando las rutas:

- main.py
- scouts_menu_utils.py
- requirements.txt
- Mongo/main.py
- Cassandra/main.py
- Dgraph/main.py
- README_MENU.md
- VERIFICACION_MENU.json

En el ZIP original la raíz real está dentro de:
Scouts-main (2)/Scouts-main/
Es la carpeta donde ya están Mongo/, Cassandra/, Dgraph/, data/ y README.md.
Si usas el clon de C:\Users\nacho\Downloads\Scouts, copia allí los archivos.

Las carpetas Mongo/, Cassandra/ y Dgraph/ se combinan con las existentes:
reemplaza únicamente su main.py. Conserva sus connect.py, populate.py,
mongo_setup.py y esquemas. Conserva todos los JSON de data/.

## Preparar Python

El entorno antiguo C:\Users\nacho\.venv no arrancó durante la revisión:
su pyvenv.cfg apunta a una instalación Python312 que no está disponible.
Crea un entorno nuevo dentro de la raíz del proyecto.

Usa una instalación normal de Python 3.12 para Windows con el lanzador py.
Si "py -3.12 --version" no funciona, instala Python 3.12 para Windows y abre
una terminal nueva de Visual Studio Code.

Desde la raíz del proyecto:

    py -3.12 -m venv .venv_menu
    .\.venv_menu\Scripts\python.exe -m pip install -r requirements.txt

No hace falta activar el entorno: los comandos siguientes usan su ruta completa.

## Iniciar las bases

Abre Docker Desktop. Si conservas los contenedores ya utilizados:

    docker start mongodb scouts-cassandra scouts-dgraph scouts-ratel

Las conexiones del ZIP original se conservan:
MongoDB localhost:27017, base scouts_db;
Cassandra 127.0.0.1:9042, keyspace scouts;
Dgraph localhost:9180 por gRPC (HTTP 8180 y Ratel 8100 en tus contenedores).

Si tus contenedores tienen otros nombres o puertos, comprueba sus conexiones
antes de cargar. No se cambian ni crean contenedores desde el menú.

## Abrir el menú

Desde la raíz del proyecto:

    .\.venv_menu\Scripts\python.exe main.py

Menú general:

    1. MongoDB: elegir consulta
    2. Cassandra: elegir consulta
    3. Dgraph: elegir consulta
    4. Carga de datos
    0. Salir

Elegir una base abre su submenú. Después de ejecutar una consulta vuelve a ese
submenú. Usa 0 para regresar al menú general.
Enter acepta el valor que aparece entre corchetes.

## Consultas disponibles

MongoDB:
1 plantilla por equipo y temporada;
2 resumen de partido;
3 estadísticas de jugador por temporada;
4 posición, estado y rango de edad;
5 contratos próximos a vencer en un número de días;
6 clasificación por competición y temporada;
7 top goleadores por temporada con límite;
8 masa salarial por equipo;
9 ejecutar las ocho.

Cassandra:
1 eventos; 2 biometría; 3 marcador; 4 estadísticas por intervalos;
5 faltas; 6 interrupciones; 7 ejecutar las seis.
Solicita partido y, en biometría/intervalos, también jugador.

Dgraph:
1 pertenencia (2.1); 2 participación (2.2); 3 agencias (2.3);
4 pases (2.4); 5 coincidencia en victorias (2.5); 6 ejecutar las cinco.
Agencias solicita jugador; pases solicita equipo; victorias solicita equipo
y mínimo de jugadores. Los valores se pasan como parámetros DQL.

## Pruebas de presentación

Con el dataset Liga MX que ya cargaste:

1. Menú general 3 (Dgraph), submenú 3 (agencias), jugador p_01.
   Esperado: Luis Malagón y su agencia con 12 representados.
2. Submenú 4 (pases), equipo t_01.
   Esperado: los cuatro jugadores del América y sus relaciones de pases.
3. Submenú 5 (victorias), equipo t_01, mínimo 3.
   Esperado: m_01 con cantidad_jugadores = 4.
4. Repite la opción 5 con mínimo 5.
   Esperado: grupos_en_victorias vacío.
5. Usa 0 para volver. Menú general 2, submenú 2:
   partido m_01 y jugador p_01. Esperado: sus mediciones biométricas.
6. Vuelve con 0. Menú general 1, submenú 1:
   equipo t_01 y temporada 2026-2027. Esperado: plantilla del América
   con cuatro integrantes en el campo roster.
7. Prueba una opción de menú no válida: debe pedir otra sin cerrarse.
8. Prueba texto donde se pide un número: debe solicitar un entero.

Fechas de nacimiento, rol adicional CM, partidos, pases, agencias, contratos
y estadísticas son simulados según dataset_sources.json.
La consulta 2.5 encuentra jugadores que coinciden en victorias; se presenta
como aproximación para estudiar alineaciones.

## Cargar datos cuando sea necesario

Las consultas no cargan ni reinician datos automáticamente.
Si los datos ya están cargados, entra directamente a las consultas.

En menú general 4 puedes seleccionar una base o las tres.
Antes de ejecutar los cargadores de Cassandra o Dgraph hay que escribir
REINICIAR. Enter cancela la operación.

Los cargadores originales NO se modifican:
- Cassandra elimina y reconstruye el keyspace scouts.
- Dgraph vacía la instancia configurada y vuelve a cargar.
- MongoDB agrega/actualiza por ID, pero no elimina documentos sobrantes.
Por eso "cargar las tres" no es una sustitución completa de MongoDB si tiene
otros IDs anteriores. Este menú no borra colecciones de MongoDB.

Si falla un cargador, la secuencia se detiene. No existe una transacción
conjunta entre las tres bases: las cargas terminadas no se deshacen.

## También funciona sin menú

Se conservan las funciones públicas run_queries, run_realtime_queries y
run_dgraph_queries con sus valores predeterminados.

Ejemplos desde la raíz:

    .\.venv_menu\Scripts\python.exe Dgraph\main.py --consulta 2.3 --jugador p_01
    .\.venv_menu\Scripts\python.exe Dgraph\main.py --consulta 2.5 --equipo t_01 --minimo 5
    .\.venv_menu\Scripts\python.exe Cassandra\main.py --consulta 2 --partido m_01 --jugador p_01
    .\.venv_menu\Scripts\python.exe Mongo\main.py --consulta 1 --equipo t_01 --temporada 2026-2027

Con --menu se abre el submenú de cada base.
Sin argumentos, los main.py de cada base ejecutan todas sus consultas;
el main.py de la raíz siempre abre el menú general.

## Comprobaciones realizadas y límites

Los cuatro componentes pasaron 28 comprobaciones mediante dobles de prueba
en memoria: selección individual, parámetros, validación de entradas,
cierre de conexiones, error de procesos, cancelación y detención de cargas.
El CQL de las seis consultas Cassandra coincide con el original.

No se ejecutó ningún cargador ni se escribió en una base para preparar este paquete.
La prueba de lectura real de Dgraph no pudo realizarse porque localhost:8180
rechazó la conexión. MongoDB y Cassandra no se probaron contra servicios reales.
VERIFICACION_MENU.json conserva el alcance de las pruebas.

## GitHub

Después de probar, publica estos ocho archivos conservando sus rutas.
No subas .venv_menu/, __pycache__/ ni contraseñas.
Los JSON, esquemas y cargadores del proyecto se conservan.

## Referencias técnicas

- Parámetros DQL: https://docs.dgraph.io/dql/query/graphql-variables/
- Procesos y códigos de salida: https://docs.python.org/3.12/library/subprocess.html
- Python para Windows: https://www.python.org/downloads/windows/
