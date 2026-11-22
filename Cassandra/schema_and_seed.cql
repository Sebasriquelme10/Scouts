-- PROYECTO: SCOUTS - MÓDULO APACHE CASSANDRA (TIME-SERIES / TIEMPO REAL)
 
CREATE KEYSPACE IF NOT EXISTS scouts
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

USE scouts;

-- ----------------------------------------------------------------------------
-- TABLA 1: match_events (Req. 3.1: Ingesta de Eventos Play-by-Play)
-- Modificación aplicada: Se agregan player_name y team_name.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scouts.match_events (
    match_id text,
    event_timestamp timestamp,
    event_id text,
    player_id text,
    player_name text,
    team_id text,
    team_name text,
    event_type text,          -- Valores del documento: 'shot', 'pass', 'foul', 'steal'
    details map<text, text>,  -- Mapa de metadatos del evento
    PRIMARY KEY ((match_id), event_timestamp, event_id)
) WITH CLUSTERING ORDER BY (event_timestamp DESC, event_id ASC);

-- ----------------------------------------------------------------------------
-- TABLA 2: player_biometrics (Req. 3.2 y 3.5: Telemetría Biométrica y Fatiga)
-- Sin cambios estructurales: Partition Key compuesta (match_id, player_id).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scouts.player_biometrics (
    match_id text,
    player_id text,
    timestamp timestamp,
    heart_rate int,
    instant_speed_kmh float,
    distance_covered_meters float,
    PRIMARY KEY ((match_id, player_id), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- ----------------------------------------------------------------------------
-- TABLA 3: live_scoreboard (Req. 3.3: Historial de Marcador Dinámico en Vivo)
-- Modificaciones aplicadas:
--   1. Se agregan equipos enfrentándose (home_team_id, home_team_name, away_team_id, away_team_name).
--   2. Se reemplaza 'quarte_period' / 'quarter_period' y 'game_time_remaining'
--      por 'match_period' (tiempo del partido de fútbol) y 'match_minute'.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scouts.live_scoreboard (
    match_id text,
    match_period int,         -- 1: Primer Tiempo, 2: Segundo Tiempo, 3: Tiempo Extra
    match_minute int,         -- Minuto progresivo del encuentro
    update_timestamp timestamp,
    home_team_id text,
    home_team_name text,
    away_team_id text,
    away_team_name text,
    home_score int,
    away_score int,
    scoring_player_id text,
    PRIMARY KEY ((match_id), match_period, match_minute, update_timestamp)
) WITH CLUSTERING ORDER BY (match_period ASC, match_minute ASC, update_timestamp DESC);

-- ----------------------------------------------------------------------------
-- TABLA 4: player_interval_stats (Req. 3.4: Estadísticas Dinámicas por Intervalos)
-- Modificaciones aplicadas:
--   1. Se elimina el tipo COUNTER (permite agregar datos de apoyo e idempotencia).
--   2. Se reemplaza 'points_counter' por métricas de fútbol del documento (goals, shots, passes, fouls).
--   3. Se agregan datos de apoyo: player_name, team_id, team_name, match_period, interval_minute.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scouts.player_interval_stats (
    match_id text,
    player_id text,
    interval_timestamp timestamp,
    player_name text,
    team_id text,
    team_name text,
    match_period int,
    interval_minute int,
    goals int,
    shots int,
    passes int,
    fouls int,
    PRIMARY KEY ((match_id, player_id), interval_timestamp)
) WITH CLUSTERING ORDER BY (interval_timestamp DESC);

-- ----------------------------------------------------------------------------
-- TABLA 5: match_fouls (Req. 3.6: Bitácora Cronológica de Faltas e Infracciones)
-- Modificación aplicada: Se agregan nombres de jugadores (offending_player_name, drawn_by_player_name).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scouts.match_fouls (
    match_id text,
    foul_timestamp timestamp,
    foul_id text,
    offending_player_id text,
    offending_player_name text,
    drawn_by_player_id text,
    drawn_by_player_name text,
    card_type text,           -- Ej. 'None', 'Yellow', 'Red'
    PRIMARY KEY ((match_id), foul_timestamp, foul_id)
) WITH CLUSTERING ORDER BY (foul_timestamp DESC, foul_id ASC);

-- ----------------------------------------------------------------------------
-- TABLA 6: match_stoppages (Req. 3.7: Registro de Interrupciones VAR / Asistencia Médica)
-- Sin cambios estructurales: almacena pausas para calcular tiempo de compensación.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scouts.match_stoppages (
    match_id text,
    start_timestamp timestamp,
    stoppage_type text,       -- Valores del documento: 'VAR', 'Medical', 'Hydration'
    duration_seconds int,
    referee_decision text,
    PRIMARY KEY ((match_id), start_timestamp)
) WITH CLUSTERING ORDER BY (start_timestamp DESC);


-- POBLADO DE DATOS DE PRUEBA (EXCLUSIVO PARA CASSANDRA)

-- 1. Poblado match_events
INSERT INTO scouts.match_events (
    match_id, event_timestamp, event_id, player_id, player_name, team_id, team_name, event_type, details
) VALUES (
    'M001', '2026-11-22 20:15:10+0000', 'E001', 'P010', 'Carlos Vega', 'T001', 'Guadalajara FC', 'pass',
    {'zone': 'midfield', 'outcome': 'completed'}
);

INSERT INTO scouts.match_events (
    match_id, event_timestamp, event_id, player_id, player_name, team_id, team_name, event_type, details
) VALUES (
    'M001', '2026-11-22 20:23:45+0000', 'E002', 'P010', 'Carlos Vega', 'T001', 'Guadalajara FC', 'shot',
    {'target': 'on_goal', 'result': 'goal'}
);

INSERT INTO scouts.match_events (
    match_id, event_timestamp, event_id, player_id, player_name, team_id, team_name, event_type, details
) VALUES (
    'M001', '2026-11-22 20:31:05+0000', 'E003', 'P024', 'Mateo Ríos', 'T002', 'Monterrey FC', 'foul',
    {'zone': 'defensive_third', 'severity': 'tactical'}
);

-- 2. Poblado player_biometrics
INSERT INTO scouts.player_biometrics (
    match_id, player_id, timestamp, heart_rate, instant_speed_kmh, distance_covered_meters
) VALUES (
    'M001', 'P010', '2026-11-22 20:23:40+0000', 176, 28.4, 3420.5
);

INSERT INTO scouts.player_biometrics (
    match_id, player_id, timestamp, heart_rate, instant_speed_kmh, distance_covered_meters
) VALUES (
    'M001', 'P010', '2026-11-22 20:23:45+0000', 184, 31.2, 3463.8
);

-- 3. Poblado live_scoreboard
INSERT INTO scouts.live_scoreboard (
    match_id, match_period, match_minute, update_timestamp,
    home_team_id, home_team_name, away_team_id, away_team_name,
    home_score, away_score, scoring_player_id
) VALUES (
    'M001', 1, 24, '2026-11-22 20:23:45+0000',
    'T001', 'Guadalajara FC', 'T002', 'Monterrey FC',
    1, 0, 'P010'
);

INSERT INTO scouts.live_scoreboard (
    match_id, match_period, match_minute, update_timestamp,
    home_team_id, home_team_name, away_team_id, away_team_name,
    home_score, away_score, scoring_player_id
) VALUES (
    'M001', 2, 68, '2026-11-22 21:23:12+0000',
    'T001', 'Guadalajara FC', 'T002', 'Monterrey FC',
    1, 1, 'P029'
);

-- 4. Poblado player_interval_stats (Sin COUNTER)
INSERT INTO scouts.player_interval_stats (
    match_id, player_id, interval_timestamp, player_name, team_id, team_name,
    match_period, interval_minute, goals, shots, passes, fouls
) VALUES (
    'M001', 'P010', '2026-11-22 20:30:00+0000', 'Carlos Vega', 'T001', 'Guadalajara FC',
    1, 30, 1, 2, 18, 0
);

INSERT INTO scouts.player_interval_stats (
    match_id, player_id, interval_timestamp, player_name, team_id, team_name,
    match_period, interval_minute, goals, shots, passes, fouls
) VALUES (
    'M001', 'P010', '2026-11-22 21:15:00+0000', 'Carlos Vega', 'T001', 'Guadalajara FC',
    2, 60, 1, 3, 34, 1
);

-- 5. Poblado match_fouls
INSERT INTO scouts.match_fouls (
    match_id, foul_timestamp, foul_id,
    offending_player_id, offending_player_name,
    drawn_by_player_id, drawn_by_player_name, card_type
) VALUES (
    'M001', '2026-11-22 20:31:05+0000', 'F001',
    'P024', 'Mateo Ríos',
    'P010', 'Carlos Vega', 'Yellow'
);

-- 6. Poblado match_stoppages
INSERT INTO scouts.match_stoppages (
    match_id, start_timestamp, stoppage_type, duration_seconds, referee_decision
) VALUES (
    'M001', '2026-11-22 20:31:15+0000', 'VAR', 95, 'Falta confirmada y tarjeta amarilla ratificada'
);


-- CONSULTAS DE VALIDACIÓN 

-- Q1 (Req. 3.1): Recuperar eventos en vivo de un partido en orden cronológico inverso
SELECT match_id, event_timestamp, event_id, player_name, team_name, event_type, details
FROM scouts.match_events
WHERE match_id = 'M001';

-- Q2 (Req. 3.2 y 3.5): Detectar fatiga biométrica de un jugador en una ventana de tiempo
SELECT match_id, player_id, timestamp, heart_rate, instant_speed_kmh, distance_covered_meters
FROM scouts.player_biometrics
WHERE match_id = 'M001'
  AND player_id = 'P010'
  AND timestamp >= '2026-11-22 20:20:00+0000';

-- Q3 (Req. 3.3): Consultar historial del marcador en vivo de un partido
SELECT match_id, match_period, match_minute, home_team_name, home_score, away_team_name, away_score, scoring_player_id
FROM scouts.live_scoreboard
WHERE match_id = 'M001';

-- Q4 (Req. 3.4): Consultar estadísticas dinámicas por intervalos de un jugador en el partido
SELECT match_id, player_id, player_name, team_name, match_period, interval_minute, goals, shots, passes, fouls
FROM scouts.player_interval_stats
WHERE match_id = 'M001'
  AND player_id = 'P010';

-- Q5 (Req. 3.6): Bitácora cronológica de faltas e infracciones de un partido
SELECT match_id, foul_timestamp, foul_id, offending_player_name, drawn_by_player_name, card_type
FROM scouts.match_fouls
WHERE match_id = 'M001';

-- Q6 (Req. 3.7): Interrupciones del partido (VAR / Medical / Hydration) para tiempo añadido
SELECT match_id, start_timestamp, stoppage_type, duration_seconds, referee_decision
FROM scouts.match_stoppages
WHERE match_id = 'M001';