#!/usr/bin/env python3
"""Extract behavioral health providers from grouped JSON and format for HTML embedding."""

import json

# Load the grouped data
with open('behavioral_health_grouped_by_address.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get all locations (all are behavioral health)
behavioral_health_locations = []
for loc in data['locations']:
    behavioral_health_locations.append({
        'location': loc['location'],
        'provider_count': loc['provider_count'],
        'providers': loc['providers']
    })

# Output as JavaScript variable
js_output = 'const locationsData = ' + json.dumps(behavioral_health_locations, indent=2, ensure_ascii=False) + ';'
print(js_output)
