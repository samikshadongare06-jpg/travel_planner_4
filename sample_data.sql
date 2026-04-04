INSERT INTO destinations (destination_id, name, state, country) VALUES
(1, 'Mahabaleshwar', 'Maharashtra', 'India');

-- ============================================================
-- ZONES
-- (central_zone_id updated after zones inserted)
-- ============================================================

INSERT INTO zones (zone_id, destination_id, name) VALUES
(1, 1, 'Mahabaleshwar Town'),   -- market, temples, mapro
(2, 1, 'Panchgani'),            -- tablelands, strawberry farms
(3, 1, 'Venna Lake Area'),      -- lake, waterfalls
(4, 1, 'Viewpoints Ridge');     -- wilson point, arthurs seat, kates point

UPDATE destinations SET central_zone_id = 1 WHERE destination_id = 1;

-- ============================================================
-- ZONE ADJACENCY GRAPH
-- Town(1) <-> Panchgani(2) <-> Ridge(4) <-> Venna(3) <-> Town(1)
-- ============================================================

INSERT INTO zone_nearby (zone_id, nearby_zone_id) VALUES
(1, 2), (1, 3),   -- Town is near Panchgani and Venna Lake
(2, 1), (2, 4),   -- Panchgani is near Town and Ridge
(3, 1), (3, 4),   -- Venna Lake is near Town and Ridge
(4, 2), (4, 3);   -- Ridge is near Panchgani and Venna Lake

-- ============================================================
-- TRAVEL TERMINALS (destination-side)
-- ============================================================

-- Mahabaleshwar area doesn't have a major airport/station in-town,
-- but for planning we keep "nearest" destination-side terminals.
INSERT INTO travel_terminals (terminal_id, destination_id, name, type) VALUES
(101, 1, 'Wathar Station (for Mahabaleshwar)', 'station'),
(102, 1, 'Pune Airport (nearest for Mahabaleshwar)', 'airport');

INSERT INTO terminal_zones (terminal_id, zone_id, priority) VALUES
(101, 3, 1),  -- arriving via Wathar: Venna area first
(101, 1, 2),
(102, 1, 1),  -- arriving via Pune airport: Town first
(102, 3, 2);

-- ============================================================
-- ATTRACTIONS
-- ============================================================

INSERT INTO attractions 
(attraction_id, destination_id, zone_id, name, rating, avg_time_minutes, 
 is_mustdo, is_strenuous, food_availability, recommended_time) VALUES

-- Zone 1: Town
(1,  1, 1, 'Mapro Garden',           4.4, 90,  FALSE, FALSE, 'integrated', 'anytime'),
(2,  1, 1, 'Krishnabai Temple',      4.0, 45,  FALSE, FALSE, 'none',       'morning'),
(3,  1, 1, 'Mahabaleshwar Temple',   4.3, 60,  FALSE, FALSE, 'none',       'morning'),
(4,  1, 1, 'Old Mahabaleshwar',      3.9, 90,  FALSE, FALSE, 'nearby',     'anytime'),

-- Zone 2: Panchgani
(5,  1, 2, 'Panchgani Tablelands',   4.5, 150, TRUE,  FALSE, 'nearby',     'morning'),
(6,  1, 2, 'Strawberry Farm Visit',  4.1, 90,  FALSE, FALSE, 'integrated', 'anytime'),
(7,  1, 2, 'Pratapgad Fort',         4.6, 180, TRUE,  TRUE,  'nearby',     'morning'),
(8,  1, 2, 'Sydney Point Panchgani', 4.0, 60,  FALSE, FALSE, 'none',       'evening'),

-- Zone 3: Venna Lake
(9,  1, 3, 'Venna Lake Boating',     4.3, 120, FALSE, FALSE, 'nearby',     'anytime'),
(10, 1, 3, 'Lingmala Waterfall',     4.3, 120, TRUE,  TRUE,  'none',       'morning'),
(11, 1, 3, 'Dhobi Waterfall',        3.8, 60,  FALSE, FALSE, 'none',       'anytime'),
(12, 1, 3, 'Chinaman Waterfall',     3.7, 45,  FALSE, FALSE, 'none',       'anytime'),

