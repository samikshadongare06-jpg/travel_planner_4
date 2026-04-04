-- ============================================================
-- SAMPLE DATA: 4 DESTINATIONS
-- Manali, Konkan, Assam, Kerala
-- Each has: zones, adjacency, terminals, attractions,
--           tags, accommodations, travel routes
-- Run with: mysql -u root -p travel_planner < sample_data_destinations.sql
-- ============================================================


-- ============================================================
-- DESTINATION 2: MANALI, HIMACHAL PRADESH
-- 4 zones, 16 attractions
-- ============================================================

INSERT INTO destinations (destination_id, name, state, country)
VALUES (2, 'Manali', 'Himachal Pradesh', 'India');

INSERT INTO zones (zone_id, destination_id, name) VALUES
(5, 2, 'Manali Town'),          -- mall road, hadimba, manu temple
(6, 2, 'Solang Valley'),        -- snow point, zorbing, paragliding
(7, 2, 'Rohtang Pass Area'),    -- rohtang, beas kund trek
(8, 2, 'Old Manali & Vashisht');-- vashisht hot springs, cafes, river

UPDATE destinations SET central_zone_id = 5 WHERE destination_id = 2;

INSERT INTO zone_nearby (zone_id, nearby_zone_id) VALUES
(5, 6), (5, 8),
(6, 5), (6, 7),
(7, 6),
(8, 5);

INSERT INTO travel_terminals (terminal_id, destination_id, name, type) VALUES
(103, 2, 'Bhuntar Airport', 'airport'),
(104, 2, 'Joginder Nagar Station', 'station');

INSERT INTO terminal_zones (terminal_id, zone_id, priority) VALUES
(103, 5, 1), (103, 8, 2),
(104, 5, 1), (104, 6, 2);

INSERT INTO attractions
(attraction_id, destination_id, zone_id, name, rating,
 avg_time_minutes, is_mustdo, is_strenuous, food_availability, recommended_time)
VALUES
-- Zone 5: Manali Town
(16, 2, 5, 'Hadimba Devi Temple',     4.4, 90,  TRUE,  FALSE, 'nearby',      'morning'),
(17, 2, 5, 'Mall Road Manali',        4.1, 120, FALSE, FALSE, 'integrated',  'anytime'),
(18, 2, 5, 'Manu Temple',             4.0, 60,  FALSE, FALSE, 'none',        'morning'),
(19, 2, 5, 'Tibetan Monastery',       4.2, 75,  FALSE, FALSE, 'none',        'morning'),
-- Zone 6: Solang Valley
(20, 2, 6, 'Solang Valley Snow Point',4.6, 180, TRUE,  FALSE, 'nearby',      'morning'),
(21, 2, 6, 'Zorbing Solang',          4.3, 90,  FALSE, TRUE,  'none',        'anytime'),
(22, 2, 6, 'Paragliding Solang',      4.5, 120, FALSE, TRUE,  'none',        'morning'),
(23, 2, 6, 'Atal Tunnel Entrance',    4.1, 60,  FALSE, FALSE, 'none',        'anytime'),
-- Zone 7: Rohtang Pass
(24, 2, 7, 'Rohtang Pass',            4.7, 240, TRUE,  FALSE, 'nearby',      'morning'),
(25, 2, 7, 'Beas Kund Trek',          4.4, 300, FALSE, TRUE,  'none',        'morning'),
(26, 2, 7, 'Rahala Falls',            4.2, 90,  FALSE, FALSE, 'none',        'morning'),
-- Zone 8: Old Manali & Vashisht
(27, 2, 8, 'Vashisht Hot Springs',    4.3, 120, FALSE, FALSE, 'nearby',      'anytime'),
(28, 2, 8, 'Old Manali Cafes Walk',   4.4, 150, FALSE, FALSE, 'integrated',  'anytime'),
(29, 2, 8, 'Beas River Walk',         4.1, 90,  FALSE, FALSE, 'none',        'evening'),
(30, 2, 8, 'Naggar Castle',           4.2, 120, FALSE, FALSE, 'nearby',      'anytime'),
(31, 2, 8, 'Jana Waterfall',          4.0, 120, FALSE, TRUE,  'none',        'morning');

