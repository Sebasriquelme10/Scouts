#Descripción: Este archivo inyecta la información de los datasets deportivos.

# 1.- Importar las funciones de conexión desde connect.py y la librería csv/pandas.
# 2.- Llamar a esas funciones importadas para abrir la sesión con con MongoDB y Cassandra para poder usarlas en el script.
# 3.- Cargar en memoria los archivos estáticos ubicados en la carpeta /data
# 4.- Limpieza de datos o sea eliminar nulos y dar formato de fechas correcto a los contratos.
# 5.- Inserción en MongoDB: Mandar los perfiles de los jugadores, equipo y contratos a sus colleciones.
# 6.- Inserción en Cassandra: Mandar los eventos de partido minuto a minuto por su alta velocidad de escritura.
# 7.- Cerrar las conexiones e imprimir un mensaje en la consola para saber que todo se ejecutó correctamente.