-- Zone 4: Viewpoints Ridge
(13, 1, 4, 'Wilson Point (Sunrise)', 4.6, 60,  TRUE,  FALSE, 'nearby',     'morning'),
(14, 1, 4, 'Arthurs Seat',           4.5, 90,  FALSE, FALSE, 'none',       'anytime'),
(15, 1, 4, 'Kates Point',            4.2, 60,  FALSE, FALSE, 'none',       'evening');

-- ============================================================
-- ATTRACTION TAGS
-- ============================================================

INSERT INTO attraction_tags (attraction_id, tag) VALUES
-- Mapro Garden
(1, 'foodie'), (1, 'relaxed'),
-- Krishnabai Temple
(2, 'spiritual'), (2, 'cultural'),
-- Mahabaleshwar Temple
(3, 'spiritual'), (3, 'historical'),
-- Old Mahabaleshwar
(4, 'historical'), (4, 'cultural'),
-- Panchgani Tablelands
(5, 'scenic'), (5, 'adventure'), (5, 'nature'),
-- Strawberry Farm
(6, 'nature'), (6, 'foodie'), (6, 'offbeat'),
-- Pratapgad Fort
(7, 'historical'), (7, 'adventure'), (7, 'scenic'),
-- Sydney Point
(8, 'scenic'), (8, 'relaxed'),
-- Venna Lake Boating
(9, 'scenic'), (9, 'relaxed'),
-- Lingmala Waterfall
(10, 'nature'), (10, 'adventure'), (10, 'scenic'),
-- Dhobi Waterfall
(11, 'nature'), (11, 'scenic'),
-- Chinaman Waterfall
(12, 'nature'), (12, 'offbeat'),
-- Wilson Point
(13, 'scenic'), (13, 'nature'),
-- Arthurs Seat
(14, 'scenic'), (14, 'adventure'),
-- Kates Point
(15, 'scenic'), (15, 'relaxed');

-- ============================================================
-- ACCOMMODATIONS
-- ============================================================

INSERT INTO accommodations 
(accommodation_id, destination_id, zone_id, name, type, max_capacity) VALUES
(1, 1, 1, 'Brightland Resort & Spa',   '5-star', 100),
(2, 1, 1, 'Evershine Keys Prima',      '4-star', 80),
(3, 1, 1, 'Hotel Dreamland',           '3-star', 40),
(4, 1, 3, 'Venna Lake Resort',         '3-star', 30),
(5, 1, 2, 'Grape County Eco Resort',   '4-star', 50),
(6, 1, 4, 'Le Meridien Mahabaleshwar', '5-star', 120);

-- ============================================================
-- TRAVEL ROUTES
-- ============================================================

INSERT INTO travel_routes 
(route_id, origin_city, destination_id, travel_mode, avg_hours) VALUES
(1, 'Pune',   1, 'car',   3.0),
(2, 'Mumbai', 1, 'car',   4.5),
(3, 'Pune',   1, 'train', 4.0),  -- Pune to Wathar station + cab
(4, 'Mumbai', 1, 'train', 5.0);

-- ============================================================
-- SAMPLE USER AND TRIP
-- (for testing the algorithm)
-- ============================================================

INSERT INTO users (user_id, email, password_hash) VALUES
(1, 'test@example.com', 'password');

INSERT INTO trips (
  trip_id, user_id, destination_id, 
  start_date, end_date, num_people,
  travel_mode, accommodation_type,
  sleep_hours, meals_per_day,
  sleep_time, wake_time,
  priority_order, flexibility,
  origin_city, arrival_terminal_id, departure_terminal_id
) VALUES (
  1, 1, 1,
  '2026-04-10', '2026-04-13', 2,
  'car', '4-star',
  8, 3,
  '22:30:00', '06:30:00',
  '["exploring","meals","rest","sleep"]', 'moderate',
  'Pune', NULL, NULL  -- car travel, no terminal
);

INSERT INTO trip_vibes (trip_id, vibe) VALUES
(1, 'scenic'),
(1, 'nature'),
(1, 'adventure');

INSERT INTO trip_meal_timings 
(trip_id, meal_type, preferred_start_minutes, preferred_end_minutes) VALUES
(1, 'breakfast', 420, 480),   -- 7:00am to 8:00am
(1, 'lunch',     780, 840),   -- 1:00pm to 2:00pm
(1, 'dinner',    1140, 1200); -- 7:00pm to 8:00pm