INSERT INTO attraction_tags (attraction_id, tag) VALUES
(16, 'spiritual'), (16, 'cultural'), (16, 'historical'),
(17, 'urban'), (17, 'foodie'), (17, 'relaxed'),
(18, 'spiritual'), (18, 'historical'),
(19, 'spiritual'), (19, 'cultural'),
(20, 'adventure'), (20, 'scenic'), (20, 'nature'),
(21, 'adventure'), (21, 'offbeat'),
(22, 'adventure'), (22, 'scenic'),
(23, 'scenic'), (23, 'offbeat'),
(24, 'scenic'), (24, 'adventure'), (24, 'nature'),
(25, 'adventure'), (25, 'nature'), (25, 'offbeat'),
(26, 'scenic'), (26, 'nature'),
(27, 'relaxed'), (27, 'offbeat'),
(28, 'foodie'), (28, 'relaxed'), (28, 'urban'),
(29, 'scenic'), (29, 'nature'), (29, 'relaxed'),
(30, 'historical'), (30, 'cultural'), (30, 'scenic'),
(31, 'nature'), (31, 'adventure');

INSERT INTO accommodations
(accommodation_id, destination_id, zone_id, name, type, max_capacity)
VALUES
(7,  2, 5, 'The Himalayan',              '5-star', 100),
(8,  2, 5, 'Manu Allaya Resort & Spa',   '4-star', 60),
(9,  2, 5, 'Hotel Rohtang Annexe',       '3-star', 40),
(10, 2, 8, 'Zostel Manali',             'budget',  30),
(11, 2, 6, 'Snow Valley Resorts',        '4-star', 50);

INSERT INTO travel_routes
(route_id, origin_city, destination_id, travel_mode, avg_hours) VALUES
(5,  'Delhi',      2, 'car',    14.0),
(6,  'Delhi',      2, 'train',  16.0),
(7,  'Chandigarh', 2, 'car',     7.0),
(8,  'Chandigarh', 2, 'train',   8.0),
(9,  'Delhi',      2, 'flight',  5.0);


-- ============================================================
-- DESTINATION 3: KONKAN COAST, MAHARASHTRA
-- 4 zones, 15 attractions
-- ============================================================

INSERT INTO destinations (destination_id, name, state, country)
VALUES (3, 'Konkan Coast', 'Maharashtra', 'India');

INSERT INTO zones (zone_id, destination_id, name) VALUES
(9,  3, 'Tarkarli & Malvan'),   -- snorkeling, scuba, beach
(10, 3, 'Sindhudurg Fort Area'),-- fort, beach, heritage
(11, 3, 'Ganpatipule'),         -- temple, beach, peaceful
(12, 3, 'Ratnagiri Town');      -- Alphonso farms, lighthouse

UPDATE destinations SET central_zone_id = 9 WHERE destination_id = 3;

INSERT INTO zone_nearby (zone_id, nearby_zone_id) VALUES
(9,  10), (9,  11),
(10, 9),  (10, 11),
(11, 9),  (11, 10), (11, 12),
(12, 11);

INSERT INTO travel_terminals (terminal_id, destination_id, name, type) VALUES
(105, 3, 'Ratnagiri Railway Station', 'station'),
(106, 3, 'Sindhudurg Airport',        'airport');

INSERT INTO terminal_zones (terminal_id, zone_id, priority) VALUES
(105, 12, 1), (105, 11, 2),
(106, 9,  1), (106, 10, 2);

INSERT INTO attractions
(attraction_id, destination_id, zone_id, name, rating,
 avg_time_minutes, is_mustdo, is_strenuous, food_availability, recommended_time)
