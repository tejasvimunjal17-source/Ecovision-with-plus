-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 007: seed reference data
-- Depends on: 001_init_schema.sql (categories, recycling_centres)
--
-- Migrates ONLY the two fixed reference-data seeds that
-- database/db.py::init_db() used to (re-)apply on every app startup:
--   - _seed_categories()          -> 9 waste categories
--   - _seed_recycling_centres()   -> 4 MCG recycling centres
-- Data values below are copied verbatim from the original
-- database/db.py so nothing about the seeded content changes.
--
-- _seed_admin() is DELIBERATELY NOT reproduced here. See
-- supabase/README.md "Admin account seeding" and scripts/create_admin.py
-- for why a default admin password should not live in a checked-in SQL
-- migration for a real cloud database, and for the safe alternative.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Categories — exact translation of the original INSERT OR IGNORE loop.
-- categories.name is UNIQUE (see 001_init_schema.sql), so ON CONFLICT
-- (name) DO NOTHING is the direct Postgres equivalent of SQLite's
-- "INSERT OR IGNORE ... (name, ...)" — re-running this migration is safe.
-- ----------------------------------------------------------------------------
insert into categories (name, description, icon, disposal_guide) values
    ('Plastic', 'Plastic bottles, bags, wrappers, containers', '🧴',
     'Rinse and place in the dry-waste bin; drop bulk plastic at an authorized recycler.'),
    ('Organic', 'Food scraps, garden waste, biodegradable matter', '🍂',
     'Compost at home or place in the wet-waste (green) bin for municipal composting.'),
    ('Paper', 'Newspaper, cardboard, cartons, office paper', '📄',
     'Flatten and keep dry; place in the dry-waste bin or sell to a kabadiwala.'),
    ('Glass', 'Bottles, jars, broken glassware', '🍾',
     'Wrap broken pieces safely, place in dry-waste bin marked ''glass''.'),
    ('Metal', 'Cans, foil, scrap metal, utensils', '🔩',
     'Place in dry-waste bin; scrap metal can be sold to authorized scrap dealers.'),
    ('Mixed', 'Non-segregated general waste', '🗑️',
     'Please segregate at source; mixed waste delays processing and recycling.'),
    ('E-Waste', 'Batteries, electronics, wires, appliances', '🔋',
     'Never mix with household waste — drop at an authorized MCG e-waste collection centre.'),
    ('Biomedical', 'Medical/clinical waste, sharps, PPE', '🩺',
     'Requires special handling — contact MCG health department or an authorized biomedical waste handler.'),
    ('Construction', 'Debris, rubble, bricks, concrete', '🧱',
     'Book a municipal C&D waste pickup; do not dump on roads or drains.')
on conflict (name) do nothing;

-- ----------------------------------------------------------------------------
-- Recycling centres — the original _seed_recycling_centres() guarded on
-- "table is currently empty" (COUNT(*) == 0), NOT a per-row unique key
-- (recycling_centres.name has no UNIQUE constraint — preserved as-is,
-- see 001_init_schema.sql). This INSERT ... SELECT ... WHERE NOT EXISTS
-- faithfully reproduces that exact "only if the table has never been
-- seeded" guard, rather than introducing a new uniqueness rule that
-- wasn't in the original schema.
-- ----------------------------------------------------------------------------
insert into recycling_centres (name, type, address, ward, latitude, longitude, contact, materials_accepted)
select * from (values
    ('MCG Material Recovery Facility - Sector 39', 'Dry Waste MRF', 'Sector 39, Gurugram',
     'Sector 39', 28.4501::double precision, 77.0424::double precision, '+91-124-2222222', 'Plastic,Paper,Metal,Glass'),
    ('MCG E-Waste Collection Centre - Sector 14', 'E-Waste', 'Sector 14, Gurugram',
     'Sector 14', 28.4699::double precision, 77.0266::double precision, '+91-124-2333333', 'E-Waste,Batteries'),
    ('Composting Unit - Sector 52', 'Organic/Composting', 'Sector 52, Gurugram',
     'Sector 52', 28.4177::double precision, 77.0729::double precision, '+91-124-2444444', 'Organic'),
    ('Scrap & Metal Recyclers - Udyog Vihar', 'Scrap/Metal', 'Udyog Vihar Phase 3, Gurugram',
     'Udyog Vihar', 28.5017::double precision, 77.0881::double precision, '+91-124-2555555', 'Metal,Glass')
) as seed_data(name, type, address, ward, latitude, longitude, contact, materials_accepted)
where not exists (select 1 from recycling_centres);
