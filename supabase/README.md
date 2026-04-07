# Curiosity Cat — Supabase Setup

## Prerequisites
- Supabase account (free tier works)
- Supabase CLI (`brew install supabase/tap/supabase`)

## Setup
1. Create a new Supabase project at https://supabase.com/dashboard
2. Run the migration:
   ```
   supabase db push --db-url postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
   ```
   Or paste `supabase/migrations/001_danger_map.sql` into the SQL editor in the dashboard.

3. Copy your project URL and anon key to your client config.

## Schema
- `close_calls` table — stores anonymised close call reports
- `danger_map_summary` view — aggregated data for dashboard
- Row Level Security: public read, authenticated write