VALUES
-- Zone 9: Tarkarli
(32, 3, 9,  'Tarkarli Beach',           4.5, 150, TRUE,  FALSE, 'nearby',     'anytime'),
(33, 3, 9,  'Scuba Diving Tarkarli',    4.6, 180, TRUE,  FALSE, 'none',       'morning'),
(34, 3, 9,  'Snorkeling Malvan',        4.4, 120, FALSE, FALSE, 'none',       'morning'),
(35, 3, 9,  'Backwater Kayaking',       4.3, 120, FALSE, FALSE, 'none',       'anytime'),
-- Zone 10: Sindhudurg Fort
(36, 3, 10, 'Sindhudurg Fort',          4.6, 150, TRUE,  FALSE, 'nearby',     'morning'),
(37, 3, 10, 'Tsunami Island',           4.2, 120, FALSE, FALSE, 'none',       'anytime'),
(38, 3, 10, 'Chivla Beach',             4.1, 90,  FALSE, FALSE, 'nearby',     'anytime'),
(39, 3, 10, 'Rock Garden Malvan',       3.9, 60,  FALSE, FALSE, 'none',       'anytime'),
-- Zone 11: Ganpatipule
(40, 3, 11, 'Ganpatipule Temple Beach', 4.5, 120, TRUE,  FALSE, 'nearby',     'morning'),
(41, 3, 11, 'Velneshwar Temple',        4.1, 90,  FALSE, FALSE, 'none',       'morning'),
(42, 3, 11, 'Guhagar Beach',            4.3, 120, FALSE, FALSE, 'none',       'anytime'),
-- Zone 12: Ratnagiri
(43, 3, 12, 'Alphonso Mango Farm Visit',4.3, 120, FALSE, FALSE, 'integrated', 'morning'),
(44, 3, 12, 'Ratnagiri Lighthouse',     4.0, 60,  FALSE, FALSE, 'none',       'evening'),
(45, 3, 12, 'Ratnadurg Fort',           4.2, 120, FALSE, FALSE, 'nearby',     'anytime'),
(46, 3, 12, 'Bhatye Beach',             4.1, 90,  FALSE, FALSE, 'none',       'evening');

INSERT INTO attraction_tags (attraction_id, tag) VALUES
(32, 'scenic'), (32, 'relaxed'), (32, 'nature'),
(33, 'adventure'), (33, 'offbeat'), (33, 'nature'),
(34, 'adventure'), (34, 'nature'),
(35, 'adventure'), (35, 'scenic'), (35, 'nature'),
(36, 'historical'), (36, 'cultural'), (36, 'scenic'),
(37, 'scenic'), (37, 'offbeat'), (37, 'nature'),
(38, 'relaxed'), (38, 'scenic'),
(39, 'offbeat'), (39, 'relaxed'),
(40, 'spiritual'), (40, 'scenic'), (40, 'relaxed'),
(41, 'spiritual'), (41, 'cultural'),
(42, 'scenic'), (42, 'relaxed'), (42, 'nature'),
(43, 'foodie'), (43, 'offbeat'), (43, 'nature'),
(44, 'scenic'), (44, 'historical'),
(45, 'historical'), (45, 'cultural'), (45, 'scenic'),
(46, 'scenic'), (46, 'relaxed');

INSERT INTO accommodations
(accommodation_id, destination_id, zone_id, name, type, max_capacity)
VALUES
(12, 3, 9,  'MTDC Tarkarli Beach Resort', '3-star', 40),
(13, 3, 9,  'Chondike Beach Resort',       '4-star', 30),
(14, 3, 10, 'Hotel Sunderban',             '3-star', 25),
(15, 3, 11, 'MTDC Ganpatipule Resort',     '3-star', 50),
(16, 3, 12, 'Hotel Nandadeep',             'budget', 20);

INSERT INTO travel_routes
(route_id, origin_city, destination_id, travel_mode, avg_hours) VALUES
(10, 'Pune',   3, 'car',   5.0),
(11, 'Mumbai', 3, 'car',   6.5),
(12, 'Pune',   3, 'train', 7.0),
(13, 'Mumbai', 3, 'train', 8.0);


