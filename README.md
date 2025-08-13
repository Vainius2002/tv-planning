# TV Campaign Planner

A Flask-based web application for planning and managing TV advertising campaigns with TRP (Target Rating Point) pricing, campaign management, and reporting features.

## Features

- **TRP Rate Management**: Set and manage pricing rates for different TV channels and target demographics
- **Campaign Creation**: Organize advertising campaigns with multiple waves (time periods)
- **Cost Calculation**: Automatic cost calculation based on TRP rates and audience reach
- **Discount System**: Apply client and agency discounts at campaign or wave level
- **Reporting**: Export campaigns as Excel reports for clients or CSV orders for agencies
- **TVC Management**: Track different TV commercials within campaigns

## Installation

1. Clone the repository and navigate to the project directory:
```bash
cd ~/py_projects/blueprint
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python run.py
```

The application will be available at: http://localhost:5000/tv-planner/

## Application Structure

### Core Concepts

1. **TRP Rates**: Base pricing for TV advertising
   - Owner (TV channel/network)
   - Target Group (demographic, e.g., "A25-55", "A18-49")
   - Price per second in EUR
   - Primary/Secondary channel splits

2. **Pricing Lists**: Collections of TRP rates for a specific period

3. **Campaigns**: Main container for TV advertising plans
   - Uses a pricing list
   - Has start and end dates
   - Contains multiple waves

4. **Waves**: Time periods within a campaign (e.g., "Week 1", "Launch Week")
   - Has start and end dates
   - Contains wave items (actual TV spots)

5. **Wave Items**: Individual TV spot purchases
   - Channel owner
   - Target group
   - TRP amount (audience reach)
   - Calculated cost

## API Usage Examples

### 1. Create TRP Rates (Base Pricing)

```bash
curl -X POST http://localhost:5000/tv-planner/trp \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "Discovery Channel",
    "target_group": "Adults 25-54",
    "primary_label": "Discovery",
    "secondary_label": "Investigation Discovery",
    "price_per_sec_eur": 200.50,
    "share_primary": 75,
    "share_secondary": 25,
    "prime_share_primary": 80,
    "prime_share_secondary": 20
  }'
```

### 2. Create a Campaign

```bash
curl -X POST http://localhost:5000/tv-planner/campaigns-api \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Summer Product Launch 2025",
    "pricing_list_id": 1,
    "start_date": "2025-06-01",
    "end_date": "2025-06-30"
  }'
```

### 3. Add a Wave to Campaign

```bash
curl -X POST http://localhost:5000/tv-planner/campaigns/{campaign_id}/waves \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Launch Week",
    "start_date": "2025-06-01",
    "end_date": "2025-06-07"
  }'
```

### 4. Add TV Spots (Wave Items)

```bash
curl -X POST http://localhost:5000/tv-planner/waves/{wave_id}/items \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "1",
    "target_group": "A25–55",
    "trps": 100
  }'
```

Note: TRPs = Target Rating Points. 100 TRPs means reaching 100% of your target audience once.

### 5. Apply Discounts

Campaign-level discount:
```bash
curl -X POST http://localhost:5000/tv-planner/campaigns/{campaign_id}/discounts \
  -H "Content-Type: application/json" \
  -d '{
    "discount_type": "client",
    "discount_percentage": 15
  }'
```

### 6. Export Reports

Excel report for clients:
```bash
curl http://localhost:5000/tv-planner/campaigns/{campaign_id}/export/client-excel -o tv_plan.xlsx
```

CSV order for agencies:
```bash
curl http://localhost:5000/tv-planner/campaigns/{campaign_id}/export/agency-csv -o tv_order.csv
```

## Web Interface

Access the web interface at: http://localhost:5000/tv-planner/

Available pages:
- `/tv-planner/` - Dashboard
- `/tv-planner/rates` - TRP rates administration
- `/tv-planner/campaigns` - Campaign management
- `/tv-planner/input` - Contact input form

## Complete Workflow Example

```bash
# 1. Check available pricing lists
curl http://localhost:5000/tv-planner/pricing-lists

# 2. Create a campaign
curl -X POST http://localhost:5000/tv-planner/campaigns-api \
  -H "Content-Type: application/json" \
  -d '{"name": "Q2 Campaign", "pricing_list_id": 1, "start_date": "2025-04-01", "end_date": "2025-06-30"}'

# 3. Add waves (time periods)
curl -X POST http://localhost:5000/tv-planner/campaigns/1/waves \
  -H "Content-Type: application/json" \
  -d '{"name": "April Week 1", "start_date": "2025-04-01", "end_date": "2025-04-07"}'

# 4. Check available owners and target groups in pricing list
curl http://localhost:5000/tv-planner/pricing-lists/1/owners
curl "http://localhost:5000/tv-planner/pricing-lists/1/targets?owner=1"

# 5. Add TV spots
curl -X POST http://localhost:5000/tv-planner/waves/1/items \
  -H "Content-Type: application/json" \
  -d '{"owner": "1", "target_group": "A25–55", "trps": 150}'

# 6. Check total cost
curl http://localhost:5000/tv-planner/waves/1/total

# 7. Apply discount
curl -X POST http://localhost:5000/tv-planner/campaigns/1/discounts \
  -H "Content-Type: application/json" \
  -d '{"discount_type": "client", "discount_percentage": 10}'

# 8. Export report
curl http://localhost:5000/tv-planner/campaigns/1/export/client-excel -o campaign_report.xlsx
```

## Database

The application uses SQLite databases:
- `tv-calc.db` - Main database for campaigns, waves, and wave items
- `app.db` - Additional application data

## API Endpoints

### TRP Management
- `GET /tv-planner/trp` - List all TRP rates
- `POST /tv-planner/trp` - Create new TRP rate
- `PATCH /tv-planner/trp/{id}` - Update TRP rate
- `DELETE /tv-planner/trp/{id}` - Delete TRP rate

### Campaign Management
- `GET /tv-planner/campaigns-api` - List campaigns
- `POST /tv-planner/campaigns-api` - Create campaign
- `PATCH /tv-planner/campaigns-api/{id}` - Update campaign
- `DELETE /tv-planner/campaigns-api/{id}` - Delete campaign

### Wave Management
- `GET /tv-planner/campaigns/{id}/waves` - List waves in campaign
- `POST /tv-planner/campaigns/{id}/waves` - Create wave
- `PATCH /tv-planner/waves/{id}` - Update wave
- `DELETE /tv-planner/waves/{id}` - Delete wave

### Wave Items
- `GET /tv-planner/waves/{id}/items` - List items in wave
- `POST /tv-planner/waves/{id}/items` - Add item to wave
- `PATCH /tv-planner/wave-items/{id}` - Update wave item
- `DELETE /tv-planner/wave-items/{id}` - Delete wave item

### Discounts
- `POST /tv-planner/campaigns/{id}/discounts` - Add campaign discount
- `POST /tv-planner/waves/{id}/discounts` - Add wave discount
- `PATCH /tv-planner/discounts/{id}` - Update discount
- `DELETE /tv-planner/discounts/{id}` - Delete discount

### Reporting
- `GET /tv-planner/campaigns/{id}/export/client-excel` - Export Excel report
- `GET /tv-planner/campaigns/{id}/export/agency-csv` - Export CSV order

## Development

To run in debug mode:
```bash
python run.py
```

To run on a different port:
```bash
FLASK_RUN_PORT=5001 flask run
```

## License

[Add your license information here]

## Contact

[Add your contact information here]