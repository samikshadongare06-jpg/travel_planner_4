CREATE TABLE users (
  user_id        INT PRIMARY KEY AUTO_INCREMENT,
  email          VARCHAR(255) NOT NULL UNIQUE,
  password_hash  VARCHAR(255) NOT NULL,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE destinations (
  destination_id   INT PRIMARY KEY AUTO_INCREMENT,
  name             VARCHAR(255) NOT NULL,
  state            VARCHAR(255),
  country          VARCHAR(255) NOT NULL DEFAULT 'India',
  central_zone_id  INT  -- preferred zone for accommodation (set after zones created)
);

CREATE TABLE zones (
  zone_id         INT PRIMARY KEY AUTO_INCREMENT,
  destination_id  INT NOT NULL,
  name            VARCHAR(255) NOT NULL,
  FOREIGN KEY (destination_id) REFERENCES destinations(destination_id)
);

-- Update destinations after zones are created
-- ALTER TABLE destinations ADD FOREIGN KEY (central_zone_id) REFERENCES zones(zone_id);

CREATE TABLE zone_nearby (
  zone_id         INT NOT NULL,
  nearby_zone_id  INT NOT NULL,
  PRIMARY KEY (zone_id, nearby_zone_id),
  FOREIGN KEY (zone_id)        REFERENCES zones(zone_id),
  FOREIGN KEY (nearby_zone_id) REFERENCES zones(zone_id)
);

CREATE TABLE travel_terminals (
  terminal_id     INT PRIMARY KEY AUTO_INCREMENT,
  destination_id  INT NOT NULL,
  name            VARCHAR(255) NOT NULL,
  type            ENUM('airport', 'station') NOT NULL,
  FOREIGN KEY (destination_id) REFERENCES destinations(destination_id)
);

-- which zones are near this terminal, in priority order
CREATE TABLE terminal_zones (
  terminal_id  INT NOT NULL,
  zone_id      INT NOT NULL,
  priority     INT NOT NULL,  -- 1 = closest, 2 = second closest etc
  PRIMARY KEY (terminal_id, zone_id),
  FOREIGN KEY (terminal_id) REFERENCES travel_terminals(terminal_id),
  FOREIGN KEY (zone_id)     REFERENCES zones(zone_id)
);

CREATE TABLE attractions (
  attraction_id      INT PRIMARY KEY AUTO_INCREMENT,
  destination_id     INT NOT NULL,
  zone_id            INT NOT NULL,
  name               VARCHAR(255) NOT NULL,
  rating             DECIMAL(2,1) NOT NULL,   -- 1.0 to 5.0
  avg_time_minutes   INT NOT NULL,             -- average time spent here
  is_mustdo          BOOLEAN NOT NULL DEFAULT FALSE,
  is_strenuous       BOOLEAN NOT NULL DEFAULT FALSE,
  food_availability  ENUM('none', 'nearby', 'integrated') NOT NULL,
  recommended_time   VARCHAR(10),              -- 'morning', 'evening', 'anytime'
  FOREIGN KEY (destination_id) REFERENCES destinations(destination_id),
  FOREIGN KEY (zone_id)        REFERENCES zones(zone_id)
);

CREATE TABLE attraction_tags (
  attraction_id  INT NOT NULL,
  tag            ENUM(
                   'adventure','scenic','cultural','historical',
                   'relaxed','foodie','nature','spiritual','urban','offbeat'
                 ) NOT NULL,
  PRIMARY KEY (attraction_id, tag),
  FOREIGN KEY (attraction_id) REFERENCES attractions(attraction_id)
);

CREATE TABLE accommodations (
  accommodation_id  INT PRIMARY KEY AUTO_INCREMENT,
  destination_id    INT NOT NULL,
  zone_id           INT NOT NULL,
  name              VARCHAR(255) NOT NULL,
  type              ENUM('budget','3-star','4-star','5-star') NOT NULL,
  max_capacity      INT NOT NULL,
  FOREIGN KEY (destination_id) REFERENCES destinations(destination_id),
  FOREIGN KEY (zone_id)        REFERENCES zones(zone_id)
);

CREATE TABLE travel_routes (
  route_id        INT PRIMARY KEY AUTO_INCREMENT,
  origin_city     VARCHAR(255) NOT NULL,  -- e.g. 'Pune'
  destination_id  INT NOT NULL,
  travel_mode     ENUM('flight','train','car') NOT NULL,
  avg_hours       DECIMAL(4,1) NOT NULL,
  FOREIGN KEY (destination_id) REFERENCES destinations(destination_id)
);

-- ============================================================
-- LAYER 2: TRIP DATA (created when user submits form)
-- ============================================================

CREATE TABLE trips (
  trip_id             INT PRIMARY KEY AUTO_INCREMENT,
  user_id             INT NOT NULL,
  destination_id      INT NOT NULL,
  start_date          DATE NOT NULL,
  end_date            DATE NOT NULL,
  num_people          INT NOT NULL DEFAULT 1,
  travel_mode         ENUM('flight','train','car') NOT NULL,
  accommodation_type  ENUM('budget','3-star','4-star','5-star') NOT NULL,
  sleep_hours         INT NOT NULL DEFAULT 8,
  meals_per_day       INT NOT NULL DEFAULT 3,
  sleep_time          TIME NOT NULL DEFAULT '22:00:00',   -- when they sleep
  wake_time           TIME NOT NULL DEFAULT '07:00:00',   -- when they wake
  priority_order      JSON NOT NULL,  -- e.g. ["exploring","meals","rest","sleep"]
  flexibility         ENUM('strict','moderate','flexible') NOT NULL DEFAULT 'moderate',
  origin_city         VARCHAR(255) NOT NULL,
  arrival_terminal_id   INT,   -- null if car
  departure_terminal_id INT,   -- null if car
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)               REFERENCES users(user_id),
  FOREIGN KEY (destination_id)        REFERENCES destinations(destination_id),
  FOREIGN KEY (arrival_terminal_id)   REFERENCES travel_terminals(terminal_id),
  FOREIGN KEY (departure_terminal_id) REFERENCES travel_terminals(terminal_id)
);