-- ============================================================
-- DESTINATION 4: ASSAM (KAZIRANGA + BRAHMAPUTRA REGION)
-- 4 zones, 15 attractions
-- ============================================================

INSERT INTO destinations (destination_id, name, state, country)
VALUES (4, 'Assam', 'Assam', 'India');

INSERT INTO zones (zone_id, destination_id, name) VALUES
(13, 4, 'Kaziranga National Park'),  -- rhino safari, elephant safari
(14, 4, 'Majuli Island'),            -- world largest river island, satras
(15, 4, 'Guwahati City'),            -- kamakhya, brahmaputra cruise
(16, 4, 'Jorhat & Tea Gardens');     -- tea estates, gibbon sanctuary

UPDATE destinations SET central_zone_id = 15 WHERE destination_id = 4;

INSERT INTO zone_nearby (zone_id, nearby_zone_id) VALUES
(13, 16), (13, 15),
(14, 15),
(15, 13), (15, 14), (15, 16),
(16, 13), (16, 15);

INSERT INTO travel_terminals (terminal_id, destination_id, name, type) VALUES
(107, 4, 'Lokpriya Gopinath Bordoloi International Airport', 'airport'),
(108, 4, 'Guwahati Railway Station', 'station');

INSERT INTO terminal_zones (terminal_id, zone_id, priority) VALUES
(107, 15, 1), (107, 13, 2),
(108, 15, 1), (108, 16, 2);

INSERT INTO attractions
(attraction_id, destination_id, zone_id, name, rating,
 avg_time_minutes, is_mustdo, is_strenuous, food_availability, recommended_time)
VALUES
-- Zone 13: Kaziranga
(47, 4, 13, 'Kaziranga Jeep Safari',      4.8, 240, TRUE,  FALSE, 'nearby',     'morning'),
(48, 4, 13, 'Elephant Safari Kaziranga',  4.6, 180, TRUE,  FALSE, 'none',       'morning'),
(49, 4, 13, 'Kaziranga Orchid Park',      4.0, 90,  FALSE, FALSE, 'nearby',     'anytime'),
(50, 4, 13, 'Mihimukh Watchtower',        4.2, 90,  FALSE, FALSE, 'none',       'morning'),
-- Zone 14: Majuli Island
(51, 4, 14, 'Majuli Island Ferry & Walk', 4.5, 300, TRUE,  FALSE, 'integrated', 'morning'),
(52, 4, 14, 'Vaishnavite Satras Visit',   4.4, 150, FALSE, FALSE, 'none',       'morning'),
(53, 4, 14, 'Majuli Mask Making Village', 4.3, 120, FALSE, FALSE, 'none',       'anytime'),
(54, 4, 14, 'Kamalabari Satra',           4.2, 90,  FALSE, FALSE, 'none',       'morning'),
-- Zone 15: Guwahati
(55, 4, 15, 'Kamakhya Temple',            4.5, 120, TRUE,  FALSE, 'nearby',     'morning'),
(56, 4, 15, 'Brahmaputra River Cruise',   4.4, 120, FALSE, FALSE, 'nearby',     'evening'),
(57, 4, 15, 'Umananda Island Temple',     4.2, 150, FALSE, FALSE, 'none',       'morning'),
(58, 4, 15, 'Assam State Museum',         3.9, 120, FALSE, FALSE, 'none',       'anytime'),
-- Zone 16: Jorhat & Tea Gardens
(59, 4, 16, 'Jorhat Tea Estate Tour',     4.5, 180, TRUE,  FALSE, 'integrated', 'morning'),
(60, 4, 16, 'Gibbon Wildlife Sanctuary',  4.3, 150, FALSE, TRUE,  'none',       'morning'),
(61, 4, 16, 'Tocklai Tea Research Center',4.1, 90,  FALSE, FALSE, 'none',       'anytime');

