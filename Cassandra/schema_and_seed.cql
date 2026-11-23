-- ============================================================================
-- PROYECTO: SCOUTS - MÓDULO APACHE CASSANDRA (SINCRONIZADO CON /data)
-- ============================================================================

DROP KEYSPACE IF EXISTS scouts;

CREATE KEYSPACE scouts
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

USE scouts;

-- ----------------------------------------------------------------------------
-- TABLA 1: match_events (Req. 3.1: Ingesta de Eventos Play-by-Play)
-- ----------------------------------------------------------------------------
CREATE TABLE scouts.match_events (
    match_id text,
    event_timestamp timestamp,
    event_id text,
    player_id text,
    player_name text,
    team_id text,
    team_name text,
    event_type text,
    details map<text, text>,
    PRIMARY KEY ((match_id), event_timestamp, event_id)
) WITH CLUSTERING ORDER BY (event_timestamp DESC, event_id ASC);

-- ----------------------------------------------------------------------------
-- TABLA 2: player_biometrics (Req. 3.2 y 3.5: Telemetría Biométrica y Fatiga)
-- ----------------------------------------------------------------------------
CREATE TABLE scouts.player_biometrics (
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
-- ----------------------------------------------------------------------------
CREATE TABLE scouts.live_scoreboard (
    match_id text,
    match_period int,
    match_minute int,
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
-- ----------------------------------------------------------------------------
CREATE TABLE scouts.player_interval_stats (
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
-- ----------------------------------------------------------------------------
CREATE TABLE scouts.match_fouls (
    match_id text,
    foul_timestamp timestamp,
    foul_id text,
    offending_player_id text,
    offending_player_name text,
    drawn_by_player_id text,
    drawn_by_player_name text,
    card_type text,
    PRIMARY KEY ((match_id), foul_timestamp, foul_id)
) WITH CLUSTERING ORDER BY (foul_timestamp DESC, foul_id ASC);

-- ----------------------------------------------------------------------------
-- TABLA 6: match_stoppages (Req. 3.7: Registro de Interrupciones VAR / Asistencia Médica)
-- ----------------------------------------------------------------------------
CREATE TABLE scouts.match_stoppages (
    match_id text,
    start_timestamp timestamp,
    stoppage_type text,
    duration_seconds int,
    referee_decision text,
    PRIMARY KEY ((match_id), start_timestamp)
) WITH CLUSTERING ORDER BY (start_timestamp DESC);


