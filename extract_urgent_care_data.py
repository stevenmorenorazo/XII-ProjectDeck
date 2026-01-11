#!/usr/bin/env python3
"""Extract urgent care locations data from JSON and format for HTML embedding."""

import json

# Load the urgent care locations data
with open('ucship_anthem_urgent_care_locations_2026-01-10 (1).json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Transform locations to match the format used in Primary_Care.html
locations = []

for loc in data['locations']:
    # Format location info
    location = {
        'address': loc.get('address') or '',
        'city': loc.get('city') or '',
        'state': loc.get('state') or '',
        'zip': loc.get('zip') or '',
        'full_address': f"{loc.get('address', '')}, {loc.get('city', '')}, {loc.get('state', '')} {loc.get('zip', '')}".strip(', '),
        'phone': loc.get('phone') or None,
        'county': loc.get('county') or None,
        'location_name': loc.get('location_name') or '',
        'website': loc.get('website') or None
    }
    
    # For urgent care, we don't have individual providers, so create a single provider entry
    # representing the location itself
    providers = [{
        'name': loc.get('location_name') or 'Urgent Care Facility',
        'specialties': ['Urgent Care'],
        'provider_role': None,
        'gender': None,
        'phone': loc.get('phone') or None
    }]
    
    locations.append({
        'location': location,
        'provider_count': 1,
        'providers': providers
    })

# Output as JavaScript variable
js_output = 'const locationsData = ' + json.dumps(locations, indent=2, ensure_ascii=False) + ';'
print(js_output)