INSERT INTO attraction_tags (attraction_id, tag) VALUES
(47, 'adventure'), (47, 'nature'), (47, 'offbeat'),
(48, 'adventure'), (48, 'nature'),
(49, 'nature'), (49, 'relaxed'),
(50, 'nature'), (50, 'scenic'),
(51, 'scenic'), (51, 'nature'), (51, 'offbeat'),
(52, 'cultural'), (52, 'spiritual'), (52, 'historical'),
(53, 'cultural'), (53, 'offbeat'),
(54, 'spiritual'), (54, 'cultural'),
(55, 'spiritual'), (55, 'cultural'), (55, 'historical'),
(56, 'scenic'), (56, 'relaxed'),
(57, 'spiritual'), (57, 'scenic'),
(58, 'cultural'), (58, 'historical'),
(59, 'nature'), (59, 'foodie'), (59, 'offbeat'),
(60, 'nature'), (60, 'adventure'),
(61, 'nature'), (61, 'offbeat');

INSERT INTO accommodations
(accommodation_id, destination_id, zone_id, name, type, max_capacity)
VALUES
(17, 4, 13, 'Iora The Retreat Kaziranga', '5-star', 40),
(18, 4, 13, 'Wild Mahseer Heritage Camp',  '4-star', 30),
(19, 4, 15, 'Radisson Blu Guwahati',       '5-star', 120),
(20, 4, 15, 'Hotel Rajmahal Guwahati',     '3-star', 50),
(21, 4, 16, 'Thengal Manor Jorhat',        '4-star', 20);

INSERT INTO travel_routes
(route_id, origin_city, destination_id, travel_mode, avg_hours) VALUES
(14, 'Delhi',   4, 'flight', 2.5),
(15, 'Kolkata', 4, 'flight', 1.0),
(16, 'Delhi',   4, 'train',  20.0),
(17, 'Kolkata', 4, 'train',  12.0);


-- ============================================================
-- DESTINATION 5: KERALA (BACKWATERS + MUNNAR REGION)
-- 4 zones, 16 attractions
-- ============================================================

INSERT INTO destinations (destination_id, name, state, country)
VALUES (5, 'Kerala', 'Kerala', 'India');

INSERT INTO zones (zone_id, destination_id, name) VALUES
(17, 5, 'Alleppey Backwaters'),  -- houseboat, canoe, backwaters
(18, 5, 'Munnar Hill Station'),  -- tea gardens, eravikulam, misty hills
(19, 5, 'Thekkady & Periyar'),   -- wildlife, spice plantation, boat ride
(20, 5, 'Kovalam & Varkala');    -- beach, cliff, lighthouse

UPDATE destinations SET central_zone_id = 17 WHERE destination_id = 5;

INSERT INTO zone_nearby (zone_id, nearby_zone_id) VALUES
(17, 19),
(18, 19),
(19, 17), (19, 18), (19, 20),
(20, 19);

INSERT INTO travel_terminals (terminal_id, destination_id, name, type) VALUES
(109, 5, 'Cochin International Airport',      'airport'),
(110, 5, 'Thiruvananthapuram Airport',        'airport'),
(111, 5, 'Ernakulam Junction Railway Station','station');

INSERT INTO terminal_zones (terminal_id, zone_id, priority) VALUES
(109, 17, 1), (109, 18, 2),
(110, 20, 1), (110, 19, 2),
(111, 17, 1), (111, 19, 2);

INSERT INTO attractions
(attraction_id, destination_id, zone_id, name, rating,
 avg_time_minutes, is_mustdo, is_strenuous, food_availability, recommended_time)