CREATE TABLE trip_vibes (
  trip_id  INT NOT NULL,
  vibe     ENUM(
             'adventure','scenic','cultural','historical',
             'relaxed','foodie','nature','spiritual','urban','offbeat'
           ) NOT NULL,
  PRIMARY KEY (trip_id, vibe),
  FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
);

CREATE TABLE trip_meal_timings (
  timing_id     INT PRIMARY KEY AUTO_INCREMENT,
  trip_id       INT NOT NULL,
  meal_type     ENUM('breakfast','lunch','dinner','snack') NOT NULL,
  preferred_start_minutes INT NOT NULL,  -- minutes from midnight e.g. 480 = 8:00am
  preferred_end_minutes   INT NOT NULL,
  FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
);

-- ============================================================
-- LAYER 3: GENERATED ITINERARY (written by algorithm)
-- ============================================================

CREATE TABLE itinerary_days (
  day_id      INT PRIMARY KEY AUTO_INCREMENT,
  trip_id     INT NOT NULL,
  day_number  INT NOT NULL,   -- 1, 2, 3...
  zone_id     INT NOT NULL,
  FOREIGN KEY (trip_id)  REFERENCES trips(trip_id),
  FOREIGN KEY (zone_id)  REFERENCES zones(zone_id)
);

CREATE TABLE itinerary_items (
  item_id        INT PRIMARY KEY AUTO_INCREMENT,
  day_id         INT NOT NULL,
  attraction_id  INT,    -- nullable: meals/rest/travel have no attraction
  slot_type      ENUM('attraction','meal','rest','travel','sleep') NOT NULL,
  meal_type      ENUM('breakfast','lunch','dinner','snack'),  -- only if slot_type=meal
  start_time     INT NOT NULL,   -- minutes from midnight (e.g. 540 = 9:00am)
  end_time       INT NOT NULL,   -- minutes from midnight
  notes          VARCHAR(255),   -- e.g. "travel to destination" or "rest time"
  FOREIGN KEY (day_id)        REFERENCES itinerary_days(day_id),
  FOREIGN KEY (attraction_id) REFERENCES attractions(attraction_id)
);

CREATE TABLE accommodation_pick (
  trip_id           INT PRIMARY KEY,
  accommodation_id  INT NOT NULL,
  FOREIGN KEY (trip_id)          REFERENCES trips(trip_id),
  FOREIGN KEY (accommodation_id) REFERENCES accommodations(accommodation_id)
);

-- ============================================================
-- OPTIONAL: SAVED PLANS (user explicitly saves)
-- ============================================================

CREATE TABLE saved_trip_plans (
  trip_id    INT PRIMARY KEY,
  saved_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
);




