# Travel Planner Backend - Groups C & D

This package contains the implementation of Groups C and D for your travel planner backend system.

## Files Created

### Group C: Day Builder Module
1. **day_builder.py** - Implementation of all day building functions:
   - `get_fixed_blocks()` - Places unmovable blocks (sleep, meals, travel)
   - `find_food_for_meals()` - Attaches food attractions to meal slots
   - `resolve_conflict()` - Handles overlapping time blocks
   - `anchor_star_attraction()` - Places the highest-scored attraction
   - `merge_empty_slots()` - Finds empty time gaps in schedule
   - `fill_remaining_slots()` - Fills gaps with attractions or rest

2. **test_day_builder.py** - Unit tests for Group C (17 tests)
   - Section 1: 6 tests for `resolve_conflict`
   - Section 2: 4 tests for `merge_empty_slots`
   - Section 3: 3 tests for `find_food_for_meals`
   - Section 4: 4 tests for `fill_remaining_slots`

### Group D: Assembly Module
3. **assembly.py** - Implementation of orchestration functions:
   - `calculate_available_hours()` - Computes usable trip hours
   - `select_accommodation()` - Chooses accommodation
   - `run_scoring_pipeline()` - Runs Group A functions
   - `run_zone_pipeline()` - Runs Group B functions
   - `run_day_builder()` - Runs Group C for all days
   - `build_itinerary()` - Master function that runs everything

4. **test_assembly.py** - Integration tests for Group D (5 tests)
   - Requires MySQL database with sample data

### Integration Test Scripts
5. **test_integration_cd.py** - Tests Group C with real data from A & B
6. **test_integration_abcd.py** - Full end-to-end pipeline test

## Prerequisites

Before running any tests, ensure you have:

1. **MySQL database** running with the `travel_planner` database
2. **Sample data** loaded (from schema_and_sample_data.md)
3. **Groups A & B** already implemented:
   - `scoring.py` (Group A)
   - `zone_management.py` (Group B)
4. **Python packages**:
   ```bash
   pip install mysql-connector-python pytest
   ```

## Project Structure

Your travel_planner folder should look like this:

```
travel_planner/
├── scoring.py               # Group A (already exists)
├── zone_management.py       # Group B (already exists)
├── day_builder.py           # Group C (NEW)
├── assembly.py              # Group D (NEW)
├── test_day_builder.py      # Group C tests (NEW)
├── test_assembly.py         # Group D tests (NEW)
├── test_integration_cd.py   # Integration test (NEW)
└── test_integration_abcd.py # Full pipeline test (NEW)
```

## How to Run Tests

### Step 1: Update Database Password

In ALL test files, change the database password:
```python
password="yourpassword",  # Change this to your actual MySQL password
```

Files to update:
- test_assembly.py
- test_integration_cd.py
- test_integration_abcd.py

### Step 2: Run Unit Tests (Group C)

Test pure functions without database:
```bash
pytest test_day_builder.py -v
```

Expected: All 17 tests should pass.

### Step 3: Run Integration Tests (Group D)

Test with database connection:
```bash
pytest test_assembly.py -v
```

Expected: All 5 tests should pass.

### Step 4: Run Group C Integration

Test day builder with real data:
```bash
python test_integration_cd.py
```

This will:
- Run Groups A and B to generate inputs
- Test each Group C function step-by-step
- Show detailed output for Day 1 schedule

### Step 5: Run Full Pipeline Test

Test the complete system end-to-end:
```bash
python test_integration_abcd.py
```

This will:
- Build a complete 3-day itinerary
- Write to database
- Display the full itinerary
- Verify all data was written correctly

## Expected Output

When `test_integration_abcd.py` passes, you should see:

```
===========================================================
PIPELINE STATUS: ALL CHECKS PASSED
Your backend is complete.
===========================================================
```

## Function Call Flow

Here's how the complete pipeline works:

```
build_itinerary(trip_id, db)
│
├── run_scoring_pipeline()
│   ├── calculate_available_hours()
│   ├── score_all_attractions()      [Group A]
│   └── build_shortlist()             [Group A]
│
├── run_zone_pipeline()
│   ├── calculate_zone_stats()        [Group B]
│   ├── drop_weak_zones()             [Group B]
│   ├── distribute_zones_to_days()    [Group B]
│   ├── assign_anchor_zones()         [Group B]
│   └── order_middle_zones()          [Group B]
│
├── run_day_builder() — for each day:
│   ├── get_fixed_blocks()            [Group C]
│   ├── find_food_for_meals()         [Group C]
│   ├── anchor_star_attraction()      [Group C]
│   ├── merge_empty_slots()           [Group C]
│   └── fill_remaining_slots()        [Group C]
│
├── select_accommodation()
│
└── Write to DB:
    ├── itinerary_days
    ├── itinerary_items
    └── accommodation_pick
```

## Key Data Structures

### Block Dict Format
Every time block uses this exact structure:
```python
{
    "attraction_id": int or None,
    "slot_type": str,      # 'attraction', 'meal', 'rest', 'travel', 'sleep'
    "meal_type": str or None,
    "start_time": int,     # minutes from midnight
    "end_time": int,
    "notes": str or None
}
```

### Time Format
All times are integers representing minutes from midnight:
- 0 = 12:00 AM
- 360 = 6:00 AM
- 720 = 12:00 PM
- 1320 = 10:00 PM

## Troubleshooting

### If tests fail:

1. **Database connection errors**:
   - Check MySQL is running
   - Verify database name is "travel_planner"
   - Update password in test files

2. **Import errors**:
   - Ensure all files are in the same directory
   - Check Groups A & B files exist

3. **Data errors**:
   - Verify sample data is loaded
   - Check trip_id=1 exists in trips table

4. **Empty shortlist**:
   - Check attractions table has data
   - Verify destination_id=1 exists

## Next Steps

Once all tests pass:

1. ✅ Backend is complete
2. 🔄 Move to frontend development
3. 📝 Create REST API endpoints
4. 🎨 Build user interface

## Questions?

If you encounter issues:
1. Check the test output carefully
2. Verify database has sample data
3. Ensure all prerequisite files exist
4. Run tests in order (unit → integration → full)

---

**Note**: These implementations follow the exact specifications from the prompt documents. All function signatures, data structures, and logic match the requirements precisely.