VALUES
-- Zone 17: Alleppey
(62, 5, 17, 'Alleppey Houseboat Stay',     4.8, 480, TRUE,  FALSE, 'integrated', 'anytime'),
(63, 5, 17, 'Alleppey Beach',              4.2, 120, FALSE, FALSE, 'nearby',     'evening'),
(64, 5, 17, 'Punnamada Lake Canoe',        4.4, 150, FALSE, FALSE, 'none',       'morning'),
(65, 5, 17, 'Marari Beach',                4.3, 120, FALSE, FALSE, 'nearby',     'anytime'),
-- Zone 18: Munnar
(66, 5, 18, 'Eravikulam National Park',    4.6, 180, TRUE,  FALSE, 'nearby',     'morning'),
(67, 5, 18, 'Munnar Tea Plantation Walk',  4.5, 150, FALSE, FALSE, 'integrated', 'morning'),
(68, 5, 18, 'Top Station Munnar',          4.4, 120, FALSE, FALSE, 'none',       'morning'),
(69, 5, 18, 'Mattupetty Dam & Lake',       4.2, 120, FALSE, FALSE, 'nearby',     'anytime'),
(70, 5, 18, 'Anamudi Peak View',           4.3, 180, FALSE, TRUE,  'none',       'morning'),
-- Zone 19: Thekkady
(71, 5, 19, 'Periyar Wildlife Boat Ride',  4.5, 180, TRUE,  FALSE, 'nearby',     'morning'),
(72, 5, 19, 'Spice Plantation Tour',       4.4, 150, FALSE, FALSE, 'integrated', 'anytime'),
(73, 5, 19, 'Elephant Junction Thekkady',  4.3, 150, FALSE, FALSE, 'none',       'morning'),
(74, 5, 19, 'Bamboo Rafting Periyar',      4.2, 180, FALSE, TRUE,  'none',       'morning'),
-- Zone 20: Kovalam & Varkala
(75, 5, 20, 'Varkala Cliff Beach',         4.6, 180, TRUE,  FALSE, 'integrated', 'anytime'),
(76, 5, 20, 'Kovalam Lighthouse Beach',    4.4, 150, FALSE, FALSE, 'nearby',     'evening'),
(77, 5, 20, 'Padmanabhaswamy Temple',      4.5, 120, FALSE, FALSE, 'none',       'morning');

INSERT INTO attraction_tags (attraction_id, tag) VALUES
(62, 'scenic'), (62, 'relaxed'), (62, 'nature'), (62, 'offbeat'),
(63, 'scenic'), (63, 'relaxed'),
(64, 'scenic'), (64, 'nature'), (64, 'relaxed'),
(65, 'scenic'), (65, 'relaxed'),
(66, 'nature'), (66, 'adventure'), (66, 'scenic'),
(67, 'nature'), (67, 'scenic'), (67, 'relaxed'),
(68, 'scenic'), (68, 'nature'),
(69, 'scenic'), (69, 'relaxed'), (69, 'nature'),
(70, 'adventure'), (70, 'nature'), (70, 'scenic'),
(71, 'nature'), (71, 'adventure'), (71, 'scenic'),
(72, 'nature'), (72, 'foodie'), (72, 'offbeat'),
(73, 'nature'), (73, 'offbeat'),
(74, 'adventure'), (74, 'nature'), (74, 'offbeat'),
(75, 'scenic'), (75, 'relaxed'), (75, 'foodie'),
(76, 'scenic'), (76, 'relaxed'),
(77, 'spiritual'), (77, 'cultural'), (77, 'historical');

INSERT INTO accommodations
(accommodation_id, destination_id, zone_id, name, type, max_capacity)
VALUES
(22, 5, 17, 'Kumarakom Lake Resort',     '5-star', 80),
(23, 5, 17, 'Emerald Isle Heritage Villa','4-star', 20),
(24, 5, 18, 'Windermere Estate Munnar',  '4-star', 30),
(25, 5, 18, 'Tea Valley Resort Munnar',  '3-star', 40),
(26, 5, 19, 'Spice Village Thekkady',    '5-star', 50),
(27, 5, 20, 'Uday Samudra Kovalam',      '5-star', 100),
(28, 5, 20, 'Zostel Varkala',           'budget',  30);

INSERT INTO travel_routes
(route_id, origin_city, destination_id, travel_mode, avg_hours) VALUES
(18, 'Mumbai',    5, 'flight', 2.0),
(19, 'Delhi',     5, 'flight', 3.0),
(20, 'Bangalore', 5, 'flight', 1.0),
(21, 'Mumbai',    5, 'train',  24.0),
(22, 'Bangalore', 5, 'train',  12.0);
