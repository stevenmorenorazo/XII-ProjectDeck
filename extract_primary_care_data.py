#!/usr/bin/env python3
"""Extract primary care providers from grouped JSON and format for HTML embedding."""

import json

# Load the grouped data
with open('ucship_anthem_providers_by_address_base.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filter for primary care providers only
primary_care_locations = []
for loc in data['locations']:
    primary_care_providers = [p for p in loc['providers'] if p.get('original_category') == 'primary_care']
    if primary_care_providers:
        primary_care_locations.append({
            'location': loc['location'],
            'provider_count': len(primary_care_providers),
            'providers': primary_care_providers
        })

# Output as JavaScript variable
js_output = 'const locationsData = ' + json.dumps(primary_care_locations, indent=2, ensure_ascii=False) + ';'
print(js_output)
