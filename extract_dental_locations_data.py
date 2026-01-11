#!/usr/bin/env python3
"""Extract Delta Dental locations data from JSON and format for HTML embedding."""

import json

# Load the Delta Dental locations data
with open('ucship_delta_dental_locations_2026-01-10.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Transform locations to match the format used in Primary_Care.html
locations = []

for loc in data['locations']:
    # Format location info
    location = {
        'address': loc.get('address') or '',
        'city': '',
        'state': '',
        'zip': '',
        'full_address': loc.get('address') or '',
        'phone': loc.get('phone') or None,
        'county': None,
        'location_name': loc.get('location_name') or ''
    }
    
    # Format people as providers
    providers = []
    for person in loc.get('people', []):
        provider = {
            'name': person.get('name') or 'Dental Provider',
            'specialty': 'Dental',
            'phone': person.get('phone') or None,
            'website': None
        }
        providers.append(provider)
    
    locations.append({
        'location': location,
        'provider_count': len(providers),
        'providers': providers
    })

# Output as JavaScript variable
js_output = 'const locationsData = ' + json.dumps(locations, indent=2, ensure_ascii=False) + ';'
print(js_output)
